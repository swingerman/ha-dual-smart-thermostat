"""Climate-backed device control steps."""

from __future__ import annotations

from typing import Any

from homeassistant.data_entry_flow import FlowResult

from ..climate_roles import setpoint_shared_heat_cool, setpoint_unsupported
from ..schemas import get_climate_control_schema


class ClimateControlSteps:
    """control_style and per-role offsets, shared by the config and options flows."""

    async def _async_step(
        self,
        step_id: str,
        flow_instance,
        user_input: dict[str, Any] | None,
        collected_config: dict,
        next_step_handler,
        defaults: dict,
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            # The same rules YAML validation uses (climate_roles.py).
            candidate = {**collected_config, **user_input}
            if setpoint_unsupported(candidate):
                errors["base"] = "setpoint_heat_pump_unsupported"
            elif setpoint_shared_heat_cool(candidate):
                errors["base"] = "setpoint_heat_cool_shared_climate"
            else:
                collected_config.update(user_input)
                return await next_step_handler()
        return flow_instance.async_show_form(
            step_id=step_id,
            data_schema=get_climate_control_schema({**defaults, **(user_input or {})}),
            errors=errors,
        )

    async def async_step_config(
        self, flow_instance, user_input, collected_config, next_step_handler
    ) -> FlowResult:
        """Handle the step in the config and reconfigure flows."""
        return await self._async_step(
            "climate_control",
            flow_instance,
            user_input,
            collected_config,
            next_step_handler,
            collected_config,
        )

    async def async_step_options(
        self,
        flow_instance,
        user_input,
        collected_config,
        next_step_handler,
        current_config,
    ) -> FlowResult:
        """Handle the step in the options flow."""
        return await self._async_step(
            "climate_control_options",
            flow_instance,
            user_input,
            collected_config,
            next_step_handler,
            current_config,
        )
