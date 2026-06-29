import logging

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_device.generic_hvac_device import GenericHVACDevice
from ..hvac_device.multi_hvac_device import MultiHvacDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class HeaterFanDevice(MultiHvacDevice):
    """Heater/heat pump combined with a fan.

    Mirrors :class:`CoolerFanDevice` for the heating side. When
    ``fan_on_with_heater`` is enabled the fan runs alongside the heater/heat
    pump while in a heating/cooling mode (the fan acts as the unit's air
    handler, issue #622). When disabled, the fan only runs in FAN_ONLY mode —
    matching the previous behavior of the generic multi device.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        devices: list[GenericHVACDevice],
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass, devices, initial_hvac_mode, environment, openings, features
        )

        self._device_type = self.__class__.__name__
        self._fan_on_with_heater = self._features.is_configured_for_fan_on_with_heater

        self.fan_device = next(
            (device for device in devices if HVACMode.FAN_ONLY in device.hvac_modes),
            None,
        )
        # The primary device is the heater or heat pump (everything but the fan).
        self.heater_device = next(
            (device for device in devices if device is not self.fan_device), None
        )

        if self.fan_device is None or self.heater_device is None:
            _LOGGER.error("Fan or heater device is not found")

    async def async_control_hvac(self, time=None, force=False):
        _LOGGER.debug(
            "%s async_control_hvac, mode: %s", self._device_type, self._hvac_mode
        )

        if self._hvac_mode == HVACMode.OFF:
            await self.async_turn_off_all(time)
            self._hvac_action_reason = HVACActionReason.NONE
            return

        if self._hvac_mode not in self.hvac_modes and self._hvac_mode is not None:
            _LOGGER.warning("Invalid HVAC mode: %s", self._hvac_mode)
            return

        if self._hvac_mode == HVACMode.FAN_ONLY:
            if self.heater_device.is_active:
                await self.heater_device.async_turn_off()
            await self.fan_device.async_control_hvac(time, force)
            self._hvac_action_reason = self.fan_device.HVACActionReason
            return

        # Heating/cooling mode: run the heater/heat pump. When opted in, the fan
        # runs alongside it as the air handler; otherwise it stays off (#622).
        await self.heater_device.async_control_hvac(time, force)
        self._hvac_action_reason = self.heater_device.HVACActionReason

        if self._fan_on_with_heater:
            await self.fan_device.async_turn_on()
        elif self.fan_device.is_active:
            await self.fan_device.async_turn_off()
