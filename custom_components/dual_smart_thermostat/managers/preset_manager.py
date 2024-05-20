import logging

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_NONE,
)
from homeassistant.const import ATTR_TEMPERATURE
from homeassistant.core import State
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import CONF_PRESETS, CONF_PRESETS_OLD
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.state_manager import StateManager

_LOGGER = logging.getLogger(__name__)


class PresetManager(StateManager):
    def __init__(
        self,
        hass,
        config: ConfigType,
        environment: EnvironmentManager,
        features: FeatureManager,
    ) -> None:
        self.hass = hass
        self._environment = environment
        self._features = features

        self._current_preset = config.get("current_preset")
        self._saved_preset = self._current_preset
        self._supported_features = 0
        self._preset_mode = PRESET_NONE

        presets_dict = {
            key: config[value] for key, value in CONF_PRESETS.items() if value in config
        }
        _LOGGER.debug("Presets dict: %s", presets_dict)
        presets = {
            key: values[ATTR_TEMPERATURE]
            for key, values in presets_dict.items()
            if ATTR_TEMPERATURE in values
        }
        # Try to load presets in old format and use if new format not available in config
        old_presets = {k: config[v] for k, v in CONF_PRESETS_OLD.items() if v in config}
        if old_presets:
            _LOGGER.warning(
                "Found deprecated presets settings in configuration. "
                "Please remove and replace with new presets settings format. "
                "Read documentation in integration repository for more details"
            )
            if not presets_dict:
                presets = old_presets
        _LOGGER.debug("Presets: %s", presets)

        presets_range = {
            key: [values[ATTR_TARGET_TEMP_LOW], values[ATTR_TARGET_TEMP_HIGH]]
            for key, values in presets_dict.items()
            if ATTR_TARGET_TEMP_LOW in values
            and ATTR_TARGET_TEMP_HIGH in values
            and values[ATTR_TARGET_TEMP_LOW] < values[ATTR_TARGET_TEMP_HIGH]
        }
        _LOGGER.debug("Presets range: %s", presets_range)

        self._presets = presets
        if len(presets):
            self._preset_modes = [PRESET_NONE] + list(presets.keys())
            _LOGGER.debug("INIT - Setting support flag: presets: %s", presets.keys())
        else:
            self._preset_modes = [PRESET_NONE]
            _LOGGER.debug("INIT - Setting support flag: presets - no presets set")

        if len(presets_range):
            _LOGGER.debug(
                "INIT - Setting support flag: presets range: %s", presets_range
            )
            self._preset_range_modes = [PRESET_NONE] + list(presets_range.keys())
        else:
            _LOGGER.debug("INIT - Setting support flag: presets range none")
            self._preset_range_modes = [PRESET_NONE]

        self._presets_range = presets_range

        if self._preset_range_modes:
            # if range mode is enabled, we need to add the range presets to the preset modes avoiding duplicates
            self._preset_modes = self._preset_modes + list(
                set(self._preset_range_modes) - set(self._preset_modes)
            )

    @property
    def presets(self):
        return self._presets

    @property
    def presets_range(self):
        return self._presets_range

    @property
    def preset_modes(self):
        return self._preset_modes

    @property
    def preset_mode(self):
        return self._preset_mode

    @property
    def has_presets(self):
        return len(self.presets) > 0

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        _LOGGER.debug("Setting preset mode: %s", preset_mode)
        if preset_mode not in (self.preset_modes or []):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self.preset_modes}"
            )
        if preset_mode == self._preset_mode:
            # I don't think we need to call async_write_ha_state if we didn't change the state
            return
        if preset_mode == PRESET_NONE:
            self._set_presets_when_no_preset_mode()
        else:
            self._set_presets_when_have_preset_mode(preset_mode)

    def _set_presets_when_no_preset_mode(self):
        """Sets target environment when preset is none."""
        _LOGGER.debug("Setting presets when no preset mode")
        self._preset_mode = PRESET_NONE
        if self._features.is_range_mode:
            self._environment.target_temp_low = self._environment.saved_target_temp_low
            self._environment.target_temp_high = (
                self._environment.saved_target_temp_high
            )
        else:
            self._environment.target_temp = self._environment.saved_target_temp

    def _set_presets_when_have_preset_mode(self, preset_mode: str):
        """Sets target temperatures when have preset is not none."""
        _LOGGER.debug("Setting presets when have preset mode")
        if self._features.is_range_mode:
            if self._preset_mode == PRESET_NONE:
                self._environment.saved_target_temp_low = (
                    self._environment.target_temp_low
                )
                self._environment.saved_target_temp_high = (
                    self._environment.target_temp_high
                )
            self._environment.target_temp_low = self._presets_range[preset_mode][0]
            self._environment.target_temp_high = self._presets_range[preset_mode][1]
        else:
            if self._preset_mode == PRESET_NONE:
                self._environment.saved_target_temp = self._environment.target_temp
            self._environment.target_temp = self._presets[preset_mode]
        self._preset_mode = preset_mode

    def apply_old_state(self, old_state: State):
        if old_state is None:
            return

        old_pres_mode = old_state.attributes.get(ATTR_PRESET_MODE)
        if self._features.is_range_mode:
            if self._preset_modes and old_pres_mode in self._presets_range:
                self._preset_mode = old_pres_mode
                self._environment.saved_target_temp_low = (
                    self._environment.target_temp_low
                )
                self._environment.saved_target_temp_high = (
                    self._environment.target_temp_high
                )

            elif self._preset_modes and old_pres_mode in self._presets:
                _LOGGER.debug("Restoring previous preset mode: %s", old_pres_mode)
                self._preset_mode = old_pres_mode
                self._environment.saved_target_temp = self._environment.target_temp
