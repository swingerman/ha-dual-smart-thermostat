from datetime import timedelta
import logging
from typing import Callable

from homeassistant.components.climate import HVACMode
from homeassistant.components.valve import DOMAIN as VALVE_DOMAIN
from homeassistant.const import STATE_ON, STATE_OPEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConditionError
from homeassistant.helpers import condition
import homeassistant.util.dt as dt_util

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacController,
    HvacEnvStrategy,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)

_LOGGER = logging.getLogger(__name__)


class GenericHvacController(HvacController):

    entity_id: str
    min_cycle_duration: timedelta
    _hvac_action_reason: HVACActionReason

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id,
        min_cycle_duration: timedelta,
        environment: EnvironmentManager,
        openings: OpeningManager,
        turn_on_callback: Callable,
        turn_off_callback: Callable,
    ) -> None:
        self._controller_type = self.__class__.__name__

        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            turn_on_callback,
            turn_off_callback,
        )

        self._hvac_action_reason = HVACActionReason.NONE

    @property
    def _is_valve(self) -> bool:
        state = self.hass.states.get(self.entity_id)
        domain = state.domain if state else None
        return domain == VALVE_DOMAIN

    @property
    def hvac_action_reason(self) -> HVACActionReason:
        return self._hvac_action_reason

    @property
    def is_active(self) -> bool:
        """If the toggleable hvac device is currently active."""
        on_state = STATE_OPEN if self._is_valve else STATE_ON

        _LOGGER.info(
            "Checking if device is active: %s, on_state: %s",
            self.entity_id,
            on_state,
        )
        if self.entity_id is not None and self.hass.states.is_state(
            self.entity_id, on_state
        ):
            return True
        return False

    def ran_long_enough(self) -> bool:
        if self.is_active:
            current_state = STATE_ON
        else:
            current_state = HVACMode.OFF

        _LOGGER.debug("Checking if device ran long enough: %s", self.entity_id)
        _LOGGER.debug("current_state: %s", current_state)
        _LOGGER.debug("min_cycle_duration: %s", self.min_cycle_duration)
        _LOGGER.debug("time: %s", dt_util.utcnow())

        try:
            long_enough = condition.state(
                self.hass,
                self.entity_id,
                current_state,
                self.min_cycle_duration,
            )
        except ConditionError:
            long_enough = False

        return long_enough

    def needs_control(
        self, active: bool, hvac_mode: HVACMode, time=None, force=False
    ) -> bool:
        """Checks if the controller needs to continue."""
        if not active or hvac_mode == HVACMode.OFF:
            _LOGGER.debug(
                "Not active or hvac mode is off active: %s, _hvac_mode: %s",
                active,
                hvac_mode,
            )
            return False

        if not force and time is None:
            # If the `force` argument is True, we
            # ignore `min_cycle_duration`.
            # If the `time` argument is not none, we were invoked for
            # keep-alive purposes, and `min_cycle_duration` is irrelevant.
            if self.min_cycle_duration:
                _LOGGER.debug(
                    "Checking if device ran long enough: %s", self.ran_long_enough()
                )
                return self.ran_long_enough()
        return True

    async def async_control_device_when_on(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when theheater is on."""

        _LOGGER.info("%s Controlling hvac while on", self.__class__.__name__)
        _LOGGER.debug("below_env_attr: %s", strategy.hvac_goal_reached)
        _LOGGER.debug("any_opening_open: %s", any_opening_open)
        _LOGGER.debug("hvac_goal_reached: %s", strategy.hvac_goal_reached)

        if strategy.hvac_goal_reached or any_opening_open:
            _LOGGER.info(
                "Turning off entity due to hvac goal reached or opening is open %s",
                self.entity_id,
            )

            await self.async_turn_off_callback()

            if strategy.hvac_goal_reached:
                _LOGGER.debug("setting hvac_action_reason goal reached")
                self._hvac_action_reason = strategy.goal_reached_reason()
            if any_opening_open:
                _LOGGER.debug("setting hvac_action_reason opening")
                self._hvac_action_reason = HVACActionReason.OPENING

        elif time is not None and not any_opening_open:
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning on entity (from active) %s",
                self.entity_id,
            )
            await self.async_turn_on_callback()
            self._hvac_action_reason = strategy.goal_not_reached_reason()
        else:
            _LOGGER.debug("No case matched when - keep device on")

    async def async_control_device_when_off(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.info("%s Controlling hvac while off", self.__class__.__name__)
        _LOGGER.debug("above_env_attr: %s", strategy.hvac_goal_reached)
        _LOGGER.debug("below_env_attr: %s", strategy.hvac_goal_not_reached)
        _LOGGER.debug("any_opening_open: %s", any_opening_open)
        _LOGGER.debug("is_active: %s", True)
        _LOGGER.debug("time: %s", time)

        if strategy.hvac_goal_not_reached and not any_opening_open:
            _LOGGER.info(
                "Turning on entity (from inactive) due to hvac goal is not reached %s",
                self.entity_id,
            )
            await self.async_turn_on_callback()
            self._hvac_action_reason = strategy.goal_not_reached_reason()
        elif time is not None or any_opening_open:
            # The time argument is passed only in keep-alive case
            _LOGGER.info("Keep-alive - Turning off entity %s", self.entity_id)
            await self.async_turn_off_callback()

            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING
        else:
            _LOGGER.debug("No case matched when - keeping device off")
