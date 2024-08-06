import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_system import US_CUSTOMARY_SYSTEM

from custom_components.dual_smart_thermostat.const import (
    CONF_HVAC_POWER_LEVELS,
    CONF_HVAC_POWER_MAX,
    CONF_HVAC_POWER_MIN,
    CONF_HVAC_POWER_TOLERANCE,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacEnvStrategy,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentAttributeType,
    EnvironmentManager,
)

_LOGGER = logging.getLogger(__name__)


class HvacPowerManager:

    _hvac_power_level = 0
    _hvac_power_percent = 0

    def __init__(
        self, hass: HomeAssistant, config: ConfigType, environment: EnvironmentManager
    ) -> None:
        self.hass = hass
        self.config = config
        self.environment = environment

        self._hvac_power_levels = config.get(CONF_HVAC_POWER_LEVELS) or 5

        hvac_power_min = config.get(CONF_HVAC_POWER_MIN)
        hvac_power_max = config.get(CONF_HVAC_POWER_MAX)

        self._hvac_power_tolerance = config.get(CONF_HVAC_POWER_TOLERANCE)

        # don't allow min to be greater than max
        # TODO: cover these cases with tests
        if (
            hvac_power_min is not None
            and hvac_power_max is not None
            and hvac_power_min > hvac_power_max
        ):
            raise ValueError(
                f"{CONF_HVAC_POWER_MIN} must be less than {CONF_HVAC_POWER_MAX}"
            )

        # don't allow min to be greater than power levels
        if hvac_power_min is not None and hvac_power_min > self._hvac_power_levels:
            raise ValueError(
                f"{CONF_HVAC_POWER_MIN} must be less than or equal to {CONF_HVAC_POWER_LEVELS}"
            )

        # don't allow max to be greater than power levels
        if hvac_power_max is not None and hvac_power_max > self._hvac_power_levels:
            raise ValueError(
                f"{CONF_HVAC_POWER_MAX} must be less than or equal to {CONF_HVAC_POWER_LEVELS}"
            )

        self._hvac_power_min = hvac_power_min or 1
        self._hvac_power_max = hvac_power_max or self._hvac_power_levels

        self._hvac_power_min_percent = (
            self._hvac_power_min / self._hvac_power_levels * 100
        )
        self._hvac_power_max_percent = (
            self._hvac_power_max / self._hvac_power_levels * 100
        )

    @property
    def hvac_power_level(self) -> int:
        return self._hvac_power_level

    @property
    def hvac_power_percent(self) -> int:
        return self._hvac_power_percent

    def _get_hvac_power_tolerance(self, is_temperature: bool) -> int:
        """handles the default value for the hvac power tolerance
        based on the unit system and the environment attribute"""

        is_imperial = self.hass.config.units is US_CUSTOMARY_SYSTEM
        default_imperial_tolerance = 33
        default_metric_tolerance = 1

        default_temperatue_tolerance = (
            default_imperial_tolerance if is_imperial else default_metric_tolerance
        )

        default_tolerance = (
            default_temperatue_tolerance if is_temperature else default_metric_tolerance
        )

        return (
            self._hvac_power_tolerance
            if self._hvac_power_tolerance is not None
            else default_tolerance
        )

    def update_hvac_power(
        self, strategy: HvacEnvStrategy, target_env_attr: str
    ) -> None:
        """updates the hvac power level based on the strategy and the target environment attribute"""

        _LOGGER.debug("Updating hvac power")

        goal_reached = strategy.hvac_goal_reached
        goal_not_reached = strategy.hvac_goal_not_reached

        if goal_reached:
            _LOGGER.debug("Updating hvac power because goal reached")
            self._hvac_power_level = 0
            self._hvac_power_percent = 0
            return

        if goal_not_reached:
            _LOGGER.debug("Updating hvac power because goal not reached")
            self._calculate_power(target_env_attr)

    def _calculate_power(self, target_env_attr: str):
        env_attribute_type = self.environment.get_env_attr_type(target_env_attr)
        is_temperature = env_attribute_type is EnvironmentAttributeType.TEMPERATURE

        match env_attribute_type:
            case EnvironmentAttributeType.TEMPERATURE:
                curr_env_value = self.environment.cur_temp
            case EnvironmentAttributeType.HUMIDITY:
                curr_env_value = self.environment.cur_humidity
            case _:
                raise ValueError(
                    f"Unsupported environment attribute type: {env_attribute_type}"
                )

        target_env_value = getattr(self.environment, target_env_attr)

        power_tolerance = self._get_hvac_power_tolerance(is_temperature)

        step_value = power_tolerance / self._hvac_power_levels

        env_difference = abs(curr_env_value - target_env_value)

        _LOGGER.debug("step value: %s", step_value)
        _LOGGER.debug("env difference: %s", env_difference)

        self._hvac_power_level = self._calculate_power_level(step_value, env_difference)
        self._hvac_power_percent = self._calculate_power_percent(
            env_difference, power_tolerance
        )

    def _calculate_power_level(self, step_value: float, env_difference: float) -> int:
        # calculate the power level
        # should increase or decrease the power level based on the difference between the current and target temperature
        _LOGGER.debug("Calculating hvac power level")

        calculated_power_level = round(env_difference / step_value, 0)

        return max(
            self._hvac_power_min, min(calculated_power_level, self._hvac_power_max)
        )

    def _calculate_power_percent(
        self, env_difference: float, power_tolerance: float
    ) -> int:
        # calculate the power percent
        # should increase or decrease the power level based on the difference between the current and target temperature
        _LOGGER.debug("Calculating hvac power percent")

        calculated_power_percent = round(env_difference / power_tolerance * 100, 0)

        return max(
            self._hvac_power_min_percent,
            min(
                calculated_power_percent,
                self._hvac_power_max_percent,
            ),
        )

    # TODO: apply preset (verify min/max)
