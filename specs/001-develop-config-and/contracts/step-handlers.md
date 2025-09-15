# Contracts: Step Handlers

This document lists the expected contracts for config/options step handlers used by the integration.

- Each step handler should expose an async API compatible with Home Assistant config flow: `async_step_<name>(user_input)` returning a `FlowResult` dict.
- Step handlers should accept a `flow_instance` and `collected_config` when invoked by a shared flow runner.
- Step handlers must only manipulate `collected_config` and not persist until the final step.
- Step handlers must provide their schema via a `get_<name>_schema(collected_config)` function so the UI is consistent across config/options flows.

The repository uses a helper-style contract for feature step handlers. The following describes the concrete expectations based on the current implementation:

1. Step handler class shape
	- Each feature has a handler class in `custom_components/dual_smart_thermostat/feature_steps/` (e.g., `HumiditySteps`, `FanSteps`, `OpeningsSteps`, `PresetsSteps`).
	- Each class implements methods with these signatures (used by both config and options flows):
	  - `async_step_toggle(self, flow_instance, user_input, collected_config, next_step_handler) -> FlowResult`
	  - `async_step_config(self, flow_instance, user_input, collected_config, next_step_handler) -> FlowResult`
	  - `async_step_options(self, flow_instance, user_input, collected_config, next_step_handler, current_config) -> FlowResult` (options-only variant)

2. Schema factories
	- Schemas are centralized in `custom_components/dual_smart_thermostat/schemas.py`.
	- Use these exact factory functions when building UI forms:
	  - `get_core_schema(system_type, defaults=None, include_name=True)`
	  - `get_features_schema(system_type, defaults=None)`
	  - Per-feature factories: `get_humidity_schema()`, `get_humidity_toggle_schema()`, `get_fan_schema()`, `get_fan_toggle_schema()`, `get_openings_selection_schema()`, `get_openings_schema(selected_entities)`, `get_preset_selection_schema(defaults)`, `get_presets_schema(user_input)`, `get_floor_heating_schema(defaults)`
	- Prefer adding an `*_options_schema(current_config)` variant if a feature needs options-flow-specific defaults; otherwise, the options step may construct a schema_dict that uses selectors directly but the preferred pattern is to keep schema creation in `schemas.py`.

3. Mutating `collected_config`
	- Step handlers must only update the provided `collected_config` mapping. They must not call Home Assistant persistence APIs directly. Final persistence happens in the flow handler (`async_create_entry` in config flow or `async_create_entry` in options flow for options update).

4. `next_step_handler` contract
	- `next_step_handler` is a callable provided by the flow handler to continue the flow (e.g., `_determine_next_step` or `_determine_options_next_step`).
	- Step handlers must call `await next_step_handler()` (or use the helper used in `OpeningsSteps._call_next_step` to support synchronous returns from tests/mocks).

5. Utilities
	- Use shared helpers in `flow_utils.py` and `schema_utils.py` to standardize selectors and validation (e.g., `EntityValidator`, `OpeningsProcessor`, `get_entity_selector`).

6. Tests
	- Provide contract tests that import `schemas.py` factories and assert the returned schemas are valid `vol.Schema` objects and include expected keys/defaults.
