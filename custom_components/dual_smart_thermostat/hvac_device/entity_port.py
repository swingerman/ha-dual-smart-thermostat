"""How a device role talks to its entity.

The one place that knows what "on" means for an entity and how to command it.
Controllers and devices call these methods; they never read the entity's state
or call its services themselves.

A port keeps a reference to its device and asks it lazily for what it needs
(`entity_id`, `role_modes()`, `climate_target()`, `setpoint_offset()`,
`control_style()`, `fan_speed()`), so nothing is copied at construction.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Mapping
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging
import math
from typing import Any

from homeassistant.components.climate import (
    ATTR_FAN_MODE,
    ATTR_HVAC_MODE,
    ATTR_HVAC_MODES,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_TARGET_TEMP_STEP,
    DOMAIN as CLIMATE_DOMAIN,
    SERVICE_SET_FAN_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, HomeAssistant, State
from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition
from homeassistant.util import dt as dt_util

from ..climate_roles import is_climate_entity
from ..const import ControlStyle

_LOGGER = logging.getLogger(__name__)


def is_unavailable(state: State | None) -> bool:
    """True when an entity has no usable state."""
    return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)


async def _call_service(
    hass: HomeAssistant,
    domain: str,
    service: str,
    data: dict[str, Any],
    context: Context | None,
    error: str,
    *args: Any,
) -> bool:
    """Blocking service call; a failure is logged (`error` + the exception), not raised."""
    try:
        await hass.services.async_call(
            domain, service, data, context=context, blocking=True
        )
    except Exception as e:  # noqa: BLE001
        _LOGGER.error(error + ". Error: %s", *args, e)
        return False
    return True


class EntityPort(ABC):
    """What a device role needs from its entity."""

    entity_id: str
    # True when the entity regulates itself and DST must not cycle it.
    self_regulating: bool = False

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        self.hass = hass
        self._device = device
        self.entity_id = device.entity_id

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """Whether the role is currently engaged."""

    @abstractmethod
    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        """Whether the current on/off state has lasted at least min_cycle."""

    @abstractmethod
    async def async_turn_on(self, context: Context | None) -> None:
        """Engage the role."""

    @abstractmethod
    async def async_turn_off(self, context: Context | None) -> None:
        """Disengage the role."""

    async def async_sync(self, context: Context | None) -> None:
        """Mirror DST state onto the entity. Nothing to mirror by default."""
        return

    def release(self) -> None:
        """The thermostat is going away: let go of shared resources."""
        return

    @abstractmethod
    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
        """DST is Off: make sure the entity is off. Off means off.

        `keep_alive` marks a periodic tick while Off: a switch is stopped if it is
        running (it reports reliably); a climate is left alone.
        """

    async def _reapply_fan_speed(self) -> None:
        """After a turn on, send the selected fan speed again.

        Many ACs (infrared ones especially) reset it on a mode change. A failure
        is logged here and never aborts the control cycle.
        """
        speed = self._device.fan_speed()
        if speed is None:
            return
        try:
            await speed.async_reapply(self.entity_id)
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning(
                "Failed to apply fan mode %s after turning on %s: %s",
                speed.current_fan_mode,
                self.entity_id,
                e,
            )


class SwitchPort(EntityPort):
    """switch / input_boolean / valve style entities (the original behaviour)."""

    @property
    def _state(self) -> State | None:
        return self.hass.states.get(self.entity_id)

    @property
    def _is_valve(self) -> bool:
        state = self._state
        return state is not None and state.domain == VALVE_DOMAIN

    @property
    def _features(self) -> int:
        state = self._state
        return state.attributes.get(ATTR_SUPPORTED_FEATURES) if state else 0

    @property
    def _supports_open_valve(self) -> bool:
        return self._is_valve and self._features & ValveEntityFeature.OPEN

    @property
    def _supports_close_valve(self) -> bool:
        return self._is_valve and self._features & ValveEntityFeature.CLOSE

    @property
    def _on_state(self) -> str:
        return STATE_OPEN if self._is_valve else STATE_ON

    @property
    def is_active(self) -> bool:
        return self.hass.states.is_state(self.entity_id, self._on_state)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        current_state = self._on_state if self.is_active else HVACMode.OFF
        try:
            return condition.state(self.hass, self.entity_id, current_state, min_cycle)
        except ConditionError:
            return False

    async def async_turn_on(self, context: Context | None) -> None:
        await self._turn_on(context)
        await self._reapply_fan_speed()

    async def _turn_on(self, context: Context | None) -> None:
        if self._supports_open_valve:
            await self._call(SERVICE_OPEN_VALVE, context)
            return

        # Skip service call only if entity is unavailable
        # This prevents blocking calls during startup when entities may be unavailable
        # Fixes issue #499 where thermostats became unavailable after restart
        # Note: We intentionally allow calls when entity is already ON because:
        # 1. Keep-alive functionality needs to send periodic turn_on calls
        # 2. Some integrations need the service call to maintain connection
        if is_unavailable(self._state):
            _LOGGER.debug("Skipping turn_on for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_ON, context)

    async def async_turn_off(self, context: Context | None) -> None:
        if self._supports_close_valve:
            await self._call(SERVICE_CLOSE_VALVE, context)
            return

        # Same unavailable rule as turn_on (issue #499)
        if is_unavailable(self._state):
            _LOGGER.debug("Skipping turn_off for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_OFF, context)

    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
        # Today's Off behaviour for switches: stop it if it is running.
        if self.is_active:
            await self.async_turn_off(context)

    async def _call(self, service: str, context: Context | None) -> None:
        _LOGGER.info("Calling %s on entity %s", service, self.entity_id)
        await _call_service(
            self.hass,
            HA_DOMAIN,
            service,
            {ATTR_ENTITY_ID: self.entity_id},
            context,
            "Error calling %s on %s",
            service,
            self.entity_id,
        )


_CHILDREN_KEY = "dual_smart_thermostat_climate_children"

_MAX_PENDING = 4
_TRACKED = (
    ("mode", lambda s: s.state),
    ("target", lambda s: s.attributes.get(ATTR_TEMPERATURE)),
    ("fan_mode", lambda s: s.attributes.get(ATTR_FAN_MODE)),
)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, abs_tol=1e-6)
    return a == b


class ClimateChild:
    """One real climate entity. The only record of its mode, shared by every role.

    Roles never store "am I on": they ask the child, so two roles on the same
    climate cannot both be active. A non-assumed child's reported state is the
    truth. An assumed_state child (IR) never confirms anything, so there DST's
    own last command is the truth.
    """

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self._lock = asyncio.Lock()
        self._commanded: str | None = None
        self._commanded_at: datetime | None = None
        self._last_pushed: float | None = None
        self._warned: set[str] = set()
        self.refs = 0  # ports holding this child; it is dropped at zero
        self.ports: set[ClimatePort] = set()  # the roles that live on this child
        self._pass_depth = 0
        self._pass_set_mode = False
        self._pass_stops: list[tuple[ClimatePort, Context | None]] = []
        # Per owner (the thermostat): the values it commanded and has not yet seen
        # reported, and the two short flags of section 3.6 of the spec.
        self._pending: dict[Any, dict[str, list[Any]]] = {}
        self._sending: dict[Any, int] = {}
        self._adopting: dict[Any, int] = {}
        self._deferred: dict[Any, Callable[[], None]] = {}
        self._off_sent_for: datetime | None = None

    @property
    def state(self) -> State | None:
        return self.hass.states.get(self.entity_id)

    @property
    def available(self) -> bool:
        return not is_unavailable(self.state)

    @property
    def assumed(self) -> bool:
        state = self.state
        return bool(state and state.attributes.get(ATTR_ASSUMED_STATE))

    def _reading(self) -> tuple[str | None, datetime | None]:
        """(mode, since): the reported state, or DST's own record if assumed."""
        state = self.state
        if is_unavailable(state):
            return None, None
        if not state.attributes.get(ATTR_ASSUMED_STATE):
            return state.state, state.last_changed
        # First sight of an assumed child: start from what HA restored.
        if self._commanded is None:
            self._commanded, self._commanded_at = state.state, state.last_changed
        return self._commanded, self._commanded_at

    @property
    def mode(self) -> str | None:
        return self._reading()[0]

    @property
    def since(self) -> datetime | None:
        return self._reading()[1]

    @property
    def wanted_on(self) -> bool:
        """Whether some role on this child is selected (not Off).

        "Off means off" is for a thermostat that is Off. A role being switched out
        because another mode was selected must never stop the child the new role
        just set, whatever order the stops and the new mode land in.
        """
        return any(
            port.device.hvac_mode not in (None, HVACMode.OFF) for port in self.ports
        )

    def device_for(self, mode: str) -> Any | None:
        """The role whose mode this is, if any role owns it."""
        return next(
            (p.device for p in self.ports if mode in p.device.role_modes()), None
        )

    @contextmanager
    def sending(self, owner: Any):
        """DST sends a sequence: changes reported meanwhile are the device's side effects."""
        self._sending[owner] = self._sending.get(owner, 0) + 1
        try:
            yield
        finally:
            self._sending[owner] -= 1
            if not any(self._sending.values()):
                deferred, self._deferred = self._deferred, {}
                for run in deferred.values():
                    run()

    def defer_while_sending(self, owner: Any, run: Callable[[], None]) -> bool:
        """Run `run` once nobody is sending to the child any more.

        Another thermostat's turn-on is a sequence of events (mode, target, fan);
        adopting from the first one would read a half-finished child. Returns
        False (and does nothing) when the child is idle, so the caller runs now.
        """
        if not any(self._sending.values()):
            return False
        self._deferred[owner] = run
        return True

    @contextmanager
    def adopting(self, owner: Any):
        """This owner adopts the child's state: its commands to the child are dropped."""
        self._adopting[owner] = self._adopting.get(owner, 0) + 1
        try:
            yield
        finally:
            self._adopting[owner] -= 1

    def _expect(self, owner: Any, attr: str, value: Any) -> None:
        if self.assumed:
            return  # an assumed child never reports back; nothing to match
        pending = self._pending.setdefault(owner, {}).setdefault(attr, [])
        pending.append(value)
        del pending[:-_MAX_PENDING]

    def _unexpect(self, owner: Any, attr: str, value: Any) -> None:
        pending = self._pending.get(owner, {}).get(attr, [])
        for index in range(len(pending) - 1, -1, -1):
            if _same(pending[index], value):
                del pending[index]
                return

    def clear(self, owner: Any) -> None:
        """Forget what this owner expects (after an adoption, or when the child goes away)."""
        self._pending.pop(owner, None)

    def external(self, owner: Any, old: State | None, new: State | None) -> set[str]:
        """Consume this owner's echoes; the attributes that changed from outside.

        Judged by value against what this owner commanded and has not yet seen
        reported. Contexts and time play no part: HA stamps a write within 5 s of
        a service call with the caller's context, and a polled device reports
        late.
        """
        if is_unavailable(old) or is_unavailable(new):
            self.clear(owner)  # first sight and reconnect adopt nothing
            return set()
        if old.attributes.get(ATTR_ASSUMED_STATE) or new.attributes.get(
            ATTR_ASSUMED_STATE
        ):
            return set()  # an assumed child reports DST's own record
        external: set[str] = set()
        for attr, read in _TRACKED:
            before, after = read(old), read(new)
            if after is None or _same(before, after):
                continue
            pending = self._pending.get(owner, {}).get(attr, [])
            match = next((i for i, v in enumerate(pending) if _same(v, after)), None)
            if match is not None:
                del pending[match]  # an echo of ours; any order is fine
            else:
                external.add(attr)
        return set() if self._sending.get(owner) else external

    def begin_pass(self) -> None:
        """A control run starts: role stops are held back until it ends."""
        self._pass_depth += 1

    @property
    def in_pass(self) -> bool:
        return self._pass_depth > 0

    def defer_stop(self, port: ClimatePort, context: Context | None) -> None:
        self._pass_stops.append((port, context))

    async def end_pass(self) -> None:
        """The run is over: send the held-back stop, unless a mode replaced it."""
        self._pass_depth -= 1
        if self._pass_depth > 0:
            return
        stops, replaced = self._pass_stops, self._pass_set_mode
        self._pass_stops, self._pass_set_mode = [], False
        if replaced:
            return  # the new mode replaced the old one: a stop would only race it
        for port, context in stops:
            if port.is_active:
                await self.async_turn_off(context, port.owner)
                return

    def _record(self, mode: str) -> None:
        """Note a command. The mode age restarts only when the mode changes."""
        self._reading()  # adopt the restored state first
        if self._commanded != mode:
            self._commanded, self._commanded_at = mode, dt_util.utcnow()
            # A mode change may reset the device's setpoint: push it again.
            self._last_pushed = None

    async def _command(
        self,
        service: str,
        data: dict[str, Any],
        context: Context | None,
        error: str,
        *args: Any,
        owner: Any,
        mode: str | None = None,
    ) -> bool:
        """Call a climate service (lock held); on failure roll the record back."""
        if self._adopting.get(owner):
            _LOGGER.debug("Adopting %s: not sending %s", self.entity_id, service)
            return False
        # Always a fresh context (logbook attribution only); never the caller's.
        context = Context(parent_id=context.id if context else None)
        before = (self._commanded, self._commanded_at, self._last_pushed)
        if mode is not None:
            self._record(mode)
            self._expect(owner, "mode", mode)
        if ATTR_TEMPERATURE in data:
            self._expect(owner, "target", data[ATTR_TEMPERATURE])
        _LOGGER.debug(
            "Sending %s.%s %s",
            CLIMATE_DOMAIN,
            service,
            data | {ATTR_ENTITY_ID: self.entity_id},
        )
        ok = await _call_service(
            self.hass,
            CLIMATE_DOMAIN,
            service,
            {ATTR_ENTITY_ID: self.entity_id, **data},
            context,
            error,
            *args,
        )
        if not ok:
            self._commanded, self._commanded_at, self._last_pushed = before
            if mode is not None:
                self._unexpect(owner, "mode", mode)
            if ATTR_TEMPERATURE in data:
                self._unexpect(owner, "target", data[ATTR_TEMPERATURE])
        return ok

    async def async_set_mode(
        self, mode: str, context: Context | None, owner: Any
    ) -> bool:
        """Command a mode. False when nothing was sent or the call failed."""
        async with self._lock:
            state = self.state
            if is_unavailable(state):
                _LOGGER.debug(
                    "Skipping set_hvac_mode for unavailable %s", self.entity_id
                )
                return False
            supported = state.attributes.get(ATTR_HVAC_MODES)
            if supported is not None and mode not in supported:
                if mode not in self._warned:
                    self._warned.add(mode)
                    _LOGGER.warning(
                        "%s does not support hvac mode %s, not sending it",
                        self.entity_id,
                        mode,
                    )
                return False
            # A reported state already in this mode makes a resend pointless; an
            # assumed device cannot report, so keep-alive resends are the point.
            self._pass_set_mode = self.in_pass
            if not state.attributes.get(ATTR_ASSUMED_STATE) and state.state == mode:
                return True
            return await self._command(
                SERVICE_SET_HVAC_MODE,
                {ATTR_HVAC_MODE: mode},
                context,
                "Error setting %s on %s",
                mode,
                self.entity_id,
                owner=owner,
                mode=mode,
            )

    async def async_turn_off(self, context: Context | None, owner: Any) -> None:
        async with self._lock:
            if not self.available:
                return
            await self._command(
                SERVICE_TURN_OFF,
                {},
                context,
                "Error turning off %s",
                self.entity_id,
                owner=owner,
                mode=HVACMode.OFF,
            )

    async def async_stop_unscoped(self, context: Context | None, owner: Any) -> None:
        """Off means off: one turn_off per child, however many roles ask for it.

        Several roles (and a slow device that has not reported yet) can all see the
        child still running; the first off is enough until the child reports
        something new.
        """
        state = self.state
        if (
            state is not None
            and self._off_sent_for is not None
            and state.last_changed == self._off_sent_for
        ):
            return
        self._off_sent_for = state.last_changed if state is not None else None
        await self.async_turn_off(context, owner)

    async def async_push_target(
        self, value: float, context: Context | None, owner: Any
    ) -> None:
        async with self._lock:
            state = self.state
            if is_unavailable(state):
                return
            attrs = state.attributes
            features = attrs.get(ATTR_SUPPORTED_FEATURES)
            if (
                features is not None
                and not features & ClimateEntityFeature.TARGET_TEMPERATURE
            ):
                return
            value = self._fit(value, attrs)
            current = (
                self._last_pushed
                if attrs.get(ATTR_ASSUMED_STATE)
                else attrs.get(ATTR_TEMPERATURE)
            )
            if current == value:
                return
            if await self._command(
                SERVICE_SET_TEMPERATURE,
                {ATTR_TEMPERATURE: value},
                context,
                "Error setting target on %s",
                self.entity_id,
                owner=owner,
            ):
                self._last_pushed = value

    async def async_set_fan_mode(
        self, fan_mode: str, context: Context | None, owner: Any
    ) -> None:
        """Send a fan speed, unless the child is not running or already has it.

        An off or unavailable child gets nothing now (the caller records the
        selection and sends it on the next turn on): an IR frame could otherwise
        power the AC on while the thermostat is Off. An assumed child is judged by
        DST's own record, since it never reports.
        """
        async with self._lock:
            state = self.state
            if self.mode in (None, HVACMode.OFF):
                return
            if (
                not state.attributes.get(ATTR_ASSUMED_STATE)
                and state.attributes.get(ATTR_FAN_MODE) == fan_mode
            ):
                return
            if self._adopting.get(owner):
                _LOGGER.debug("Adopting %s: not sending fan mode", self.entity_id)
                return
            data = {ATTR_ENTITY_ID: self.entity_id, ATTR_FAN_MODE: fan_mode}
            _LOGGER.debug(
                "Sending %s.%s %s", CLIMATE_DOMAIN, SERVICE_SET_FAN_MODE, data
            )
            self._expect(owner, "fan_mode", fan_mode)
            try:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_FAN_MODE,
                    data,
                    context=Context(parent_id=context.id if context else None),
                    blocking=True,
                )
            except Exception:
                self._unexpect(owner, "fan_mode", fan_mode)
                raise

    @staticmethod
    def _fit(value: float, attrs: Mapping[str, Any]) -> float:
        """Round to the child's step (whole degrees if it has none), then clamp.

        The pushed value is one the child can hold, so what it reports back
        equals what was pushed and the "already set" check cannot loop.
        """
        step = attrs.get(ATTR_TARGET_TEMP_STEP) or 1
        value = round(round(value / step) * step, 4)
        low, high = attrs.get(ATTR_MIN_TEMP), attrs.get(ATTR_MAX_TEMP)
        if low is not None:
            value = max(value, low)
        if high is not None:
            value = min(value, high)
        return value


def peek_climate_child(hass: HomeAssistant, entity_id: str) -> ClimateChild | None:
    """The shared ClimateChild if a port holds one, without taking a reference."""
    return hass.data.get(_CHILDREN_KEY, {}).get(entity_id)


def acquire_climate_child(hass: HomeAssistant, entity_id: str) -> ClimateChild:
    """Get or create the single ClimateChild for a real climate entity.

    Reference counted: every port holds one reference until it is released, so
    a thermostat going away can neither strand a stale record of the device nor
    pull the child from under another thermostat that shares it.
    """
    children = hass.data.setdefault(_CHILDREN_KEY, {})
    if entity_id not in children:
        children[entity_id] = ClimateChild(hass, entity_id)
    children[entity_id].refs += 1
    return children[entity_id]


def release_climate_child(child: ClimateChild) -> None:
    """Drop one reference; the last one removes the child."""
    child.refs -= 1
    if child.refs <= 0:
        child.hass.data.get(_CHILDREN_KEY, {}).pop(child.entity_id, None)


class ClimatePort(EntityPort):
    """One role's view of a (possibly shared) climate entity."""

    @property
    def device(self) -> Any:
        return self._device

    @property
    def owner(self) -> Any:
        """The thermostat this role belongs to (its FeatureManager)."""
        return self._device.features

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        super().__init__(hass, device)
        self._child = acquire_climate_child(hass, device.entity_id)
        self._child.ports.add(self)
        self.self_regulating = device.control_style() == ControlStyle.SETPOINT
        self._released = False

    def release(self) -> None:
        if not self._released:  # idempotent: one reference per port, once
            self._released = True
            self._child.ports.discard(self)
            if not any(p.owner is self.owner for p in self._child.ports):
                self._child.clear(self.owner)
            release_climate_child(self._child)

    @property
    def is_active(self) -> bool:
        # The first role mode is the one commanded; any of them counts as running
        # (a heat pump in either mode, so a flip of its flag still stops it).
        return self._child.mode in self._device.role_modes()

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        if not min_cycle:  # none configured: nothing to wait for
            return True
        since = self._child.since
        return since is not None and dt_util.utcnow() - since >= min_cycle

    async def _push(self, context: Context | None) -> None:
        target = self._device.climate_target()
        if target is not None:
            await self._child.async_push_target(
                target + self._device.setpoint_offset(), context, self.owner
            )

    async def async_turn_on(self, context: Context | None) -> None:
        # One sequence: what the device reports meanwhile (a reset fan, a changed
        # setpoint) is its own side effect, not the user's.
        with self._child.sending(self.owner):
            if not await self._child.async_set_mode(
                self._device.role_modes()[0], context, self.owner
            ):
                return
            await self._push(context)
            # Last, so the speed lands after the mode change that may have reset it.
            await self._reapply_fan_speed()

    async def async_sync(self, context: Context | None) -> None:
        # Only the role the child is serving may touch its setpoint.
        if self.is_active:
            await self._push(context)

    async def async_turn_off(self, context: Context | None) -> None:
        # Only the role the child is currently serving may stop it, so an idle
        # cooler's stop can never switch off the heater on the same device. And only
        # while a role is selected: when the thermostat is Off it leaves the device
        # alone (a stop of the Off transition goes through async_stop).
        if self.is_active and self._child.wanted_on:
            if self._child.in_pass:
                self._child.defer_stop(self, context)
            else:
                await self._child.async_turn_off(context, self.owner)

    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
        # Off means off, once, on the transition to Off: whatever mode the child is
        # in, even one no role owns, but only while no role on the child is selected
        # (otherwise this role is just being switched out). While the thermostat
        # stays Off, a keep-alive tick leaves a climate alone, so the AC's own
        # remote keeps working.
        if keep_alive:
            return
        if self._child.wanted_on:
            await self.async_turn_off(context)
        elif self._child.mode not in (None, HVACMode.OFF):
            await self._child.async_stop_unscoped(context, self.owner)


def make_port(hass: HomeAssistant, device: Any) -> EntityPort:
    """Build the port for a device's role from its entity domain."""
    if is_climate_entity(device.entity_id):
        return ClimatePort(hass, device)
    return SwitchPort(hass, device)
