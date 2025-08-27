import logging

from homeassistant.components.climate.const import (
    PRESET_NONE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.typing import ConfigType

from ..const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_HVAC_POWER_LEVELS,
    CONF_HVAC_POWER_TOLERANCE,
)
from ..managers.environment_manager import EnvironmentManager
from ..managers.state_manager import StateManager
from ..preset_env.preset_env import PresetEnv

_LOGGER = logging.getLogger(__name__)


class FeatureManager(StateManager):

    def __init__(
        self, hass: HomeAssistant, config: ConfigType, environment: EnvironmentManager
    ) -> None:
        self.hass = hass
        self.environment = environment
        self._cooler_entity_id = config.get(CONF_COOLER)
        self._heater_entity_id = config.get(CONF_HEATER)
        self._ac_mode = config.get(CONF_AC_MODE)
        if self._cooler_entity_id is not None and self._heater_entity_id is not None:
            self._ac_mode = False

        self._fan_mode = config.get(CONF_FAN_MODE)
        self._fan_entity_id = config.get(CONF_FAN)
        self._fan_on_with_cooler = config.get(CONF_FAN_ON_WITH_AC)
        self._fan_tolerance = config.get(CONF_FAN_HOT_TOLERANCE)
        self._fan_air_outside = config.get(CONF_FAN_AIR_OUTSIDE)
        self._fan_tolerance_on_entity_id = config.get(CONF_FAN_HOT_TOLERANCE_TOGGLE)

        self._dryer_entity_id = config.get(CONF_DRYER)
        self._humidity_sensor_entity_id = config.get(CONF_HUMIDITY_SENSOR)
        self._heat_pump_cooling_entity_id = config.get(CONF_HEAT_PUMP_COOLING)

        self._aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self._aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)
        self._aux_heater_dual_mode = config.get(CONF_AUX_HEATING_DUAL_MODE)

        self._heat_cool_mode = config.get(CONF_HEAT_COOL_MODE)
        self._default_support_flags = (
            ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        )

        self._supported_features = self._default_support_flags

        self._hvac_power_levels = config.get(CONF_HVAC_POWER_LEVELS)
        self._hvac_power_tolerance = config.get(CONF_HVAC_POWER_TOLERANCE)

    @property
    def heat_pump_cooling_entity_id(self) -> str:
        return self._heat_pump_cooling_entity_id

    @property
    def supported_features(self) -> int:
        """Return the supported features."""
        return self._supported_features

    @property
    def is_target_mode(self) -> bool:
        """Check if current support flag is for target temp mode."""
        return (
            self._supported_features & ClimateEntityFeature.TARGET_TEMPERATURE
            and not (
                self._supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
        )

    @property
    def is_range_mode(self) -> bool:
        """Check if current support flag is for range temp mode."""
        return bool(
            self._supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        )

    @property
    def is_configured_for_cooler_mode(self) -> bool:
        """Determines if the cooler mode is configured."""
        return self._heater_entity_id is not None and self._ac_mode is True

    @property
    def is_configured_for_dual_mode(self) -> bool:
        """Determined if the dual mode is configured."""

        """NOTE: this doesn't mean heat/cool mode is configured, just that the dual mode is configured"""

        return self._heater_entity_id is not None and self._cooler_entity_id is not None

    @property
    def is_configured_for_heat_cool_mode(self) -> bool:
        """Checks if the configuration is complete for heat/cool mode."""
        _LOGGER.info("is_configured_for_heat_cool_mode")
        _LOGGER.info("heat_cool_mode: %s", self._heat_cool_mode)
        _LOGGER.info("target_temp_high: %s", self.environment.target_temp_high)
        _LOGGER.info("target_temp_low: %s", self.environment.target_temp_low)

        return self._heat_cool_mode or (
            self.environment.target_temp_high is not None
            and self.environment.target_temp_low is not None
        )

    @property
    def is_configured_for_aux_heating_mode(self) -> bool:
        """Determines if the aux heater is configured."""
        if self._aux_heater_entity_id is None:
            return False

        if self._aux_heater_timeout is None:
            return False

        return True

    @property
    def aux_heater_timeout(self) -> int:
        """Return the aux heater timeout."""
        return self._aux_heater_timeout

    @property
    def aux_heater_dual_mode(self) -> bool:
        """Return the aux heater dual mode."""
        return self._aux_heater_dual_mode

    @property
    def is_configured_for_fan_mode(self) -> bool:
        """Determines if the fan mode is configured."""
        return self._fan_entity_id is not None

    @property
    def is_configured_fan_mode_tolerance(self) -> bool:
        """Determines if the fan mode is configured."""
        return self._is_configured_for_fan_mode() and self._fan_tolerance is not None

    @property
    def is_configured_for_fan_only_mode(self) -> bool:
        """Determines if the fan mode is configured."""
        return (
            self._heater_entity_id is not None
            and self._fan_mode is True
            and self._fan_entity_id is None
        )

    @property
    def is_configured_for_fan_on_with_cooler(self) -> bool:
        """Determines if the fan mode with cooler is configured."""
        return self._fan_on_with_cooler

    @property
    def is_fan_uses_outside_air(self) -> bool:
        return self._fan_air_outside

    @property
    def fan_hot_tolerance_on_entity(self) -> bool:
        return self._fan_tolerance_on_entity_id

    @property
    def is_configured_for_dryer_mode(self) -> bool:
        """Determines if the dryer mode is configured."""
        return (
            self._dryer_entity_id is not None
            and self._humidity_sensor_entity_id is not None
        )

    @property
    def is_configured_for_heat_pump_mode(self) -> bool:
        """Determines if the heat pump cooling is configured."""
        return self._heat_pump_cooling_entity_id is not None

    @property
    def is_configured_for_hvac_power_levels(self) -> bool:
        """Determines if the HVAC power levels are configured."""
        return (
            self._hvac_power_levels is not None
            or self._hvac_power_tolerance is not None
        )

    def set_support_flags(
        self,
        presets: dict[str, PresetEnv],
        preset_mode: str,
        current_hvac_mode: HVACMode = None,
    ) -> None:
        """Set the correct support flags based on configuration."""
        _LOGGER.debug("Setting support flags")

        if not self.is_configured_for_heat_cool_mode or current_hvac_mode in (
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
        ):
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_TEMPERATURE
            )
            if len(presets):
                _LOGGER.debug(
                    "Setting support target mode flags to %s", self._supported_features
                )
                self._supported_features |= ClimateEntityFeature.PRESET_MODE

        elif current_hvac_mode == HVACMode.DRY:
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_HUMIDITY
            )
            self.environment.set_default_target_humidity()

        else:
            self._supported_features = (
                self._default_support_flags
                | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            _LOGGER.debug("Setting support flags to %s", self._supported_features)
            if len(presets):
                self._supported_features |= ClimateEntityFeature.PRESET_MODE
                _LOGGER.debug(
                    "Setting support flags presets in range mode to %s",
                    self._supported_features,
                )

        if preset_mode == PRESET_NONE:
            self.environment.set_default_target_temps(
                self.is_target_mode, self.is_range_mode, current_hvac_mode
            )

        if self.is_configured_for_dryer_mode:
            self._supported_features |= ClimateEntityFeature.TARGET_HUMIDITY

    def apply_old_state(
        self, old_state: State | None, hvac_mode: HVACMode | None = None, presets=[]
    ) -> None:
        if old_state is None:
            return

        _LOGGER.debug("Features applying old state")
        old_supported_features = old_state.attributes.get(ATTR_SUPPORTED_FEATURES)
        if (
            old_supported_features not in (None, 0)
            and old_supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            and self.is_configured_for_heat_cool_mode
            and hvac_mode in (HVACMode.HEAT_COOL, HVACMode.OFF)
        ):
            self._supported_features = (
                self._default_support_flags
                | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            if len(presets):
                _LOGGER.debug("Setting support flag: presets for range mode")
                self._supported_features |= ClimateEntityFeature.PRESET_MODE

        else:
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_TEMPERATURE
            )

    def hvac_modes_support_range_temp(self, hvac_modes: list[HVACMode]) -> bool:
        return (
            HVACMode.COOL in hvac_modes or HVACMode.FAN_ONLY in hvac_modes
        ) and HVACMode.HEAT in hvac_modes
