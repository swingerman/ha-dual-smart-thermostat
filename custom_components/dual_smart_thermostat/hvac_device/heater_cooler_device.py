import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import Context, HomeAssistant

from custom_components.dual_smart_thermostat.const import ToleranceDevice
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_device.controllable_hvac_device import (
    ControlableHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.cooler_device import (
    CoolerDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.heater_device import (
    HeaterDevice,
)
from custom_components.dual_smart_thermostat.hvac_device.hvac_device import (
    HVACDevice,
    merge_hvac_modes,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class HeaterCoolerDevice(HVACDevice, ControlableHVACDevice):

    def __init__(
        self,
        hass: HomeAssistant,
        heater_device: HeaterDevice,
        cooler_device: CoolerDevice,
        initial_hvac_mode: HVACMode,
        temperatures: TemperatureManager,
        openings: OpeningManager,
    ) -> None:
        super().__init__(hass, temperatures, openings)
        self._device_type = self.__class__.__name__
        self.heater_device = heater_device
        self.cooler_device = cooler_device

        # _hvac_modes are the combined values of the heater_device.hvac_modes and cooler_device.hvac_modes without duplicates
        device_hvac_modes = merge_hvac_modes(
            heater_device.hvac_modes, cooler_device.hvac_modes
        )

        self.hvac_modes = merge_hvac_modes(device_hvac_modes, [HVACMode.HEAT_COOL])

        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
        else:
            self._hvac_mode = None

    def set_context(self, context: Context):
        self.heater_device.set_context(context)
        self.cooler_device.set_context(context)
        self._context = context

    def get_device_ids(self) -> list[str]:
        device_ids = []
        if (
            hasattr(self.heater_device, "entity_id")
            and self.heater_device.entity_id is not None
        ):
            device_ids.append(self.heater_device.entity_id)
        else:
            device_ids += self.heater_device.get_device_ids()

        if (
            hasattr(self.cooler_device, "entity_id")
            and self.cooler_device.entity_id is not None
        ):
            device_ids.append(self.cooler_device.entity_id)
        else:
            device_ids += self.cooler_device.get_device_ids()

        return device_ids

    @property
    def is_active(self) -> bool:
        return self.heater_device.is_active or self.cooler_device.is_active

    @property
    def hvac_action(self) -> HVACAction:
        if self.heater_device.is_active:
            return HVACAction.HEATING
        if self.cooler_device.is_active:
            # cooler can be coler/fan device
            return self.cooler_device.hvac_action
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        return HVACAction.IDLE

    def on_startup(self):
        self.heater_device.on_startup()
        self.cooler_device.on_startup()

        self.async_control_hvac()

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.info({self.__class__.__name__})
        match self._hvac_mode:
            case HVACMode.COOL | HVACMode.FAN_ONLY:
                await self.heater_device.async_turn_off()
                await self.cooler_device.async_control_hvac(time, force)
            case HVACMode.HEAT:
                await self.cooler_device.async_turn_off()
                await self.heater_device.async_control_hvac(time, force)
            case HVACMode.HEAT_COOL:
                await self._async_control_heat_cool(time, force)
            case HVACMode.OFF:
                await self.async_turn_off()
            case _:
                _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)

    def is_cold_or_hot(self) -> tuple[bool, bool, ToleranceDevice]:
        """Check if the floor is too cold or too hot."""

        _LOGGER.debug("is_cold_or_hot")

        if self.heater_device.is_active:
            too_cold = self.temperatures.is_too_cold("_target_temp_low")
            too_hot = self.temperatures.is_too_hot("_target_temp_low")
            tolerance_device = ToleranceDevice.HEATER
        elif self.cooler_device.is_active:
            too_cold = self.temperatures.is_too_cold("_target_temp_high")
            too_hot = self.temperatures.is_too_hot("_target_temp_high")
            tolerance_device = ToleranceDevice.COOLER
        else:
            too_cold = self.temperatures.is_too_cold("_target_temp_low")
            too_hot = self.temperatures.is_too_hot("_target_temp_high")
            tolerance_device = ToleranceDevice.AUTO
        return too_cold, too_hot, tolerance_device

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        _LOGGER.info("Setting hvac mode to %s of %s", hvac_mode, self.hvac_modes)
        if hvac_mode in self.hvac_modes:
            _LOGGER.debug("hvac mode found")
            self._hvac_mode = hvac_mode

            if hvac_mode is not HVACMode.OFF:
                # handles HVACmode.HEAT
                if hvac_mode in self.heater_device.hvac_modes:
                    self.heater_device.hvac_mode = hvac_mode
                elif hvac_mode == HVACMode.HEAT_COOL:
                    self.heater_device.hvac_mode = HVACMode.HEAT
                # handles HVACmode.COOL
                if hvac_mode in self.cooler_device.hvac_modes:
                    self.cooler_device.hvac_mode = hvac_mode
                elif hvac_mode == HVACMode.HEAT_COOL:
                    self.cooler_device.hvac_mode = HVACMode.COOL
            else:
                self.heater_device.hvac_mode = hvac_mode
                self.cooler_device.hvac_mode = hvac_mode

        else:
            _LOGGER.debug("Hvac mode %s is not in %s", hvac_mode, self.hvac_modes)
            self._hvac_mode = HVACMode.OFF

        if self._hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
            self._hvac_action_reason = HVACActionReason.NONE
        else:
            await self.async_control_hvac(self, force=True)

        _LOGGER.info("Hvac mode set to %s", self._hvac_mode)

    async def _async_control_heat_cool(self, time=None, force=False) -> None:
        """Check if we need to turn heating on or off."""

        _LOGGER.info("_async_control_heat_cool")
        if not self._active and self.temperatures.cur_temp is not None:
            self._active = True

        if self.openings.any_opening_open:
            await self.async_turn_off()
            self._hvac_action_reason = HVACActionReason.OPENING
        elif self.temperatures.is_floor_hot:
            await self.heater_device.async_turn_off()
            self._hvac_action_reason = HVACActionReason.OVERHEAT
        elif self.temperatures.is_floor_cold:
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
        _LOGGER.debug("async_heater_cooler_toggle")
        too_cold, too_hot, tolerance_device = self.is_cold_or_hot()

        _LOGGER.debug(
            "too_cold: %s, too_hot: %s, tolerance_device: %s",
            too_cold,
            too_hot,
            tolerance_device,
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

    async def async_turn_on(self):
        await self.async_control_hvac()

    async def async_turn_off(self):
        await self.heater_device.async_turn_off()
        await self.cooler_device.async_turn_off()

    async def _async_check_device_initial_state(self) -> None:
        """Child devices on_startup handles this."""
        pass
