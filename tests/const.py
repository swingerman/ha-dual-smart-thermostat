from homeassistant.const import(
    CONF_NAME,
    CONF_PLATFORM,
)

from custom_components.dual_smart_thermostat.const import(
    DOMAIN as DUAL_SMART_THERMOSTAT_DOMAIN,
    CONF_HEATER,
    CONF_COOLER,
    CONF_INITIAL_HVAC_MODE,
)

from homeassistant.components.climate import(
    HVACMode,
)

CONF_TARGET_SENSOR = "target_sensor"
MOCK_HEATER_SWITCH = "input_boolean.heater"
MOCK_COOLER_SWITCH = "input_boolean.cooler"
MOCK_TARGET_SENSOR = "sensor.target_temperature"

MOCK_CONFIG_HEATER = {
        CONF_NAME: "test",
        CONF_PLATFORM: DUAL_SMART_THERMOSTAT_DOMAIN,
        CONF_HEATER: MOCK_HEATER_SWITCH,
        CONF_TARGET_SENSOR: MOCK_TARGET_SENSOR,
        CONF_INITIAL_HVAC_MODE: HVACMode.HEAT,
        }

MOCK_CONFIG_COOLER = {
        CONF_NAME: "test",
        CONF_PLATFORM: DUAL_SMART_THERMOSTAT_DOMAIN,
        CONF_COOLER: MOCK_COOLER_SWITCH,
        CONF_TARGET_SENSOR: MOCK_TARGET_SENSOR,
        CONF_INITIAL_HVAC_MODE: HVACMode.COOL,
        }
