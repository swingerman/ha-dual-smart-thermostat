"""How a device role talks to its entity.

The one place that knows what "on" means for an entity and how to command it.
Controllers and devices call these methods; they never read the entity's state
or call its services themselves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
import logging
from typing import Callable

from homeassistant.components.climate import HVACMode
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
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

    @abstractmethod
    async def async_stop(self, context: Context | None) -> None:
        """DST is Off: make sure the entity is off. Off means off."""


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
    def is_active(self) -> bool:
        on_state = STATE_OPEN if self._is_valve else STATE_ON
        return self.hass.states.is_state(self.entity_id, on_state)

    def ran_long_enough(self, min_cycle: timedelta) -> bool:
        current_state = STATE_ON if self.is_active else HVACMode.OFF
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

    async def async_stop(self, context: Context | None) -> None:
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
        except Exception as e:
            _LOGGER.error(
                "Error calling %s on %s. Error: %s", service, self.entity_id, e
            )


def make_port(
    hass: HomeAssistant,
    entity_id: str,
    *,
    role_mode: Callable[[], HVACMode | None],
    target: Callable[[], float | None],
) -> EntityPort:
    """Build the port for a role from the entity domain."""
    return SwitchPort(hass, entity_id)
