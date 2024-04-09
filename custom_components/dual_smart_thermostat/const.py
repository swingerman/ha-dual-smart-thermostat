"""const."""

from homeassistant.backports.enum import StrEnum
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

DOMAIN = "dual_smart_thermostat"

CONF_HEATER = "heater"
CONF_AUX_HEATER = "secondary_heater"
CONF_AUX_HEATING_TIMEOUT = "secondary_heater_timeout"
CONF_AUX_HEATING_DUAL_MODE = "secondary_heater_dual_mode"
CONF_COOLER = "cooler"
CONF_FAN = "fan"
CONF_FAN_ON_WITH_COOLER = "fan_turn_on_with_cooler"
CONF_FAN_COOL_TOLERANCE = "fan_cool_tolerance"
CONF_SENSOR = "target_sensor"
CONF_FLOOR_SENSOR = "floor_sensor"
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
CONF_HEAT_COOL_MODE = "heat_cool_mode"

ATTR_PREV_TARGET = "prev_target_temp"
ATTR_PREV_TARGET_LOW = "prev_target_temp_low"
ATTR_PREV_TARGET_HIGH = "prev_target_temp_high"
ATTR_HVAC_ACTION_REASON = "hvac_action_reason"
ATTR_TIMEOUT = "timeout"

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
        vol.Required(ATTR_TIMEOUT): vol.All(cv.time_period, cv.positive_timedelta),
    }
)


class ToleranceDevice(StrEnum):
    """Tolerance device for climate devices."""

    HEATER = "heater"
    COOLER = "cooler"
    AUTO = "auto"
