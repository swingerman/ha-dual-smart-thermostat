"""Presets configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import OptionsFlow
from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult

from ..const import CONF_PRESETS
from ..schemas import get_preset_selection_schema, get_presets_schema


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

        return flow_instance.async_show_form(
            step_id="preset_selection",
            data_schema=get_preset_selection_schema(),
        )

    async def async_step_config(
        self, flow_instance, user_input: dict[str, Any] | None, collected_config: dict
    ) -> FlowResult:
        """Handle presets configuration."""
        if user_input is not None:
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

        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(collected_config),
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

        return flow_instance.async_show_form(
            step_id="presets",
            data_schema=get_presets_schema(collected_config),
        )
