import logging
from typing import Callable

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import Context, HomeAssistant, callback

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_device.controllable_hvac_device import ControlableHVACDevice
from ..hvac_device.hvac_device import HVACDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class MultiHvacDevice(HVACDevice, ControlableHVACDevice):

    hvac_devices = []

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list[ControlableHVACDevice],
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass,
            environment,
            openings,
        )
        self._device_type = self.__class__.__name__

        self._features = features

        self.hvac_devices = devices

        self.init_hvac_modes(devices)

        self.set_initial_hvac_mode(initial_hvac_mode)

    def set_context(self, context: Context):
        for device in self.hvac_devices:
            device.set_context(context)

    def get_device_ids(self) -> list[str]:
        device_ids = []
        for device in self.hvac_devices:
            device_ids += device.get_device_ids()

        return device_ids

    def set_initial_hvac_mode(self, initial_hvac_mode: HVACMode):
        if initial_hvac_mode in self.hvac_modes:
            self._hvac_mode = initial_hvac_mode
            self.set_sub_devices_hvac_mode(initial_hvac_mode)
        else:
            self._hvac_mode = None

    @property
    def is_active(self) -> bool:
        for device in self.hvac_devices:
            if device.is_active:
                return True
        return False

    @property
    def hvac_mode(self) -> HVACMode:
        return self._hvac_mode

    @hvac_mode.setter
    def hvac_mode(self, hvac_mode: HVACMode):
        self._hvac_mode = hvac_mode
        if hvac_mode == HVACMode.OFF:
            for device in self.hvac_devices:
                device.hvac_mode = HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        for device in self.hvac_devices:
            if device.hvac_action != HVACAction.IDLE and device.is_active:
                return device.hvac_action

        return HVACAction.IDLE

    def set_sub_devices_hvac_mode(self, hvac_mode: HVACMode) -> None:
        _LOGGER.debug("Setting sub devices hvac mode to %s", hvac_mode)
        for device in self.hvac_devices:
            if hvac_mode in device.hvac_modes:
                device.hvac_mode = hvac_mode

    async def async_set_hvac_mode(self, hvac_mode: HVACMode):
        _LOGGER.info(
            "Attempting to set hvac mode to %s of %s", hvac_mode, self.hvac_modes
        )

        # sub function to handle off hvac mode
        @callback
        async def _async_handle_off_mode(*_) -> None:
            self.hvac_mode = HVACMode.OFF
            await self.async_turn_off()
            self._hvac_action_reason = HVACActionReason.NONE

        if hvac_mode not in self.hvac_modes:
            _LOGGER.debug("Hvac mode %s is not in %s", hvac_mode, self.hvac_modes)
            await _async_handle_off_mode()
            return

        if hvac_mode == HVACMode.OFF:
            await _async_handle_off_mode()
            return

        _LOGGER.debug("hvac mode found")
        self.hvac_mode = hvac_mode

        self.set_sub_devices_hvac_mode(hvac_mode)

        await self.async_control_hvac(force=True)

        _LOGGER.info("Hvac mode set to %s", self._hvac_mode)

    async def async_control_hvac(self, time=None, force: bool = False):
        _LOGGER.debug(
            "Controlling hvac %s, time: %s, force: %s", self._hvac_mode, time, force
        )
        if self._hvac_mode == HVACMode.OFF:
            await self.async_turn_off_all(time)

        if self._hvac_mode not in self.hvac_modes and self._hvac_mode is not None:
            _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)
            return

        for device in self.hvac_devices:
            if self.hvac_mode in device.hvac_modes:
                await device.async_control_hvac(time, force)
                self._hvac_action_reason = device.HVACActionReason
            elif device.is_active:
                await device.async_turn_off()

            # self._hvac_action_reason = device.HVACActionReason

    async def async_on_startup(self, async_write_ha_state_cb: Callable = None):
        self._async_write_ha_state_cb = async_write_ha_state_cb
        for device in self.hvac_devices:
            await device.async_on_startup(async_write_ha_state_cb)

    async def async_turn_on(self):
        await self.async_control_hvac(force=True)

    async def async_turn_off(self):
        await self.async_turn_off_all(time=None)

    async def async_turn_off_all(self, time):
        for device in self.hvac_devices:
            if device.is_active or time is not None:
                await device.async_turn_off()

    async def _async_check_device_initial_state(self) -> None:
        """Child devices on_startup handles this."""
        pass
