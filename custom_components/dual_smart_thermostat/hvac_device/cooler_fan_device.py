import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_hvac_device import (
    MultiHvacDevice,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)

_LOGGER = logging.getLogger(__name__)


class CoolerFanDevice(MultiHvacDevice):

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass, devices, initial_hvac_mode, environment, openings, features
        )

        self._device_type = self.__class__.__name__
        self._fan_on_with_cooler = self._features.is_configured_for_fan_on_with_cooler

        self.cooler_device = next(
            device for device in devices if HVACMode.COOL in device.hvac_modes
        )
        self.fan_device = next(
            device for device in devices if HVACMode.FAN_ONLY in device.hvac_modes
        )

        if self.fan_device is None or self.cooler_device is None:
            _LOGGER.error("Fan or cooler device is not found")
            return

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @MultiHvacDevice.hvac_mode.setter
    def hvac_mode(self, hvac_mode: HVACMode):  # noqa: F811

        _LOGGER.debug("Setter setting hvac_mode: %s", hvac_mode)
        self._hvac_mode = hvac_mode
        self.set_sub_devices_hvac_mode(hvac_mode)

    async def _async_check_device_initial_state(self) -> None:
        """Prevent the device from keep running if HVACMode.OFF."""
        pass

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.info({self.__class__.__name__})
        _LOGGER.debug("hvac_mode: %s", self._hvac_mode)
        match self._hvac_mode:
            case HVACMode.COOL:
                if self._fan_on_with_cooler:
                    await self.fan_device.async_control_hvac(time, force)
                    await self.cooler_device.async_control_hvac(time, force)
                    self.HVACActionReason = self.cooler_device.HVACActionReason
                else:

                    is_within_fan_tolerance = self.environment.is_within_fan_tolerance(
                        self.fan_device.target_temp_attr
                    )
                    is_warmer_outside = self.environment.is_warmer_outside
                    is_fan_air_outside = self.fan_device.fan_air_surce_outside

                    if is_within_fan_tolerance and not (
                        is_fan_air_outside and is_warmer_outside
                    ):
                        _LOGGER.debug("within fan tolerance")
                        self.fan_device.hvac_mode = HVACMode.FAN_ONLY
                        await self.fan_device.async_control_hvac(time, force)
                        await self.cooler_device.async_turn_off()
                        self.HVACActionReason = (
                            HVACActionReason.TARGET_TEMP_NOT_REACHED_WITH_FAN
                        )
                    else:
                        _LOGGER.debug("outside fan tolerance")
                        await self.cooler_device.async_control_hvac(time, force)
                        await self.fan_device.async_turn_off()
                        self.HVACActionReason = self.cooler_device.HVACActionReason

            case HVACMode.FAN_ONLY:
                await self.cooler_device.async_turn_off()
                await self.fan_device.async_control_hvac(time, force)
                self.HVACActionReason = self.fan_device.HVACActionReason
            case HVACMode.OFF:
                await self.async_turn_off()
                self.HVACActionReason = HVACActionReason.NONE
            case _:
                if self._hvac_mode is not None:
                    _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)
