import logging
from typing import Any

from homeassistant.components.climate.const import (
    PRESET_NONE,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_SUPPORTED_FEATURES
from homeassistant.core import State
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HEAT_COOL_MODE,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.state_manager import StateManager

_LOGGER = logging.getLogger(__name__)


class FeatureManager(StateManager):

    def __init__(
        self, hass, config: ConfigType, environment: EnvironmentManager
    ) -> None:
        self.hass = hass
        self.environment = environment
        self._supported_features = 0
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

        self._dryer_entity_id = config.get(CONF_DRYER)
        self._humidity_sensor_entity_id = config.get(CONF_HUMIDITY_SENSOR)

        self._aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self._aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)
        self._aux_heater_dual_mode = config.get(CONF_AUX_HEATING_DUAL_MODE)

        self._heat_cool_mode = config.get(CONF_HEAT_COOL_MODE)
        self._default_support_flags = (
            ClimateEntityFeature.TURN_OFF | ClimateEntityFeature.TURN_ON
        )

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
        return self._supported_features & ClimateEntityFeature.TARGET_TEMPERATURE_RANGE

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
    def is_configured_for_dryer_mode(self) -> bool:
        """Determines if the dryer mode is configured."""
        return (
            self._dryer_entity_id is not None
            and self._humidity_sensor_entity_id is not None
        )

    def set_support_flags(
        self,
        presets: dict[str, Any],
        presets_range,
        preset_mode: str,
        hvac_modes: list[HVACMode],
        current_hvac_mode: HVACMode = None,
    ) -> None:
        """Set the correct support flags based on configuration."""
        _LOGGER.debug("Setting support flags")

        if not self.is_configured_for_heat_cool_mode or current_hvac_mode in (
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
            HVACMode.HEAT,
        ):
            if self.is_range_mode and preset_mode != PRESET_NONE:
                self.environment.target_temp_low = (
                    self.environment.saved_target_temp_low
                )
                self.environment.target_temp_high = (
                    self.environment.saved_target_temp_high
                )
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_TEMPERATURE
            )
            if len(presets):
                _LOGGER.debug("Setting support flags to %s", self._supported_features)
                self._supported_features |= ClimateEntityFeature.PRESET_MODE
        else:
            if self.is_target_mode and preset_mode != PRESET_NONE:
                self.environment.target_temp = self.environment.saved_target_temp
            self._supported_features = (
                self._default_support_flags
                | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
            )
            _LOGGER.debug("Setting support flags to %s", self._supported_features)
            if len(presets_range):
                self._supported_features |= ClimateEntityFeature.PRESET_MODE
                _LOGGER.debug(
                    "Setting support flags presets in range mode to %s",
                    self._supported_features,
                )
        self.environment.set_default_target_temps(
            self.is_target_mode, self.is_range_mode, hvac_modes
        )

        if self.is_configured_for_dryer_mode:
            self._supported_features |= ClimateEntityFeature.TARGET_HUMIDITY

    def apply_old_state(self, old_state: State, hvac_mode, presets_range) -> None:
        if old_state is None:
            return

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
            if len(presets_range):
                _LOGGER.debug("Setting support flag: presets for range mode")
                self._supported_features |= ClimateEntityFeature.PRESET_MODE

        else:
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_TEMPERATURE
            )
