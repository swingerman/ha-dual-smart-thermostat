"""Openings configuration steps."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ..const import (
    ATTR_CLOSING_TIMEOUT,
    ATTR_OPENING_TIMEOUT,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
)
from ..flow_utils import OpeningsProcessor
from ..schemas import get_openings_selection_schema, get_openings_toggle_schema

_LOGGER = logging.getLogger(__name__)


class OpeningsSteps:
    """Handle openings configuration steps for both config and options flows."""

    def __init__(self):
        """Initialize openings steps handler."""
        pass

    async def _call_next_step(self, next_step_handler):
        """Call next_step_handler and await only if it returns an awaitable.

        Some tests and mocks return a plain dict (synchronous). Awaiting a
        non-awaitable raises TypeError, so detect awaitables and handle both
        cases.
        """
        result = next_step_handler()
        if hasattr(result, "__await__"):
            return await result
        return result

    async def async_step_toggle(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle openings toggle configuration."""
        if user_input is not None:
            # Log the user input to debug the issue
            _LOGGER.debug("async_step_toggle - user_input: %s", user_input)
            _LOGGER.debug(
                "async_step_toggle - collected_config before: %s", collected_config
            )
            collected_config.update(user_input)
            _LOGGER.debug(
                "async_step_toggle - collected_config after: %s", collected_config
            )
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
            # Log the user input to debug the issue
            _LOGGER.debug("async_step_selection - user_input: %s", user_input)
            _LOGGER.debug(
                "async_step_selection - collected_config before: %s", collected_config
            )
            collected_config.update(user_input)
            _LOGGER.debug(
                "async_step_selection - collected_config after: %s", collected_config
            )
            return await self.async_step_config(
                flow_instance, None, collected_config, next_step_handler
            )

        # log the openings
        _LOGGER.info(
            "Selected openings: %s", collected_config.get("selected_openings", [])
        )

        schema = get_openings_selection_schema(
            defaults=collected_config.get("selected_openings", [])
        )

        return flow_instance.async_show_form(
            step_id="openings_selection", data_schema=schema
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
            # Log the user input to debug the issue
            _LOGGER.debug("async_step_config - user_input: %s", user_input)
            _LOGGER.debug(
                "async_step_config - collected_config before: %s", collected_config
            )

            # Process the openings input and convert to the expected format
            selected_entities = collected_config.get("selected_openings", [])
            _LOGGER.debug(
                "async_step_config - selected_entities: %s", selected_entities
            )

            openings_list = OpeningsProcessor.process_openings_config(
                user_input, selected_entities
            )
            _LOGGER.debug(
                "async_step_config - openings_list processed: %s", openings_list
            )

            if openings_list:
                collected_config[CONF_OPENINGS] = openings_list

            # Clean openings scope configuration
            OpeningsProcessor.clean_openings_scope(collected_config)

            _LOGGER.debug(
                "async_step_config - collected_config after processing: %s",
                collected_config,
            )

            return await self._call_next_step(next_step_handler)

        selected_entities = collected_config.get("selected_openings", [])

        # If no entities selected, skip timeout configuration
        if not selected_entities:
            return await self._call_next_step(next_step_handler)

        # Build schema: include scope selector plus section-based per-entity timeout fields
        schema_dict = {}

        # Add HVAC scope options based on system configuration
        scope_options = [{"value": "all", "label": "All HVAC modes"}]

        # Cool mode - available when cooling capability exists
        has_cooling = (
            bool(collected_config.get("cooler"))
            or bool(collected_config.get("ac_mode"))
            or bool(collected_config.get("heat_pump_cooling"))
        )
        if has_cooling:
            scope_options.append({"value": "cool", "label": "Cooling only"})

        # Heat mode - available when heater is configured AND not in AC-only mode
        # (AC-only mode uses heater entity as AC unit)
        has_heating = (
            bool(collected_config.get("heater"))
            and not (
                collected_config.get("ac_mode") and not collected_config.get("cooler")
            )
        ) or bool(collected_config.get("heat_pump_cooling"))

        if has_heating:
            scope_options.append({"value": "heat", "label": "Heating only"})

        # Heat/Cool mode - available when both heating and cooling are configured
        # and heat_cool_mode is enabled
        if has_heating and has_cooling and collected_config.get("heat_cool_mode"):
            scope_options.append({"value": "heat_cool", "label": "Heat/Cool mode"})

        # Fan mode - available when fan is configured (all system types)
        if collected_config.get("fan") or collected_config.get("fan_mode"):
            scope_options.append({"value": "fan_only", "label": "Fan only"})

        # Dry mode - available when dryer is configured (all system types)
        if collected_config.get("dryer"):
            scope_options.append({"value": "dry", "label": "Dry mode"})

        # Add scope selector
        schema_dict[
            vol.Optional(
                CONF_OPENINGS_SCOPE,
                default=collected_config.get(CONF_OPENINGS_SCOPE, "all"),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=scope_options)
        )

        # Add indexed timeout fields for each entity
        # Use simple indexed naming that can have static translations
        current_openings = collected_config.get(CONF_OPENINGS, [])
        existing_timeouts = {}

        # Extract existing timeout values from current config if available
        for opening in current_openings:
            if isinstance(opening, dict):
                entity_id = opening["entity_id"]
                if entity_id in selected_entities:
                    existing_timeouts[entity_id] = {
                        "opening": opening.get(ATTR_OPENING_TIMEOUT, 0),
                        "closing": opening.get(ATTR_CLOSING_TIMEOUT, 0),
                    }

        for i, entity_id in enumerate(selected_entities):
            # Add a display label for the entity
            if "." in entity_id:
                display_name = entity_id.split(".", 1)[1].replace("_", " ").title()
            else:
                display_name = entity_id.replace("_", " ").title()

            # Add a text display field to show which entity this section is for
            label_key = f"opening_{i + 1}_label"
            schema_dict[vol.Optional(label_key, default=f"🚪 {display_name}")] = (
                selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.TEXT,
                        multiline=False,
                    )
                )
            )

            # Store entity mapping for processing later
            open_key = f"opening_{i + 1}_timeout_open"
            close_key = f"opening_{i + 1}_timeout_close"

            # Get existing values or default to 0
            default_open = existing_timeouts.get(entity_id, {}).get("opening", 0)
            default_close = existing_timeouts.get(entity_id, {}).get("closing", 0)

            schema_dict[vol.Optional(open_key, default=default_open)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )

            schema_dict[vol.Optional(close_key, default=default_close)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0, max=3600, step=1, mode=selector.NumberSelectorMode.BOX
                    )
                )
            )

        return flow_instance.async_show_form(
            step_id="openings_config",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={
                "selected_entities": "\n".join(
                    f"• {entity_id}" for entity_id in selected_entities
                )
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
        # Two-step behavior: first show selection, then show scope+timeouts
        if user_input is not None:
            # Log the user input to debug the issue
            _LOGGER.debug("async_step_options - user_input: %s", user_input)
            _LOGGER.debug(
                "async_step_options - collected_config before: %s", collected_config
            )

            # If this submission contains selected_openings, treat it as the
            # first step and show the detailed options form next.
            if user_input.get("selected_openings") and not any(
                k
                for k in user_input.keys()
                if k == CONF_OPENINGS_SCOPE
                or k.endswith("_timeout_open")
                or k.endswith("_timeout_close")
            ):
                # Store the selection and render the detailed options step
                collected_config["selected_openings"] = user_input["selected_openings"]
                _LOGGER.debug(
                    "async_step_options - stored selected_openings: %s",
                    user_input["selected_openings"],
                )
                # Delegate to the same config renderer used by config flow
                return await self.async_step_config(
                    flow_instance, None, collected_config, next_step_handler
                )

            # Otherwise, treat as the detailed options submission and process
            if user_input.get("selected_openings"):
                selected = user_input["selected_openings"]
            else:
                selected = collected_config.get("selected_openings", [])

            _LOGGER.debug("async_step_options - selected for processing: %s", selected)

            # Process openings with timeouts using shared utility
            openings_list = OpeningsProcessor.process_openings_config(
                user_input, selected
            )
            _LOGGER.debug(
                "async_step_options - openings_list processed: %s", openings_list
            )

            if openings_list:
                collected_config[CONF_OPENINGS] = openings_list

            # Store scope if provided, otherwise preserve existing
            if user_input.get(CONF_OPENINGS_SCOPE) is not None:
                collected_config[CONF_OPENINGS_SCOPE] = user_input[CONF_OPENINGS_SCOPE]

            # If no entities selected, remove configuration
            if not selected:
                collected_config.pop(CONF_OPENINGS, None)
                collected_config.pop(CONF_OPENINGS_SCOPE, None)

            _LOGGER.debug(
                "async_step_options - collected_config before final update: %s",
                collected_config,
            )
            collected_config.update(user_input)
            _LOGGER.debug(
                "async_step_options - collected_config after final update: %s",
                collected_config,
            )
            return await self._call_next_step(next_step_handler)

        # Initial display: show only the selection step with current selected entities
        current_openings = current_config.get(CONF_OPENINGS, [])
        _LOGGER.debug(
            "async_step_options - current_openings from config: %s", current_openings
        )
        selected_entities = OpeningsProcessor.extract_selected_entities_from_config(
            current_openings
        )
        _LOGGER.debug(
            "async_step_options - extracted selected_entities: %s", selected_entities
        )

        schema = get_openings_selection_schema(defaults=selected_entities)

        return flow_instance.async_show_form(
            step_id="openings_options", data_schema=schema
        )
