from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_controller.cooler_controller import CoolerHvacController
from ..hvac_controller.hvac_controller import HvacGoal
from ..hvac_device.generic_hvac_device import GenericHVACDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.hvac_power_manager import HvacPowerManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class CoolerDevice(GenericHVACDevice):

    hvac_modes = [HVACMode.COOL, HVACMode.OFF]

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
            hvac_goal=HvacGoal.LOWER,
        )

        self.hvac_controller = CoolerHvacController(
            hass,
            entity_id,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

    @property
    def target_env_attr(self) -> str:
        return (
            "_target_temp_high"
            if self.features.is_range_mode
            else self._target_env_attr
        )

    # override
    def is_below_target_env_attr(self) -> bool:
        """Check if temperature is below target.

        Fix for issue #10: When cooler is active IN RANGE MODE (heat/cool mode),
        check if target is reached WITHOUT subtracting cold_tolerance. The cooler
        should turn off when it reaches the setpoint, not setpoint - cold_tolerance.

        In standalone mode, use tolerance for hysteresis to prevent rapid cycling.
        """
        if self.is_active and self.features.is_range_mode:
            # Cooler is ON in heat/cool mode: turn off when target is reached
            target_temp = getattr(self.environment, self.target_env_attr)
            if self.environment.cur_temp is None or target_temp is None:
                return False
            return self.environment.cur_temp <= target_temp
        else:
            # Cooler is OFF or in standalone mode: use tolerance
            return self.environment.is_too_cold(self.target_env_attr)

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.COOLING
        return HVACAction.IDLE
