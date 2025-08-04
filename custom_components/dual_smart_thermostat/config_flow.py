"""Config flow for Dual Smart Thermostat integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN, SensorDeviceClass
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_NAME, DEGREE
from homeassistant.helpers import selector
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaConfigFlowHandler,
    SchemaFlowFormStep,
)

from .const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_DRY_TOLERANCE,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_HVAC_POWER_LEVELS,
    CONF_HVAC_POWER_MAX,
    CONF_HVAC_POWER_MIN,
    CONF_HVAC_POWER_TOLERANCE,
    CONF_INITIAL_HVAC_MODE,
    CONF_KEEP_ALIVE,
    CONF_MAX_FLOOR_TEMP,
    CONF_MAX_HUMIDITY,
    CONF_MAX_TEMP,
    CONF_MIN_DUR,
    CONF_MIN_FLOOR_TEMP,
    CONF_MIN_HUMIDITY,
    CONF_MIN_TEMP,
    CONF_MOIST_TOLERANCE,
    CONF_OPENINGS,
    CONF_OUTSIDE_SENSOR,
    CONF_PRECISION,
    CONF_PRESETS,
    CONF_SENSOR,
    CONF_STALE_DURATION,
    CONF_TARGET_HUMIDITY,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    CONF_TEMP_STEP,
    DEFAULT_TOLERANCE,
    DOMAIN,
)

# Basic configuration schema - essential settings
BASIC_CONFIG_SCHEMA = {
    vol.Required(CONF_NAME): selector.TextSelector(),
    vol.Required(CONF_HEATER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Required(CONF_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Optional(CONF_COOLER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_AC_MODE, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_HEAT_COOL_MODE, default=False): selector.BooleanSelector(),
    vol.Optional(
        CONF_COLD_TOLERANCE, default=DEFAULT_TOLERANCE
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1,
            min=0.1,
            max=5.0
        )
    ),
    vol.Optional(
        CONF_HOT_TOLERANCE, default=DEFAULT_TOLERANCE
    ): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1,
            min=0.1,
            max=5.0
        )
    ),
}

# Advanced settings schema - optional features
ADVANCED_CONFIG_SCHEMA = {
    vol.Optional(CONF_MIN_DUR): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_KEEP_ALIVE): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_STALE_DURATION): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_INITIAL_HVAC_MODE): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["heat", "cool", "heat_cool", "off", "fan_only", "dry"],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_PRECISION): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["0.1", "0.5", "1.0"],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_TEMP_STEP): selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=["0.1", "0.5", "1.0"],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    ),
    vol.Optional(CONF_MIN_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_MAX_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_TARGET_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_TARGET_TEMP_HIGH): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_TARGET_TEMP_LOW): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_OUTSIDE_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
}

# Heating features schema
HEATING_FEATURES_SCHEMA = {
    vol.Optional(CONF_AUX_HEATER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_AUX_HEATING_DUAL_MODE, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_AUX_HEATING_TIMEOUT): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
    vol.Optional(CONF_HEAT_PUMP_COOLING): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=BINARY_SENSOR_DOMAIN)
    ),
}

# Floor temperature schema
FLOOR_TEMP_SCHEMA = {
    vol.Optional(CONF_FLOOR_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Optional(CONF_MAX_FLOOR_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
    vol.Optional(CONF_MIN_FLOOR_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
}

# Fan features schema
FAN_FEATURES_SCHEMA = {
    vol.Optional(CONF_FAN): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_FAN_MODE, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_FAN_ON_WITH_AC, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_FAN_AIR_OUTSIDE, default=False): selector.BooleanSelector(),
    vol.Optional(CONF_FAN_HOT_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1
        )
    ),
}

# Humidity features schema
HUMIDITY_FEATURES_SCHEMA = {
    vol.Optional(CONF_DRYER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.HUMIDITY
        )
    ),
    vol.Optional(CONF_MIN_HUMIDITY): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement="%",
            min=0,
            max=100
        )
    ),
    vol.Optional(CONF_MAX_HUMIDITY): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement="%",
            min=0,
            max=100
        )
    ),
    vol.Optional(CONF_TARGET_HUMIDITY): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement="%",
            min=0,
            max=100
        )
    ),
    vol.Optional(CONF_DRY_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement="%",
            step=1
        )
    ),
    vol.Optional(CONF_MOIST_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement="%",
            step=1
        )
    ),
}

# Power management schema
POWER_FEATURES_SCHEMA = {
    vol.Optional(CONF_HVAC_POWER_LEVELS): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX,
            min=2,
            max=10
        )
    ),
    vol.Optional(CONF_HVAC_POWER_MIN): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX,
            min=0,
            max=100
        )
    ),
    vol.Optional(CONF_HVAC_POWER_MAX): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX,
            min=0,
            max=100
        )
    ),
    vol.Optional(CONF_HVAC_POWER_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1
        )
    ),
}

# Presets schema
PRESETS_SCHEMA = {
    vol.Optional(v): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    )
    for v in CONF_PRESETS.values()
}

# Options flow schema (subset of basic config for reconfiguration)
OPTIONS_SCHEMA = {
    vol.Optional(CONF_COOLER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_AC_MODE): selector.BooleanSelector(),
    vol.Optional(CONF_HEAT_COOL_MODE): selector.BooleanSelector(),
    vol.Optional(CONF_COLD_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1,
            min=0.1,
            max=5.0
        )
    ),
    vol.Optional(CONF_HOT_TOLERANCE): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE, 
            step=0.1,
            min=0.1,
            max=5.0
        )
    ),
}

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(vol.Schema(BASIC_CONFIG_SCHEMA), next_step="advanced"),
    "advanced": SchemaFlowFormStep(vol.Schema(ADVANCED_CONFIG_SCHEMA), next_step="heating"),
    "heating": SchemaFlowFormStep(vol.Schema(HEATING_FEATURES_SCHEMA), next_step="floor_temp"),
    "floor_temp": SchemaFlowFormStep(vol.Schema(FLOOR_TEMP_SCHEMA), next_step="fan"),
    "fan": SchemaFlowFormStep(vol.Schema(FAN_FEATURES_SCHEMA), next_step="humidity"),
    "humidity": SchemaFlowFormStep(vol.Schema(HUMIDITY_FEATURES_SCHEMA), next_step="power"),
    "power": SchemaFlowFormStep(vol.Schema(POWER_FEATURES_SCHEMA), next_step="presets"),
    "presets": SchemaFlowFormStep(vol.Schema(PRESETS_SCHEMA)),
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(vol.Schema(OPTIONS_SCHEMA), next_step="advanced"),
    "advanced": SchemaFlowFormStep(vol.Schema(ADVANCED_CONFIG_SCHEMA), next_step="heating"),
    "heating": SchemaFlowFormStep(vol.Schema(HEATING_FEATURES_SCHEMA), next_step="floor_temp"),
    "floor_temp": SchemaFlowFormStep(vol.Schema(FLOOR_TEMP_SCHEMA), next_step="fan"),
    "fan": SchemaFlowFormStep(vol.Schema(FAN_FEATURES_SCHEMA), next_step="humidity"),
    "humidity": SchemaFlowFormStep(vol.Schema(HUMIDITY_FEATURES_SCHEMA), next_step="power"),
    "power": SchemaFlowFormStep(vol.Schema(POWER_FEATURES_SCHEMA), next_step="presets"),
    "presets": SchemaFlowFormStep(vol.Schema(PRESETS_SCHEMA)),
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Dual Smart Thermostat."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
