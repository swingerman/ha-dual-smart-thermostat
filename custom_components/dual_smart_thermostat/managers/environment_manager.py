from datetime import timedelta
import enum
import logging
import math
from typing import Any

from homeassistant.components.climate import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
)
from homeassistant.components.climate.const import PRESET_NONE, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_conversion import TemperatureConverter

from custom_components.dual_smart_thermostat.const import (
    ATTR_PREV_TARGET,
    ATTR_PREV_TARGET_HIGH,
    ATTR_PREV_TARGET_LOW,
    CONF_COLD_TOLERANCE,
    CONF_DRY_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FLOOR_SENSOR,
    CONF_HOT_TOLERANCE,
    CONF_MAX_FLOOR_TEMP,
    CONF_MAX_HUMIDITY,
    CONF_MAX_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_MIN_HUMIDITY,
    CONF_MIN_TEMP,
    CONF_MOIST_TOLERANCE,
    CONF_OUTSIDE_SENSOR,
    CONF_PRECISION,
    CONF_SENSOR,
    CONF_STALE_DURATION,
    CONF_TARGET_HUMIDITY,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    CONF_TEMP_STEP,
    DEFAULT_MAX_FLOOR_TEMP,
)
from custom_components.dual_smart_thermostat.managers.state_manager import StateManager

_LOGGER = logging.getLogger(__name__)


class TargetTemperatures:
    temperature: float
    temp_high: float
    temp_low: float

    def __init__(self, temperature: float, temp_high: float, temp_low: float) -> None:
        self.temperature = temperature
        self.temp_high = temp_high
        self.temp_low = temp_low


class EnvironmentAttributeType(enum.StrEnum):
    """Enum for environment attributes."""

    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"


class EnvironmentManager(StateManager):
    """Class to manage the temperatures of the thermostat."""

    def __init__(self, hass: HomeAssistant, config: ConfigType):
        self.hass = hass
        self._sensor_floor = config.get(CONF_FLOOR_SENSOR)
        self._sensor = config.get(CONF_SENSOR)
        self._outside_sensor = config.get(CONF_OUTSIDE_SENSOR)
        self._sensor_stale_duration: timedelta | None = config.get(CONF_STALE_DURATION)

        self._min_temp = config.get(CONF_MIN_TEMP)
        self._max_temp = config.get(CONF_MAX_TEMP)

        self._min_humidity = config.get(CONF_MIN_HUMIDITY)
        self._max_himidity = config.get(CONF_MAX_HUMIDITY)
        self._target_humidity = config.get(CONF_TARGET_HUMIDITY)
        self._moist_tolerance = config.get(CONF_MOIST_TOLERANCE) or 0
        self._dry_tolerance = config.get(CONF_DRY_TOLERANCE) or 0

        self._max_floor_temp = config.get(CONF_MAX_FLOOR_TEMP)
        self._min_floor_temp = config.get(CONF_MIN_FLOOR_TEMP)

        self._target_temp = config.get(CONF_TARGET_TEMP)
        self._target_temp_high = config.get(CONF_TARGET_TEMP_HIGH)
        self._target_temp_low = config.get(CONF_TARGET_TEMP_LOW)
        self._temp_target_temperature_step = config.get(CONF_TEMP_STEP)

        self._cold_tolerance = config.get(CONF_COLD_TOLERANCE)
        self._hot_tolerance = config.get(CONF_HOT_TOLERANCE)
        self._fan_hot_tolerance = config.get(CONF_FAN_HOT_TOLERANCE)

        self._saved_target_temp = self.target_temp or None
        self._saved_target_temp_low = None
        self._saved_target_temp_high = None
        self._temp_precision = config.get(CONF_PRECISION)

        self._temperature_unit = hass.config.units.temperature_unit

        self._cur_temp = None
        self._cur_floor_temp = None
        self._cur_outside_temp = None
        self._cur_humidity = None
        self._saved_target_humidity = None

    @property
    def cur_temp(self) -> float:
        return self._cur_temp

    @cur_temp.setter
    def cur_temp(self, temp: float) -> None:
        _LOGGER.debug("Setting current temperature: %s", temp)
        self._cur_temp = temp

    @property
    def cur_floor_temp(self) -> float:
        return self._cur_floor_temp

    @cur_floor_temp.setter
    def cur_floor_temp(self, temperature) -> None:
        self._cur_floor_temp = temperature

    @property
    def cur_outside_temp(self) -> float:
        return self._cur_outside_temp

    @property
    def target_temp(self) -> float:
        return self._target_temp

    @target_temp.setter
    def target_temp(self, temp: float) -> None:
        _LOGGER.debug("Setting target temperature property: %s", temp)
        self._target_temp = temp

    @property
    def target_temp_high(self) -> float:
        return self._target_temp_high

    @target_temp_high.setter
    def target_temp_high(self, temp: float) -> None:
        self._target_temp_high = temp

    @property
    def target_temp_low(self) -> float:
        return self._target_temp_low

    @target_temp_low.setter
    def target_temp_low(self, temp: float) -> None:
        _LOGGER.debug("Setting target temperature low: %s", temp)
        self._target_temp_low = temp

    @property
    def target_temperature_step(self) -> float:
        return self._temp_target_temperature_step

    @property
    def max_temp(self) -> float:
        if self._max_temp is not None:
            return self._max_temp
        return TemperatureConverter.convert(
            DEFAULT_MAX_TEMP, UnitOfTemperature.CELSIUS, self._temperature_unit
        )

    @property
    def min_temp(self) -> float:
        if self._min_temp is not None:
            return self._min_temp
        return TemperatureConverter.convert(
            DEFAULT_MIN_TEMP, UnitOfTemperature.CELSIUS, self._temperature_unit
        )

    @property
    def max_floor_temp(self) -> float:
        return self._max_floor_temp

    @max_floor_temp.setter
    def max_floor_temp(self, temp: float) -> None:
        self._max_floor_temp = temp

    @property
    def min_floor_temp(self) -> float:
        return self._min_floor_temp

    @property
    def saved_target_temp(self) -> float:
        return self._saved_target_temp

    @saved_target_temp.setter
    def saved_target_temp(self, temp: float) -> None:
        _LOGGER.debug("Setting saved target temp: %s", temp)
        self._saved_target_temp = temp

    @property
    def saved_target_temp_low(self) -> float:
        return self._saved_target_temp_low

    @saved_target_temp_low.setter
    def saved_target_temp_low(self, temp: float) -> None:
        _LOGGER.debug("Setting saved target temp low: %s", temp)
        self._saved_target_temp_low = temp

    @property
    def saved_target_temp_high(self) -> float:
        return self._saved_target_temp_high

    @saved_target_temp_high.setter
    def saved_target_temp_high(self, temp: float) -> None:
        self._saved_target_temp_high = temp

    @property
    def saved_target_humidity(self) -> float:
        return self._saved_target_humidity

    @saved_target_humidity.setter
    def saved_target_humidity(self, humidity: float) -> None:
        self._saved_target_humidity = humidity

    @property
    def fan_hot_tolerance(self) -> float:
        return self._fan_hot_tolerance

    @property
    def max_humidity(self) -> float:
        return self._max_himidity

    @property
    def min_humidity(self) -> float:
        return self._min_humidity

    @property
    def target_humidity(self) -> float:
        return self._target_humidity

    @target_humidity.setter
    def target_humidity(self, humidity: float) -> None:
        self._target_humidity = humidity

    @property
    def cur_humidity(self) -> float:
        return self._cur_humidity

    def get_env_attr_type(self, attr: str) -> EnvironmentAttributeType:
        return (
            EnvironmentAttributeType.HUMIDITY
            if attr == "_target_humidity"
            else EnvironmentAttributeType.TEMPERATURE
        )

    def set_temperature_range_from_saved(self) -> None:
        self.target_temp_low = self.saved_target_temp_low
        self.target_temp_high = self.saved_target_temp_high

    def set_temperature_range_from_hvac_mode(
        self, temperature: float, hvac_mode: HVACMode
    ) -> None:

        self.set_temperature_target(temperature)

        if hvac_mode == HVACMode.HEAT:
            self.set_temperature_range(temperature, temperature, self.target_temp_high)

        else:
            self.set_temperature_range(temperature, self.target_temp_low, temperature)

    def set_temperature_target(self, temperature: float) -> None:
        _LOGGER.info("Setting target temperature: %s", temperature)
        if temperature is None:
            return

        self._target_temp = temperature

    def set_temperature_range(
        self, temperature: float, temp_low: float, temp_high: float
    ) -> None:

        _LOGGER.debug(
            "Setting target temperature range: %s, %s, %s",
            temperature,
            temp_low,
            temp_high,
        )

        if temp_low is None:
            temp_low = temperature - PRECISION_WHOLE

        if temp_high is None:
            temp_high = temperature + PRECISION_WHOLE

        if temp_low > temp_high:
            temp_low = temp_high - PRECISION_WHOLE

        if temp_high < temp_low:
            temp_high = temp_low + PRECISION_WHOLE

        self._target_temp = temperature
        self._target_temp_low = temp_low
        self._target_temp_high = temp_high

    def is_within_fan_tolerance(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is below target."""
        if self._cur_temp is None or self._fan_hot_tolerance is None:
            return False
        target_temp = getattr(self, target_attr)

        too_hot_for_ac_temp = target_temp + self._hot_tolerance
        too_hot_for_fan_temp = (
            target_temp + self._hot_tolerance + self._fan_hot_tolerance
        )

        _LOGGER.info(
            "is_within_fan_tolerance, cur_temp: %s,  %s, %s",
            self._cur_temp,
            too_hot_for_ac_temp,
            too_hot_for_fan_temp,
        )

        return (
            self._cur_temp >= too_hot_for_ac_temp
            and self._cur_temp <= too_hot_for_fan_temp
        )

    @property
    def is_warmer_outside(self) -> bool:
        """Checks if the outside temperature is warmer or equal than the inside temperature."""
        if self._cur_temp is None or self._outside_sensor is None:
            return False

        outside_state = self.hass.states.get(self._outside_sensor)
        if outside_state is None:
            return False

        outside_temp = float(outside_state.state)
        return outside_temp >= self._cur_temp

    def is_too_cold(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is below target."""
        if self._cur_temp is None:
            return False
        target_temp = getattr(self, target_attr)
        _LOGGER.debug(
            "Target temp attr: %s, Target temp: %s, current temp: %s, tolerance: %s",
            target_attr,
            target_temp,
            self._cur_temp,
            self._cold_tolerance,
        )
        return target_temp >= self._cur_temp + self._cold_tolerance

    def is_too_hot(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is above target."""
        # _LOGGER.debug(
        #     "is_too_hot,  %s, %s, %s, %s, ishot: %s",
        #     self._cur_temp,
        #     target_attr,
        #     getattr(self, target_attr),
        #     self._hot_tolerance,
        #     self._cur_temp >= getattr(self, target_attr) + self._hot_tolerance,
        # )
        if self._cur_temp is None:
            return False
        target_temp = getattr(self, target_attr)
        return self._cur_temp >= target_temp + self._hot_tolerance

    @property
    def is_too_moist(self) -> bool:
        """Checks if the current humidity is above target."""
        if self._cur_humidity is None:
            return False
        return self._cur_humidity >= self._target_humidity + self._moist_tolerance

    @property
    def is_too_dry(self) -> bool:
        """Checks if the current humidity is below target."""
        if self._cur_humidity is None:
            return False
        return self._cur_humidity <= self._target_humidity - self._dry_tolerance

    @property
    def is_floor_hot(self) -> bool:
        """If the floor temp is above limit."""
        if (
            (self._sensor_floor is not None)
            and (self._max_floor_temp is not None)
            and (self._cur_floor_temp is not None)
            and (self.cur_floor_temp >= self.max_floor_temp)
        ):
            return True
        return False

    @property
    def is_floor_cold(self) -> bool:
        """If the floor temp is below limit."""
        if (
            (self._sensor_floor is not None)
            and (self._min_floor_temp is not None)
            and (self._cur_floor_temp is not None)
            and (self.cur_floor_temp <= self.min_floor_temp)
        ):
            return True
        return False

    @callback
    def update_temp_from_state(self, state: State) -> None:
        """Update thermostat with latest state from sensor."""
        try:
            cur_temp = float(state.state)
            if not math.isfinite(cur_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_temp = cur_temp
        except ValueError as ex:
            _LOGGER.error("Unable to update from sensor: %s", ex)

    @callback
    def update_floor_temp_from_state(self, state: State):
        """Update ermostat with latest floor temp state from floor temp sensor."""
        try:
            cur_floor_temp = float(state.state)
            if not math.isfinite(cur_floor_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_floor_temp = cur_floor_temp
        except ValueError as ex:
            _LOGGER.error("Unable to update from floor temp sensor: %s", ex)

    @callback
    def update_outside_temp_from_state(self, state: State):
        """Update thermostat with latest outside temp state from outside temp sensor."""
        try:
            cur_outside_temp = float(state.state)
            if not math.isfinite(cur_outside_temp):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_outside_temp = cur_outside_temp
        except ValueError as ex:
            _LOGGER.error("Unable to update from outside temp sensor: %s", ex)

    @callback
    def update_humidity_from_state(self, state: State):
        """Update thermostat with latest humidity state from humidity sensor."""
        try:
            cur_humidity = float(state.state)
            if not math.isfinite(cur_humidity):
                raise ValueError(f"Sensor has illegal state {state.state}")
            self._cur_humidity = cur_humidity
        except ValueError as ex:
            _LOGGER.error("Unable to update from humidity sensor: %s", ex)

    def set_default_target_humidity(self) -> None:
        """Set default values for target humidity."""
        if self._target_humidity is not None:
            return

        _LOGGER.info("Setting default target humidity")
        self._target_humidity = 50

    def set_default_target_temps(
        self, is_target_mode: bool, is_range_mode: bool, hvac_mode: HVACMode
    ) -> None:
        """Set default values for target temperatures."""
        _LOGGER.debug(
            "Setting default target temperatures, target mode: %s, range mode: %s, hvac_mode: %s",
            is_target_mode,
            is_range_mode,
            hvac_mode,
        )
        if is_target_mode:
            self._set_default_temps_target_mode(hvac_mode)

        elif is_range_mode:
            self._set_default_temps_range_mode()

    def _set_default_temps_target_mode(self, hvac_mode: HVACMode) -> None:

        _LOGGER.info(
            "Setting default target temperature target mode: %s, target_temp: %s",
            hvac_mode,
            self._target_temp,
        )
        _LOGGER.debug(
            "saved target temp low: %s, saved target temp high: %s",
            self._saved_target_temp_low,
            self._saved_target_temp_high,
        )

        if hvac_mode == HVACMode.COOL or hvac_mode == HVACMode.FAN_ONLY:
            if self._saved_target_temp_high is None:
                if self._target_temp is not None:
                    return
                self._target_temp = self.max_temp
                _LOGGER.warning(
                    "Undefined target high temperature, falling back to %s",
                    self._target_temp,
                )
            else:
                _LOGGER.debug(
                    "Setting target temp to saved target temp high: %s",
                    self._saved_target_temp_high,
                )
                self._target_temp = self._saved_target_temp_high
            # return

        if hvac_mode == HVACMode.HEAT:
            if self._saved_target_temp_low is None:
                if self._target_temp is not None:
                    return
                self._target_temp = self.min_temp
                _LOGGER.warning(
                    "Undefined target low temperature, falling back to %s",
                    self._target_temp,
                )
            else:
                _LOGGER.debug(
                    "Setting target temp to saved target temp low: %s",
                    self._saved_target_temp_low,
                )
                self._target_temp = self._saved_target_temp_low

    def _set_default_temps_range_mode(self) -> None:
        if self._target_temp_low is not None and self._target_temp_high is not None:
            return
        _LOGGER.info("Setting default target temperature range mode")

        if self._target_temp is None:
            self._target_temp = self.min_temp
            self._target_temp_low = self.min_temp
            self._target_temp_high = self.max_temp
            _LOGGER.warning(
                "Undefined target temperature range, fell back to %s-%s-%s",
                self._target_temp,
                self._target_temp_low,
                self._target_temp_high,
            )
            return

        self._target_temp_low = self._target_temp
        self._target_temp_high = self._target_temp
        if self._target_temp + PRECISION_WHOLE >= self.max_temp:
            self._target_temp_low -= PRECISION_WHOLE
        else:
            self._target_temp_high += PRECISION_WHOLE

    def set_temepratures_from_hvac_mode_and_presets(
        self,
        hvac_mode: HVACMode,
        preset_mode: str,
        presets_range: dict[str, Any],
        old_preset_mode: str | None = None,
    ) -> None:
        if preset_mode is None or preset_mode is PRESET_NONE:
            return

        _LOGGER.debug(
            "Setting temperatures from hvac mode and presets: %s, %s, %s",
            hvac_mode,
            preset_mode,
            presets_range,
        )

        if (
            hvac_mode == HVACMode.HEAT
            and preset_mode in presets_range
            and presets_range[preset_mode][0] is not None
        ):
            _LOGGER.debug(
                "HVACMode.HEAT Setting target temp from preset: %s",
                presets_range[preset_mode][0],
            )
            self._target_temp = presets_range[preset_mode][0]
        elif (
            hvac_mode in [HVACMode.COOL, HVACMode.FAN_ONLY]
            and preset_mode in presets_range
            and presets_range[preset_mode][0] is not None
        ):
            _LOGGER.debug(
                "HVACMode.COOL, HVACMode.FAN_ONLY Setting target temp from preset: %s, sved_target_temp: %s",
                presets_range[preset_mode][1],
                self._saved_target_temp,
            )
            preset_match_old = old_preset_mode == preset_mode
            self._target_temp = (
                self._saved_target_temp
                if preset_match_old and self._saved_target_temp
                else presets_range[preset_mode][1]
            )
        else:
            _LOGGER.debug("Setting target temp from preset, unhandled case")

    def apply_old_state(self, old_state: State) -> None:
        _LOGGER.debug("Applying old state: %s", old_state)
        if old_state is None:
            return

        # If we have no initial temperature, restore
        if self._target_temp_low is None:
            old_target_min = old_state.attributes.get(
                ATTR_PREV_TARGET_LOW
            ) or old_state.attributes.get(ATTR_TARGET_TEMP_LOW)
            if old_target_min is not None:
                self._target_temp_low = float(old_target_min)
        if self._target_temp_high is None:
            old_target_max = old_state.attributes.get(
                ATTR_PREV_TARGET_HIGH
            ) or old_state.attributes.get(ATTR_TARGET_TEMP_HIGH)
            if old_target_max is not None:
                self._target_temp_high = float(old_target_max)
        if self._target_temp is None:
            _LOGGER.info("Restoring previous target temperature")
            old_target = old_state.attributes.get(ATTR_PREV_TARGET)
            if old_target is None:
                _LOGGER.info("No previous target temperature")
                old_target = old_state.attributes.get(ATTR_TEMPERATURE)
            # fix issues caused by old version saving target as dict
            if isinstance(old_target, dict):
                old_target = old_target.get(ATTR_TEMPERATURE)
            if old_target is not None:
                _LOGGER.info("Restoring previous target temperature: %s", old_target)

                self._target_temp = float(old_target)

        self._max_floor_temp = (
            old_state.attributes.get("max_floor_temp") or DEFAULT_MAX_FLOOR_TEMP
        )
