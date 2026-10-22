from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_device.cooler_device import CoolerDevice
from ..hvac_device.fan_speed import FanSpeedControl
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.hvac_power_manager import HvacPowerManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class FanDevice(CoolerDevice):

    hvac_modes = [HVACMode.FAN_ONLY, HVACMode.OFF]
    fan_air_surce_outside = False
    pushes_setpoint = False

    def role_mode(self) -> HVACMode:
        return HVACMode.FAN_ONLY

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
        hvac_power: HvacPowerManager,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
            hvac_power,
        )

        if self.features.is_fan_uses_outside_air:
            self.fan_air_surce_outside = True

        # Fan speed control capabilities (detected on construction)
        self.speed = FanSpeedControl(hass, entity_id)

    async def async_turn_on(self):
        """Turn on the fan and apply the selected fan mode."""
        # First turn on the fan using parent class logic
        await super().async_turn_on()

        # Then apply fan mode if supported and a mode is set
        # A climate's port already re-applied the speed after setting the mode.
        if (
            not self.speed.is_climate
            and self.speed.supports_fan_mode
            and self.speed.current_fan_mode is not None
        ):
            _LOGGER.debug(
                "Applying fan mode %s after turning on %s",
                self.speed.current_fan_mode,
                self.entity_id,
            )
            try:
                await self.speed.async_set_fan_mode(self.speed.current_fan_mode)
            except Exception as e:
                _LOGGER.warning(
                    "Failed to apply fan mode %s after turning on %s: %s",
                    self.speed.current_fan_mode,
                    self.entity_id,
                    e,
                )

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.FAN
        return HVACAction.IDLE
