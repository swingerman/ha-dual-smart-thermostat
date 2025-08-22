"""Schema definitions for dual smart thermostat configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    ATTR_CLOSING_TIMEOUT,
    ATTR_OPENING_TIMEOUT,
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
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
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
    CONF_SYSTEM_TYPE,
    CONF_TARGET_HUMIDITY,
    CONF_TARGET_TEMP,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    CONF_TEMP_STEP,
    DEFAULT_TOLERANCE,
    SYSTEM_TYPES,
)
from .schema_utils import (
    get_boolean_selector,
    get_entity_selector,
    get_multi_select_selector,
    get_percentage_selector,
    get_select_selector,
    get_temperature_selector,
    get_text_selector,
    get_time_selector,
)


def get_system_type_schema():
    """Get system type selection schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SYSTEM_TYPE): get_select_selector(
                options=[{"value": k, "label": v} for k, v in SYSTEM_TYPES.items()],
                mode=selector.SelectSelectorMode.LIST,
            ),
        }
    )


def get_base_schema():
    """Get base configuration schema with logically grouped fields."""
    return vol.Schema(
        {
            # Basic Information
            vol.Required(CONF_NAME): get_text_selector(),
            # Sensors
            vol.Required(CONF_SENSOR): get_entity_selector(SENSOR_DOMAIN),
        }
    )


def get_grouped_schema(
    system_type: str,
    show_heater: bool = True,
    show_cooler: bool = True,
    show_aux_heater: bool = False,
    show_dryer: bool = False,
    show_dual_stage: bool = False,
    show_heat_pump_cooling: bool = False,
    show_ac_mode: bool = False,
    show_fan_mode: bool = False,
) -> vol.Schema:
    """Get grouped schema based on system type and selected options."""
    schema_dict = {}

    # Core entities based on system type
    if show_heater:
        schema_dict[vol.Required(CONF_HEATER)] = get_entity_selector(SWITCH_DOMAIN)

    if show_cooler:
        schema_dict[vol.Required(CONF_COOLER)] = get_entity_selector(SWITCH_DOMAIN)

    if show_aux_heater:
        schema_dict[vol.Optional(CONF_AUX_HEATER)] = get_entity_selector(SWITCH_DOMAIN)

    if show_dryer:
        schema_dict[vol.Required(CONF_DRYER)] = get_entity_selector(SWITCH_DOMAIN)

    # Special modes
    if show_dual_stage:
        schema_dict[vol.Optional(CONF_AUX_HEATING_DUAL_MODE, default=False)] = (
            get_boolean_selector()
        )

    if show_heat_pump_cooling:
        schema_dict[vol.Optional(CONF_HEAT_PUMP_COOLING, default=False)] = (
            get_boolean_selector()
        )

    if show_ac_mode:
        schema_dict[vol.Optional(CONF_AC_MODE, default=False)] = get_boolean_selector()

    if show_fan_mode:
        schema_dict[vol.Optional(CONF_FAN_MODE, default=False)] = get_boolean_selector()

    return vol.Schema(schema_dict)


def get_heating_schema():
    """Get heating-specific configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HEATER): get_entity_selector(SWITCH_DOMAIN),
        }
    )


def get_cooling_schema():
    """Get cooling-specific configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_COOLER): get_entity_selector(SWITCH_DOMAIN),
        }
    )


def get_dual_stage_schema():
    """Get dual stage heating configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HEATER): get_entity_selector(SWITCH_DOMAIN),
            vol.Optional(CONF_AUX_HEATER): get_entity_selector(SWITCH_DOMAIN),
            vol.Optional(
                CONF_AUX_HEATING_DUAL_MODE, default=False
            ): get_boolean_selector(),
            vol.Optional(CONF_AUX_HEATING_TIMEOUT, default=15): get_time_selector(
                min_value=0, max_value=3600
            ),
        }
    )


def get_floor_heating_toggle_schema():
    """Get floor heating toggle schema."""
    return vol.Schema(
        {
            vol.Optional("floor_heating", default=False): get_boolean_selector(),
        }
    )


def get_floor_heating_schema():
    """Get floor heating configuration schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_FLOOR_SENSOR): get_entity_selector(SENSOR_DOMAIN),
            vol.Optional(CONF_MAX_FLOOR_TEMP, default=28): get_temperature_selector(
                min_value=5, max_value=35
            ),
            vol.Optional(CONF_MIN_FLOOR_TEMP, default=5): get_temperature_selector(
                min_value=5, max_value=35
            ),
        }
    )


def get_openings_toggle_schema():
    """Get openings toggle schema."""
    return vol.Schema(
        {
            vol.Optional("openings", default=False): get_boolean_selector(),
        }
    )


def get_fan_toggle_schema():
    """Get fan toggle schema."""
    return vol.Schema(
        {
            vol.Optional("fan", default=False): get_boolean_selector(),
        }
    )


def get_humidity_toggle_schema():
    """Get humidity toggle schema."""
    return vol.Schema(
        {
            vol.Optional("humidity", default=False): get_boolean_selector(),
        }
    )


def get_ac_only_features_schema():
    """Get AC only features selection schema."""
    return vol.Schema(
        {
            vol.Optional("configure_fan", default=False): get_boolean_selector(),
            vol.Optional("configure_openings", default=False): get_boolean_selector(),
            vol.Optional("configure_humidity", default=False): get_boolean_selector(),
            vol.Optional("configure_presets", default=False): get_boolean_selector(),
            vol.Optional("configure_advanced", default=False): get_boolean_selector(),
        }
    )


def get_openings_selection_schema(collected_config: dict[str, Any] = None):
    """Get schema for selecting opening entities."""
    if collected_config is None:
        collected_config = {}

    return vol.Schema(
        {
            vol.Required(CONF_OPENINGS): get_multi_select_selector(
                options=[
                    {"value": entity_id, "label": entity_id}
                    for entity_id in sorted(
                        [
                            e.entity_id
                            for e in collected_config.get("hass", {})
                            .get("states", {})
                            .values()
                            if e.domain
                            in [INPUT_BOOLEAN_DOMAIN, "binary_sensor", SWITCH_DOMAIN]
                            and not e.entity_id.startswith("sensor.")
                        ]
                    )
                ]
            ),
        }
    )


def get_openings_schema(selected_entities: list[str]):
    """Get schema for configuring opening timeouts."""
    schema_dict = {}

    for entity_id in selected_entities:

        schema_dict[vol.Optional(f"{entity_id}_{ATTR_OPENING_TIMEOUT}", default=30)] = (
            get_time_selector(min_value=0, max_value=3600)
        )
        schema_dict[vol.Optional(f"{entity_id}_{ATTR_CLOSING_TIMEOUT}", default=30)] = (
            get_time_selector(min_value=0, max_value=3600)
        )

    return vol.Schema(schema_dict)


def get_openings_translations_data(
    selected_entities: list[str],
) -> dict[str, dict[str, str]]:
    """Get dynamic translations data for openings configuration."""
    data = {}
    data_description = {}

    for entity_id in selected_entities:
        # Extract friendly name from entity_id for display (remove domain prefix)
        if "." in entity_id:
            display_name = entity_id.split(".", 1)[1].replace("_", " ").title()
        else:
            display_name = entity_id.replace("_", " ").title()

        data[f"{entity_id}_{ATTR_OPENING_TIMEOUT}"] = (
            f"Opening timeout - {display_name}"
        )
        data[f"{entity_id}_{ATTR_CLOSING_TIMEOUT}"] = (
            f"Closing timeout - {display_name}"
        )

        data_description[f"{entity_id}_{ATTR_OPENING_TIMEOUT}"] = (
            f"Time to wait after {display_name} opens before turning off HVAC. This prevents brief openings from affecting operation. Leave empty for immediate response."
        )
        data_description[f"{entity_id}_{ATTR_CLOSING_TIMEOUT}"] = (
            f"Time to wait after {display_name} closes before turning HVAC back on. This ensures the opening is fully closed and room can be efficiently conditioned. Leave empty for immediate response."
        )

    return {"data": data, "data_description": data_description}


def get_fan_schema():
    """Get fan configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_FAN): get_entity_selector(SWITCH_DOMAIN),
            vol.Optional(CONF_FAN_ON_WITH_AC, default=True): get_boolean_selector(),
            vol.Optional(CONF_FAN_AIR_OUTSIDE, default=False): get_boolean_selector(),
            vol.Optional(
                CONF_FAN_HOT_TOLERANCE_TOGGLE, default=False
            ): get_boolean_selector(),
        }
    )


def get_humidity_schema():
    """Get humidity configuration schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HUMIDITY_SENSOR): get_entity_selector(SENSOR_DOMAIN),
            vol.Optional(CONF_DRYER): get_entity_selector(SWITCH_DOMAIN),
            vol.Optional(CONF_TARGET_HUMIDITY, default=50): get_percentage_selector(),
            vol.Optional(CONF_DRY_TOLERANCE, default=3): get_percentage_selector(
                max_value=20
            ),
            vol.Optional(CONF_MOIST_TOLERANCE, default=3): get_percentage_selector(
                max_value=20
            ),
            vol.Optional(CONF_MIN_HUMIDITY, default=30): get_percentage_selector(),
            vol.Optional(CONF_MAX_HUMIDITY, default=99): get_percentage_selector(),
        }
    )


def get_additional_sensors_schema():
    """Get additional sensors configuration schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_OUTSIDE_SENSOR): get_entity_selector(SENSOR_DOMAIN),
        }
    )


def get_heat_cool_mode_schema():
    """Get heat/cool mode configuration schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_HEAT_COOL_MODE, default=False): get_boolean_selector(),
        }
    )


def get_advanced_settings_schema():
    """Get advanced settings configuration schema."""
    return vol.Schema(
        {
            vol.Optional(CONF_MIN_TEMP, default=7): get_temperature_selector(
                min_value=5, max_value=35
            ),
            vol.Optional(CONF_MAX_TEMP, default=35): get_temperature_selector(
                min_value=5, max_value=50
            ),
            vol.Optional(CONF_TARGET_TEMP, default=20): get_temperature_selector(
                min_value=5, max_value=35
            ),
            vol.Optional(CONF_TARGET_TEMP_HIGH, default=26): get_temperature_selector(
                min_value=5, max_value=35
            ),
            vol.Optional(CONF_TARGET_TEMP_LOW, default=21): get_temperature_selector(
                min_value=5, max_value=35
            ),
            vol.Optional(
                CONF_COLD_TOLERANCE, default=DEFAULT_TOLERANCE
            ): get_temperature_selector(min_value=0.1, max_value=10, step=0.1),
            vol.Optional(
                CONF_HOT_TOLERANCE, default=DEFAULT_TOLERANCE
            ): get_temperature_selector(min_value=0.1, max_value=10, step=0.1),
            vol.Optional(CONF_MIN_DUR, default=300): get_time_selector(
                min_value=0, max_value=3600
            ),
            vol.Optional(CONF_KEEP_ALIVE, default=300): get_time_selector(
                min_value=0, max_value=3600
            ),
            vol.Optional(CONF_PRECISION, default=0.1): get_select_selector(
                options=[
                    {"value": "0.1", "label": "0.1"},
                    {"value": "0.5", "label": "0.5"},
                    {"value": "1.0", "label": "1.0"},
                ]
            ),
            vol.Optional(CONF_TEMP_STEP, default=1): get_select_selector(
                options=[
                    {"value": "1", "label": "1"},
                    {"value": "0.5", "label": "0.5"},
                ]
            ),
        }
    )


def get_preset_selection_schema():
    """Get preset selection schema."""
    # Attempt to load translation labels from the integration translations file.
    labels: dict[str, str] = {}
    try:
        trans_path = Path(__file__).parent / "translations" / "en.json"
        if trans_path.exists():
            with trans_path.open("r", encoding="utf-8") as fh:
                trans = json.load(fh)

            # Support a shared/common section so translations can be reused
            # between config and options flows to avoid duplication.
            shared = (
                trans.get("shared", {})
                .get("step", {})
                .get("preset_selection", {})
                .get("data", {})
            ) or {}
            common = (
                trans.get("common", {})
                .get("step", {})
                .get("preset_selection", {})
                .get("data", {})
            ) or {}

            config_labels = (
                trans.get("config", {})
                .get("step", {})
                .get("preset_selection", {})
                .get("data", {})
            ) or {}
            options_labels = (
                trans.get("options", {})
                .get("step", {})
                .get("preset_selection", {})
                .get("data", {})
            ) or {}

            # Merge with priority: shared/common < config < options
            merged: dict[str, str] = {}
            merged.update(shared)
            merged.update(common)
            merged.update(config_labels)
            merged.update(options_labels)
            labels = merged
    except Exception:
        labels = {}

    options = []
    for k, _v in CONF_PRESETS.items():
        # Use translation label if available, fall back to a title-cased key
        label = labels.get(k, k.replace("_", " ").title())
        options.append({"value": k, "label": label})

    return vol.Schema(
        {
            vol.Optional("presets", default=[]): get_multi_select_selector(
                options=options
            ),
        }
    )


def get_presets_schema(user_input: dict[str, Any]) -> vol.Schema:
    """Get presets configuration schema based on selected presets.

    This function accepts multiple input shapes to remain backward compatible:
    - New multi-select format: user_input["presets"] -> list[str] or list[dict(value,label)]
    - Old boolean format: user_input contains keys per-preset (either preset key or internal name) set to True
    """
    schema_dict = {}

    # Defensive: user_input may be None or empty
    if not user_input:
        selected_presets: list[str] = []
    else:
        # Prefer explicit 'presets' key produced by the multi-select selector
        if "presets" in user_input:
            raw = user_input.get("presets") or []
            # Normalize entries: allow list of strings or list of option dicts
            selected_presets = [
                (item["value"] if isinstance(item, dict) and "value" in item else item)
                for item in raw
            ]
        else:
            # Fallback: detect old boolean format. CONF_PRESETS maps display->internal names.
            selected_presets = []
            for preset_key, internal_name in CONF_PRESETS.items():
                if user_input.get(preset_key) or user_input.get(internal_name):
                    selected_presets.append(preset_key)

    for preset in selected_presets:
        if preset in CONF_PRESETS:
            schema_dict[vol.Optional(f"{preset}_temp", default=20)] = (
                get_temperature_selector(min_value=5, max_value=35)
            )

    return vol.Schema(schema_dict)
