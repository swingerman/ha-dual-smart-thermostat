"""Presets configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_NAME
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
        current_config = None
        try:
            if hasattr(flow_instance, "_get_entry"):
                entry = flow_instance._get_entry()
                current_config = entry.data if entry is not None else None
        except Exception:
            current_config = None

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
            # Validate template or number values for all preset temperature fields
            import voluptuous as vol

            from ..schemas import validate_template_or_number

            errors = {}
            for key, value in user_input.items():
                # Check if this is a preset temperature field
                if (
                    key.endswith(("_temp", "_temp_low", "_temp_high"))
                    and value is not None
                ):
                    try:
                        # Validate the value
                        validated_value = validate_template_or_number(value)
                        user_input[key] = validated_value
                    except vol.Invalid as e:
                        errors[key] = str(e)

            # If there are validation errors, show the form again with errors
            if errors:
                schema_context = build_schema_context_from_flow(
                    flow_instance, collected_config
                )
                return flow_instance.async_show_form(
                    step_id="presets",
                    data_schema=get_presets_schema(schema_context),
                    errors={"base": "invalid_template"},
                )

            collected_config.update(user_input)

            # For config flow, this is the final step
            if not isinstance(flow_instance, OptionsFlow):
                return flow_instance.async_create_entry(
                    title=collected_config[CONF_NAME],
                    data=collected_config,
                )
            else:
                # For options flow, continue (this becomes async_update_entry call)
                return flow_instance.async_create_entry(title="", data=collected_config)

        schema_context = build_schema_context_from_flow(flow_instance, collected_config)
        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(schema_context),
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle presets options (for options flow)."""
        if user_input is not None:
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

        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(schema_context),
        )
