from datetime import timedelta
import logging
from typing import Callable

from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_controller.generic_controller import (
    GenericHvacController,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacEnvStrategy,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)

_LOGGER = logging.getLogger(__name__)


class HeaterHvacConroller(GenericHvacController):

    def __init__(
        self,
        hass: HomeAssistant,
        heater_entity_id: str,
        min_cycle_duration: timedelta,
        environment: EnvironmentManager,
        openings: OpeningManager,
        turn_on_callback: Callable,
        turn_off_callback: Callable,
    ) -> None:
        super().__init__(
            hass,
            heater_entity_id,
            min_cycle_duration,
            environment,
            openings,
            turn_on_callback,
            turn_off_callback,
        )

    # override
    async def async_control_device_when_on(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when theheater is on."""

        _LOGGER.info("%s Controlling hvac while on", self.__class__.__name__)

        too_hot = strategy.hvac_goal_reached
        is_floor_hot = self._environment.is_floor_hot
        is_floor_cold = self._environment.is_floor_cold

        _LOGGER.debug("_async_control_device_when_on, floor cold: %s", is_floor_cold)
        _LOGGER.debug("_async_control_device_when_on, floor hot: %s", is_floor_hot)
        _LOGGER.debug("_async_control_device_when_on, too_hot: %s", too_hot)

        if ((too_hot or is_floor_hot) or any_opening_open) and not is_floor_cold:
            _LOGGER.debug("Turning off heater %s", self.entity_id)

            await self.async_turn_off_callback()

            if too_hot:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_REACHED
            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING

        elif time is not None and not any_opening_open and not is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning on heater (from active) %s",
                self.entity_id,
            )
            self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED
            await self.async_turn_on_callback()

    # override
    async def async_control_device_when_off(
        self,
        strategy: HvacEnvStrategy,
        any_opening_open: bool,
        time=None,
    ) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.info("%s Controlling hvac while off", self.__class__.__name__)

        too_cold = strategy.hvac_goal_not_reached
        _LOGGER.debug("too_cold: %s", strategy.hvac_goal_reached)

        is_floor_hot = self._environment.is_floor_hot
        is_floor_cold = self._environment.is_floor_cold

        if (too_cold and not any_opening_open and not is_floor_hot) or is_floor_cold:
            _LOGGER.info("Turning on heater (from inactive) %s", self.entity_id)

            await self.async_turn_on_callback()

            if is_floor_cold:
                self._hvac_action_reason = HVACActionReason.LIMIT
            else:
                self._hvac_action_reason = HVACActionReason.TARGET_TEMP_NOT_REACHED

        elif time is not None or any_opening_open or is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.debug("Keep-alive - Turning off heater %s", self.entity_id)
            await self.async_turn_off_callback()

            if is_floor_hot:
                self._hvac_action_reason = HVACActionReason.OVERHEAT
            if any_opening_open:
                self._hvac_action_reason = HVACActionReason.OPENING

        else:
            _LOGGER.debug(
                "No case matched - keeping device off - too_cold: %s, any_opening_open: %s, is_floor_hot: %s, is_floor_cold: %s, time: %s. Taking default action to turn off heater.",
                too_cold,
                any_opening_open,
                is_floor_hot,
                is_floor_cold,
                time,
            )
            # await self.async_turn_off_callback()
            _LOGGER.debug(
                "Setting hvac_action_reason. Target temp recached: %s",
                strategy.hvac_goal_reached,
            )
            if strategy.hvac_goal_reached:
                self._hvac_action_reason = strategy.goal_reached_reason()
            else:
                self._hvac_action_reason = strategy.goal_not_reached_reason()
