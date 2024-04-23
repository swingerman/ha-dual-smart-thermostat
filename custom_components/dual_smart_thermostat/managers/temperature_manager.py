import logging
import math
from typing import Any

from homeassistant.components.climate import DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP
from homeassistant.components.climate.const import HVACMode
from homeassistant.const import ATTR_TEMPERATURE, PRECISION_WHOLE, UnitOfTemperature
from homeassistant.core import HomeAssistant, State, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util.unit_conversion import TemperatureConverter

from custom_components.dual_smart_thermostat.const import (
    ATTR_PREV_TARGET,
    ATTR_PREV_TARGET_HIGH,
    ATTR_PREV_TARGET_LOW,
    CONF_COLD_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FLOOR_SENSOR,
    CONF_HOT_TOLERANCE,
    CONF_MAX_FLOOR_TEMP,
    CONF_MAX_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_MIN_TEMP,
    CONF_PRECISION,
    CONF_SENSOR,
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


class TemperatureManager(StateManager):

    def __init__(
        self,
        hass: HomeAssistant,
        config: ConfigType,
        presets: dict[str, Any],
    ):
        self.hass = hass
        self._sensor_floor = config.get(CONF_FLOOR_SENSOR)
        self._sensor = config.get(CONF_SENSOR)

        self._min_temp = config.get(CONF_MIN_TEMP)
        self._max_temp = config.get(CONF_MAX_TEMP)

        self._max_floor_temp = config.get(CONF_MAX_FLOOR_TEMP)
        self._min_floor_temp = config.get(CONF_MIN_FLOOR_TEMP)

        self._target_temp = config.get(CONF_TARGET_TEMP)
        self._target_temp_high = config.get(CONF_TARGET_TEMP_HIGH)
        self._target_temp_low = config.get(CONF_TARGET_TEMP_LOW)
        self._temp_target_temperature_step = config.get(CONF_TEMP_STEP)

        self._cold_tolerance = config.get(CONF_COLD_TOLERANCE)
        self._hot_tolerance = config.get(CONF_HOT_TOLERANCE)
        self._fan_hot_tolerance = config.get(CONF_FAN_HOT_TOLERANCE)

        self._saved_target_temp = self.target_temp or next(iter(presets.values()), None)
        self._saved_target_temp_low = None
        self._saved_target_temp_high = None
        self._temp_precision = config.get(CONF_PRECISION)

        self._temperature_unit = hass.config.units.temperature_unit

        self._cur_temp = None
        self._cur_floor_temp = None

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
        _LOGGER.debug("Setting max floor temp property: %s", temp)
        self._max_floor_temp = temp

    @property
    def min_floor_temp(self) -> float:
        return self._min_floor_temp

    @property
    def saved_target_temp(self) -> float:
        return self._saved_target_temp

    @saved_target_temp.setter
    def saved_target_temp(self, temp: float) -> None:
        self._saved_target_temp = temp

    @property
    def saved_target_temp_low(self) -> float:
        return self._saved_target_temp_low

    @saved_target_temp_low.setter
    def saved_target_temp_low(self, temp: float) -> None:
        self._saved_target_temp_low = temp

    @property
    def saved_target_temp_high(self) -> float:
        return self._saved_target_temp_high

    @saved_target_temp_high.setter
    def saved_target_temp_high(self, temp: float) -> None:
        self._saved_target_temp_high = temp

    @property
    def fan_cold_tolerance(self) -> float:
        return self._fan_hot_tolerance

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
        # if temp_low is None or temp_high is None:
        #     return

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

    @property
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
            self._cur_temp > too_hot_for_ac_temp
            and self._cur_temp <= too_hot_for_fan_temp
        )

    def is_too_cold(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is below target."""
        if self._cur_temp is None:
            return False
        target_temp = getattr(self, target_attr)
        _LOGGER.debug("Target temp: %s, current temp: %s", target_temp, self._cur_temp)
        return target_temp >= self._cur_temp + self._cold_tolerance

    def is_too_hot(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is above target."""
        _LOGGER.debug(
            "is_too_hot,  %s, %s, %s", self._cur_temp, target_attr, self._hot_tolerance
        )
        if self._cur_temp is None:
            return False
        target_temp = getattr(self, target_attr)
        return self._cur_temp >= target_temp + self._hot_tolerance

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

    def set_default_target_temps(
        self, is_target_mode: bool, is_range_mode: bool, hvac_modes: list[HVACMode]
    ) -> None:
        """Set default values for target temperatures."""
        _LOGGER.debug(
            "Setting default target temperatures, target mode: %s, range mode: %s, hvac_mode: %s",
            is_target_mode,
            is_range_mode,
            hvac_modes,
        )
        if is_target_mode:
            self._set_default_temps_target_mode(hvac_modes)

        elif is_range_mode:
            self._set_default_temps_range_mode()

    def _set_default_temps_target_mode(self, hvac_modes: list[HVACMode]) -> None:
        if self._target_temp is not None:
            return

        _LOGGER.info("Setting default target temperature target mode: %s", hvac_modes)

        # if HVACMode.COOL in hvac_device.hvac_modes or hvac_mode == HVACMode.COOL:
        if HVACMode.COOL in hvac_modes or HVACMode.FAN_ONLY in hvac_modes:
            if self._target_temp_high is None:
                self._target_temp = self.max_temp
                _LOGGER.warning(
                    "Undefined target temperature, falling back to %s",
                    self._target_temp,
                )
            else:
                self._target_temp = self._target_temp_high
            return

        if self._target_temp_low is None:
            self._target_temp = self.min_temp
            _LOGGER.warning(
                "Undefined target temperature, falling back to %s",
                self._target_temp,
            )
        else:
            self._target_temp = self._target_temp_low

    def _set_default_temps_range_mode(self) -> None:
        if self._target_temp_low is not None and self._target_temp_high is not None:
            return
        _LOGGER.info("Setting default target temperature range mode")

        if self._target_temp is None:
            self._target_temp = self.min_temp
            self._target_temp_low = self.min_temp
            self._target_temp_high = self.max_temp
            _LOGGER.warning(
                "Undefined target temperature range, falled back to %s-%s-%s",
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

    def apply_old_state(self, old_state: State) -> None:
        if old_state is None:
            return

        # If we have no initial temperature, restore
        if self._target_temp_low is None:
            old_target_min = old_state.attributes.get(ATTR_PREV_TARGET_LOW)
            if old_target_min is not None:
                self._target_temp_low = float(old_target_min)
        if self._target_temp_high is None:
            old_target_max = old_state.attributes.get(ATTR_PREV_TARGET_HIGH)
            if old_target_max is not None:
                self._target_temp_high = float(old_target_max)
        if self._target_temp is None:
            _LOGGER.info("Restoring previous target temperature")
            old_target = old_state.attributes.get(ATTR_PREV_TARGET)
            if old_target is None:
                _LOGGER.info("No previous target temperature")
                old_target = old_state.attributes.get(ATTR_TEMPERATURE)
            if old_target is not None:
                _LOGGER.info("Restoring previous target temperature: %s", old_target)
                self._target_temp = float(old_target)

        self._max_floor_temp = (
            old_state.attributes.get("max_floor_temp") or DEFAULT_MAX_FLOOR_TEMP
        )
