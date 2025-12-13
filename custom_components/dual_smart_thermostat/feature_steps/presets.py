"""Presets configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from ..const import CONF_PRESETS
from ..schemas import get_preset_selection_schema, get_presets_schema
from .shared import build_schema_context_from_flow


class PresetsSteps:
    """Handle presets configuration steps for both config and options flows."""

    def __init__(self):
        """Initialize presets steps handler."""
        pass

    async def async_step_selection(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle preset selection step."""
        if user_input is not None:
            collected_config.update(user_input)

            # For options flow, mark that we've shown presets to prevent loops
            if isinstance(flow_instance, OptionsFlow):
                collected_config["presets_shown"] = True

            # Check if any presets are enabled
            # Support both formats: new multi-select ("presets": ["away", "home"])
            # and old boolean format ("away": True, "home": True)
            selected_presets = user_input.get("presets", [])
            if selected_presets:
                # New multi-select format
                any_preset_enabled = bool(selected_presets)
            else:
                # Old boolean format - check individual preset keys
                any_preset_enabled = any(
                    user_input.get(preset_key, False)
                    for preset_key in CONF_PRESETS.values()
                )

            if any_preset_enabled:
                # At least one preset is enabled, proceed to configuration
                if isinstance(flow_instance, OptionsFlow):
                    # Options flow - show presets configuration
                    return await flow_instance.async_step_presets(None)
                else:
                    # Config flow - proceed to final presets step
                    return await self.async_step_config(
                        flow_instance, None, collected_config
                    )
            else:
                # No presets enabled, skip configuration and continue flow
                return await next_step_handler()

        # Attempt to include current persisted presets selection so the options
        # form pre-checks any presets that already have configuration.
        # For reconfigure flows, collected_config already contains existing data.
        # For options flows, we need to get it from the entry.
        current_config = (
            collected_config  # Start with collected_config (works for reconfigure)
        )

        # If collected_config doesn't have presets, try getting from entry (options flow)
        if "presets" not in current_config:
            try:
                if hasattr(flow_instance, "_get_entry"):
                    entry = flow_instance._get_entry()
                    current_config = (
                        entry.data if entry is not None else collected_config
                    )
            except Exception:
                current_config = collected_config

        # Determine defaults: if current config contains presets (new format)
        # use those; otherwise if presets exist in data map keys, mark them.
        defaults = []
        if current_config and isinstance(current_config.get("presets"), list):
            defaults = current_config.get("presets")

        return flow_instance.async_show_form(
            step_id="preset_selection",
            data_schema=get_preset_selection_schema(defaults=defaults),
        )

    async def async_step_config(
        self, flow_instance, user_input: dict[str, Any] | None, collected_config: dict
    ) -> FlowResult:
        """Handle presets configuration."""
        if user_input is not None:
            return await self._process_preset_config_input(
                flow_instance, user_input, collected_config
            )

        # Show preset configuration form
        schema_context = build_schema_context_from_flow(flow_instance, collected_config)
        # Transform new format presets to old format for form display
        schema_context = self._flatten_presets_for_form(schema_context)
        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(schema_context),
        )

    async def _process_preset_config_input(
        self, flow_instance, user_input: dict, collected_config: dict
    ) -> FlowResult:
        """Process and validate preset configuration input."""
        # Validate all preset temperature fields
        errors = self._validate_preset_temperature_fields(user_input)

        # If validation errors exist, show form again with errors
        if errors:
            return self._show_preset_form_with_errors(flow_instance, collected_config)

        # Transform old format preset fields to new format before saving
        user_input = self._transform_preset_fields_to_new_format(user_input)

        # Update configuration with validated input
        collected_config.update(user_input)

        # Finish flow based on flow type (config or options)
        return await self._finish_preset_config_flow(flow_instance, collected_config)

    def _flatten_presets_for_form(self, config: dict) -> dict:
        """Flatten new format presets to old format for form display.

        New format: {"home": {"temperature": 10, "min_floor_temp": 8}}
        Old format: {"home_temp": 10, "home_min_floor_temp": 8}

        This allows existing form fields to display saved preset values correctly.
        """
        from homeassistant.components.climate.const import (
            ATTR_HUMIDITY,
            ATTR_TARGET_TEMP_HIGH,
            ATTR_TARGET_TEMP_LOW,
        )
        from homeassistant.const import ATTR_TEMPERATURE

        from ..const import CONF_MAX_FLOOR_TEMP, CONF_MIN_FLOOR_TEMP, CONF_PRESETS

        flattened = dict(config)  # Start with a copy

        # Map of attribute names to their field suffixes
        attr_to_suffix = {
            ATTR_TEMPERATURE: "_temp",
            ATTR_TARGET_TEMP_LOW: "_temp_low",
            ATTR_TARGET_TEMP_HIGH: "_temp_high",
            CONF_MIN_FLOOR_TEMP: "_min_floor_temp",
            CONF_MAX_FLOOR_TEMP: "_max_floor_temp",
            ATTR_HUMIDITY: "_humidity",
        }

        # Check each possible preset key
        for preset_display_name, preset_normalized_name in CONF_PRESETS.items():
            # Check if this preset exists in the new format
            if preset_normalized_name in config and isinstance(
                config[preset_normalized_name], dict
            ):
                preset_data = config[preset_normalized_name]
                # Flatten each attribute to old format field names
                for attr_name, suffix in attr_to_suffix.items():
                    if attr_name in preset_data:
                        # Use normalized name for field (e.g., "home_temp", "anti_freeze_temp")
                        field_name = f"{preset_normalized_name}{suffix}"
                        flattened[field_name] = preset_data[attr_name]

        return flattened

    def _transform_preset_fields_to_new_format(self, user_input: dict) -> dict:
        """Transform old format preset fields to new format.

        Old format: {"preset_temp": value, "preset_min_floor_temp": value, ...}
        New format: {"preset": {"temperature": value, "min_floor_temp": value, ...}}

        This ensures presets are stored in the new format that PresetManager expects.
        Handles all preset properties: temperature, temp ranges, floor temps, humidity.
        """
        from homeassistant.components.climate.const import (
            ATTR_HUMIDITY,
            ATTR_TARGET_TEMP_HIGH,
            ATTR_TARGET_TEMP_LOW,
        )
        from homeassistant.const import ATTR_TEMPERATURE

        from ..const import CONF_MAX_FLOOR_TEMP, CONF_MIN_FLOOR_TEMP

        transformed = {}
        preset_data = {}

        # Map of field suffixes to their corresponding attribute names in PresetEnv
        field_mappings = {
            "_temp": ATTR_TEMPERATURE,
            "_temp_low": ATTR_TARGET_TEMP_LOW,
            "_temp_high": ATTR_TARGET_TEMP_HIGH,
            "_min_floor_temp": CONF_MIN_FLOOR_TEMP,
            "_max_floor_temp": CONF_MAX_FLOOR_TEMP,
            "_humidity": ATTR_HUMIDITY,
        }

        for key, value in user_input.items():
            # Check if this key matches any preset field pattern
            matched = False
            for suffix, attr_name in field_mappings.items():
                if key.endswith(suffix):
                    # Extract preset key by removing the suffix
                    preset_key = key[: -len(suffix)]
                    if preset_key not in preset_data:
                        preset_data[preset_key] = {}
                    preset_data[preset_key][attr_name] = value
                    matched = True
                    break

            if not matched:
                # Not a preset field, keep as-is
                transformed[key] = value

        # Add transformed preset data to config
        for preset_key, preset_config in preset_data.items():
            # Store using the preset key (e.g., "home", "anti_freeze")
            transformed[preset_key] = preset_config

        return transformed

    def _validate_preset_temperature_fields(self, user_input: dict) -> dict:
        """Validate preset temperature fields (supports templates and numbers).

        Returns dictionary of errors if validation fails, empty dict otherwise.
        """
        import voluptuous as vol

        from ..schemas import validate_template_or_number

        errors = {}
        for key, value in user_input.items():
            # Check if this is a preset temperature field
            if key.endswith(("_temp", "_temp_low", "_temp_high")):
                try:
                    # Validate the value (handles None, empty strings, numbers, templates)
                    validated_value = validate_template_or_number(value)
                    if validated_value is None:
                        # Remove empty/None values from config
                        user_input.pop(key, None)
                    else:
                        user_input[key] = validated_value
                except vol.Invalid as e:
                    errors[key] = str(e)

        return errors

    def _show_preset_form_with_errors(
        self, flow_instance, collected_config: dict
    ) -> FlowResult:
        """Show preset configuration form with validation errors."""
        schema_context = build_schema_context_from_flow(flow_instance, collected_config)
        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(schema_context),
            errors={"base": "invalid_template"},
        )

    async def _finish_preset_config_flow(
        self, flow_instance, collected_config: dict
    ) -> FlowResult:
        """Finish preset configuration based on flow type."""
        # For config flow, this is the final step
        if not isinstance(flow_instance, OptionsFlow):
            # Call _async_finish_flow to properly handle both config and reconfigure flows
            return await flow_instance._async_finish_flow()
        else:
            # For options flow, continue (this becomes async_update_entry call)
            return flow_instance.async_create_entry(title="", data=collected_config)

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle presets options (for options flow)."""
        if user_input is not None:
            # Transform old format preset fields to new format before saving
            user_input = self._transform_preset_fields_to_new_format(user_input)
            collected_config.update(user_input)
            return await next_step_handler()
        # Attempt to include current persisted config in the schema context
        current_config = None
        try:
            # Options flows may provide a _get_entry method returning the config entry
            if hasattr(flow_instance, "_get_entry"):
                entry = flow_instance._get_entry()
                current_config = entry.data if entry is not None else None
        except Exception:
            current_config = None

        schema_context = build_schema_context_from_flow(
            flow_instance, collected_config, current_config
        )

        # For options flow, attempt to derive a defaults mapping of selected
        # preset keys so the selection UI shows which presets are already
        # configured.
        defaults = []
        if current_config:
            # If presets stored as list under 'presets' use that
            presets_list = current_config.get("presets")
            if isinstance(presets_list, list):
                defaults = presets_list
            else:
                # Fallback: detect boolean keys for older format
                for preset_key in CONF_PRESETS:
                    if current_config.get(preset_key) or current_config.get(
                        CONF_PRESETS.get(preset_key)
                    ):
                        defaults.append(preset_key)

        # Supply defaults into the presets selection schema via schema_context
        schema_context["presets_defaults"] = defaults

        # Transform new format presets to old format for form display
        schema_context = self._flatten_presets_for_form(schema_context)

        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(schema_context),
        )
