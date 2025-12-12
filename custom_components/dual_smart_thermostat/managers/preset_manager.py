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

from ..const import CONF_PRESETS, CONF_PRESETS_OLD
from ..managers.environment_manager import EnvironmentManager
from ..managers.feature_manager import FeatureManager
from ..managers.state_manager import StateManager
from ..preset_env.preset_env import PresetEnv

_LOGGER = logging.getLogger(__name__)


class PresetManager(StateManager):

    _preset_env: PresetEnv

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
        self._preset_env = PresetEnv()

        self._presets = self._get_preset_modes_from_config(config)
        self._preset_modes = (
            list(self._presets.keys() | [PRESET_NONE]) if self._presets else []
        )
        _LOGGER.debug("Presets: %s", self._presets)
        _LOGGER.debug("Preset modes: %s", self._preset_modes)

    @property
    def presets(self):
        return self._presets

    @property
    def preset_modes(self) -> list[str]:
        return self._preset_modes

    @property
    def preset_mode(self):
        return self._preset_mode

    @property
    def has_presets(self):
        return len(self.presets) > 0

    @property
    def preset_env(self) -> PresetEnv:
        return self._preset_env

    def _get_preset_modes_from_config(
        self, config: ConfigType
    ) -> list[dict[str:PresetEnv]]:
        """Get preset modes from config."""
        presets_dict = {
            key: config[value] for key, value in CONF_PRESETS.items() if value in config
        }
        _LOGGER.debug("Presets dict: %s", presets_dict)

        # create class instances for each preset
        for key, values in presets_dict.items():
            if isinstance(values, dict):
                presets_dict[key] = PresetEnv(**values)
            else:
                presets_dict[key] = PresetEnv(temperature=values)
        presets = presets_dict

        _LOGGER.debug("Presets generated: %s", presets)

        # Try to load presets in old format and use if new format not available in config
        old_presets = {
            k: {ATTR_TEMPERATURE: config[v]}
            for k, v in CONF_PRESETS_OLD.items()
            if v in config
        }
        if old_presets:
            _LOGGER.warning(
                "Found deprecated presets settings in configuration. "
                "Please remove and replace with new presets settings format. "
                "Read documentation in integration repository for more details"
            )
            for key, values in old_presets.items():
                old_presets[key] = PresetEnv(**values)

            if not presets_dict:
                presets = old_presets
            else:
                _LOGGER.warning(
                    "New presets settings found in configuration. "
                    "Ignoring deprecated presets settings"
                )
        return presets

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        _LOGGER.debug("Setting preset mode: %s", preset_mode)
        if preset_mode not in (self.preset_modes or []):
            raise ValueError(
                f"Got unsupported preset_mode {preset_mode}. Must be one of {self.preset_modes}"
            )

        if preset_mode == PRESET_NONE and preset_mode == self._preset_mode:
            _LOGGER.debug("Preset mode is already none")
            return
        # if preset_mode == self._preset_mode we still need to continue
        # to set the target environment to the preset mode
        if preset_mode == PRESET_NONE:
            self._preset_mode = PRESET_NONE
            self._preset_env = PresetEnv()
        else:
            self._set_presets_when_have_preset_mode(preset_mode)

        _LOGGER.debug("Preset env set: %s", self._preset_env)

    def _set_presets_when_have_preset_mode(self, preset_mode: str):
        """Sets target temperatures when have preset is not none."""
        _LOGGER.debug("Setting presets when have preset mode")
        if self._features.is_range_mode:
            _LOGGER.debug("Setting preset in range mode")
        else:
            _LOGGER.debug("Setting preset in target mode")
            # this logic is handled in _set_presets_when_no_preset_mode
            if self._preset_mode == PRESET_NONE:
                # if self._preset_mode == PRESET_NONE and preset_mode != PRESET_NONE:
                _LOGGER.debug(
                    "Saving target temp when target and no preset: %s",
                    self._environment.target_temp,
                )
                self._environment.saved_target_temp = self._environment.target_temp

        self._preset_mode = preset_mode
        self._preset_env = self.presets[preset_mode]

    async def apply_old_state(self, old_state: State):
        """Restore state from previous session."""
        if old_state is None:
            return

        _LOGGER.debug("Presets applying old state: %s", old_state)
        _LOGGER.debug("Current target temp: %s", self._environment.target_temp)

        old_preset_mode = old_state.attributes.get(ATTR_PRESET_MODE)
        old_temperature = old_state.attributes.get(ATTR_TEMPERATURE)
        old_target_temp_low = old_state.attributes.get(ATTR_TARGET_TEMP_LOW)
        old_target_temp_high = old_state.attributes.get(ATTR_TARGET_TEMP_HIGH)

        if self._features.is_range_mode:
            await self._apply_range_mode_state(
                old_preset_mode,
                old_temperature,
                old_target_temp_low,
                old_target_temp_high,
            )
        else:
            await self._apply_single_temp_mode_state(old_preset_mode, old_temperature)

    async def _apply_range_mode_state(
        self,
        old_preset_mode: str | None,
        old_temperature: float | None,
        old_target_temp_low: float | None,
        old_target_temp_high: float | None,
    ):
        """Restore range mode (heat/cool) state."""
        _LOGGER.debug("Apply preset range mode - old state: %s", old_preset_mode)

        if not self._preset_modes or old_preset_mode not in self._presets:
            _LOGGER.debug("No matching preset for range mode: %s", old_preset_mode)
            return

        _LOGGER.debug("Restoring previous preset mode range: %s", old_preset_mode)
        self._preset_mode = old_preset_mode

        # Save current target temps before applying preset
        self._environment.saved_target_temp_low = self._environment.target_temp_low
        self._environment.saved_target_temp_high = self._environment.target_temp_high

        if old_temperature is not None:
            _LOGGER.debug("Saved target temperature: %s", self._environment.target_temp)
            self._environment.saved_target_temp = float(old_temperature)

        # Apply preset temperatures
        preset = self._presets[old_preset_mode]
        await self._restore_range_temps_from_preset(
            preset, old_target_temp_low, old_target_temp_high
        )

    async def _apply_single_temp_mode_state(
        self, old_preset_mode: str | None, old_temperature: float | None
    ):
        """Restore single temperature mode state."""
        if not self._preset_modes or old_preset_mode not in self._presets:
            self._restore_temperature_fallback(old_temperature, old_preset_mode)
            return

        _LOGGER.debug("Restoring previous preset mode target: %s", old_preset_mode)
        _LOGGER.debug("Target temp: %s", self._environment.target_temp)
        _LOGGER.debug("Preset config: %s", self._presets[old_preset_mode])
        _LOGGER.debug("Old temperature: %s", old_temperature)

        self._preset_mode = old_preset_mode
        self._environment.saved_target_temp = self._environment.target_temp

        # Prefer old temperature if available (actual state)
        if old_temperature is not None:
            self._environment.target_temp = float(old_temperature)
            return

        # Otherwise restore from preset configuration
        await self._restore_temp_from_preset(self._presets[old_preset_mode])

    async def _restore_range_temps_from_preset(
        self,
        preset: PresetEnv,
        old_target_temp_low: float | None,
        old_target_temp_high: float | None,
    ):
        """Restore range temperatures from preset, preferring old state values."""
        # Use template-aware getters for preset temperatures
        preset_temp_low = preset.get_target_temp_low(self.hass)
        preset_temp_high = preset.get_target_temp_high(self.hass)

        # Prefer old state values, fall back to preset values
        if preset_temp_low is not None:
            self._environment.target_temp_low = (
                float(old_target_temp_low)
                if old_target_temp_low
                else float(preset_temp_low)
            )

        if preset_temp_high is not None:
            self._environment.target_temp_high = (
                float(old_target_temp_high)
                if old_target_temp_high
                else float(preset_temp_high)
            )

    async def _restore_temp_from_preset(self, preset):
        """Restore temperature from preset configuration (supports multiple formats)."""
        # Handle legacy float format
        if isinstance(preset, float):
            self._environment.target_temp = float(preset)
            return

        # Handle legacy dict format
        if isinstance(preset, dict) and ATTR_TEMPERATURE in preset:
            self._environment.target_temp = float(preset[ATTR_TEMPERATURE])
            return

        # Handle PresetEnv object with template support
        if hasattr(preset, "get_temperature"):
            temp = preset.get_temperature(self.hass)
            if temp is not None:
                self._environment.target_temp = temp
            return

        _LOGGER.debug("Unhandled preset format: %s", type(preset))

    def _restore_temperature_fallback(
        self, old_temperature: float | None, old_preset_mode: str | None
    ):
        """Restore temperature when no preset match found."""
        _LOGGER.debug("No matching preset found")
        if old_temperature is not None and old_preset_mode is None:
            _LOGGER.debug("Restoring previous target temp: %s", old_temperature)
            self._environment.target_temp = float(old_temperature)

    def find_matching_preset(self) -> str | None:
        """Find a preset that matches the current environment settings.

        Returns the first matching preset name, or None if no match is found.
        """
        if not self._presets:
            return None

        current_temp = self._environment.target_temp
        current_temp_low = self._environment.target_temp_low
        current_temp_high = self._environment.target_temp_high
        current_humidity = getattr(self._environment, "target_humidity", None)
        current_min_floor_temp = getattr(self._environment, "_min_floor_temp", None)
        current_max_floor_temp = getattr(self._environment, "_max_floor_temp", None)

        _LOGGER.debug(
            "Checking for matching preset. Current values - temp: %s, temp_low: %s, temp_high: %s, humidity: %s, min_floor: %s, max_floor: %s",
            current_temp,
            current_temp_low,
            current_temp_high,
            current_humidity,
            current_min_floor_temp,
            current_max_floor_temp,
        )

        for preset_name, preset_env in self._presets.items():
            if self._preset_mode == preset_name:
                # Skip if already in this preset
                continue

            if self._values_match_preset(
                preset_env,
                current_temp,
                current_temp_low,
                current_temp_high,
                current_humidity,
                current_min_floor_temp,
                current_max_floor_temp,
            ):
                _LOGGER.debug("Found matching preset: %s", preset_name)
                return preset_name

        _LOGGER.debug("No matching preset found")
        return None

    def _values_match_preset(
        self,
        preset_env,
        current_temp,
        current_temp_low,
        current_temp_high,
        current_humidity,
        current_min_floor_temp,
        current_max_floor_temp,
    ) -> bool:
        """Check if current values match a preset environment.

        Returns True if all non-None values in the preset match the current values.
        Only checks values that are actually set in the current environment.
        """
        # Check temperature values
        if not self._check_temperature_match(preset_env, current_temp):
            return False

        if not self._check_temperature_range_match(
            preset_env, current_temp_low, current_temp_high
        ):
            return False

        if not self._check_humidity_match(preset_env, current_humidity):
            return False

        if not self._check_floor_temp_limits_match(
            preset_env, current_min_floor_temp, current_max_floor_temp
        ):
            return False

        return True

    def _check_temperature_match(self, preset_env, current_temp: float | None) -> bool:
        """Check if single temperature matches preset.

        For template-based presets, evaluates the template to get current value.
        """
        # Get the preset temperature, evaluating template if needed
        preset_temp = preset_env.get_temperature(self.hass)

        if preset_temp is None:
            return True

        if current_temp is None:
            return False

        return self._values_equal(preset_temp, current_temp)

    def _check_temperature_range_match(
        self,
        preset_env,
        current_temp_low: float | None,
        current_temp_high: float | None,
    ) -> bool:
        """Check if temperature range matches preset.

        For template-based presets, evaluates templates to get current values.
        """
        # Get preset values, evaluating templates if needed
        preset_temp_low = preset_env.get_target_temp_low(self.hass)
        preset_temp_high = preset_env.get_target_temp_high(self.hass)

        # Check low temperature
        if preset_temp_low is not None:
            if current_temp_low is None or not self._values_equal(
                preset_temp_low, current_temp_low
            ):
                return False

        # Check high temperature
        if preset_temp_high is not None:
            if current_temp_high is None or not self._values_equal(
                preset_temp_high, current_temp_high
            ):
                return False

        return True

    def _check_humidity_match(self, preset_env, current_humidity: float | None) -> bool:
        """Check if humidity matches preset."""
        if preset_env.humidity is None:
            return True

        if current_humidity is None:
            return False

        return self._values_equal(preset_env.humidity, current_humidity)

    def _check_floor_temp_limits_match(
        self,
        preset_env,
        current_min_floor_temp: float | None,
        current_max_floor_temp: float | None,
    ) -> bool:
        """Check if floor temperature limits match preset.

        Floor limits are only checked if they are set in the current environment.
        This is because floor limits are only set when a preset is applied, not when temperature is set.
        """
        # Check min floor temperature
        if preset_env.min_floor_temp is not None and current_min_floor_temp is not None:
            if not self._values_equal(
                preset_env.min_floor_temp, current_min_floor_temp
            ):
                return False

        # Check max floor temperature
        if preset_env.max_floor_temp is not None and current_max_floor_temp is not None:
            if not self._values_equal(
                preset_env.max_floor_temp, current_max_floor_temp
            ):
                return False

        return True

    def _values_equal(
        self, value1: float, value2: float, tolerance: float = 0.001
    ) -> bool:
        """Check if two float values are equal within tolerance."""
        return abs(value1 - value2) <= tolerance
