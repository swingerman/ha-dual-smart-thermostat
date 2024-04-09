from datetime import timedelta
import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.specific_hvac_device import (
    SpecificHVACDevice,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class HeaterDevice(SpecificHVACDevice):

    hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        temperatures: TemperatureManager,
        openings: OpeningManager,
        range_mode: bool = False,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            temperatures,
            openings,
        )

        if range_mode:
            self._target_temp_attr = "_target_temp_low"

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.debug({self.__class__.__name__})
        _LOGGER.debug("async_control_hvac")
        self._set_self_active()

        if not self._needs_control(time, force):
            _LOGGER.debug("No need for control")
            return

        _LOGGER.debug("Needs control")

        if self.is_active:
            await self._async_control_device_when_on(time)
        else:
            await self._async_control_device_when_off(time)

    async def _async_control_device_when_on(self, time=None) -> None:
        """Check if we need to turn heating on or off when theheater is on."""
        too_hot = self.temperatures.is_too_hot(self._target_temp_attr)
        is_floor_hot = self.temperatures.is_floor_hot
        is_floor_cold = self.temperatures.is_floor_cold
        any_opening_open = self.openings.any_opening_open

        _LOGGER.debug("_async_control_device_when_on, floor cold: %s", is_floor_cold)

        if ((too_hot or is_floor_hot) or any_opening_open) and not is_floor_cold:
            _LOGGER.debug("Turning off heater %s", self.entity_id)

            await self.async_turn_off()

            if too_hot:
                self._HVACActionReason = HVACActionReason.TARGET_TEMP_REACHED
            if is_floor_hot:
                self._HVACActionReason = HVACActionReason.OVERHEAT
            if self.openings.any_opening_open:
                self._HVACActionReason = HVACActionReason.OPENING

        elif time is not None and not any_opening_open and not is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.info(
                "Keep-alive - Turning on heater (from active) %s",
                self.entity_id,
            )
            self._HVACActionReason = HVACActionReason.TARGET_TEMP_NOT_REACHED
            await self.async_turn_on()

    async def _async_control_device_when_off(self, time=None) -> None:
        """Check if we need to turn heating on or off when the heater is off."""
        _LOGGER.debug("%s _async_control_device_when_off", self.__class__.__name__)

        too_cold = self.temperatures.is_too_cold(self._target_temp_attr)
        is_floor_hot = self.temperatures.is_floor_hot
        is_floor_cold = self.temperatures.is_floor_cold
        any_opening_open = self.openings.any_opening_open

        if (too_cold and not any_opening_open and not is_floor_hot) or is_floor_cold:
            _LOGGER.debug("Turning on heater (from inactive) %s", self.entity_id)

            await self.async_turn_on()

            if is_floor_cold:
                self._HVACActionReason = HVACActionReason.LIMIT
            else:
                self._HVACActionReason = HVACActionReason.TARGET_TEMP_NOT_REACHED

        elif time is not None or any_opening_open or is_floor_hot:
            # The time argument is passed only in keep-alive case
            _LOGGER.debug("Keep-alive - Turning off heater %s", self.entity_id)
            await self.async_turn_off()

            if is_floor_hot:
                self._HVACActionReason = HVACActionReason.OVERHEAT
            if self.openings.any_opening_open:
                self._HVACActionReason = HVACActionReason.OPENING
