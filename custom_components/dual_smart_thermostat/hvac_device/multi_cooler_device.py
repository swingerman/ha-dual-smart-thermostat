"""Multi-cooler device that controls multiple cooler switches as one unit."""

from datetime import timedelta
from typing import List

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_controller.cooler_controller import (
    CoolerHvacController,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacGoal,
)
from custom_components.dual_smart_thermostat.hvac_device.multi_switch_device import (
    MultiSwitchDevice,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.hvac_power_manager import (
    HvacPowerManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)


class MultiCoolerDevice(MultiSwitchDevice):
    """A cooler device that controls multiple cooler switches as one unit."""

    hvac_modes = [HVACMode.COOL, HVACMode.OFF]

    def __init__(
        self,
        hass: HomeAssistant,
        entity_ids: List[str],
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
        hvac_power: HvacPowerManager,
    ) -> None:
        super().__init__(
            hass,
            entity_ids,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
            hvac_power,
            hvac_goal=HvacGoal.LOWER,
        )

        # Use the first entity ID for the controller
        primary_entity_id = entity_ids[0] if entity_ids else None
        self.hvac_controller = CoolerHvacController(
            hass,
            primary_entity_id,
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

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.COOLING
        return HVACAction.IDLE