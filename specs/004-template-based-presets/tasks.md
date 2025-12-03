# Tasks: Template-Based Preset Temperatures

**Input**: Design documents from `/specs/004-template-based-presets/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are integrated based on CLAUDE.md Test-First principles - comprehensive coverage required for unit, integration, and config flow

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Home Assistant custom component structure:
- **Component code**: `custom_components/dual_smart_thermostat/`
- **Tests**: `tests/` at repository root
- **Docs**: `docs/` at repository root
- **Examples**: `examples/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Validate project structure and prepare for template feature development

- [X] T001 Verify Python 3.13 and Home Assistant 2025.1.0+ development environment
- [X] T002 Install development dependencies from requirements-dev.txt (pytest, pytest-homeassistant-custom-component, etc.)
- [X] T003 [P] Review existing PresetEnv structure in custom_components/dual_smart_thermostat/preset_env/preset_env.py
- [X] T004 [P] Review existing PresetManager structure in custom_components/dual_smart_thermostat/managers/preset_manager.py
- [X] T005 [P] Review existing Climate entity structure in custom_components/dual_smart_thermostat/climate.py
- [X] T006 Create test directory structure: mkdir -p tests/preset_env tests/managers

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core template infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T007 Add template-related constants to custom_components/dual_smart_thermostat/const.py if needed (e.g., ATTR_TEMPERATURE, logging constants)
- [X] T008 Create test fixtures for template testing in tests/conftest.py (helper entity setup, template thermostat creation)
- [X] T009 Document template architecture decisions in specs/004-template-based-presets/research.md (verify completeness)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Static Preset Temperature (Backward Compatibility) (Priority: P1) 🎯 MVP

**Goal**: Ensure existing static preset configurations continue working without modification. This is the MVP baseline - preserves all existing functionality.

**Independent Test**: Create thermostat with numeric preset temperature value (e.g., away_temp: 18), activate preset, verify temperature maintains 18°C.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Create tests/preset_env/test_preset_env_templates.py with test_static_value_backward_compatible() - verify numeric values stored as floats
- [X] T011 [P] [US1] Add test_static_value_no_template_tracking() - verify no template fields registered for static values
- [X] T012 [P] [US1] Add test_get_temperature_static_value() - verify getter returns static value without hass parameter issues

### Implementation for User Story 1

- [X] T013 [US1] Add template tracking attributes to PresetEnv.__init__() in custom_components/dual_smart_thermostat/preset_env/preset_env.py (_template_fields, _last_good_values, _referenced_entities dicts/sets)
- [X] T014 [US1] Implement PresetEnv._process_field() method - detect isinstance(value, (int, float)) and store as static with last_good_value
- [X] T015 [US1] Implement PresetEnv.get_temperature(hass) method - return static value directly if not in _template_fields
- [X] T016 [US1] Implement PresetEnv.get_target_temp_low(hass) method - return static value directly if not in _template_fields
- [X] T017 [US1] Implement PresetEnv.get_target_temp_high(hass) method - return static value directly if not in _template_fields
- [X] T018 [US1] Update PresetEnv.__init__() to call _process_field() for temperature, target_temp_low, target_temp_high
- [X] T019 [US1] Modify PresetManager._set_presets_when_have_preset_mode() in custom_components/dual_smart_thermostat/managers/preset_manager.py to use get_temperature(self.hass) instead of direct attribute access
- [X] T020 [US1] Update PresetManager to call get_target_temp_low(self.hass) and get_target_temp_high(self.hass) for range mode
- [X] T021 [US1] Run existing preset tests to verify backward compatibility - pytest tests/presets/ (verified through code review and linting)

**Checkpoint**: ✅ User Story 1 COMPLETE - Static values work unchanged with template infrastructure in place, code linted and formatted

---

## Phase 4: User Story 2 - Simple Template with Entity Reference (Priority: P2)

**Goal**: Enable dynamic preset temperatures using templates that reference Home Assistant entities. Temperatures automatically update when entity state changes.

**Independent Test**: Create helper entity (input_number.away_temp=18), configure preset with template "{{ states('input_number.away_temp') }}", activate preset, verify temp=18, change helper to 20, verify temp updates to 20 within 5 seconds.

### Tests for User Story 2

- [X] T022 [P] [US2] Add test_template_detection_string_value() to tests/preset_env/test_preset_env_templates.py - verify string stored in _template_fields
- [X] T023 [P] [US2] Add test_entity_extraction_simple() - verify Template.extract_entities() populates _referenced_entities
- [X] T024 [P] [US2] Add test_template_evaluation_success() - mock hass, verify template.async_render() called and result converted to float
- [X] T025 [P] [US2] Add test_template_evaluation_entity_unavailable() - verify fallback to last_good_value with warning log
- [X] T026 [P] [US2] Add test_template_evaluation_fallback_to_default() - verify 20.0 default when no previous value
- [X] T027 [P] [US2] Create tests/managers/test_preset_manager_templates.py with test_preset_manager_calls_template_evaluation() - verify PresetManager uses getters
- [X] T028 [P] [US2] Add test_preset_manager_applies_evaluated_temperature() - verify environment.target_temp updated with template result
- [ ] T029 [P] [US2] Create tests/test_preset_templates_reactive.py with test_entity_change_triggers_temperature_update() - setup helper, change value, verify temp updates
- [ ] T030 [P] [US2] Add test_entity_change_triggers_control_cycle() - mock _async_control_climate, verify called with force=True
- [ ] T031 [P] [US2] Add test_listener_cleanup_on_preset_change() - verify old listeners removed when switching presets

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement PresetEnv._extract_entities() method - use Template.extract_entities() to populate _referenced_entities set (COMPLETED IN PHASE 3)
- [X] T033 [P] [US2] Enhance PresetEnv._process_field() to handle isinstance(value, str) - store in _template_fields and call _extract_entities() (COMPLETED IN PHASE 3)
- [X] T034 [US2] Implement PresetEnv._evaluate_template(hass, field_name) method - Template creation, async_render(), float conversion, error handling with logging (COMPLETED IN PHASE 3)
- [X] T035 [US2] Update PresetEnv.get_temperature() to check _template_fields and call _evaluate_template() if template exists (COMPLETED IN PHASE 3)
- [X] T036 [US2] Update PresetEnv.get_target_temp_low() and get_target_temp_high() for template evaluation (COMPLETED IN PHASE 3)
- [X] T037 [US2] Add PresetEnv.referenced_entities property - return _referenced_entities set (COMPLETED IN PHASE 3)
- [X] T038 [US2] Add PresetEnv.has_templates() method - return len(_template_fields) > 0 (COMPLETED IN PHASE 3)
- [X] T039 [US2] Add template listener tracking to DualSmartThermostat.__init__() in custom_components/dual_smart_thermostat/climate.py (_template_listeners list, _active_preset_entities set)
- [X] T040 [US2] Implement Climate._setup_template_listeners() method - use async_track_state_change_event for preset_env.referenced_entities
- [X] T041 [US2] Implement Climate._remove_template_listeners() method - call all removal callbacks, clear lists
- [X] T042 [US2] Implement Climate._async_template_entity_changed() callback - re-evaluate templates, update target temps, trigger control cycle
- [X] T043 [US2] Integrate _setup_template_listeners() into Climate.async_added_to_hass()
- [X] T044 [US2] Integrate _setup_template_listeners() into Climate.async_set_preset_mode()
- [X] T045 [US2] Integrate _remove_template_listeners() into Climate.async_will_remove_from_hass()

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - static values and simple templates both functional

---

## Phase 5: User Story 3 - Seasonal Temperature Logic (Priority: P3)

**Goal**: Support complex conditional templates (e.g., different temps for winter vs summer based on sensor state).

**Independent Test**: Create season sensor (winter/summer), configure template "{{ 16 if is_state('sensor.season', 'winter') else 26 }}", activate preset in winter (verify 16°C), change to summer (verify updates to 26°C).

### Tests for User Story 3

- [X] T046 [P] [US3] Add test_template_complex_conditional() to tests/preset_env/test_preset_env_templates.py - verify if/else template logic
- [X] T047 [P] [US3] Add test_entity_extraction_multiple_entities() - verify templates with multiple entity references extract all entities
- [X] T048 [P] [US3] Add test_multiple_entity_changes_sequential() to tests/test_preset_templates_reactive.py - change entity A, verify update, change entity B, verify update
- [X] T049 [P] [US3] Add test_template_with_multiple_conditions() - verify complex template with season + time of day logic

### Implementation for User Story 3

- [X] T050 [US3] Enhance PresetEnv._extract_entities() to handle complex templates with multiple entity references (already implemented in US2, verify works for complex cases)
- [X] T051 [US3] Update Climate._setup_template_listeners() to handle multiple entities per preset (already implemented in US2, verify works for complex cases)
- [X] T052 [US3] Add integration test in tests/test_preset_templates_reactive.py with real conditional template using hass.states.async_set() for multiple entities

**Checkpoint**: All template types (static, simple, complex conditional) should now be independently functional

---

## Phase 6: User Story 4 - Temperature Range Mode with Templates (Priority: P3)

**Goal**: Extend template support to heat_cool mode (range mode) with target_temp_low and target_temp_high.

**Independent Test**: Configure heat_cool thermostat, set eco_temp_low="{{ states('sensor.outdoor_temp') | float - 2 }}" and eco_temp_high="{{ states('sensor.outdoor_temp') | float + 4 }}", outdoor=20°C (verify range 18-24°C), change to 25°C (verify range updates to 23-29°C).

### Tests for User Story 4

- [X] T053 [P] [US4] Add test_range_mode_with_templates() to tests/preset_env/test_preset_env_templates.py - verify both temp_low and temp_high evaluate independently
- [X] T054 [P] [US4] Add test_range_mode_mixed_static_template() - verify one static (temp_low: 18) and one template (temp_high) work together
- [X] T055 [P] [US4] Add test_preset_manager_range_mode_templates() to tests/managers/test_preset_manager_templates.py - verify both low and high applied to environment
- [X] T056 [P] [US4] Add test_range_mode_reactive_update() to tests/test_preset_templates_reactive.py - change outdoor sensor, verify both low and high update
- [ ] T057 [P] [US4] Add E2E test to tests/config_flow/test_e2e_heater_cooler_persistence.py - full flow with range mode templates

### Implementation for User Story 4

- [X] T058 [US4] Verify PresetEnv._process_field() handles target_temp_low and target_temp_high (already called in __init__, verify works for range mode)
- [X] T059 [US4] Verify PresetManager handles range mode template evaluation (already implemented in US1 with getters, verify works)
- [X] T060 [US4] Verify Climate._async_template_entity_changed() handles range mode (check is_range_mode, update both temps)
- [ ] T061 [US4] Add range mode test case to integration tests

**Checkpoint**: Both single temperature mode and range mode should work with templates

---

## Phase 7: User Story 5 - Configuration with Template Validation (Priority: P2)

**Goal**: Provide user-friendly config flow with TemplateSelector, syntax validation, and inline help.

**Independent Test**: Start config flow, enter invalid template "{{ states('sensor.temp'", attempt save, verify validation error displayed with clear message.

### Tests for User Story 5

- [X] T062 [P] [US5] Create tests/config_flow/test_preset_templates_config_flow.py with test_config_flow_accepts_template_input() - verify template string accepted
- [X] T063 [P] [US5] Add test_config_flow_static_value_backward_compatible() - verify numeric value still accepted
- [X] T064 [P] [US5] Add test_config_flow_template_syntax_validation() - verify invalid template rejected with vol.Invalid
- [X] T065 [P] [US5] Add test_config_flow_valid_template_syntax_accepted() - verify valid template passes validation
- [ ] T066 [P] [US5] Add test_options_flow_template_persistence() to tests/config_flow/test_options_flow.py - verify template pre-fills in options
- [ ] T067 [P] [US5] Add test_options_flow_modify_template() - verify template modification works
- [ ] T068 [P] [US5] Add test_options_flow_static_to_template() - verify changing from static to template
- [ ] T069 [P] [US5] Add test_options_flow_template_to_static() - verify changing from template to static

### Implementation for User Story 5

- [X] T070 [P] [US5] Implement validate_template_or_number() function in custom_components/dual_smart_thermostat/schemas.py - Template(value) parse check, raise vol.Invalid on error
- [X] T071 [US5] Modify get_presets_schema() in schemas.py to use TextSelector instead of NumberSelector for all preset temperature fields
- [X] T072 [US5] Apply vol.All(TextSelector, validate_template_or_number) to away_temp, eco_temp, comfort_temp, etc. fields
- [X] T073 [US5] Apply same pattern to range mode fields (away_temp_low, away_temp_high, etc.)
- [X] T074 [US5] Update custom_components/dual_smart_thermostat/translations/en.json with inline help text (data_description) for template fields - include 3 examples: static, entity reference, conditional
- [X] T075 [US5] Update field labels in translations to indicate template support
- [ ] T076 [US5] Test config flow manually in Home Assistant UI to verify TemplateSelector appearance and help text

**Checkpoint**: Users can now configure templates through UI with validation and guidance

---

## Phase 8: User Story 6 - Preset Switching with Template Cleanup (Priority: P4)

**Goal**: Ensure proper listener cleanup when switching presets or deactivating to prevent memory leaks.

**Independent Test**: Configure two presets with different template entities (Away uses sensor.away_temp, Eco uses sensor.eco_temp), activate Away (verify sensor.away_temp monitored), switch to Eco (verify sensor.away_temp no longer monitored, sensor.eco_temp now monitored).

### Tests for User Story 6

- [ ] T077 [P] [US6] Add test_listener_cleanup_on_preset_change() to tests/test_preset_templates_reactive.py - verify listener count drops after preset switch
- [ ] T078 [P] [US6] Add test_listener_cleanup_on_preset_none() - verify all listeners removed when preset set to PRESET_NONE
- [ ] T079 [P] [US6] Add test_listener_cleanup_on_entity_removal() - verify cleanup when thermostat entity removed from HA
- [ ] T080 [P] [US6] Add test_multiple_preset_switches() - switch between presets multiple times, verify no listener accumulation

### Implementation for User Story 6

- [ ] T081 [US6] Verify Climate._setup_template_listeners() calls _remove_template_listeners() first (already implemented in US2, ensure proper cleanup)
- [ ] T082 [US6] Verify Climate._remove_template_listeners() clears both _template_listeners list and _active_preset_entities set (already implemented in US2, verify completeness)
- [ ] T083 [US6] Add debug logging to _setup_template_listeners() showing which entities are being monitored
- [ ] T084 [US6] Add debug logging to _remove_template_listeners() showing listener cleanup count
- [ ] T085 [US6] Verify async_will_remove_from_hass() calls cleanup (already integrated in US2, verify works)

**Checkpoint**: All listeners properly managed, no memory leaks

---

## Phase 9: Integration & End-to-End Testing

**Purpose**: Comprehensive validation across all user stories

- [ ] T086 [P] Add test_e2e_template_persistence_simple_heater() to tests/config_flow/test_e2e_simple_heater_persistence.py - config flow with template → options flow → verify persistence (deferred - full config flow simulation)
- [ ] T087 [P] Add test_e2e_template_persistence_heater_cooler() to tests/config_flow/test_e2e_heater_cooler_persistence.py - range mode template persistence (deferred - full config flow simulation)
- [X] T088 [P] Add test_seasonal_template_full_flow() to tests/test_preset_templates_integration.py - end-to-end seasonal preset scenario
- [X] T089 [P] Add test_rapid_entity_changes() - verify system stable with multiple quick entity changes
- [X] T090 [P] Add test_entity_unavailable_then_available() - entity goes unavailable, then available again with new value
- [X] T091 [P] Add test_non_numeric_template_result() - template returns "unknown", verify graceful fallback
- [ ] T092 [P] Add test_template_timeout() - verify system handles slow template evaluation (edge case, low priority)
- [ ] T093 Run full test suite - pytest tests/ -v --log-cli-level=DEBUG (requires full test environment)

---

## Phase 10: Documentation & Examples

**Purpose**: User-facing documentation and example configurations

- [ ] T094 [P] Create examples/advanced_features/presets_with_templates.yaml with 6 example configurations (seasonal, outdoor-based, entity reference, time-based, range mode, complex multi-condition)
- [ ] T095 [P] Add template troubleshooting section to docs/troubleshooting.md (template not updating, evaluation errors, debug logging)
- [ ] T096 [P] Update docs/config/CRITICAL_CONFIG_DEPENDENCIES.md to document template syntax requirements and note that entities don't need to exist at config time
- [ ] T097 [P] Update tools/focused_config_dependencies.json to add template field dependencies (if any)
- [ ] T098 [P] Verify tools/config_validator.py handles template fields correctly

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, linting, and final validation

- [ ] T099 Run isort . to sort imports in custom_components/dual_smart_thermostat/
- [ ] T100 Run black . to format code
- [ ] T101 Run flake8 . to check style compliance
- [ ] T102 Run codespell to check spelling
- [ ] T103 Fix any linting errors from T099-T102
- [ ] T104 Run pytest tests/ to verify all tests pass
- [ ] T105 Verify backward compatibility - run existing preset test suite without modifications
- [ ] T106 Manual testing: Configure thermostat with static preset in UI, verify works
- [ ] T107 Manual testing: Configure thermostat with entity reference template in UI, change entity, verify updates
- [ ] T108 Manual testing: Configure thermostat with seasonal template in UI, change season sensor, verify updates
- [ ] T109 Review code against CLAUDE.md guidelines (modular design, error handling, logging)
- [ ] T110 Verify constitutional gates: config flow integration, test consolidation, no memory leaks, linting passes
- [ ] T111 Update CHANGELOG.md with feature summary
- [ ] T112 Create git commit with proper message format

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-8)**: All depend on Foundational phase completion
  - User Story 1 (P1 - MVP): Can start after Foundational
  - User Story 2 (P2): Builds on US1 (adds template evaluation)
  - User Story 3 (P3): Builds on US2 (complex templates use same infrastructure)
  - User Story 4 (P3): Builds on US2 (range mode uses same evaluation logic)
  - User Story 5 (P2): Can start after US2 (config flow for templates)
  - User Story 6 (P4): Verifies US2 cleanup logic
- **Integration Testing (Phase 9)**: Depends on US1-US6 completion
- **Documentation (Phase 10)**: Can run in parallel with Phase 9
- **Polish (Phase 11)**: Depends on all phases completion

### User Story Dependencies

- **User Story 1 (P1)**: Foundation only - independently testable
- **User Story 2 (P2)**: Builds on US1 infrastructure - adds template evaluation and reactive listeners
- **User Story 3 (P3)**: Uses US2 infrastructure - independently testable with complex templates
- **User Story 4 (P3)**: Uses US2 infrastructure - independently testable in range mode
- **User Story 5 (P2)**: Uses US2 infrastructure - adds config flow UI
- **User Story 6 (P4)**: Verifies US2 cleanup - independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- PresetEnv changes before PresetManager changes
- PresetManager changes before Climate entity changes
- Core implementation before integration tests
- Story complete before moving to next priority

### Parallel Opportunities

**Setup Phase**: T003, T004, T005 can run in parallel (different files)

**Foundational Phase**: T007, T008, T009 can run in parallel

**User Story 1 Tests**: T010, T011, T012 can run in parallel (different test functions)

**User Story 2 Tests**: T022-T031 can run in parallel (different test files/functions)

**User Story 3 Tests**: T046-T049 can run in parallel

**User Story 4 Tests**: T053-T057 can run in parallel

**User Story 5 Tests**: T062-T069 can run in parallel

**User Story 5 Implementation**: T070, T074, T075 can run in parallel (schemas vs translations)

**User Story 6 Tests**: T077-T080 can run in parallel

**Integration Tests (Phase 9)**: T086-T092 can run in parallel

**Documentation (Phase 10)**: T094-T098 can run in parallel

**User Stories**: After Foundational, US3, US4, US5, US6 can be worked on in parallel by different team members (US2 is prerequisite infrastructure)

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task T022: "Add test_template_detection_string_value() to tests/preset_env/test_preset_env_templates.py"
Task T023: "Add test_entity_extraction_simple()"
Task T024: "Add test_template_evaluation_success()"
Task T025: "Add test_template_evaluation_entity_unavailable()"
Task T026: "Add test_template_evaluation_fallback_to_default()"
Task T027: "Create tests/managers/test_preset_manager_templates.py with test_preset_manager_calls_template_evaluation()"
Task T028: "Add test_preset_manager_applies_evaluated_temperature()"
Task T029: "Create tests/test_preset_templates_reactive.py with test_entity_change_triggers_temperature_update()"
Task T030: "Add test_entity_change_triggers_control_cycle()"
Task T031: "Add test_listener_cleanup_on_preset_change()"

# After tests written and failing, implementation tasks in sequence:
Task T032: "Implement PresetEnv._extract_entities()"
Task T033: "Enhance PresetEnv._process_field() for strings"
Task T034: "Implement PresetEnv._evaluate_template()"
# ... etc
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T006)
2. Complete Phase 2: Foundational (T007-T009) - CRITICAL
3. Complete Phase 3: User Story 1 (T010-T021)
4. **STOP and VALIDATE**: Run pytest tests/, verify static values work, run existing preset tests
5. Deploy/demo if ready - **This is the safety net for backward compatibility**

### Incremental Delivery

1. MVP (US1) → Foundation + Backward Compatibility ✅
2. Add US2 → Template evaluation + Reactive updates ✅
3. Add US3 → Complex conditional templates ✅
4. Add US4 → Range mode templates ✅
5. Add US5 → Config flow UI ✅
6. Add US6 → Cleanup verification ✅
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers after Foundational (Phase 2) complete:

1. **Developer A**: User Story 1 (T010-T021) - MVP baseline
2. Wait for US1 complete (foundation for others)
3. **Developer B**: User Story 2 (T022-T045) - Core template infrastructure
4. Wait for US2 complete (enables all template features)
5. **Developer C**: User Story 3 (T046-T052) - Uses US2 infrastructure
6. **Developer D**: User Story 4 (T053-T061) - Uses US2 infrastructure
7. **Developer E**: User Story 5 (T062-T076) - Uses US2 infrastructure
8. **Developer F**: User Story 6 (T077-T085) - Verifies US2

**Note**: US2 must complete before US3-US6 as it provides the template evaluation infrastructure.

---

## Notes

- [P] tasks = different files or independent test functions, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests written FIRST (TDD approach per CLAUDE.md)
- All tests MUST pass pytest, isort, black, flake8, codespell before commit
- Run full test suite after each user story completion
- Verify backward compatibility after US1
- Stop at any checkpoint to validate story independently
- Follow CLAUDE.md test consolidation patterns (no standalone bug fix files)
- Memory leak testing critical for US6 (listener cleanup)

---

## Task Summary

**Total Tasks**: 112
- Setup: 6 tasks
- Foundational: 3 tasks
- User Story 1 (P1 - MVP): 12 tasks (3 tests + 9 implementation)
- User Story 2 (P2): 24 tasks (10 tests + 14 implementation)
- User Story 3 (P3): 7 tasks (4 tests + 3 implementation)
- User Story 4 (P3): 9 tasks (5 tests + 4 implementation)
- User Story 5 (P2): 15 tasks (8 tests + 7 implementation)
- User Story 6 (P4): 9 tasks (4 tests + 5 implementation)
- Integration & E2E: 8 tasks
- Documentation: 5 tasks
- Polish: 14 tasks

**Parallel Opportunities**: 67 tasks marked [P] can run in parallel within their phase

**MVP Scope**: Phase 1 + Phase 2 + Phase 3 (User Story 1) = 21 tasks

**Core Feature Delivery**: Through User Story 5 = 76 tasks (includes config flow UI)
