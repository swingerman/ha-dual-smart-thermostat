"""Fan configuration steps."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.data_entry_flow import FlowResult

from ..const import CONF_FAN, CONF_FAN_AIR_OUTSIDE, CONF_FAN_MODE, CONF_FAN_ON_WITH_AC
from ..schemas import get_fan_schema, get_fan_toggle_schema

_LOGGER = logging.getLogger(__name__)


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
            _LOGGER.debug(
                "Fan config - user_input received: %s",
                {k: v for k, v in user_input.items() if k.startswith("fan")},
            )
            collected_config.update(user_input)
            _LOGGER.debug(
                "Fan config - collected_config after update: fan_mode=%s, fan_on_with_ac=%s",
                collected_config.get(CONF_FAN_MODE),
                collected_config.get(CONF_FAN_ON_WITH_AC),
            )
            return await next_step_handler()

        # Use the shared context in case schema factories need hass/current values
        _LOGGER.debug("Fan config - Showing form with no defaults (new config)")
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
            _LOGGER.debug(
                "Fan options - user_input received: %s",
                {k: v for k, v in user_input.items() if k.startswith("fan")},
            )
            _LOGGER.debug(
                "Fan options - collected_config before update: fan_mode=%s, fan_on_with_ac=%s",
                collected_config.get(CONF_FAN_MODE),
                collected_config.get(CONF_FAN_ON_WITH_AC),
            )
            collected_config.update(user_input)
            _LOGGER.debug(
                "Fan options - collected_config after update: fan_mode=%s, fan_on_with_ac=%s",
                collected_config.get(CONF_FAN_MODE),
                collected_config.get(CONF_FAN_ON_WITH_AC),
            )
            return await next_step_handler()

        # Use the unified schema with current config as defaults
        _LOGGER.debug(
            "Fan options - Showing form with current_config defaults: fan=%s, fan_mode=%s, fan_on_with_ac=%s, fan_air_outside=%s",
            current_config.get(CONF_FAN),
            current_config.get(CONF_FAN_MODE),
            current_config.get(CONF_FAN_ON_WITH_AC),
            current_config.get(CONF_FAN_AIR_OUTSIDE),
        )
        return flow_instance.async_show_form(
            step_id="fan_options",
            data_schema=get_fan_schema(defaults=current_config),
        )
