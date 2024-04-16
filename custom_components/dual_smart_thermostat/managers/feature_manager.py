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
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_HEAT_COOL_MODE,
    CONF_HEATER,
)
from custom_components.dual_smart_thermostat.managers.state_manager import StateManager
from custom_components.dual_smart_thermostat.managers.temperature_manager import (
    TemperatureManager,
)

_LOGGER = logging.getLogger(__name__)


class FeatureManager(StateManager):

    def __init__(
        self, hass, config: ConfigType, temperatures: TemperatureManager
    ) -> None:
        self.hass = hass
        self.temperatures = temperatures
        self._supported_features = 0
        self._cooler_entity_id = config.get(CONF_COOLER)
        self._heater_entity_id = config.get(CONF_HEATER)
        self._ac_mode = config.get(CONF_AC_MODE)

        self._aux_heater_entity_id = config.get(CONF_AUX_HEATER)
        self._aux_heater_timeout = config.get(CONF_AUX_HEATING_TIMEOUT)

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
    def is_configured_for_heat_cool_mode(self) -> bool:
        """Checks if the configuration is complete for heat/cool mode."""
        return (
            self._heat_cool_mode
            or (
                self.temperatures.target_temp_high is not None
                and self.temperatures.target_temp_low is not None
            )
            or (
                self._heater_entity_id is not None
                and self._cooler_entity_id is not None
            )
        )

    @property
    def _is_configured_for_aux_heating_mode(self) -> bool:
        """Determines if the aux heater is configured."""
        if self._aux_heater_entity_id is None:
            return False

        if self._aux_heater_timeout is None:
            return False

        return True

    def set_support_flags(
        self,
        presets: dict[str, Any],
        hvac_modes: list[HVACMode],
        presets_range,
        current_hvac_mode: HVACMode = None,
    ) -> None:
        """Set the correct support flags based on configuration."""
        _LOGGER.debug("Setting support flags")

        preset_mode = None

        if not self.is_configured_for_heat_cool_mode:
            if self.is_range_mode and preset_mode != PRESET_NONE:
                self.temperatures.target_temp_low = (
                    self.temperatures.saved_target_temp_low
                )
                self.temperatures.target_temp_high = (
                    self.temperatures.saved_target_temp_high
                )
            self._supported_features = (
                self._default_support_flags | ClimateEntityFeature.TARGET_TEMPERATURE
            )
            if len(presets):
                _LOGGER.debug("Setting support flags to %s", self._supported_features)
                self._supported_features |= ClimateEntityFeature.PRESET_MODE
        else:
            if self.is_target_mode and preset_mode != PRESET_NONE:
                self.temperatures.target_temp = self.temperatures.saved_target_temp

            if current_hvac_mode not in [None, HVACMode.OFF, HVACMode.HEAT_COOL]:
                self._supported_features = (
                    self._default_support_flags
                    | ClimateEntityFeature.TARGET_TEMPERATURE
                )

                if current_hvac_mode == HVACMode.HEAT:
                    self.temperatures.target_temp = self.temperatures.target_temp_low

                else:  # can be COOL, FAN_ONLY
                    self.temperatures.target_temp = self.temperatures.target_temp_high

            else:
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

        self.temperatures.set_default_target_temps(
            self.is_target_mode, self.is_range_mode, hvac_modes
        )

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
