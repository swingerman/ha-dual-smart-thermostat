# Implementation Tasks: Config & Options Flow (per-system iterations)

## Phase 0 — Review and small fixes (priority)
- [ ] Review `custom_components/dual_smart_thermostat/config_flow.py` and `options_flow.py` to ensure the three main steps are implemented cleanly and call into unified feature steps.
- [ ] Verify schema factories live in `schemas.py` and are reused by both config and options flows.
- [ ] Run focused tests for `simple_heater` and `ac_only` system types and fix any failing tests.
 - [ ] Reorganize tests into clearer folders per `REORG.md` and verify all tests pass after the move. See `specs/001-develop-config-and/REORG.md` for mapping and steps.

## Phase 1 — Finish `heater_with_cooler` (in progress)
- [ ] Implement missing UI schemas for heater+cooler core settings.
- [ ] Ensure feature selection shows correct features for heater+cooler.
- [ ] Implement or verify per-feature steps for heater+cooler (fan, humidity, openings, floor heating, presets).
- [ ] Add unit/integration tests covering hot path and 1-2 edge cases (ordering, selector behavior).

## Phase 2 — Implement `heat_pump` system type
- [ ] Design `core_settings` schema for heat pump (modes, heat/cool behavior)
- [ ] Add config & options flow branch for heat pump
- [ ] Verify feature selection applicability for heat pump and per-feature steps
- [ ] Add tests similar to other system types

## Phase 3 — Feature modules verification & tests
- [ ] For each feature (fan, humidity, openings, floor heating, presets):
  - [ ] Ensure the feature step is isolated in `feature_steps/` and exposes `get_<feature>_schema`.
  - [ ] Add unit tests for schema validation.
  - [ ] Add integration tests that simulate config and options flows for that feature.

## Phase 4 — UX polish and translations
- [ ] Verify English translations are present for all new steps and strings.
- [ ] Add/or update help text for non-blocking ordering guidance.

## Phase 5 — Final QA & PR
- [ ] Run full test suite: `pytest -q`
- [ ] Prepare PR with description and link to spec
- [ ] Address reviewer feedback
