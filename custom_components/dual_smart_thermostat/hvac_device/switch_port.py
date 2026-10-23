"""Port for switch / input_boolean / valve entities."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN, ValveEntityFeature
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, State
from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition

from .entity_port import EntityPort, _call_service, is_unavailable

_LOGGER = logging.getLogger(__name__)


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
