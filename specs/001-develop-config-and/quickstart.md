# Quickstart: Implementing Config & Options Flow (iteration per system type)

1. Checkout the feature branch:

```bash
git checkout 001-develop-config-and
```

2. Work iteratively per system type (one iteration = implement one system type and its tests):
   - `simple_heater` — already implemented (verify tests and translations)
   - `ac_only` — already implemented (verify tests and translations)
   - `heater_with_cooler` — in progress (complete implementation and tests)
   - `heat_pump` — not implemented (implement last)

3. For each system type:
   - Add/verify schema in `custom_components/dual_smart_thermostat/schemas.py`
   - Ensure `config_flow.py` has a branch path for this system type that calls the unified `features` step
   - Implement per-feature step modules under `feature_steps/` as needed
   - Add tests under `tests/config_flow/` and feature tests under `tests/features/`

Implementation quick links (open these first):

- `custom_components/dual_smart_thermostat/config_flow.py::ConfigFlowHandler` — main routing logic and `_determine_next_step`
- `custom_components/dual_smart_thermostat/options_flow.py::OptionsFlowHandler` — options merging and `_determine_options_next_step`
- `custom_components/dual_smart_thermostat/schemas.py` — all schema factories used by flows (get_core_schema, get_features_schema, per-feature schemas)
- `custom_components/dual_smart_thermostat/feature_steps/` — per-feature step helpers (HumiditySteps, FanSteps, OpeningsSteps, PresetsSteps)

When iterating on a system type, run the focused tests referenced below and inspect the listed files to understand current behavior before editing.

4. Run the focused tests for changed files:

```bash
pytest tests/config_flow/test_step_ordering.py -q
pytest tests/features/test_ac_features_ux.py -q
```

5. When all system types are implemented and tests pass, open a PR from `001-develop-config-and` to `master`.
