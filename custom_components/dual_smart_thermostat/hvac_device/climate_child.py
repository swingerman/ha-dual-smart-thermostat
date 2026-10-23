"""One real climate entity, shared by every role (and thermostat) that uses it."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime
import logging
import math
from typing import TYPE_CHECKING, Any

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
from homeassistant.const import (
    ATTR_ASSUMED_STATE,
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
)
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.util import dt as dt_util

from .climate_echo import ClimateEcho, _enter, _leave
from .entity_port import _call_service, is_unavailable

if TYPE_CHECKING:
    from .climate_port import ClimatePort

_LOGGER = logging.getLogger(__name__)

_CHILDREN_KEY = "dual_smart_thermostat_climate_children"


class _PassAction:
    """What a control run holds back for one role until it ends."""

    def __init__(self) -> None:
        self.stop = False  # a stop was deferred ...
        self.stop_context: Context | None = None  # ... with this context
        self.push = False  # the setpoint (and, with turn_on, the fan speed)
        self.turn_on = False
        self.context: Context | None = None


_PASS = "pass"


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
        self.echo = ClimateEcho(lambda: {port.owner for port in self.ports})
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
                and (self.echo.pending_mode(port.owner) or self.mode)
                in port.role_modes()
            ):
                with self.echo.sending(port.owner):
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
        if self.echo.is_adopting(owner):
            _LOGGER.debug("Adopting %s: not sending %s", self.entity_id, service)
            return False
        # Always a fresh context (logbook attribution only); never the caller's.
        context = self.echo.own_context(context)
        before = (self._commanded, self._commanded_at, self._last_pushed)
        if "mode" in expect:
            self._record(expect["mode"])
        if "fan_mode" in expect:
            self.echo.fan_commanded(owner, expect["fan_mode"])
        if not self.assumed:  # an assumed child never reports back: nothing to match
            self.echo.expect(owner, expect)
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
                self.echo.retract(owner, attr, value)
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
                and self.echo.pending_mode(owner) == mode
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
            if (self.echo.pending_mode(owner) or self.mode) in (None, HVACMode.OFF):
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
