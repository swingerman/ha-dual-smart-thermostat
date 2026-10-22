from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant, State

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

    def setpoint_offset(self) -> float:
        return 0.0

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

    @property
    def supports_fan_mode(self) -> bool:
        """Return if fan supports speed control."""
        return self.speed.supports_fan_mode

    @property
    def fan_modes(self) -> list[str]:
        """Return list of available fan modes."""
        return self.speed.fan_modes

    @property
    def uses_preset_modes(self) -> bool:
        """Return if fan uses preset modes (vs percentage)."""
        return self.speed.uses_preset_modes

    @property
    def current_fan_mode(self) -> str | None:
        """Return current fan mode."""
        return self.speed.current_fan_mode

    def restore_fan_mode(self, fan_mode: str) -> None:
        """Restore fan mode from persisted state."""
        self.speed.restore_fan_mode(fan_mode)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set the fan speed mode."""
        await self.speed.async_set_fan_mode(fan_mode)

    def redetect_capabilities(self, entity_id: str, new_state: State) -> bool:
        """Retry detection once our entity shows up."""
        return self.speed.redetect_capabilities(entity_id, new_state)

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
