"""constants"""
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
)

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = "Dual Smart"
DEFAULT_MAX_FLOOR_TEMP = 28.0

CONF_HEATER = "heater"
CONF_COOLER = "cooler"
CONF_SENSOR = "target_sensor"
CONF_FLOOR_SENSOR = "floor_sensor"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_MAX_FLOOR_TEMP = "max_floor_temp"
CONF_TARGET_TEMP = "target_temp"
CONF_TARGET_TEMP_HIGH = "target_temp_high"
CONF_TARGET_TEMP_LOW = "target_temp_low"
CONF_AC_MODE = "ac_mode"
CONF_MIN_DUR = "min_cycle_duration"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HOT_TOLERANCE = "hot_tolerance"
CONF_KEEP_ALIVE = "keep_alive"
CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_AWAY_TEMP = "away_temp"
CONF_PRECISION = "precision"
CONF_OPENINGS = "openings"
SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE
