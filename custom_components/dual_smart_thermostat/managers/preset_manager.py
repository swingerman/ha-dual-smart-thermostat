import logging

from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    PRESET_NONE,
    HVACMode,
)
from homeassistant.components.humidifier import ATTR_HUMIDITY
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
        presets = presets_dict

        _LOGGER.debug("Presets generated: %s", presets)
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

        # sets the target environment to the preset mode
        # _LOGGER.debug(
        #     "Setting target temp when no preset mode, %s, %s",
        #     self._environment.target_temp,
        #     next(iter(presets.values())),
        # )

        first_preset = next(iter(presets.values()), None)
        if isinstance(first_preset, dict):
            preset_temperature = (
                first_preset.get(ATTR_TEMPERATURE) if first_preset else None
            )
        else:
            preset_temperature = first_preset

        _LOGGER.debug("Preset temperature: %s", preset_temperature)

        self._environment.saved_target_temp = (
            self._environment.target_temp or preset_temperature or None
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

    def set_preset_mode(self, preset_mode: str, hvac_mode: HVACMode) -> None:
        """Set new preset mode."""
        _LOGGER.debug("Setting preset mode: %s", preset_mode)
        if preset_mode not in (self.preset_modes or []):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self.preset_modes}"
            )
        if preset_mode == PRESET_NONE and preset_mode == self._preset_mode:
            return
        # if preset_mode == self._preset_mode we still need to continue
        # to set the target environment to the preset mode
        if preset_mode == PRESET_NONE:
            self._set_presets_when_no_preset_mode()
        else:
            self._set_presets_when_have_preset_mode(preset_mode, hvac_mode)

    def _set_presets_when_no_preset_mode(self):
        """Sets target environment when preset is none."""
        _LOGGER.debug("Setting presets when no preset mode")
        _LOGGER.debug(
            "saved_target_temp_low: %s", self._environment.saved_target_temp_low
        )
        _LOGGER.debug(
            "saved_target_temp_high: %s", self._environment.saved_target_temp_high
        )
        self._preset_mode = PRESET_NONE
        if self._features.is_range_mode:
            self._environment.target_temp_low = self._environment.saved_target_temp_low
            self._environment.target_temp_high = (
                self._environment.saved_target_temp_high
            )
        else:
            self._environment.target_temp = self._environment.saved_target_temp

        if self._environment.saved_target_humidity:
            self._environment.target_humidity = self._environment.saved_target_humidity

    def _set_presets_when_have_preset_mode(self, preset_mode: str, hvac_mode: HVACMode):
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
            _LOGGER.debug(
                "Preset Setting target temp low: %s",
                self._presets_range[preset_mode][0],
            )
            _LOGGER.debug(
                "Preset Setting target temp high: %s",
                self._presets_range[preset_mode][1],
            )
            self._environment.target_temp_low = self._presets_range[preset_mode][0]
            self._environment.target_temp_high = self._presets_range[preset_mode][1]
        else:
            if self._preset_mode == PRESET_NONE:
                _LOGGER.debug(
                    "Saving target temp when target and no preset: %s",
                    self._environment.target_temp,
                )
                self._environment.saved_target_temp = self._environment.target_temp
            # handles when temperature is set in preset
            if self._presets[preset_mode].get(ATTR_TEMPERATURE) is not None:
                self._environment.target_temp = self._presets[preset_mode][
                    ATTR_TEMPERATURE
                ]
            # handles when temperature is not set in preset but temp range is set
            else:
                self._environment.set_temepratures_from_hvac_mode_and_presets(
                    hvac_mode, preset_mode, self._presets_range, self._preset_mode
                )

        if self._features.is_configured_for_dryer_mode:
            if self._preset_mode == PRESET_NONE:
                self._environment.saved_target_humidity = (
                    self._environment.target_humidity
                )
            self._environment.target_humidity = self._presets[preset_mode][
                ATTR_HUMIDITY
            ]

        self._preset_mode = preset_mode

        # if self._features.is_configured_for_dryer_mode:

    def apply_old_state(self, old_state: State):
        if old_state is None:
            return

        _LOGGER.debug("Presets applying old state")
        _LOGGER.debug("Old state: %s", old_state)
        _LOGGER.debug("target temp: %s", self._environment.target_temp)

        old_pres_mode = old_state.attributes.get(ATTR_PRESET_MODE)
        old_temperature = old_state.attributes.get(ATTR_TEMPERATURE)
        old_target_temp_low = old_state.attributes.get(ATTR_TARGET_TEMP_LOW)
        old_target_temp_high = old_state.attributes.get(ATTR_TARGET_TEMP_HIGH)

        if self._features.is_range_mode:
            _LOGGER.debug("Apply preset range mode - old state: %s", old_pres_mode)
            if self._preset_modes and old_pres_mode in self._presets_range:
                _LOGGER.debug("Restoring previous preset mode range: %s", old_pres_mode)
                self._preset_mode = old_pres_mode

                # need to save the previous target temps
                # before we apply a preset
                self._environment.saved_target_temp_low = (
                    self._environment.target_temp_low
                )
                self._environment.saved_target_temp_high = (
                    self._environment.target_temp_high
                )

                preset = self._presets_range[old_pres_mode]
                if preset:

                    if old_temperature is not None:
                        _LOGGER.debug(
                            "saved target temperature: %s",
                            self._environment.target_temp,
                        )
                        self._environment.saved_target_temp = float(old_temperature)

                    self._environment.target_temp_low = (
                        float(old_target_temp_low)
                        if old_target_temp_low
                        else float(preset[0])
                    )
                    self._environment.target_temp_high = (
                        float(old_target_temp_high)
                        if old_target_temp_high
                        else float(preset[1])
                    )

        elif self._preset_modes and old_pres_mode in self._presets:
            _LOGGER.debug("Restoring previous preset mode target: %s", old_pres_mode)
            _LOGGER.debug("Target temp: %s", self._environment.target_temp)
            _LOGGER.debug("Target temp form preset: %s", self._presets[old_pres_mode])
            _LOGGER.debug("Old temperature: %s", old_temperature)

            self._preset_mode = old_pres_mode
            self._environment.saved_target_temp = self._environment.target_temp

            if old_temperature is not None:
                self._environment.target_temp = float(old_temperature)
                return

            if isinstance(self._presets[old_pres_mode], float):
                self._environment.target_temp = float(self._presets[old_pres_mode])
            elif (
                isinstance(self._presets[old_pres_mode], dict)
                and ATTR_TEMPERATURE in self._presets[old_pres_mode]
            ):
                self._environment.target_temp = float(
                    self._presets[old_pres_mode][ATTR_TEMPERATURE]
                )
            else:
                _LOGGER.debug("Restoring previous preset mode temp unhandled")

        else:
            _LOGGER.debug("Restoring previous preset mode no match")
