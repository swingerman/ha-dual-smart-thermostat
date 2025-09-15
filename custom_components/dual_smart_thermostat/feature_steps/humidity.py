"""Humidity configuration steps."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
import voluptuous as vol

from ..const import (
    CONF_DRY_TOLERANCE,
    CONF_DRYER,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_HUMIDITY,
    CONF_MIN_HUMIDITY,
    CONF_MOIST_TOLERANCE,
    CONF_TARGET_HUMIDITY,
)
from ..schema_utils import get_entity_selector
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

        schema_dict = {}

        # Always show humidity sensor option
        # Use the shared entity selector helper to ensure consistent
        # domain-only selector behavior. Using the specific
        # `device_class` filter can prevent some sensors from appearing
        # in the frontend selector; the integration prefers domain-only
        # filtering for broader compatibility in options flow.
        schema_dict[
            vol.Optional(
                CONF_HUMIDITY_SENSOR,
                default=current_config.get(CONF_HUMIDITY_SENSOR),
            )
        ] = get_entity_selector(SENSOR_DOMAIN)

        # Always show dryer option
        schema_dict[
            vol.Optional(CONF_DRYER, default=current_config.get(CONF_DRYER))
        ] = selector.EntitySelector(selector.EntitySelectorConfig(domain="switch"))

        # Always show all humidity configuration fields
        # Use current_config value if present, otherwise fall back to the same
        # defaults used by the config flow schema so options forms are pre-filled
        # consistently.
        schema_dict[
            vol.Optional(
                CONF_TARGET_HUMIDITY,
                default=current_config.get(CONF_TARGET_HUMIDITY, 50),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
                min=0,
                max=100,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_MIN_HUMIDITY, default=current_config.get(CONF_MIN_HUMIDITY, 30)
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
                min=0,
                max=100,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_MAX_HUMIDITY, default=current_config.get(CONF_MAX_HUMIDITY, 99)
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement="%",
                min=0,
                max=100,
            )
        )

        # Always show tolerance settings
        for conf_key in [CONF_DRY_TOLERANCE, CONF_MOIST_TOLERANCE]:
            # Default tolerances: 3% when not set in current_config
            default_value = current_config.get(conf_key, 3)
            schema_dict[vol.Optional(conf_key, default=default_value)] = (
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        unit_of_measurement="%",
                        min=1,
                        max=20,
                    )
                )
            )

        return flow_instance.async_show_form(
            step_id="humidity_options",
            data_schema=vol.Schema(schema_dict),
        )
