"""Config flow for Dual Smart Thermostat integration."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

import voluptuous as vol

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
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
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_INITIAL_HVAC_MODE,
    CONF_KEEP_ALIVE,
    CONF_MAX_FLOOR_TEMP,
    CONF_MAX_TEMP,
    CONF_MIN_DUR,
    CONF_MIN_TEMP,
    CONF_OUTSIDE_SENSOR,
    CONF_PRECISION,
    CONF_PRESETS,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
    CONF_TEMP_STEP,
    DEFAULT_TOLERANCE,
    DOMAIN,
)

# Basic configuration schema - essential settings
CONFIG_SCHEMA = {
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
    vol.Optional(CONF_MIN_DUR): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
}

# Additional features schema
ADDITIONAL_FEATURES_SCHEMA = {
    vol.Optional(CONF_AUX_HEATER): selector.EntitySelector(
        selector.EntitySelectorConfig(domain=SWITCH_DOMAIN)
    ),
    vol.Optional(CONF_OUTSIDE_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Optional(CONF_FLOOR_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.TEMPERATURE
        )
    ),
    vol.Optional(CONF_HUMIDITY_SENSOR): selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain=SENSOR_DOMAIN, device_class=SensorDeviceClass.HUMIDITY
        )
    ),
    vol.Optional(CONF_MAX_FLOOR_TEMP): selector.NumberSelector(
        selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX, 
            unit_of_measurement=DEGREE
        )
    ),
}

# Advanced settings schema
ADVANCED_SETTINGS_SCHEMA = {
    vol.Optional(CONF_KEEP_ALIVE): selector.DurationSelector(
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

# Options flow schema - allows changing most settings except required ones
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
    vol.Optional(CONF_MIN_DUR): selector.DurationSelector(
        selector.DurationSelectorConfig(allow_negative=False)
    ),
}

CONFIG_FLOW = {
    "user": SchemaFlowFormStep(vol.Schema(CONFIG_SCHEMA), next_step="additional"),
    "additional": SchemaFlowFormStep(vol.Schema(ADDITIONAL_FEATURES_SCHEMA), next_step="advanced"),
    "advanced": SchemaFlowFormStep(vol.Schema(ADVANCED_SETTINGS_SCHEMA), next_step="presets"),
    "presets": SchemaFlowFormStep(vol.Schema(PRESETS_SCHEMA)),
}

OPTIONS_FLOW = {
    "init": SchemaFlowFormStep(vol.Schema(OPTIONS_SCHEMA), next_step="additional"),
    "additional": SchemaFlowFormStep(vol.Schema(ADDITIONAL_FEATURES_SCHEMA), next_step="advanced"),
    "advanced": SchemaFlowFormStep(vol.Schema(ADVANCED_SETTINGS_SCHEMA), next_step="presets"),
    "presets": SchemaFlowFormStep(vol.Schema(PRESETS_SCHEMA)),
}


class ConfigFlowHandler(SchemaConfigFlowHandler, domain=DOMAIN):
    """Handle a config or options flow for Dual Smart Thermostat."""

    config_flow = CONFIG_FLOW
    options_flow = OPTIONS_FLOW

    def async_config_entry_title(self, options: Mapping[str, Any]) -> str:
        """Return config entry title."""
        return cast(str, options[CONF_NAME])
