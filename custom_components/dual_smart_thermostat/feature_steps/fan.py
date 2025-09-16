"""Fan configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ..const import CONF_FAN, CONF_FAN_AIR_OUTSIDE, CONF_FAN_MODE, CONF_FAN_ON_WITH_AC
from ..schemas import get_fan_schema, get_fan_toggle_schema


class FanSteps:
    """Handle fan configuration steps for both config and options flows."""

    def __init__(self):
        """Initialize fan steps handler."""
        pass

    async def async_step_toggle(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle fan toggle configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        return flow_instance.async_show_form(
            step_id="fan_toggle",
            data_schema=get_fan_toggle_schema(),
        )

    async def async_step_config(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle fan configuration."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        # Use the shared context in case schema factories need hass/current values
        return flow_instance.async_show_form(
            step_id="fan",
            data_schema=get_fan_schema(),
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        current_config: dict,
    ) -> FlowResult:
        """Handle fan options (for options flow)."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        schema_dict = {}

        # Always show fan entity selector
        schema_dict[vol.Optional(CONF_FAN, default=current_config.get(CONF_FAN))] = (
            selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))
        )

        # Always show fan configuration options
        schema_dict.update(
            {
                vol.Optional(
                    CONF_FAN_MODE, default=current_config.get(CONF_FAN_MODE, False)
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_FAN_ON_WITH_AC,
                    default=current_config.get(CONF_FAN_ON_WITH_AC, False),
                ): selector.BooleanSelector(),
                vol.Optional(
                    CONF_FAN_AIR_OUTSIDE,
                    default=current_config.get(CONF_FAN_AIR_OUTSIDE, False),
                ): selector.BooleanSelector(),
            }
        )

        return flow_instance.async_show_form(
            step_id="fan_options",
            data_schema=vol.Schema(schema_dict),
        )
