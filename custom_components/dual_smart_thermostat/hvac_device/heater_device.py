from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from ..hvac_action_reason.hvac_action_reason import HVACActionReason
from ..hvac_controller.heater_controller import HeaterHvacConroller
from ..hvac_controller.hvac_controller import HvacGoal
from ..hvac_device.generic_hvac_device import GenericHVACDevice
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.hvac_power_manager import HvacPowerManager
from ..managers.opening_manager import OpeningManager

_LOGGER = logging.getLogger(__name__)


class HeaterDevice(GenericHVACDevice):

    hvac_modes = [HVACMode.HEAT, HVACMode.OFF]

    def role_modes(self) -> tuple[HVACMode, ...]:
        return (HVACMode.HEAT,)

    def setpoint_offset(self) -> float:
        return self.features.heater_setpoint_offset

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
            hvac_goal=HvacGoal.RAISE,
        )

        self.hvac_controller = HeaterHvacConroller(
            self.port,
            min_cycle_duration,
            environment,
            openings,
            self.async_turn_on,
            self.async_turn_off,
        )

    @property
    def target_env_attr(self) -> str:
        return (
            "_target_temp_low" if self.features.is_range_mode else self._target_env_attr
        )

    def _is_comfort_floor_demand(self) -> bool:
        return self.environment.is_comfort_floor_demand(self.target_env_attr)

    # override: comfort floor is part of the heating goal, so every existing
    # safety rule (max floor, openings, min cycle) applies to it unchanged.
    def is_below_target_env_attr(self) -> bool:
        return super().is_below_target_env_attr() or self._is_comfort_floor_demand()

    # override
    def is_above_target_env_attr(self) -> bool:
        return (
            super().is_above_target_env_attr() and not self._is_comfort_floor_demand()
        )

    # override
    def target_env_attr_not_reached_reason(self) -> HVACActionReason:
        target = getattr(self.environment, self.target_env_attr)
        cur = self.environment.cur_temp
        if (
            None not in (cur, target)
            and cur >= target
            and self._is_comfort_floor_demand()
        ):
            return HVACActionReason.COMFORT_FLOOR
        return HVACActionReason.TARGET_TEMP_NOT_REACHED

    @property
    def hvac_action(self) -> HVACAction:
        _LOGGER.debug(
            "HeaterDevice hvac_action. is_active: %s, hvac_mode: %s",
            self.is_active,
            self.hvac_mode,
        )
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.HEATING
        return HVACAction.IDLE
