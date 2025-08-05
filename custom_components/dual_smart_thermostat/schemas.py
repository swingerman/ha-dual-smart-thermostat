"""Schema definitions for dual smart thermostat configuration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.input_boolean import DOMAIN as INPUT_BOOLEAN_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import section
from homeassistant.helpers import selector
import voluptuous as vol

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

_LOGGER = logging.getLogger(__name__)


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


def get_floor_heating_schema(defaults: dict[str, Any] | None = None):
    """Get floor heating configuration schema.

    Accepts an optional `defaults` mapping to pre-populate selectors (used by
    the options flow to show the currently configured floor sensor/limits).
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                CONF_FLOOR_SENSOR, default=defaults.get(CONF_FLOOR_SENSOR)
            ): get_entity_selector(SENSOR_DOMAIN),
            vol.Optional(
                CONF_MAX_FLOOR_TEMP, default=defaults.get(CONF_MAX_FLOOR_TEMP, 28)
            ): get_temperature_selector(min_value=5, max_value=35),
            vol.Optional(
                CONF_MIN_FLOOR_TEMP, default=defaults.get(CONF_MIN_FLOOR_TEMP, 5)
            ): get_temperature_selector(min_value=5, max_value=35),
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


def get_ac_only_features_schema(defaults: dict[str, Any] | None = None):
    """Get AC only features selection schema.

    Accepts an optional `defaults` dict to pre-select toggles for features that
    are already configured in the current entry data (used by the options flow).
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                "configure_fan", default=bool(defaults.get("configure_fan", False))
            ): get_boolean_selector(),
            vol.Optional(
                "configure_openings",
                default=bool(defaults.get("configure_openings", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_humidity",
                default=bool(defaults.get("configure_humidity", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_presets",
                default=bool(defaults.get("configure_presets", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_advanced",
                default=bool(defaults.get("configure_advanced", False)),
            ): get_boolean_selector(),
        }
    )


def get_simple_heater_features_schema(defaults: dict[str, Any] | None = None):
    """Get Simple Heater features selection schema.

    The simple heater doesn't expose AC-specific features like fan or
    humidity by default, but users may still want to configure openings,
    presets or advanced settings. This combined step mirrors the AC-only
    features step but scoped for simple heater systems.
    """
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Optional(
                "configure_openings",
                default=bool(defaults.get("configure_openings", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_presets",
                default=bool(defaults.get("configure_presets", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_floor_heating",
                default=bool(defaults.get("configure_floor_heating", False)),
            ): get_boolean_selector(),
            vol.Optional(
                "configure_advanced",
                default=bool(defaults.get("configure_advanced", False)),
            ): get_boolean_selector(),
        }
    )


def get_system_features_schema(system_type: str):
    """Return a features-selection schema tailored to the given system type.

    This lets each system present a single combined "which features do you
    want to configure" step (including advanced), and subsequent steps are
    shown conditionally based on the selections.
    """
    # Base features available to most systems
    schema = {
        vol.Optional("configure_presets", default=False): get_boolean_selector(),
        vol.Optional("configure_openings", default=False): get_boolean_selector(),
        vol.Optional("configure_advanced", default=False): get_boolean_selector(),
    }

    if system_type in ["heater_cooler", "heat_pump"]:
        # These systems can have fans and humidity control
        schema[vol.Optional("configure_fan", default=False)] = get_boolean_selector()
        schema[vol.Optional("configure_humidity", default=False)] = (
            get_boolean_selector()
        )

    # Floor heating can be configured for most heating-capable systems
    if system_type in ["simple_heater", "heater_cooler", "heat_pump", "dual_stage"]:
        schema[vol.Optional("configure_floor_heating", default=False)] = (
            get_boolean_selector()
        )

    return vol.Schema(schema)


def get_core_schema(
    system_type: str, defaults: dict[str, Any] | None = None, include_name: bool = True
):
    """Build the core configuration schema used by both config and options flows.

    This centralizes the field choices and selector types so config and options
    flows render the same UI. Pass `defaults` to populate selector defaults
    (used by options flow where current values exist). If `include_name` is
    False the name field is omitted (used by options flow).
    """
    defaults = defaults or {}
    schema_dict: dict[Any, Any] = {}

    # Base fields (name and sensor) — include name only for config flow
    if include_name:
        schema_dict[vol.Required(CONF_NAME, default=defaults.get(CONF_NAME))] = (
            get_text_selector()
        )

    schema_dict[vol.Required(CONF_SENSOR, default=defaults.get(CONF_SENSOR))] = (
        get_entity_selector(SENSOR_DOMAIN)
    )

    # Core entities based on system type
    if system_type == "ac_only":
        # AC-only uses heater field for compatibility
        schema_dict[
            vol.Required(
                CONF_HEATER,
                default=defaults.get(CONF_HEATER) or defaults.get(CONF_COOLER),
            )
        ] = get_entity_selector(SWITCH_DOMAIN)
    else:
        # Heater is required unless system explicitly hides it
        schema_dict[vol.Required(CONF_HEATER, default=defaults.get(CONF_HEATER))] = (
            get_entity_selector(SWITCH_DOMAIN)
        )

        # Show cooler for systems that have separate cooler
        if system_type == "heater_cooler":
            schema_dict[
                vol.Optional(CONF_COOLER, default=defaults.get(CONF_COOLER))
            ] = get_entity_selector(SWITCH_DOMAIN)

        # AC mode toggle (not for simple heater)
        if system_type != "simple_heater":
            schema_dict[
                vol.Optional(CONF_AC_MODE, default=defaults.get(CONF_AC_MODE, False))
            ] = get_boolean_selector()

        # Heat pump cooling toggle
        if system_type == "heat_pump":
            schema_dict[
                vol.Optional(
                    CONF_HEAT_PUMP_COOLING,
                    default=defaults.get(CONF_HEAT_PUMP_COOLING, False),
                )
            ] = get_boolean_selector()

    # Common tolerance/time options that were present in options flow core
    schema_dict[
        vol.Optional(
            CONF_COLD_TOLERANCE,
            default=defaults.get(CONF_COLD_TOLERANCE, DEFAULT_TOLERANCE),
        )
    ] = get_percentage_selector()
    schema_dict[
        vol.Optional(
            CONF_HOT_TOLERANCE,
            default=defaults.get(CONF_HOT_TOLERANCE, DEFAULT_TOLERANCE),
        )
    ] = get_percentage_selector()
    schema_dict[vol.Optional(CONF_MIN_DUR, default=defaults.get(CONF_MIN_DUR))] = (
        get_time_selector()
    )

    return vol.Schema(schema_dict)


def get_openings_selection_schema(
    collected_config: dict[str, Any] = None, defaults: list[str] = None
):
    """Get schema for selecting opening entities."""
    # log the defaults
    _LOGGER.debug("Openings selection defaults: %s", defaults)
    return vol.Schema(
        {
            vol.Optional(
                "selected_openings", default=defaults or []
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=[INPUT_BOOLEAN_DOMAIN, BINARY_SENSOR_DOMAIN, SWITCH_DOMAIN],
                    multiple=True,
                )
            ),
        }
    )


def get_openings_schema(selected_entities: list[str]):
    """Get schema for configuring opening timeouts."""
    schema_dict = {}
    # Group each opening's timeout fields into a collapsible section so the UI
    # shows a separate, optional group per selected entity. Section keys are
    # generated from the entity id (e.g. "binary_sensor.front_door_timeouts").
    # Static translations may be provided in the integration `translations/en.json`
    # under the `config.step.openings_config.sections` mapping if desired.
    for entity_id in selected_entities:
        inner_schema = vol.Schema(
            {
                vol.Optional("timeout_open", default=30): get_time_selector(
                    min_value=0, max_value=3600
                ),
                vol.Optional("timeout_close", default=30): get_time_selector(
                    min_value=0, max_value=3600
                ),
            }
        )

        # Use a section keyed by the entity id + suffix so each entity has its
        # own collapsible group in the frontend. Start open by default.
        section_key = vol.Optional(entity_id)
        schema_dict[section_key] = section(inner_schema, {"collapsed": False})

    return vol.Schema(schema_dict)


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


def get_preset_selection_schema(defaults: list[str] | None = None):
    """Get preset selection schema.

    Accepts an optional list of preset keys to pre-select in the multi-select
    selector (used by the options flow to pre-check presets that have
    configuration data stored in the entry).
    """
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
            vol.Optional("presets", default=defaults or []): get_multi_select_selector(
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
