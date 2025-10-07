"""Humidity configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult

from ..schemas import get_humidity_schema, get_humidity_toggle_schema


class HumiditySteps:
    """Handle humidity configuration steps for both config and options flows."""

    def __init__(self):
        """Initialize humidity steps handler."""
        pass

    async def async_step_toggle(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle humidity toggle configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        return flow_instance.async_show_form(
            step_id="humidity_toggle",
            data_schema=get_humidity_toggle_schema(),
        )

    async def async_step_config(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle humidity control configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        # Use the shared context in case schema factories need hass/current values
        return flow_instance.async_show_form(
            step_id="humidity",
            data_schema=get_humidity_schema(),
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        current_config: dict,
    ) -> FlowResult:
        """Handle humidity options (for options flow)."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        # Use the unified schema with current config as defaults
        return flow_instance.async_show_form(
            step_id="humidity_options",
            data_schema=get_humidity_schema(defaults=current_config),
        )
