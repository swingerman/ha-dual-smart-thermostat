"""How a device role talks to its entity.

The one place that knows what "on" means for an entity and how to command it.
Controllers and devices call these methods; they never read the entity's state
or call its services themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    SERVICE_SET_HVAC_MODE,
    SERVICE_SET_TEMPERATURE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
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

from ..climate_roles import CLIMATE_DOMAIN, is_climate_entity
from ..const import ControlStyle

_LOGGER = logging.getLogger(__name__)


class EntityPort(ABC):
    """What a device role needs from its entity."""

    entity_id: str
    # True when the entity regulates itself and DST must not cycle it.
    self_regulating: bool = False

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
        self, context: Context | None, keep_alive: bool = False
    ) -> None:
        """DST is Off: make sure the entity is off. Off means off.

        `keep_alive` marks a periodic tick: resend off to an entity whose
        record cannot be trusted (an assumed_state climate). A switch reports
        its state reliably, so for it a tick is no different from any stop.
        """


class SwitchPort(EntityPort):
    """switch / input_boolean / valve style entities (the original behaviour)."""

    def __init__(self, hass: HomeAssistant, entity_id: str) -> None:
        self.hass = hass
        self.entity_id = entity_id

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
        return state.attributes.get("supported_features") if state else 0

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
        if self._supports_open_valve:
            await self._call(SERVICE_OPEN_VALVE, context)
            return

        # Skip service call only if entity is unavailable
        # This prevents blocking calls during startup when entities may be unavailable
        # Fixes issue #499 where thermostats became unavailable after restart
        # Note: We intentionally allow calls when entity is already ON because:
        # 1. Keep-alive functionality needs to send periodic turn_on calls
        # 2. Some integrations need the service call to maintain connection
        if self._unavailable():
            _LOGGER.debug("Skipping turn_on for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_ON, context)

    async def async_turn_off(self, context: Context | None) -> None:
        if self._supports_close_valve:
            await self._call(SERVICE_CLOSE_VALVE, context)
            return

        # Same unavailable rule as turn_on (issue #499)
        if self._unavailable():
            _LOGGER.debug("Skipping turn_off for unavailable entity %s", self.entity_id)
            return
        await self._call(SERVICE_TURN_OFF, context)

    async def async_stop(
        self, context: Context | None, keep_alive: bool = False
    ) -> None:
        # Today's Off behaviour for switches: stop it if it is running.
        if self.is_active:
            await self.async_turn_off(context)

    def _unavailable(self) -> bool:
        state = self._state
        return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    async def _call(self, service: str, context: Context | None) -> None:
        _LOGGER.info("Calling %s on entity %s", service, self.entity_id)
        try:
            await self.hass.services.async_call(
                HA_DOMAIN,
                service,
                {ATTR_ENTITY_ID: self.entity_id},
                context=context,
                blocking=True,
            )
        except Exception as e:  # noqa: BLE001
            _LOGGER.error(
                "Error calling %s on %s. Error: %s", service, self.entity_id, e
            )


_CHILDREN_KEY = "dual_smart_thermostat_climate_children"


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

    @property
    def state(self) -> State | None:
        return self.hass.states.get(self.entity_id)

    @property
    def available(self) -> bool:
        state = self.state
        return state is not None and state.state not in (
            STATE_UNAVAILABLE,
            STATE_UNKNOWN,
        )

    @property
    def assumed(self) -> bool:
        state = self.state
        return bool(state and state.attributes.get("assumed_state"))

    def _adopt_reported(self) -> None:
        """First sight of an assumed child: start from what HA restored."""
        if self._commanded is None and self.available:
            self._commanded = self.state.state
            self._commanded_at = self.state.last_changed

    @property
    def mode(self) -> str | None:
        if not self.available:
            return None
        if self.assumed:
            self._adopt_reported()
            return self._commanded
        return self.state.state

    @property
    def since(self) -> datetime | None:
        if not self.available:
            return None
        if self.assumed:
            self._adopt_reported()
            return self._commanded_at
        return self.state.last_changed

    def _record(self, mode: str) -> None:
        """Note a command. The mode age restarts only when the mode changes."""
        self._adopt_reported()
        if self._commanded != mode:
            self._commanded, self._commanded_at = mode, dt_util.utcnow()
            # A mode change may reset the device's setpoint: push it again.
            self._last_pushed = None

    async def async_set_mode(self, mode: str, context: Context | None) -> bool:
        """Command a mode. False when nothing was sent or the call failed."""
        async with self._lock:
            if not self.available:
                _LOGGER.debug(
                    "Skipping set_hvac_mode for unavailable %s", self.entity_id
                )
                return False
            supported = self.state.attributes.get("hvac_modes")
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
            if not self.assumed and self.state.state == mode:
                return True
            before = (self._commanded, self._commanded_at, self._last_pushed)
            self._record(mode)
            try:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_HVAC_MODE,
                    {ATTR_ENTITY_ID: self.entity_id, ATTR_HVAC_MODE: mode},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error(
                    "Error setting %s on %s. Error: %s", mode, self.entity_id, e
                )
                self._commanded, self._commanded_at, self._last_pushed = before
                return False
            return True

    async def async_turn_off(self, context: Context | None) -> None:
        async with self._lock:
            if not self.available:
                return
            before = (self._commanded, self._commanded_at, self._last_pushed)
            self._record(HVACMode.OFF)
            try:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_TURN_OFF,
                    {ATTR_ENTITY_ID: self.entity_id},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error("Error turning off %s. Error: %s", self.entity_id, e)
                self._commanded, self._commanded_at, self._last_pushed = before

    async def async_push_target(self, value: float, context: Context | None) -> None:
        async with self._lock:
            if not self.available:
                return
            features = self.state.attributes.get("supported_features")
            if (
                features is not None
                and not features & ClimateEntityFeature.TARGET_TEMPERATURE
            ):
                return
            attrs = self.state.attributes
            value = self._fit(value, attrs)
            current = self._last_pushed if self.assumed else attrs.get("temperature")
            if current == value:
                return
            try:
                await self.hass.services.async_call(
                    CLIMATE_DOMAIN,
                    SERVICE_SET_TEMPERATURE,
                    {ATTR_ENTITY_ID: self.entity_id, ATTR_TEMPERATURE: value},
                    context=context,
                    blocking=True,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error(
                    "Error setting target on %s. Error: %s", self.entity_id, e
                )
                return
            self._last_pushed = value

    @staticmethod
    def _fit(value: float, attrs: Mapping[str, Any]) -> float:
        """Round to the child's step (whole degrees if it has none), then clamp.

        The pushed value is one the child can hold, so what it reports back
        equals what was pushed and the "already set" check cannot loop.
        """
        step = attrs.get("target_temp_step") or 1
        value = round(round(value / step) * step, 4)
        low, high = attrs.get("min_temp"), attrs.get("max_temp")
        if low is not None:
            value = max(value, low)
        if high is not None:
            value = min(value, high)
        return value


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

    def __init__(
        self,
        child: ClimateChild,
        role_mode: Callable[[], HVACMode],
        target: Callable[[], float | None],
        offset: Callable[[], float],
        style: ControlStyle,
    ) -> None:
        self._child = child
        self._role_mode = role_mode
        self._target = target
        self._offset = offset
        self.self_regulating = style == ControlStyle.SETPOINT
        self.entity_id = child.entity_id
        self._released = False

    def release(self) -> None:
        if not self._released:  # idempotent: one reference per port, once
            self._released = True
            release_climate_child(self._child)

    @property
    def is_active(self) -> bool:
        return self._child.mode == self._role_mode()

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        if not min_cycle:  # none configured: nothing to wait for
            return True
        since = self._child.since
        return since is not None and dt_util.utcnow() - since >= min_cycle

    async def _push(self, context: Context | None) -> None:
        target = self._target()
        if target is not None:
            await self._child.async_push_target(target + self._offset(), context)

    async def async_turn_on(self, context: Context | None) -> None:
        if await self._child.async_set_mode(self._role_mode(), context):
            await self._push(context)

    async def async_sync(self, context: Context | None) -> None:
        # Only the role the child is serving may touch its setpoint.
        if self.is_active:
            await self._push(context)

    async def async_turn_off(self, context: Context | None) -> None:
        # Only the role the child is currently serving may stop it, so an idle
        # cooler's keep-alive can never switch off the heater on the same device.
        if self.is_active:
            await self._child.async_turn_off(context)

    async def async_stop(
        self, context: Context | None, keep_alive: bool = False
    ) -> None:
        # Off means off: whatever mode the child is in, even one no role owns.
        # An assumed child may have missed the last off, so a tick resends.
        if self._child.mode not in (None, HVACMode.OFF) or (
            keep_alive and self._child.assumed and self._child.available
        ):
            await self._child.async_turn_off(context)


def make_port(
    hass: HomeAssistant,
    entity_id: str,
    *,
    role_mode: Callable[[], HVACMode],
    target: Callable[[], float | None],
    offset: Callable[[], float] = lambda: 0.0,
    style: ControlStyle = ControlStyle.ON_OFF,
) -> EntityPort:
    """Build the port for a role from the entity domain."""
    if is_climate_entity(entity_id):
        return ClimatePort(
            acquire_climate_child(hass, entity_id), role_mode, target, offset, style
        )
    return SwitchPort(hass, entity_id)
