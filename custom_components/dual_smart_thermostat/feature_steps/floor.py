"""Floor heating configuration steps shared between config and options flows."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult
import voluptuous as vol

from ..config_validation import comfort_floor_error
from ..const import (
    CONF_COMFORT_FLOOR_TEMP,
    CONF_FLOOR_SENSOR,
    FLOOR_SETTING_KEYS,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from ..schemas import get_base_schema, get_floor_heating_schema, get_grouped_schema


def _submitted(user_input: dict[str, Any]) -> dict[str, Any]:
    # An emptied comfort_floor_temp is absent from user_input; store None so a
    # stale persisted value can't survive the entry merge.
    return {CONF_COMFORT_FLOOR_TEMP: None, **user_input}


def _collect(collected_config: dict, user_input: dict[str, Any]) -> None:
    collected_config.update(_submitted(user_input))


def _floor_errors(
    collected_config: dict, user_input: dict[str, Any] | None
) -> dict[str, str]:
    # Same rule YAML validation uses (config_validation.py).
    if user_input is None:
        return {}
    candidate = {**collected_config, **_submitted(user_input)}
    code = comfort_floor_error(candidate)
    return {CONF_COMFORT_FLOOR_TEMP: code} if code else {}


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
                errors = flow_instance._entity_errors(user_input)

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
            flow_instance._collect_entity_input(user_input)
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
        errors = _floor_errors(collected_config, user_input)
        if user_input is not None and not errors:
            _collect(collected_config, user_input)
            return await next_step_handler()

        return flow_instance.async_show_form(
            step_id="floor_config",
            data_schema=get_floor_heating_schema(
                hass=flow_instance.hass, defaults=user_input
            ),
            errors=errors,
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
        errors = _floor_errors(collected_config, user_input)
        if user_input is not None and not errors:
            _collect(collected_config, user_input)
            return await next_step_handler()

        # Use the real schema factory for consistent selectors and include
        # current persisted values so the options form shows defaults.
        defaults = {}

        # current_config parameter is passed from the options flow call
        entry_data = current_config or {}

        # Prefer collected overrides, otherwise fall back to persisted entry data
        for key in (CONF_FLOOR_SENSOR, *FLOOR_SETTING_KEYS):
            if collected_config.get(key) is not None:
                defaults[key] = collected_config.get(key)
            elif entry_data.get(key) is not None:
                defaults[key] = entry_data.get(key)

        return flow_instance.async_show_form(
            step_id="floor_options",
            data_schema=get_floor_heating_schema(
                hass=flow_instance.hass, defaults={**defaults, **(user_input or {})}
            ),
            errors=errors,
        )
