# Tasks: Separate Temperature Tolerances for Heating and Cooling Modes

**Input**: Design documents from `/specs/002-separate-tolerances/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tolerance_selection_api.md, quickstart.md

**Tests**: Required per project constitution (Test-Driven Development is NON-NEGOTIABLE)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Source code**: `custom_components/dual_smart_thermostat/`
- **Tests**: `tests/`
- **Tools**: `tools/`
- **Documentation**: `docs/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

**Status**: ✅ Project already initialized - No setup tasks required

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T001 [P] Add CONF_HEAT_TOLERANCE constant to custom_components/dual_smart_thermostat/const.py
- [ ] T002 [P] Add CONF_COOL_TOLERANCE constant to custom_components/dual_smart_thermostat/const.py
- [ ] T003 Add heat_tolerance and cool_tolerance fields to ADVANCED_SCHEMA in custom_components/dual_smart_thermostat/schemas.py with voluptuous validation (range 0.1-5.0, optional)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 & 2 - Core Tolerance Logic with Backward Compatibility (Priority: P1) 🎯 MVP

**Goal**: Implement separate heat_tolerance and cool_tolerance parameters with mode-aware selection logic while maintaining 100% backward compatibility with existing cold_tolerance/hot_tolerance configurations

**Independent Test**: Configure heat_tolerance=0.3 and cool_tolerance=2.0, switch between HEAT and COOL modes, verify thermostat uses correct tolerance (±0.3°C in heating, ±2.0°C in cooling). Test legacy config without mode-specific tolerances works identically to previous version.

**Note**: US1 and US2 are implemented together since backward compatibility is built into the core tolerance selection algorithm.

### Tests for User Story 1 & 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T004 [P] [US1][US2] Unit test for _get_active_tolerance_for_mode() with HEAT mode using heat_tolerance in tests/managers/test_environment_manager.py
- [ ] T005 [P] [US1][US2] Unit test for _get_active_tolerance_for_mode() with COOL mode using cool_tolerance in tests/managers/test_environment_manager.py
- [ ] T006 [P] [US1][US2] Unit test for _get_active_tolerance_for_mode() with HEAT_COOL mode switching between heat/cool tolerances in tests/managers/test_environment_manager.py
- [ ] T007 [P] [US1][US2] Unit test for _get_active_tolerance_for_mode() with FAN_ONLY mode using cool_tolerance in tests/managers/test_environment_manager.py
- [ ] T008 [P] [US1][US2] Unit test for legacy fallback when heat_tolerance is None in tests/managers/test_environment_manager.py
- [ ] T009 [P] [US1][US2] Unit test for legacy fallback when cool_tolerance is None in tests/managers/test_environment_manager.py
- [ ] T010 [P] [US1][US2] Unit test for legacy fallback when both mode-specific tolerances are None in tests/managers/test_environment_manager.py
- [ ] T011 [P] [US1][US2] Unit test for set_hvac_mode() stores mode correctly in tests/managers/test_environment_manager.py
- [ ] T012 [P] [US1][US2] Unit test for is_too_cold() uses heat_tolerance in HEAT mode in tests/managers/test_environment_manager.py
- [ ] T013 [P] [US1][US2] Unit test for is_too_hot() uses cool_tolerance in COOL mode in tests/managers/test_environment_manager.py
- [ ] T014 [P] [US1][US2] Unit test for tolerance selection with None hvac_mode falls back to legacy in tests/managers/test_environment_manager.py

### Implementation for User Story 1 & 2

- [ ] T015 [P] [US1][US2] Add _hvac_mode, _heat_tolerance, _cool_tolerance attributes to EnvironmentManager.__init__() in custom_components/dual_smart_thermostat/managers/environment_manager.py
- [ ] T016 [US1][US2] Implement set_hvac_mode(hvac_mode) method in custom_components/dual_smart_thermostat/managers/environment_manager.py (depends on T015)
- [ ] T017 [US1][US2] Implement _get_active_tolerance_for_mode() method with priority-based selection algorithm in custom_components/dual_smart_thermostat/managers/environment_manager.py (depends on T015, T016)
- [ ] T018 [US1][US2] Modify is_too_cold() to use _get_active_tolerance_for_mode() for cold tolerance in custom_components/dual_smart_thermostat/managers/environment_manager.py (depends on T017)
- [ ] T019 [US1][US2] Modify is_too_hot() to use _get_active_tolerance_for_mode() for hot tolerance in custom_components/dual_smart_thermostat/managers/environment_manager.py (depends on T017)
- [ ] T020 [US1][US2] Add call to environment.set_hvac_mode() in async_set_hvac_mode() in custom_components/dual_smart_thermostat/climate.py (depends on T016)
- [ ] T021 [US1][US2] Add call to environment.set_hvac_mode() during state restoration in custom_components/dual_smart_thermostat/climate.py (depends on T016)

### Verification for User Story 1 & 2

- [ ] T022 [US1][US2] Run unit tests to verify all tolerance selection tests pass: pytest tests/managers/test_environment_manager.py -v (depends on T004-T021)
- [ ] T023 [US1][US2] Verify code passes linting: isort ., black ., flake8 ., codespell (depends on T015-T021)

**Checkpoint**: At this point, core tolerance logic should work correctly with both mode-specific and legacy configurations

---

## Phase 4: User Story 3 - Configure Tolerances Through UI (Priority: P2)

**Goal**: Enable users to configure heat_tolerance and cool_tolerance through Home Assistant UI with proper validation, pre-filling of current values, and clear descriptions explaining override behavior

**Independent Test**: Navigate to thermostat options flow → Advanced Settings, enter heat_tolerance=0.3 and cool_tolerance=2.0, save configuration, restart Home Assistant, verify values persist and are applied to runtime behavior

### Tests for User Story 3

- [ ] T024 [P] [US3] Options flow test for advanced settings includes heat_tolerance field in tests/config_flow/test_options_flow.py
- [ ] T025 [P] [US3] Options flow test for advanced settings includes cool_tolerance field in tests/config_flow/test_options_flow.py
- [ ] T026 [P] [US3] Options flow test for tolerance value validation (0.1-5.0 range) in tests/config_flow/test_options_flow.py
- [ ] T027 [P] [US3] Options flow test for tolerance field pre-fills current values in tests/config_flow/test_options_flow.py
- [ ] T028 [P] [US3] Options flow test for optional tolerance fields can be left empty in tests/config_flow/test_options_flow.py
- [ ] T029 [P] [US3] Options flow test for invalid tolerance values show validation errors in tests/config_flow/test_options_flow.py

### Implementation for User Story 3

- [ ] T030 [US3] Add heat_tolerance NumberSelector to advanced_dict in async_step_init() in custom_components/dual_smart_thermostat/options_flow.py (depends on T001-T003)
- [ ] T031 [US3] Add cool_tolerance NumberSelector to advanced_dict in async_step_init() in custom_components/dual_smart_thermostat/options_flow.py (depends on T001-T003)
- [ ] T032 [P] [US3] Add heat_tolerance field translation to custom_components/dual_smart_thermostat/translations/en.json
- [ ] T033 [P] [US3] Add cool_tolerance field translation to custom_components/dual_smart_thermostat/translations/en.json
- [ ] T034 [P] [US3] Add heat_tolerance help text translation explaining override behavior to custom_components/dual_smart_thermostat/translations/en.json
- [ ] T035 [P] [US3] Add cool_tolerance help text translation explaining override behavior to custom_components/dual_smart_thermostat/translations/en.json

### Verification for User Story 3

- [ ] T036 [US3] Run options flow tests to verify UI integration: pytest tests/config_flow/test_options_flow.py -k tolerance -v (depends on T024-T035)
- [ ] T037 [US3] Verify code passes linting: isort ., black ., flake8 ., codespell (depends on T030-T035)

**Checkpoint**: At this point, users can configure tolerances through UI and values persist correctly

---

## Phase 5: User Story 4 - Partial Override Support (Priority: P3)

**Goal**: Support partial tolerance override where users configure only heat_tolerance OR only cool_tolerance while keeping legacy behavior for the unconfigured mode

**Independent Test**: Configure cold_tolerance=0.5, hot_tolerance=0.5 (legacy), cool_tolerance=1.5 (override), test HEAT mode uses legacy (±0.5°C) and COOL mode uses override (±1.5°C)

**Note**: Core logic for partial override already implemented in Phase 3. This phase focuses on edge case testing.

### Tests for User Story 4

- [ ] T038 [P] [US4] Integration test for partial override (only heat_tolerance set) in tests/config_flow/test_simple_heater_features_integration.py
- [ ] T039 [P] [US4] Integration test for partial override (only cool_tolerance set) in tests/config_flow/test_ac_only_features_integration.py
- [ ] T040 [P] [US4] Integration test for partial override with heat_pump system in tests/config_flow/test_heat_pump_features_integration.py
- [ ] T041 [P] [US4] Integration test for partial override with heater_cooler system in tests/config_flow/test_heater_cooler_features_integration.py

### Verification for User Story 4

- [ ] T042 [US4] Run integration tests to verify partial override: pytest tests/config_flow/ -k "partial" -v (depends on T038-T041)

**Checkpoint**: All user stories (US1-US4) should now be independently functional

---

## Phase 6: E2E Persistence & System Type Coverage

**Purpose**: Verify tolerance configuration persists correctly across all system types and restart cycles

- [ ] T043 [P] E2E persistence test for simple_heater with mode-specific tolerances in tests/config_flow/test_e2e_simple_heater_persistence.py
- [ ] T044 [P] E2E persistence test for ac_only with mode-specific tolerances in tests/config_flow/test_e2e_ac_only_persistence.py
- [ ] T045 [P] E2E persistence test for heat_pump with mode-specific tolerances in tests/config_flow/test_e2e_heat_pump_persistence.py
- [ ] T046 [P] E2E persistence test for heater_cooler with mode-specific tolerances in tests/config_flow/test_e2e_heater_cooler_persistence.py
- [ ] T047 [P] E2E persistence test for legacy config (no mode-specific tolerances) in tests/config_flow/test_e2e_simple_heater_persistence.py
- [ ] T048 [P] E2E persistence test for mixed config (legacy + partial override) in tests/config_flow/test_e2e_heat_pump_persistence.py

### Verification

- [ ] T049 Run all E2E persistence tests: pytest tests/config_flow/ -k "e2e" -v (depends on T043-T048)

**Checkpoint**: Tolerance configuration persists correctly across all system types

---

## Phase 7: Functional Testing Across HVAC Modes

**Purpose**: Verify tolerance behavior in runtime operation for different HVAC modes

- [ ] T050 [P] Functional test for heat_tolerance in HEAT mode activates at correct threshold in tests/test_heater_mode.py
- [ ] T051 [P] Functional test for heat_tolerance in HEAT mode deactivates at correct threshold in tests/test_heater_mode.py
- [ ] T052 [P] Functional test for cool_tolerance in COOL mode activates at correct threshold in tests/test_cooler_mode.py
- [ ] T053 [P] Functional test for cool_tolerance in COOL mode deactivates at correct threshold in tests/test_cooler_mode.py
- [ ] T054 [P] Functional test for HEAT_COOL mode switches between heat/cool tolerances in tests/test_heat_pump_mode.py
- [ ] T055 [P] Functional test for legacy config in HEAT mode behaves identically to old version in tests/test_heater_mode.py
- [ ] T056 [P] Functional test for legacy config in COOL mode behaves identically to old version in tests/test_cooler_mode.py

### Verification

- [ ] T057 Run functional tests to verify runtime behavior: pytest tests/test_heater_mode.py tests/test_cooler_mode.py tests/test_heat_pump_mode.py -k tolerance -v (depends on T050-T056)

**Checkpoint**: All HVAC modes respect appropriate tolerances in runtime operation

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, dependency tracking, validation, and final quality checks

- [ ] T058 [P] Add heat_tolerance entry to tools/focused_config_dependencies.json
- [ ] T059 [P] Add cool_tolerance entry to tools/focused_config_dependencies.json
- [ ] T060 [P] Add tolerance validation rules to tools/config_validator.py
- [ ] T061 [P] Add tolerance documentation to docs/config/CRITICAL_CONFIG_DEPENDENCIES.md with examples
- [ ] T062 Verify configuration validator passes: python tools/config_validator.py (depends on T058-T061)
- [ ] T063 [P] Run full test suite to ensure no regressions: pytest
- [ ] T064 [P] Run code quality checks: pre-commit run --all-files
- [ ] T065 [P] Generate test coverage report: pytest --cov=custom_components/dual_smart_thermostat --cov-report=html
- [ ] T066 Manual testing following quickstart.md validation procedure

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ Already complete - Project initialized
- **Foundational (Phase 2)**: No dependencies - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - Phase 3 (US1&2): Can start after Foundational - No dependencies on other stories
  - Phase 4 (US3): Can start after Foundational - Integrates with Phase 3 but independently testable
  - Phase 5 (US4): Can start after Foundational - Tests edge cases of Phase 3 logic
- **E2E Persistence (Phase 6)**: Depends on Phase 3 & Phase 4 (needs core logic + UI)
- **Functional Testing (Phase 7)**: Depends on Phase 3 (needs core logic)
- **Polish (Phase 8)**: Depends on all previous phases being complete

### User Story Dependencies

- **User Story 1&2 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1&2 but independently testable
- **User Story 4 (P3)**: Can start after Foundational (Phase 2) - Tests edge cases of US1&2 logic but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- EnvironmentManager implementation before climate.py integration
- Options flow implementation before UI tests
- Core implementation complete before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 2 (Foundational)**: T001 and T002 can run in parallel (different constants)
- **Phase 3 Tests**: T004-T014 can run in parallel (independent test cases)
- **Phase 3 Implementation**: T015 and T020-T021 can run in parallel (different files)
- **Phase 4 Tests**: T024-T029 can run in parallel (independent test cases)
- **Phase 4 Implementation**: T032-T035 can run in parallel (translation strings)
- **Phase 5 Tests**: T038-T041 can run in parallel (different system types)
- **Phase 6 Tests**: T043-T048 can run in parallel (different system types)
- **Phase 7 Tests**: T050-T056 can run in parallel (different test files)
- **Phase 8 Documentation**: T058-T061 can run in parallel (different files)

---

## Parallel Example: User Story 1&2 Tests

```bash
# Launch all unit tests for User Story 1&2 together:
Task: "Unit test for _get_active_tolerance_for_mode() with HEAT mode using heat_tolerance"
Task: "Unit test for _get_active_tolerance_for_mode() with COOL mode using cool_tolerance"
Task: "Unit test for _get_active_tolerance_for_mode() with HEAT_COOL mode switching"
Task: "Unit test for _get_active_tolerance_for_mode() with FAN_ONLY mode using cool_tolerance"
Task: "Unit test for legacy fallback when heat_tolerance is None"
Task: "Unit test for legacy fallback when cool_tolerance is None"
Task: "Unit test for legacy fallback when both mode-specific tolerances are None"
Task: "Unit test for set_hvac_mode() stores mode correctly"
Task: "Unit test for is_too_cold() uses heat_tolerance in HEAT mode"
Task: "Unit test for is_too_hot() uses cool_tolerance in COOL mode"
Task: "Unit test for tolerance selection with None hvac_mode falls back to legacy"

# All tests can be written concurrently as they test independent aspects
```

---

## Parallel Example: User Story 3 Translations

```bash
# Launch all translation tasks for User Story 3 together:
Task: "Add heat_tolerance field translation"
Task: "Add cool_tolerance field translation"
Task: "Add heat_tolerance help text translation"
Task: "Add cool_tolerance help text translation"

# All translations can be written concurrently as they're independent entries
```

---

## Implementation Strategy

### MVP First (User Stories 1&2 Only)

1. Complete Phase 2: Foundational (T001-T003)
2. Complete Phase 3: User Story 1&2 (T004-T023)
3. **STOP and VALIDATE**: Run unit tests, verify core logic works
4. Test with legacy config and mode-specific config
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Foundational (Phase 2) → Foundation ready
2. Add User Story 1&2 (Phase 3) → Test independently → Deploy/Demo (MVP!) 🎯
3. Add User Story 3 (Phase 4) → Test independently → Deploy/Demo (UI accessible)
4. Add User Story 4 (Phase 5) → Test independently → Deploy/Demo (Edge cases covered)
5. Complete E2E & Functional testing (Phase 6-7) → Full coverage validated
6. Polish & Documentation (Phase 8) → Production ready

### Parallel Team Strategy

With multiple developers:

1. Team completes Foundational (Phase 2) together
2. Once Foundational is done:
   - **Developer A**: Phase 3 (Core logic - US1&2)
   - **Developer B**: Phase 4 (UI integration - US3) - can start in parallel
   - **Developer C**: Phase 5 (Edge case tests - US4) - can start in parallel
3. Team collaborates on Phase 6-7 (E2E & Functional tests)
4. Team collaborates on Phase 8 (Polish & Documentation)

---

## Task Summary

**Total Tasks**: 66

**By Phase**:
- Phase 1 (Setup): 0 tasks (already complete)
- Phase 2 (Foundational): 3 tasks (T001-T003)
- Phase 3 (US1&2 - Core Logic): 20 tasks (T004-T023)
- Phase 4 (US3 - UI): 14 tasks (T024-T037)
- Phase 5 (US4 - Edge Cases): 5 tasks (T038-T042)
- Phase 6 (E2E Persistence): 7 tasks (T043-T049)
- Phase 7 (Functional Testing): 8 tasks (T050-T057)
- Phase 8 (Polish): 9 tasks (T058-T066)

**By User Story**:
- User Story 1&2 (P1 - Core + Backward Compatibility): 20 tasks
- User Story 3 (P2 - UI Configuration): 14 tasks
- User Story 4 (P3 - Partial Override): 5 tasks
- Cross-Cutting (E2E, Functional, Polish): 24 tasks

**Parallel Opportunities**: 47 tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phase 2 + Phase 3 = 23 tasks (T001-T023)

**Suggested First Sprint**: Complete MVP (Phases 2-3) to deliver core functionality with backward compatibility

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Follow CLAUDE.md guidelines for configuration flow integration
- All code must pass isort, black, flake8, codespell before commit
- Constitution requirements all validated and approved
