"""const."""

import enum

from homeassistant.components.climate.const import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_SLEEP,
)
from homeassistant.const import ATTR_ENTITY_ID
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

DEFAULT_TOLERANCE = 0.3
DEFAULT_NAME = "Dual Smart Thermostat"
DEFAULT_MAX_FLOOR_TEMP = 28.0

MIN_CYCLE_KEEP_ALIVE = 60.0

DOMAIN = "dual_smart_thermostat"

# Configuration keys
CONF_SYSTEM_TYPE = "system_type"


class SystemType(enum.StrEnum):
    """System type enumeration for dual smart thermostat."""

    SIMPLE_HEATER = "simple_heater"
    AC_ONLY = "ac_only"
    HEATER_COOLER = "heater_cooler"
    HEAT_PUMP = "heat_pump"
    DUAL_STAGE = "dual_stage"
    FLOOR_HEATING = "floor_heating"


# Legacy constants for backward compatibility
SYSTEM_TYPE_SIMPLE_HEATER = SystemType.SIMPLE_HEATER
SYSTEM_TYPE_AC_ONLY = SystemType.AC_ONLY
SYSTEM_TYPE_HEATER_COOLER = SystemType.HEATER_COOLER
SYSTEM_TYPE_HEAT_PUMP = SystemType.HEAT_PUMP
SYSTEM_TYPE_DUAL_STAGE = SystemType.DUAL_STAGE
SYSTEM_TYPE_FLOOR_HEATING = SystemType.FLOOR_HEATING

# System types for UI selection
SYSTEM_TYPES = {
    SystemType.SIMPLE_HEATER: "Simple Heater Only",
    SystemType.AC_ONLY: "Air Conditioning Only",
    SystemType.HEATER_COOLER: "Heater with Cooler",
    SystemType.HEAT_PUMP: "Heat Pump",
    "advanced": "Advanced (Custom Setup)",
}

CONF_HEATER = "heater"
CONF_AUX_HEATER = "secondary_heater"
CONF_AUX_HEATING_TIMEOUT = "secondary_heater_timeout"
CONF_AUX_HEATING_DUAL_MODE = "secondary_heater_dual_mode"
CONF_COOLER = "cooler"

CONF_DRYER = "dryer"
CONF_MIN_HUMIDITY = "min_humidity"
CONF_MAX_HUMIDITY = "max_humidity"
CONF_TARGET_HUMIDITY = "target_humidity"
CONF_DRY_TOLERANCE = "dry_tolerance"
CONF_MOIST_TOLERANCE = "moist_tolerance"
CONF_HUMIDITY_SENSOR = "humidity_sensor"

CONF_FAN = "fan"
CONF_FAN_MODE = "fan_mode"
CONF_FAN_ON_WITH_AC = "fan_on_with_ac"
CONF_FAN_HOT_TOLERANCE = "fan_hot_tolerance"
CONF_FAN_HOT_TOLERANCE_TOGGLE = "fan_hot_tolerance_toggle"
CONF_FAN_AIR_OUTSIDE = "fan_air_outside"
CONF_SENSOR = "target_sensor"
CONF_STALE_DURATION = "sensor_stale_duration"
CONF_FLOOR_SENSOR = "floor_sensor"
CONF_OUTSIDE_SENSOR = "outside_sensor"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
CONF_MAX_FLOOR_TEMP = "max_floor_temp"
CONF_MIN_FLOOR_TEMP = "min_floor_temp"
CONF_TARGET_TEMP = "target_temp"
CONF_TARGET_TEMP_HIGH = "target_temp_high"
CONF_TARGET_TEMP_LOW = "target_temp_low"
CONF_AC_MODE = "ac_mode"
CONF_MIN_DUR = "min_cycle_duration"
CONF_COLD_TOLERANCE = "cold_tolerance"
CONF_HOT_TOLERANCE = "hot_tolerance"
CONF_KEEP_ALIVE = "keep_alive"
CONF_INITIAL_HVAC_MODE = "initial_hvac_mode"
CONF_PRECISION = "precision"
CONF_TEMP_STEP = "target_temp_step"
CONF_OPENINGS = "openings"
CONF_OPENINGS_SCOPE = "openings_scope"
CONF_HEAT_COOL_MODE = "heat_cool_mode"
CONF_HEAT_PUMP_COOLING = "heat_pump_cooling"

# HVAC power levels
CONF_HVAC_POWER_LEVELS = "hvac_power_levels"
CONF_HVAC_POWER_MIN = "hvac_power_min"
CONF_HVAC_POWER_MAX = "hvac_power_max"
CONF_HVAC_POWER_TOLERANCE = "hvac_power_tolerance"
ATTR_HVAC_POWER_LEVEL = "hvac_power_level"
ATTR_HVAC_POWER_PERCENT = "hvac_power_percent"

ATTR_PREV_TARGET = "prev_target_temp"
ATTR_PREV_TARGET_LOW = "prev_target_temp_low"
ATTR_PREV_TARGET_HIGH = "prev_target_temp_high"
ATTR_PREV_HUMIDITY = "prev_humidity"
ATTR_HVAC_ACTION_REASON = "hvac_action_reason"
ATTR_OPENING_TIMEOUT = "timeout"
ATTR_CLOSING_TIMEOUT = "closing_timeout"

PRESET_ANTI_FREEZE = "Anti Freeze"

CONF_PRESETS = {
    p: f"{p.replace(' ', '_').lower()}"
    for p in (
        PRESET_AWAY,
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_HOME,
        PRESET_SLEEP,
        PRESET_ANTI_FREEZE,
        PRESET_ACTIVITY,
        PRESET_BOOST,
    )
}
CONF_PRESETS_OLD = {k: f"{v}_temp" for k, v in CONF_PRESETS.items()}


TIMED_OPENING_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_OPENING_TIMEOUT): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
        vol.Optional(ATTR_CLOSING_TIMEOUT): vol.All(
            cv.time_period, cv.positive_timedelta
        ),
    }
)


class ToleranceDevice(enum.StrEnum):
    """Tolerance device for climate devices."""

    HEATER = "heater"
    COOLER = "cooler"
    DRYER = "dryer"
    AUTO = "auto"
