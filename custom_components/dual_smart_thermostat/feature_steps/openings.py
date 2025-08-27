"""Openings configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ..const import CONF_OPENINGS, CONF_OPENINGS_SCOPE
from ..flow_utils import OpeningsProcessor
from ..schemas import (
    get_openings_schema,
    get_openings_selection_schema,
    get_openings_toggle_schema,
    get_openings_translations_data,
)


class OpeningsSteps:
    """Handle openings configuration steps for both config and options flows."""

    def __init__(self):
        """Initialize openings steps handler."""
        pass

    async def async_step_toggle(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle openings toggle configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        return flow_instance.async_show_form(
            step_id="openings_toggle",
            data_schema=get_openings_toggle_schema(),
        )

    async def async_step_selection(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle openings selection configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await self.async_step_config(
                flow_instance, None, collected_config, next_step_handler
            )

        return flow_instance.async_show_form(
            step_id="openings_selection",
            data_schema=get_openings_selection_schema(collected_config),
        )

    async def async_step_config(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle openings timeout configuration."""
        if user_input is not None:
            # Process the openings input and convert to the expected format
            selected_entities = collected_config.get("selected_openings", [])
            openings_list = OpeningsProcessor.process_openings_config(
                user_input, selected_entities
            )

            if openings_list:
                collected_config[CONF_OPENINGS] = openings_list

            # Clean openings scope configuration
            OpeningsProcessor.clean_openings_scope(collected_config)

            return await next_step_handler()

        selected_entities = collected_config.get("selected_openings", [])

        # If no entities selected, skip timeout configuration
        if not selected_entities:
            return await next_step_handler()

        # Get dynamic translations for the form
        translations = get_openings_translations_data(selected_entities)

        return flow_instance.async_show_form(
            step_id="openings_config",
            data_schema=get_openings_schema(selected_entities),
            description_placeholders={
                **translations["data"],
                **translations["data_description"],
            },
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        current_config: dict,
    ) -> FlowResult:
        """Handle openings options (for options flow)."""
        if user_input is not None:
            # Process openings configuration similar to the main config flow
            if user_input.get("selected_openings"):
                # Store updated openings selection
                collected_config["selected_openings"] = user_input["selected_openings"]

                # Store HVAC scope if provided
                if user_input.get(CONF_OPENINGS_SCOPE):
                    collected_config[CONF_OPENINGS_SCOPE] = user_input[
                        CONF_OPENINGS_SCOPE
                    ]

                # Process openings with timeouts using shared utility
                openings_list = OpeningsProcessor.process_openings_config(
                    user_input, user_input["selected_openings"]
                )

                if openings_list:
                    collected_config[CONF_OPENINGS] = openings_list
            else:
                # Remove openings configuration if no entities selected
                collected_config.pop(CONF_OPENINGS, None)
                collected_config.pop(CONF_OPENINGS_SCOPE, None)

            collected_config.update(user_input)
            return await next_step_handler()

        # Get current openings configuration
        current_openings = current_config.get(CONF_OPENINGS, [])

        # Extract selected entities from current configuration using shared utility
        selected_entities = OpeningsProcessor.extract_selected_entities_from_config(
            current_openings
        )

        # Create schema with current values and timeout options
        schema_dict = {
            vol.Optional(
                "selected_openings", default=selected_entities
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "sensor", "switch", "input_boolean"],
                    multiple=True,
                )
            ),
        }

        # Add HVAC scope options
        scope_options = [{"value": "all", "label": "All HVAC modes"}]
        if current_config.get("heater"):
            scope_options.append({"value": "heat", "label": "Heating only"})

        has_cooling = (
            bool(current_config.get("cooler"))
            or bool(current_config.get("ac_mode"))
            or bool(current_config.get("heat_pump_cooling"))
        )
        if has_cooling:
            scope_options.append({"value": "cool", "label": "Cooling only"})

        if current_config.get("heater") and has_cooling:
            scope_options.append({"value": "heat_cool", "label": "Heat/Cool mode"})

        if current_config.get("fan"):
            scope_options.append({"value": "fan_only", "label": "Fan only"})

        schema_dict[
            vol.Optional(
                CONF_OPENINGS_SCOPE,
                default=current_config.get(CONF_OPENINGS_SCOPE, "all"),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=scope_options)
        )

        # Add timeout fields for all currently selected entities
        for entity_id in selected_entities:
            # Add opening timeout field
            schema_dict[vol.Optional(f"{entity_id}_timeout_open", default=0)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )
            # Add closing timeout field
            schema_dict[vol.Optional(f"{entity_id}_timeout_close", default=0)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )

        return flow_instance.async_show_form(
            step_id="openings_options",
            data_schema=vol.Schema(schema_dict),
        )
