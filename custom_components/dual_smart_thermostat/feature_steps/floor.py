"""Floor heating configuration steps shared between config and options flows."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from ..const import (
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from ..schemas import get_base_schema, get_floor_heating_schema, get_grouped_schema


class FloorSteps:
    """Handle floor heating configuration for both config and options flows."""

    def __init__(self) -> None:
        return None

    async def async_step_heating(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle the initial floor-heating 'basic' step used by config flow.

        This now performs the same basic validation that used to live inline
        in the config flow. When valid, it advances to the detailed
        floor configuration step; when invalid it re-renders the same form
        with errors.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Reuse the flow's basic validation helper (the flow instance is
            # passed in so we can call its helpers from here).
            if not await flow_instance._validate_basic_config(user_input):
                heater = user_input.get(CONF_HEATER)
                sensor = user_input.get(CONF_SENSOR)

                if heater and sensor and heater == sensor:
                    errors["base"] = "same_heater_sensor"

                # Render the same grouped schema used by the flow with errors
                base = get_base_schema()
                grouped = get_grouped_schema(
                    SYSTEM_TYPE_SIMPLE_HEATER, show_heater=True
                )
                schema = vol.Schema({**base.schema, **grouped.schema})

                return flow_instance.async_show_form(
                    step_id="floor_heating", data_schema=schema, errors=errors
                )

            # Valid submission: save and show detailed floor config
            collected_config.update(user_input)
            return await self.async_step_config(
                flow_instance, None, collected_config, next_step_handler
            )

        # No submission: show the initial floor-heating grouped form
        base = get_base_schema()
        grouped = get_grouped_schema(SYSTEM_TYPE_SIMPLE_HEATER, show_heater=True)
        schema = vol.Schema({**base.schema, **grouped.schema})

        return flow_instance.async_show_form(
            step_id="floor_heating", data_schema=schema
        )

    async def async_step_config(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
    ) -> FlowResult:
        """Handle the detailed floor configuration step used by config flow."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        return flow_instance.async_show_form(
            step_id="floor_config",
            data_schema=get_floor_heating_schema(hass=flow_instance.hass),
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        current_config: dict,
    ) -> FlowResult:
        """Handle the floor heating options step used by options flow."""
        if user_input is not None:
            collected_config.update(user_input)
            return await next_step_handler()

        # Use the real schema factory for consistent selectors and include
        # current persisted values so the options form shows defaults.
        defaults = {}

        # current_config parameter is passed from the options flow call
        entry_data = current_config or {}

        # Prefer collected overrides, otherwise fallback to persisted entry data
        if collected_config.get(CONF_FLOOR_SENSOR):
            defaults[CONF_FLOOR_SENSOR] = collected_config.get(CONF_FLOOR_SENSOR)
        elif entry_data and entry_data.get(CONF_FLOOR_SENSOR):
            defaults[CONF_FLOOR_SENSOR] = entry_data.get(CONF_FLOOR_SENSOR)

        # Numeric limits
        if collected_config.get(CONF_MAX_FLOOR_TEMP) is not None:
            defaults[CONF_MAX_FLOOR_TEMP] = collected_config.get(CONF_MAX_FLOOR_TEMP)
        elif entry_data and entry_data.get(CONF_MAX_FLOOR_TEMP) is not None:
            defaults[CONF_MAX_FLOOR_TEMP] = entry_data.get(CONF_MAX_FLOOR_TEMP)

        if collected_config.get(CONF_MIN_FLOOR_TEMP) is not None:
            defaults[CONF_MIN_FLOOR_TEMP] = collected_config.get(CONF_MIN_FLOOR_TEMP)
        elif entry_data and entry_data.get(CONF_MIN_FLOOR_TEMP) is not None:
            defaults[CONF_MIN_FLOOR_TEMP] = entry_data.get(CONF_MIN_FLOOR_TEMP)

        return flow_instance.async_show_form(
            step_id="floor_options",
            data_schema=get_floor_heating_schema(
                hass=flow_instance.hass, defaults=defaults
            ),
        )
