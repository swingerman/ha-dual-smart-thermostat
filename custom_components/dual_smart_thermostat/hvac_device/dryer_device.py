from datetime import timedelta
import logging

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacGoal,
)
from custom_components.dual_smart_thermostat.hvac_device.generic_hvac_device import (
    GenericHVACDevice,
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


class DryerDevice(GenericHVACDevice):

    _target_env_attr: str = "_target_humidity"

    hvac_modes = [HVACMode.DRY, HVACMode.OFF]

    def __init__(
        self,
        hass: HomeAssistant,
        entity_id: str,
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
    ) -> None:
        super().__init__(
            hass,
            entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
            hvac_goal=HvacGoal.LOWER,
        )

    @property
    def hvac_action(self) -> HVACAction:
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        if self.is_active:
            return HVACAction.DRYING
        return HVACAction.IDLE

    # override
    def _set_self_active(self) -> None:
        """Checks if active state needs to be set true."""
        _LOGGER.debug("_active: %s", self._active)
        _LOGGER.debug("cur_humidity: %s", self.environment.cur_humidity)
        _LOGGER.debug("target_env_attr: %s", self.target_env_attr)
        target_humidity = getattr(self.environment, self.target_env_attr)
        _LOGGER.debug("target_humidity: %s", target_humidity)

        if (
            not self._active
            and None not in (self.environment.cur_humidity, target_humidity)
            and self._hvac_mode != HVACMode.OFF
        ):
            self._active = True
            _LOGGER.debug(
                "Obtained current and target humidity. Device active. %s, %s",
                self.environment.cur_humidity,
                target_humidity,
            )

    # override
    def target_env_attr_reached_reason(self) -> HVACActionReason:
        return HVACActionReason.TARGET_HUMIDITY_REACHED

    # override
    def target_env_attr_not_reached_reason(self) -> HVACActionReason:
        return HVACActionReason.TARGET_HUMIDITY_NOT_REACHED

    # override
    def is_below_target_env_attr(self) -> bool:
        """is too dry?"""
        return self.environment.is_too_dry

    # override
    def is_above_target_env_attr(self) -> bool:
        """is too moist?"""
        return self.environment.is_too_moist
