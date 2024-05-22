import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.const import ToleranceDevice
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    merge_hvac_modes,
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


class HeaterCoolerDevice(MultiHvacDevice):

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

        self.heater_device = next(
            device for device in devices if HVACMode.HEAT in device.hvac_modes
        )
        self.cooler_device = next(
            device for device in devices if HVACMode.COOL in device.hvac_modes
        )

        if self.heater_device is None or self.cooler_device is None:
            _LOGGER.error("Heater or cooler device is not found")
            return

        if self._features.is_configured_for_heat_cool_mode:
            self.hvac_modes = merge_hvac_modes(self.hvac_modes, [HVACMode.HEAT_COOL])

        self.set_initial_hvac_mode(initial_hvac_mode)

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @hvac_mode.setter
    def hvac_mode(self, hvac_mode: HVACMode):
        if hvac_mode == HVACMode.HEAT_COOL:
            self.heater_device.hvac_mode = HVACMode.HEAT
            self.cooler_device.hvac_mode = HVACMode.COOL
        else:
            self.set_sub_devices_hvac_mode(hvac_mode)
        self._hvac_mode = hvac_mode

    async def async_control_hvac(self, time=None, force: bool = False):

        _LOGGER.debug(
            "async_control_hvac. hvac_mode: %s, force: %s", self._hvac_mode, force
        )

        supports_heat_cool = HVACMode.HEAT_COOL in self.hvac_modes

        if supports_heat_cool and self.hvac_mode == HVACMode.HEAT_COOL:
            await self._async_control_heat_cool(time, force)
            return

        await super().async_control_hvac(time, force)

    def is_cold_or_hot(self) -> tuple[bool, bool, ToleranceDevice]:
        """Check if the floor is too cold or too hot."""

        _LOGGER.debug("is_cold_or_hot")
        _LOGGER.debug("heater_device.is_active: %s", self.heater_device.is_active)
        _LOGGER.debug("cooler_device.is_active: %s", self.cooler_device.is_active)

        if self.heater_device.is_active:
            too_cold = self.environment.is_too_cold("_target_temp_low")
            too_hot = self.environment.is_too_hot("_target_temp_low")
            tolerance_device = ToleranceDevice.HEATER
        elif self.cooler_device.is_active:
            too_cold = self.environment.is_too_cold("_target_temp_high")
            too_hot = self.environment.is_too_hot("_target_temp_high")
            tolerance_device = ToleranceDevice.COOLER
        else:
            too_cold = self.environment.is_too_cold("_target_temp_low")
            too_hot = self.environment.is_too_hot("_target_temp_high")
            tolerance_device = ToleranceDevice.AUTO
        return too_cold, too_hot, tolerance_device

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):

        _LOGGER.debug("async_set_hvac_mode %s", hvac_mode)
        if hvac_mode == HVACMode.HEAT_COOL:
            _LOGGER.debug("async_set_hvac_mode heat_cool setting devices hvac_modes")
            self.heater_device.hvac_mode = HVACMode.HEAT
            self.cooler_device.hvac_mode = HVACMode.COOL

        await super().async_set_hvac_mode(hvac_mode)

    async def _async_control_heat_cool(self, time=None, force=False) -> None:
        """Check if we need to turn heating on or off."""

        _LOGGER.info("_async_control_heat_cool. time: %s, force: %s", time, force)
        if not self._active and self.environment.cur_temp is not None:
            self._active = True

        if self.openings.any_opening_open(self.hvac_mode):
            await self.async_turn_off()
            self._hvac_action_reason = HVACActionReason.OPENING
        elif self.environment.is_floor_hot and self.heater_device.is_active:
            await self.heater_device.async_turn_off()
            self._hvac_action_reason = HVACActionReason.OVERHEAT
        elif self.environment.is_floor_cold:
            await self.heater_device.async_turn_on()
            self._hvac_action_reason = HVACActionReason.LIMIT
        else:
            await self.async_heater_cooler_toggle(time, force)

        if time is not None:
            # The time argument is passed only in keep-alive case
            _LOGGER.info("Keep-alive - Toggling on heater cooler")
            await self.async_heater_cooler_toggle(time, force)

    async def async_heater_cooler_toggle(self, time=None, force=False) -> None:
        """Toggle heater cooler based on temp and tolarance."""
        _LOGGER.debug("async_heater_cooler_toggle time: %s, force: %s", time, force)
        too_cold, too_hot, tolerance_device = self.is_cold_or_hot()

        _LOGGER.debug(
            "too_cold: %s, too_hot: %s, tolerance_device: %s, force: %s ",
            too_cold,
            too_hot,
            tolerance_device,
            force,
        )
        match tolerance_device:
            case ToleranceDevice.HEATER:
                await self.heater_device.async_control_hvac(time, force)
                self._hvac_action_reason = self.heater_device.HVACActionReason
            case ToleranceDevice.COOLER:
                await self.cooler_device.async_control_hvac(time, force)
                self._hvac_action_reason = self.cooler_device.HVACActionReason
            case _:
                await self._async_auto_toggle(too_cold, too_hot, time, force)

    async def _async_auto_toggle(
        self, too_cold, too_hot, time=None, force=False
    ) -> None:
        _LOGGER.debug("_async_auto_toggle")
        _LOGGER.debug("too_cold: %s, too_hot: %s", too_cold, too_hot)
        _LOGGER.debug("time: %s, force: %s", time, force)
        if too_cold:
            await self.heater_device.async_control_hvac(time, force)
            self._hvac_action_reason = self.heater_device.HVACActionReason
            await self.cooler_device.async_turn_off()
        elif too_hot:
            await self.cooler_device.async_control_hvac(time, force)
            self._hvac_action_reason = self.cooler_device.HVACActionReason
            await self.heater_device.async_turn_off()
        else:
            await self.heater_device.async_turn_off()
            await self.cooler_device.async_turn_off()
            self._hvac_action_reason = HVACActionReason.TARGET_TEMP_REACHED

    async def _async_check_device_initial_state(self) -> None:
        """Child devices on_startup handles this."""
        pass
