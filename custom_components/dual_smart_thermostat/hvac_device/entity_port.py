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
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import math
from typing import Any, NamedTuple

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
    STATE_CLOSED,
    STATE_OFF,
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

    # A stop is scoped to the role's own mode on a device shared by several roles
    # (a climate); begin_pass/end_pass bracket a control run on such a device.
    role_scoped = False

    def begin_pass(self) -> None:
        return

    async def end_pass(self) -> None:
        return

    def holds_stop(self, min_cycle: timedelta) -> bool:
        """A goal-reached stop must wait for the minimum cycle, even in a forced run.

        Only a climate holds it (its compressor); a switch lets a forced run skip
        the minimum cycle.
        """
        return False

    def holds_start(self, min_cycle: timedelta) -> bool:
        """A start must wait for the minimum cycle, even in a forced run."""
        return False

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
    """switch / input_boolean / valve style entities."""

    @property
    def _state(self) -> State | None:
        return self.hass.states.get(self.entity_id)

    @staticmethod
    def _is_valve(state: State | None) -> bool:
        return state is not None and state.domain == VALVE_DOMAIN

    @classmethod
    def _supports(cls, state: State | None, feature: ValveEntityFeature) -> bool:
        return cls._is_valve(state) and bool(
            state.attributes.get(ATTR_SUPPORTED_FEATURES, 0) & feature
        )

    @classmethod
    def _on_state(cls, state: State | None) -> str:
        return STATE_OPEN if cls._is_valve(state) else STATE_ON

    @classmethod
    def _off_state(cls, state: State | None) -> str:
        return STATE_CLOSED if cls._is_valve(state) else STATE_OFF

    @property
    def is_active(self) -> bool:
        state = self._state
        return state is not None and state.state == self._on_state(state)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        state = self._state
        active = state is not None and state.state == self._on_state(state)
        current = self._on_state(state) if active else self._off_state(state)
        try:
            return condition.state(self.hass, self.entity_id, current, min_cycle)
        except ConditionError:
            return False

    async def async_turn_on(self, context: Context | None) -> None:
        await self._turn_on(context)
        await self._reapply_fan_speed()

    async def _turn_on(self, context: Context | None) -> None:
        state = self._state
        if self._supports(state, ValveEntityFeature.OPEN):
            await self._call(SERVICE_OPEN_VALVE, context)
            return

        # An unavailable entity gets no call (startup, #499). An entity already on
        # does: keep-alive resends turn_on, and some integrations need it.
        if is_unavailable(state):
            _LOGGER.debug("Skipping turn_on for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_ON, context)

    async def async_turn_off(self, context: Context | None) -> None:
        state = self._state
        if self._supports(state, ValveEntityFeature.CLOSE):
            await self._call(SERVICE_CLOSE_VALVE, context)
            return

        if is_unavailable(state):  # as for turn_on (#499)
            _LOGGER.debug("Skipping turn_off for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_OFF, context)

    async def async_stop(
        self, context: Context | None, *, keep_alive: bool = False
    ) -> None:
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
# HA stamps a state write with the entity's last service context for this long
# (CONTEXT_RECENT_TIME_SECONDS): a device reacting to our command reports under it.
_OWN_CONTEXT_WINDOW = timedelta(seconds=5)


@dataclass
class ExternalReport:
    """What a state report of a child means for one thermostat."""

    changed: set[str] = field(default_factory=set)  # attributes changed from outside
    fan_dropped: bool = False  # the device dropped our fan: send it again, once


class _Expected(NamedTuple):
    """A value `origin` commanded and nobody has seen reported yet."""

    value: Any
    origin: Any
    at: datetime


class _PassAction:
    """What a control run holds back for one role until it ends."""

    def __init__(self) -> None:
        self.stop = False  # a stop was deferred ...
        self.stop_context: Context | None = None  # ... with this context
        self.push = False  # the setpoint (and, with turn_on, the fan speed)
        self.turn_on = False
        self.context: Context | None = None


def _enter(counts: dict, key: Any) -> bool:
    """Depth-counted bracket: True when this is the outermost entry."""
    counts[key] = counts.get(key, 0) + 1
    return counts[key] == 1


def _leave(counts: dict, key: Any) -> bool:
    """True when this closes the outermost entry."""
    counts[key] -= 1
    return counts[key] == 0


_PASS = "pass"

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
        # the roles that live on this child; it is dropped when the last one goes
        self.ports: set[ClimatePort] = set()
        self._depth: dict[Any, int] = {}  # the control pass (_PASS)
        self._pass_set_mode = False
        self._pass_actions: dict[ClimatePort, _PassAction] = {}
        # Per owner (the thermostat): what it commanded and has not yet seen reported.
        self._pending: dict[Any, dict[str, list[_Expected]]] = {}
        self._sending: dict[Any, int] = {}
        self._fan_sent: set[Any] = set()  # owners whose sequence has sent its fan
        self._own_contexts: dict[str, datetime] = {}  # contexts of our recent commands
        self._last_fan: dict[Any, str] = {}  # owner -> the fan it commanded last
        self._fan_resent: set[Any] = set()  # ... and have, in this sequence
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
    def commanded(self) -> str | None:
        return self._commanded

    @property
    def commanded_at(self) -> datetime | None:
        return self._commanded_at

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
        return any(port.selected for port in self.ports)

    def port_for(self, mode: str) -> ClimatePort | None:
        """The role (port) whose mode this is, if any role owns it."""
        return next((p for p in self.ports if mode in p.role_modes()), None)

    @contextmanager
    def sending(self, owner: Any):
        """DST sends a sequence: changes reported meanwhile are the device's side effects."""
        if _enter(self._sending, owner):
            self._fan_sent.discard(owner)
            self._fan_resent.discard(owner)
        try:
            yield
        finally:
            _leave(self._sending, owner)
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
        _enter(self._adopting, owner)
        try:
            yield
        finally:
            _leave(self._adopting, owner)

    def _observers(self, origin: Any) -> set[Any]:
        """Every thermostat on this child: a command of one is an echo for all."""
        return {port.owner for port in self.ports} | {origin}

    def _own_context(self, parent: Context | None) -> Context:
        """A fresh context for one of our commands (logbook attribution only)."""
        context = Context(parent_id=parent.id if parent else None)
        now = dt_util.utcnow()
        self._own_contexts[context.id] = now
        for stale in [
            i for i, at in self._own_contexts.items() if now - at > _OWN_CONTEXT_WINDOW
        ]:
            del self._own_contexts[stale]
        return context

    def _expect(self, origin: Any, expect: dict[str, Any]) -> None:
        """Record the values `origin` commanded and nobody has seen reported yet.

        Peers record them too, so a command of a thermostat (its own control, such
        as a safety stop, as much as the user's) is never taken for the user acting
        on the device by another thermostat sharing the child.
        """
        observers, now = self._observers(origin), dt_util.utcnow()
        for attr, value in expect.items():
            for observer in observers:
                pending = self._pending.setdefault(observer, {}).setdefault(attr, [])
                pending.append(_Expected(value, origin, now))
                del pending[:-_MAX_PENDING]

    def _unexpect(self, origin: Any, attr: str, value: Any) -> None:
        for observer in self._observers(origin):
            pending = self._pending.get(observer, {}).get(attr, [])
            for index in range(len(pending) - 1, -1, -1):
                entry = pending[index]
                if entry.origin is origin and _same(entry.value, value):
                    del pending[index]
                    break

    def clear(self, origin: Any) -> None:
        """Forget what `origin` commanded (after its adoption, or when it goes away)."""
        for attrs in self._pending.values():
            for attr, pending in attrs.items():
                attrs[attr] = [e for e in pending if e.origin is not origin]

    def forget(self, owner: Any) -> None:
        """The thermostat is going away: no record of it may outlive it."""
        self.clear(owner)
        for record in (
            self._pending,
            self._sending,
            self._adopting,
            self._deferred,
            self._last_fan,
        ):
            record.pop(owner, None)
        self._fan_sent.discard(owner)
        self._fan_resent.discard(owner)

    def reset(self, observer: Any) -> None:
        """The child went away: nothing pending is meaningful any more."""
        self._pending.pop(observer, None)

    def external(
        self, owner: Any, old: State | None, new: State | None
    ) -> ExternalReport:
        """Consume this owner's echoes; the attributes that changed from outside.

        Judged by value against what this owner commanded and has not yet seen
        reported. Contexts and time play no part: HA stamps a write within 5 s of
        a service call with the caller's context, and a polled device reports
        late.
        """
        if is_unavailable(old) or is_unavailable(new):
            self.reset(owner)  # first sight and reconnect adopt nothing
            return ExternalReport()
        if old.attributes.get(ATTR_ASSUMED_STATE) or new.attributes.get(
            ATTR_ASSUMED_STATE
        ):
            return ExternalReport()  # an assumed child reports DST's own record
        external: set[str] = set()
        fan_dropped = False
        for attr, read in _TRACKED:
            before, after = read(old), read(new)
            if after is None or _same(before, after):
                continue
            pending = self._pending.get(owner, {}).get(attr, [])
            match = next(
                (i for i, entry in enumerate(pending) if _same(entry.value, after)),
                None,
            )
            if match is not None:
                del pending[match]  # an echo of ours; any order is fine
            else:
                external.add(attr)
                # The device moved on without reporting what was commanded: the
                # expectations recorded before this report are stale and must not
                # swallow a later press (a peer's command sent since is kept).
                pending[:] = [e for e in pending if e.at >= new.last_updated]
        if "fan_mode" in external and self._dropped_by_device(owner, new):
            # The device answered our own command with its default (a power-on
            # reset): not the user. Say it again once, adopt nothing.
            external.discard("fan_mode")
            if owner not in self._fan_resent:
                self._fan_resent.add(owner)
                fan_dropped = True
        if self._sending.get(owner):
            # Side effects of the sequence (a mode that resets the fan) are not the
            # user's; but the fan is the last thing sent, so a fan reported after
            # it was sent is someone else's last word.
            external = external & {ATTR_FAN_MODE} if owner in self._fan_sent else set()
        return ExternalReport(external, fan_dropped)

    def pending_mode(self, owner: Any) -> str | None:
        """The last mode `owner` commanded that the device has not reported yet."""
        pending = self._pending.get(owner, {}).get("mode", [])
        return next((e.value for e in reversed(pending) if e.origin is owner), None)

    def _dropped_by_device(self, owner: Any, new: State) -> bool:
        """A fan reported under the context of our own command, not what we sent.

        HA stamps a write with the entity's last service context while it is
        recent, so a device reacting to our command carries ours; an automation
        or the UI carries their own. (A remote press within seconds of our
        command would carry ours too: it is overridden once.)
        """
        sent = self._last_fan.get(owner)
        at = self._own_contexts.get(new.context.id)
        return (
            sent is not None
            and at is not None
            and dt_util.utcnow() - at <= _OWN_CONTEXT_WINDOW
            and not _same(new.attributes.get(ATTR_FAN_MODE), sent)
        )

    def begin_pass(self) -> None:
        """A control run starts: role stops are held back until it ends."""
        _enter(self._depth, _PASS)

    @property
    def in_pass(self) -> bool:
        return self._depth.get(_PASS, 0) > 0

    def _action(self, port: ClimatePort) -> _PassAction:
        return self._pass_actions.setdefault(port, _PassAction())

    def defer_stop(self, port: ClimatePort, context: Context | None) -> None:
        action = self._action(port)
        action.stop, action.stop_context = True, context

    def defer_tail(
        self, port: ClimatePort, context: Context | None, *, turn_on: bool
    ) -> None:
        """Inside a run the setpoint (and a turn on's fan speed) wait for its end:
        the run decides the child's final state first, then sends it."""
        action = self._action(port)
        action.push, action.context = True, context
        action.turn_on = action.turn_on or turn_on

    async def end_pass(self) -> None:
        """The run is over: the held-back setpoints and fan speeds, then the stop
        (unless a mode replaced it)."""
        if not _leave(self._depth, _PASS):
            return
        actions, replaced = self._pass_actions, self._pass_set_mode
        self._pass_actions, self._pass_set_mode = {}, False
        for port, action in actions.items():
            # Once, with the run's final target, only if its mode still stands and
            # the run does not stop it.
            stopped = not replaced and action.stop
            if (
                action.push
                and not stopped
                and (self.pending_mode(port.owner) or self.mode) in port.role_modes()
            ):
                with self.sending(port.owner):
                    await port.async_finish_turn_on(
                        action.context, turn_on=action.turn_on
                    )
        if replaced:
            return  # the new mode replaced the old one: a stop would only race it
        for port, action in actions.items():
            if action.stop and port.is_active:
                await self.async_turn_off(action.stop_context, port.owner)
                return

    def _held(self, state: State, attr: str) -> Any:
        """What the child already has, as far as DST can know (else None).

        A reported state is the truth; an assumed child never reports, so only the
        target has a record (what DST last pushed) and a resend is never pointless.
        """
        assumed = state.attributes.get(ATTR_ASSUMED_STATE)
        if attr == "target":
            return (
                self._last_pushed if assumed else state.attributes.get(ATTR_TEMPERATURE)
            )
        if assumed:
            return None
        return state.state if attr == "mode" else state.attributes.get(ATTR_FAN_MODE)

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
        expect: dict[str, Any],
    ) -> bool:
        """Call a climate service (lock held); on failure roll the record back.

        `expect` names what the call sets ("mode", "target", "fan_mode"): the values
        are recorded as ours until the device reports them back.
        """
        if self._adopting.get(owner):
            _LOGGER.debug("Adopting %s: not sending %s", self.entity_id, service)
            return False
        # Always a fresh context (logbook attribution only); never the caller's.
        context = self._own_context(context)
        before = (self._commanded, self._commanded_at, self._last_pushed)
        if "mode" in expect:
            self._record(expect["mode"])
        if "fan_mode" in expect:
            self._fan_sent.add(owner)
            self._last_fan[owner] = expect["fan_mode"]
        if not self.assumed:  # an assumed child never reports back: nothing to match
            self._expect(owner, expect)
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
            for attr, value in expect.items():
                self._unexpect(owner, attr, value)
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
            if self._held(state, "mode") == mode or (
                # Commanded earlier in this run and not reported yet (a slow device)
                not state.attributes.get(ATTR_ASSUMED_STATE)
                and self.in_pass
                and self.pending_mode(owner) == mode
            ):
                return True
            return await self._command(
                SERVICE_SET_HVAC_MODE,
                {ATTR_HVAC_MODE: mode},
                context,
                "Error setting %s on %s",
                mode,
                self.entity_id,
                owner=owner,
                expect={"mode": mode},
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
                expect={"mode": HVACMode.OFF},
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
            if self._held(state, "target") == value:
                return
            if await self._command(
                SERVICE_SET_TEMPERATURE,
                {ATTR_TEMPERATURE: value},
                context,
                "Error setting target on %s",
                self.entity_id,
                owner=owner,
                expect={"target": value},
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
            if is_unavailable(state):
                return
            # What DST just commanded counts as running even if the device has not
            # reported it yet, so a turn on always lands its fan speed.
            if (self.pending_mode(owner) or self.mode) in (None, HVACMode.OFF):
                return
            if self._held(state, "fan_mode") == fan_mode:
                return
            await self._command(
                SERVICE_SET_FAN_MODE,
                {ATTR_FAN_MODE: fan_mode},
                context,
                "Error setting fan mode on %s",
                self.entity_id,
                owner=owner,
                expect={"fan_mode": fan_mode},
            )

    @staticmethod
    def _fit(value: float, attrs: Mapping[str, Any]) -> float:
        """Round to the child's step (whole degrees if it has none), then clamp.

        The pushed value is one the child can hold, so what it reports back
        equals what was pushed and the "already set" check cannot loop.
        """
        step = attrs.get(ATTR_TARGET_TEMP_STEP) or 1
        # half rounds away from zero (the user's intent), not to even like round()
        steps = value / step
        value = round(
            math.copysign(math.floor(abs(steps) + 0.5 + 1e-9), steps) * step, 4
        )
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

    The child lives while a port holds it (`ClimatePort.release` removes the last
    one), so a thermostat going away can neither strand a stale record of the
    device nor pull the child from under another thermostat that shares it.
    """
    children = hass.data.setdefault(_CHILDREN_KEY, {})
    if entity_id not in children:
        children[entity_id] = ClimateChild(hass, entity_id)
    return children[entity_id]


class ClimatePort(EntityPort):
    """One role's view of a (possibly shared) climate entity."""

    @property
    def owner(self) -> Any:
        """The thermostat this role belongs to (its FeatureManager)."""
        return self._device.features

    def __init__(self, hass: HomeAssistant, device: Any) -> None:
        super().__init__(hass, device)
        self._child = acquire_climate_child(hass, device.entity_id)
        self._child.ports.add(self)
        self.self_regulating = device.control_style() == ControlStyle.SETPOINT

    def role_modes(self) -> list:
        """The child modes this role runs in (the first is the one commanded)."""
        return self._device.role_modes()

    @property
    def selected(self) -> bool:
        """Whether the thermostat's mode selects this role (it is not Off)."""
        return self._device.hvac_mode not in (None, HVACMode.OFF)

    @property
    def pushes_setpoint(self) -> bool:
        return self._device.pushes_setpoint

    def release(self) -> None:
        child = self._child
        if self not in child.ports:
            return  # idempotent
        child.ports.discard(self)
        if not any(p.owner is self.owner for p in child.ports):
            child.forget(self.owner)
        if not child.ports:
            child.hass.data.get(_CHILDREN_KEY, {}).pop(child.entity_id, None)

    @property
    def is_active(self) -> bool:
        # The first role mode is the one commanded; any of them counts as running
        # (a heat pump in either mode, so a flip of its flag still stops it).
        return self._child.mode in self.role_modes()

    role_scoped = True

    def begin_pass(self) -> None:
        self._child.begin_pass()

    async def end_pass(self) -> None:
        await self._child.end_pass()

    def holds_stop(self, min_cycle: timedelta) -> bool:
        return not self.ran_long_enough(min_cycle)

    def holds_start(self, min_cycle: timedelta) -> bool:
        # Switching a running child from one role's mode to another's is not a start.
        return self._child.mode == HVACMode.OFF and not self.ran_long_enough(min_cycle)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        if not min_cycle:  # none configured: nothing to wait for
            return True
        child = self._child
        if child.mode == HVACMode.OFF:
            # Only an off DST itself commanded counts: an off nobody saw running (a
            # restart, a new entity) says nothing about the compressor.
            since = child.commanded_at if child.commanded == HVACMode.OFF else None
            return since is None or dt_util.utcnow() - since >= min_cycle
        since = child.since
        return since is not None and dt_util.utcnow() - since >= min_cycle

    async def _push(self, context: Context | None) -> None:
        target = self._device.climate_target()
        if target is not None:
            await self._child.async_push_target(
                self.dst_target_to_device(target), context, self.owner
            )

    def dst_target_to_device(self, target: float) -> float:
        """DST's target as this role pushes it (plus the role's setpoint offset)."""
        return target + self._device.setpoint_offset()

    def device_target_to_dst(self, value: float) -> float:
        """The inverse: a target reported by the device, in DST's own terms."""
        return round(value - self._device.setpoint_offset(), 4)

    async def async_turn_on(self, context: Context | None) -> None:
        # One sequence: what the device reports meanwhile (a reset fan, a changed
        # setpoint) is its own side effect, not the user's.
        with self._child.sending(self.owner):
            if not await self._child.async_set_mode(
                self.role_modes()[0], context, self.owner
            ):
                return
            if self._child.in_pass:
                self._child.defer_tail(self, context, turn_on=True)
                return
            await self.async_finish_turn_on(context, turn_on=True)

    async def async_finish_turn_on(
        self, context: Context | None, *, turn_on: bool
    ) -> None:
        await self._push(context)
        if turn_on:
            # Last, so the speed lands after the mode change that may have reset it.
            await self._reapply_fan_speed()

    async def async_sync(self, context: Context | None) -> None:
        # Only the role the child is serving may touch its setpoint.
        if self.is_active:
            if self._child.in_pass:
                self._child.defer_tail(self, context, turn_on=False)
            else:
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
        # (otherwise this role is just being switched out). A keep-alive tick while
        # Off leaves a climate alone, so the AC's own remote keeps working.
        child = self._child
        if keep_alive:
            return
        if not child.wanted_on and child.mode not in (None, HVACMode.OFF):
            await child.async_stop_unscoped(context, self.owner)
        else:
            await self.async_turn_off(context)


def make_port(hass: HomeAssistant, device: Any) -> EntityPort:
    """Build the port for a device's role from its entity domain."""
    if is_climate_entity(device.entity_id):
        return ClimatePort(hass, device)
    return SwitchPort(hass, device)
