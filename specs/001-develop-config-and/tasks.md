# Tasks for Feature: Develop Config & Options Flows (Phase 1 authoritative)

This `tasks.md` is generated from `specs/001-develop-config-and/plan.md`. Each task is actionable, dependency-ordered, and includes file paths, exact commands to run locally, acceptance criteria, and notes about parallelization ([P] = parallelizable with other [P] tasks).

Guidance for reviewers:
- Each task must be reviewed by running the commands in the "How to run" section and confirming the Acceptance Criteria.
- All code tasks follow TDD: create failing tests first, implement changes, then make tests pass.
- Keep PRs small and focused; prefer single responsibility per PR.

Summary: ✅ E2E scaffold (T001), config flow tests (T002), and complete E2E implementation (T003) COMPLETED with comprehensive implementation insights documented. **T003 ACHIEVED BEYOND ORIGINAL SCOPE**: Full E2E coverage for both system types (config + options flows) with CI integration. ✅ T004 (Remove Advanced option) COMPLETED. ✅ T005 (heater_cooler) and ✅ T006 (heat_pump) COMPLETED with comprehensive TDD implementation. ❌ T007 REMOVED (duplicate of T005/T006). 🆕 **T007A ADDED** (feature interaction testing - CRITICAL). **Current priority**: Test feature interactions & HVAC modes (T007A - NEW CRITICAL TASK), normalize keys (T008), then polish & release (T009, T012).

---

## Universal Acceptance Criteria Template (All System Types)

This template applies to **all system type implementations** (simple_heater, ac_only, heater_cooler, heat_pump).

### Test-Driven Development (TDD)
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in existing system type tests

### Config Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully to completion
2. ✅ **Valid configuration is created** - Config entry data matches `data-model.md` structure
3. ✅ **Climate entity is created** - Verify entity appears in HA with correct entity_id

### Config Flow - Data Structure Validation
- ✅ All required fields from schema are present in saved config
- ✅ Field types match expected types (entity_id strings, numeric values, booleans)
- ✅ System-specific fields are correctly configured (varies by system type)
- ✅ Advanced settings are flattened to top level (tolerances, min_cycle_duration)
- ✅ `name` field is collected

### Options Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully
2. ✅ **Configuration is updated correctly** - Modified fields are persisted
3. ✅ **Unmodified fields are preserved** - Fields not changed remain intact

### Options Flow - Data Structure Validation
- ✅ `name` field is omitted in options flow
- ✅ Options flow pre-fills all fields from existing config
- ✅ System type is displayed but non-editable
- ✅ Updated config matches `data-model.md` structure after changes

### E2E Persistence Tests (CRITICAL)
**Each system type MUST have an E2E test** that validates the complete lifecycle:
- ✅ **test_e2e_simple_heater_persistence.py** - Simple heater config → options → persistence
- ✅ **test_e2e_ac_only_persistence.py** - AC only config → options → persistence
- ✅ **test_e2e_heater_cooler_persistence.py** - Heater/cooler config → options → persistence
- ⏳ **test_e2e_heat_pump_persistence.py** - TODO: Add when heat_pump is implemented (T006)
- ⏳ **test_e2e_dual_stage_persistence.py** - TODO: Add if dual_stage needs testing
- ⏳ **test_e2e_floor_heating_persistence.py** - TODO: Add if floor_heating needs testing

**What E2E tests validate:**
1. Complete config flow creates correct entry (no transient flags saved)
2. Options flow shows pre-filled values from config entry
3. Feature toggles show checked state when features are configured
4. Changes made in options flow persist correctly (to entry.options)
5. Original values preserved (in entry.data)
6. Reopening options flow shows updated values (merged data + options)
7. Unmodified fields are preserved during partial updates

**Why these tests are critical:**
- Would have caught the options flow persistence bug (mappingproxy handling)
- Validate real Home Assistant behavior, not just Mocks
- Test actual storage flow (data vs options)
- Prevent regressions in persistence logic

### Field-Specific Validation (Unit Tests)
- ✅ Optional entity fields accept empty values (vol.UNDEFINED pattern)
- ✅ Numeric fields have correct defaults when not provided
- ✅ Required fields raise validation errors when missing
- ✅ Entity field validation prevents duplicate entities where applicable

### Feature Integration
- ✅ Features step allows toggling features on/off
- ✅ Enabled features show their configuration steps
- ✅ Feature settings are saved under correct keys
- ✅ Feature settings match schema definitions

### Business Logic Validation
- ✅ Device class works correctly with schema (HeaterDevice, CoolerDevice, etc.)
- ✅ Config flow creates working climate entity
- ✅ Climate entity has correct HVAC modes for system type
- ✅ System-specific behavior works as expected

### Scope Notes
- ❌ **E2E tests**: Not required for new system types (covered by simple_heater/ac_only)
- ✅ **Python tests**: Focus on unit/integration tests for data validation and business logic

---

Task IDs: T001..T012

## Current Status (Updated)

**Completed Tasks:**
- ✅ T001 (E2E Playwright scaffold) — Closed as completed on 2025-09-16
- ✅ T002 (Playwright tests for config & options flows) — Closed as completed on 2025-09-18
- ✅ T003 (Complete E2E implementation: Options Flow + CI) — **COMPLETED BEYOND SCOPE** on 2025-01-17

**Active Tasks (Updated Priorities):**
- 🔥 T004 (Remove Advanced Custom Setup option) — Issue #414 open — **HIGH PRIORITY**
- 🔥 T007 (Add Python unit tests for climate entity validation) — Issue #417 open — **ELEVATED TO HIGH PRIORITY**
- ✅ T005-T006 COMPLETED — Issues #415-416 closed
- 🔄 T007A, T008-T012 (Remaining tasks) — Issues #418-422 open

**Original Parent Issue:**
- ✅ #157 "[feat] config flow" — Closed as completed on 2025-09-16

T001 — Add E2E Playwright scaffold (Phase 1A) [P] — ✅ [COMPLETED] [GitHub Issue #411](https://github.com/swingerman/ha-dual-smart-thermostat/issues/411)
- Files to create:
  - `tests/e2e/docker-compose.yml`
  - `tests/e2e/ha_config/configuration.yaml`
  - `tests/e2e/playwright.config.ts`
  - `tests/e2e/README.md`
  - `tests/e2e/scripts/regenerate_baselines.sh`
- Description:
  - Provide a reproducible Docker Compose setup to run Home Assistant with the custom component mounted and minimal entities required for the flows.
  - Provide Playwright config for `testDir` and `storageState` usage and baseline artifact paths.
- How to run (developer machine with Docker):
  ```bash
  cd tests/e2e
  docker compose up -d
  # Wait 60-120s or tail the HA logs:
  docker compose logs -f homeassistant
  ```
- Acceptance criteria:
  - `docker compose ps` shows `homeassistant` container healthy and reachable on mapped ports.
  - The `README.md` includes regeneration instructions and token handling notes.
- Parallelization: [P] with T002 once HA is reachable.

T002 — Add Playwright tests for config & options flows (Phase 1A) [P] — ✅ [COMPLETED] [GitHub Issue #412](https://github.com/swingerman/ha-dual-smart-thermostat/issues/412)
- Files created:
  - ✅ `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts` — **RECOMMENDED: Clean implementation using reusable helpers**
  - ✅ `tests/e2e/tests/specs/config_flow.spec.ts` — Legacy implementation with detailed debugging
  - ⏳ `tests/e2e/tests/specs/options_flow.spec.ts` — Ready for T003 implementation
  - ✅ `tests/e2e/playwright/setup.ts` — **Reusable HomeAssistantSetup class and step detection functions**
  - ✅ `tests/e2e/baselines/simple_heater/` — Screenshot baselines
- **Implementation Status & Key Findings**:
  - ✅ **T003 Simple Heater Config Flow WORKING**: Complete 4-step flow implemented
    1. System Type Selection (radio buttons) 
    2. Basic Configuration (name, temperature sensor, heater switch)
    3. Features Configuration (skipped for basic flow)
    4. Confirmation Dialog (final verification)
  - ✅ **Home Assistant UI Patterns Discovered**: 
    - Config flows use modal dialogs (URL never changes)
    - Step detection via dialog content + form elements analysis
    - `ha-picker-field` interaction: click → type → Tab (not Enter)
    - Form visibility checking essential before interaction
  - ✅ **Reliable Element Selectors Identified**:
    - `'ha-dialog[open]'` for config flow dialogs
    - `'dialog-data-entry-flow button[part="base"]'` for submit buttons
    - `'ha-integration-list-item:has-text("...")'` for integration cards
- **Documented Insights**: See `tests/e2e/LESSONS_LEARNED.md` for complete implementation patterns
- How to run locally:
  ```bash
  # From repo root
  cd tests/e2e
  npx playwright test tests/specs/config_flow.spec.ts --headed
  ```
- Acceptance criteria:
  - ✅ **ACHIEVED**: Config flow test completes 4-step flow without assertion failures
  - ✅ **ACHIEVED**: Comprehensive logging and error handling implemented
  - ⏳ **PENDING**: REST API validation (to be added in T003 options flow)
- **Next Steps**: Apply discovered patterns to options flow implementation
- Parallelization: [P] with T001 (scaffold) and T004 (CI) when HA reachable.

T003 — Complete E2E implementation: Options Flow + CI — ✅ [COMPLETED BEYOND SCOPE] [GitHub Issue #413](https://github.com/swingerman/ha-dual-smart-thermostat/issues/413)
- Files created:
  - ✅ `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts` — **COMPLETED: Clean implementation using reusable helpers**
  - ✅ `tests/e2e/tests/specs/ac_only_config_flow.spec.ts` — **COMPLETED: AC-only config flow**
  - ✅ `tests/e2e/tests/specs/basic_heater_options_flow.spec.ts` — **COMPLETED: Options flow for basic heater**
  - ✅ `tests/e2e/tests/specs/ac_only_options_flow.spec.ts` — **COMPLETED: Options flow for AC-only**
  - ✅ `tests/e2e/tests/specs/integration_creation_verification.spec.ts` — **COMPLETED: Integration verification**
  - ✅ `.github/workflows/e2e.yml` — CI workflow functional
- **ACHIEVEMENT STATUS**: **EXCEEDED ORIGINAL REQUIREMENTS**
  - ✅ **Config flow tests**: Complete for both `simple_heater` and `ac_only`
  - ✅ **Options flow tests**: Complete for both system types with pre-fill validation
  - ✅ **Integration management**: Create, verify, and cleanup integrations
  - ✅ **CI integration**: E2E tests running automatically on PRs
  - ✅ **Robust helpers**: Reusable `HomeAssistantSetup` class with comprehensive methods
- **Key Implementation Achievements**:
  - ✅ Complete 4-step flow implementation (system type → basic config → features → confirmation)
  - ✅ Options flow with pre-fill validation and system type handling
  - ✅ Integration existence verification (simplified, reliable approach)
  - ✅ Comprehensive error handling and logging
  - ✅ Cross-system-type compatibility testing
- How to run locally:
  ```bash
  cd tests/e2e
  # Run all E2E tests
  npx playwright test --headed
  # Run specific system type tests
  npx playwright test tests/specs/basic_heater_config_flow.spec.ts --headed
  npx playwright test tests/specs/ac_only_options_flow.spec.ts --headed
  ```
- Acceptance criteria:
  - ✅ **ACHIEVED**: Config flow tests pass consistently for both system types
  - ✅ **ACHIEVED**: Options flow tests complete full modification workflow
  - ✅ **ACHIEVED**: CI workflow runs E2E tests automatically
  - ✅ **ACHIEVED**: Integration creation/deletion verification working
- **Documentation**: Implementation patterns documented in `tests/e2e/LESSONS_LEARNED.md`
- **Recommendation**: **CLOSE ISSUE #413 AS COMPLETE** - exceeded original scope

T004 — Remove Advanced (Custom Setup) option (Phase 1B) — [GitHub Issue #414](https://github.com/swingerman/ha-dual-smart-thermostat/issues/414)
- Files to edit:
  - `custom_components/dual_smart_thermostat/const.py`
  - `custom_components/dual_smart_thermostat/schemas.py`
  - `custom_components/dual_smart_thermostat/config_flow.py`
  - `custom_components/dual_smart_thermostat/options_flow.py`
- Steps:
  1. Update `const.py` remove the advanced mapping: remove the `"advanced": "Advanced (Custom Setup)"` entry from `SYSTEM_TYPES`.
  2. Update `get_system_type_schema()` in `schemas.py` to expose only the four system types: `simple_heater`, `ac_only`, `heater_cooler`, `heat_pump`.
  3. Remove any `if`/`branch` code in flows that references the `advanced` type, preserving other logic.
  4. Run `pytest -q` and fix any failing tests due to changed options.
- How to run locally:
  ```bash
  pytest tests/config_flow -q
  ```
- Acceptance criteria:
  - No more references to `"advanced"` in the codebase (grep check).
  - `pytest -q` passes locally; schema shows only four types.
- Parallelization: Not parallel; recommend doing after T001 and before T005/T006.

T005 — Complete `heater_cooler` implementation (Phase 1C) 🔥 [TDD APPROACH] — [GitHub Issue #415](https://github.com/swingerman/ha-dual-smart-thermostat/issues/415)
- **UPDATED APPROACH** (2025-01-06): Test-first implementation using bugs discovered today as foundation
- **Strategy**: Write failing tests FIRST (RED), implement code (GREEN), validate no regressions (REFACTOR)

**Phase 1: Write Failing Tests FIRST (RED)**
- Files to create:
  - `tests/config_flow/test_heater_cooler_config_flow.py`:
    - ✅ Test name field is required and collected (bug fix 2025-01-06)
    - ✅ Test fan_hot_tolerance field exists with default 0.5 (bug fix 2025-01-06)
    - ✅ Test fan_hot_tolerance_toggle is optional (vol.UNDEFINED when empty) (bug fix 2025-01-06)
    - ❌ Test heater field is required
    - ❌ Test cooler field is required
    - ❌ Test heat_cool_mode toggle exists and defaults correctly
    - ❌ Test advanced_settings section extracts and flattens correctly
    - ❌ Test validation: same heater/cooler entity error
    - ❌ Test validation: same heater/sensor entity error
    - ❌ Test successful submission proceeds to features step

  - `tests/config_flow/test_heater_cooler_options_flow.py`:
    - ❌ Test options flow omits name field
    - ❌ Test options flow pre-fills all heater_cooler fields from existing config
    - ❌ Test options flow preserves unmodified fields
    - ❌ Test system type display (non-editable in options)

  - `tests/unit/test_heater_cooler_schema.py`:
    - ❌ Test get_heater_cooler_schema(defaults=None, include_name=True) includes all required fields
    - ❌ Test get_heater_cooler_schema(defaults=None, include_name=False) omits name field
    - ❌ Test get_heater_cooler_schema(defaults={...}) pre-fills values correctly
    - ❌ Test all fields use correct selectors (entity, number, boolean)
    - ❌ Test optional entity fields use vol.UNDEFINED when no default provided
    - ❌ Test advanced_settings section structure

**Phase 2: Implement Code to Pass Tests (GREEN)**
- Files to edit:
  - `custom_components/dual_smart_thermostat/schemas.py`:
    - ✅ COMPLETED: get_heater_cooler_schema(defaults, include_name) with name field
    - ✅ COMPLETED: fan_hot_tolerance numeric field with default 0.5
    - ✅ COMPLETED: fan_hot_tolerance_toggle using vol.UNDEFINED
    - ❌ TODO: Verify all other fields (heater, cooler, heat_cool_mode, tolerances)

  - `custom_components/dual_smart_thermostat/config_flow.py`:
    - ✅ COMPLETED: async_step_heater_cooler calls schema with defaults=None, include_name=True
    - ❌ TODO: Verify validation logic for heater/cooler/sensor

  - `custom_components/dual_smart_thermostat/options_flow.py`:
    - ❌ TODO: Verify async_step_basic uses get_heater_cooler_schema with include_name=False

**Phase 3: Feature Integration Tests (After Basic Works)**
- Files to create (LATER):
  - `tests/features/test_heater_cooler_with_fan.py`
  - `tests/features/test_heater_cooler_with_humidity.py`
  - `tests/features/test_heater_cooler_with_presets.py`
  - `tests/unit/test_heater_cooler_climate_entity.py`

**How to run (TDD RED-GREEN-REFACTOR cycle):**
```bash
# Phase 1: Write tests (should FAIL initially)
pytest tests/config_flow/test_heater_cooler_config_flow.py -v
pytest tests/unit/test_heater_cooler_schema.py -v

# Phase 2: Implement code to make tests pass
# ... make changes to schemas.py, config_flow.py ...

# Phase 3: Verify tests now PASS
pytest tests/config_flow/test_heater_cooler_config_flow.py -v
pytest tests/unit/test_heater_cooler_schema.py -v

# Phase 4: Ensure no regressions
pytest tests/config_flow -v
pytest tests/unit -v
```

**Bug Fixes Already Applied (2025-01-06):**
- ✅ Missing name field in get_heater_cooler_schema() - line 248 config_flow.py
- ✅ Missing fan_hot_tolerance numeric field in schema - line 690 schemas.py
- ✅ fan_hot_tolerance_toggle validation error (None vs vol.UNDEFINED) - line 695 schemas.py
- ✅ Unified fan/humidity schemas to remove duplication
- ✅ Added translations for fan_hot_tolerance and fan_hot_tolerance_toggle
- ✅ Updated README.md documentation for both fields

**Acceptance Criteria (UPDATED TDD APPROACH + DATA VALIDATION):**

**Test-Driven Development (TDD):**
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in existing simple_heater/ac_only tests

**Config Flow - Core Requirements:**
1. ✅ Flow completes without error - All steps navigate successfully to completion
2. ✅ Valid configuration is created - Config entry data matches `data-model.md` structure
3. ✅ Climate entity is created - Verify entity appears in HA with correct entity_id

**Config Flow - Data Structure Validation:**
- ✅ All required fields from schema are present in saved config
- ✅ Field types match expected types (entity_id strings, numeric values, booleans)
- ✅ System-specific fields: `heater`, `cooler`, `target_sensor` are entity_ids
- ✅ `heat_cool_mode` field exists with correct boolean default
- ✅ Advanced settings are flattened to top level (tolerances, min_cycle_duration)
- ✅ `name` field is collected (bug fix 2025-01-06 verified)

**Options Flow - Core Requirements:**
1. ✅ Flow completes without error - All steps navigate successfully
2. ✅ Configuration is updated correctly - Modified fields are persisted
3. ✅ Unmodified fields are preserved - Fields not changed remain intact

**Options Flow - Data Structure Validation:**
- ✅ `name` field is omitted in options flow
- ✅ Options flow pre-fills all heater_cooler fields from existing config
- ✅ System type is displayed but non-editable
- ✅ Updated config matches `data-model.md` structure after changes

**Field-Specific Validation (Unit Tests):**
- ✅ Optional entity fields accept empty values (vol.UNDEFINED pattern)
- ✅ Numeric fields have correct defaults when not provided
- ✅ Required fields (heater, cooler, sensor) raise validation errors when missing
- ✅ Validation: same heater/cooler entity produces error
- ✅ Validation: same heater/sensor entity produces error

**Feature Integration:**
- ✅ Features step allows toggling features on/off
- ✅ Enabled features show their configuration steps
- ✅ Feature settings are saved under correct keys
- ✅ Feature settings match schema definitions

**Business Logic Validation:**
- ✅ HeaterCoolerDevice class works correctly with schema
- ✅ Config flow creates working climate entity
- ✅ Climate entity has correct HVAC modes for heater_cooler system

**Scope Notes:**
- ❌ **REMOVED**: E2E test coverage (covered by simple_heater/ac_only E2E tests)
- ✅ **FOCUS**: Python unit/integration tests for data validation and business logic

**Parallelization**: Can be run in parallel with T006 and T007 if no shared files are edited simultaneously.

T006 — Complete `heat_pump` implementation ✅ [COMPLETED] — [GitHub Issue #416](https://github.com/swingerman/ha-dual-smart-thermostat/issues/416)
- **SCOPE REDUCTION**: Focus on Python implementation and unit tests only; E2E tests removed from scope
- **Strategy**: Write failing tests FIRST (RED), implement code (GREEN), validate no regressions (REFACTOR)

**Files to create/edit:**
- `custom_components/dual_smart_thermostat/schemas.py` (complete `get_heat_pump_schema` and `heat_pump_cooling` support)
- `custom_components/dual_smart_thermostat/feature_steps/` handlers
- Tests: `tests/config_flow/test_heat_pump_config_flow.py`, `tests/config_flow/test_heat_pump_options_flow.py`
- **NEW**: `tests/unit/test_heat_pump_climate_entity.py` — Test climate entity generation for heat_pump
- **NEW**: `tests/unit/test_heat_pump_schema.py` — Test schema structure and defaults

**Special Implementation Notes:**
- The `heat_pump_cooling` field may be an entity selector (preferred) or a boolean
- Ensure schema supports entity ids and the options flow offers a selector
- Single `heater` switch is used for both heating and cooling modes

**Acceptance Criteria (TDD APPROACH + DATA VALIDATION):**

**Test-Driven Development (TDD):**
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in existing system type tests

**Config Flow - Core Requirements:**
1. ✅ Flow completes without error - All steps navigate successfully to completion
2. ✅ Valid configuration is created - Config entry data matches `data-model.md` structure
3. ✅ Climate entity is created - Verify entity appears in HA with correct entity_id

**Config Flow - Data Structure Validation:**
- ✅ All required fields from schema are present in saved config
- ✅ Field types match expected types (entity_id strings, numeric values, booleans)
- ✅ System-specific fields: `heater` (entity_id), `heat_pump_cooling` (entity_id or boolean)
- ✅ `target_sensor` is entity_id
- ✅ Advanced settings are flattened to top level (tolerances, min_cycle_duration)
- ✅ `name` field is collected in config flow

**Options Flow - Core Requirements:**
1. ✅ Flow completes without error - All steps navigate successfully
2. ✅ Configuration is updated correctly - Modified fields are persisted
3. ✅ Unmodified fields are preserved - Fields not changed remain intact

**Options Flow - Data Structure Validation:**
- ✅ `name` field is omitted in options flow
- ✅ Options flow pre-fills all heat_pump fields from existing config
- ✅ System type is displayed but non-editable
- ✅ Updated config matches `data-model.md` structure after changes

**Field-Specific Validation (Unit Tests):**
- ✅ `heat_pump_cooling` accepts entity_id (preferred) or boolean
- ✅ `heat_pump_cooling` entity selector functionality works correctly
- ✅ Optional entity fields accept empty values (vol.UNDEFINED pattern)
- ✅ Numeric fields have correct defaults when not provided
- ✅ Required fields (heater, sensor) raise validation errors when missing

**Feature Integration:**
- ✅ Features step allows toggling features on/off
- ✅ Enabled features show their configuration steps
- ✅ Feature settings are saved under correct keys
- ✅ Feature settings match schema definitions

**Business Logic Validation:**
- ✅ HeatPumpDevice class works correctly with schema
- ✅ Config flow creates working climate entity
- ✅ Climate entity has correct HVAC modes based on heat_pump_cooling state
- ✅ Dynamic heat_pump_cooling entity state changes update available HVAC modes

**Scope Notes:**
- ❌ **REMOVED**: E2E test coverage (covered by simple_heater/ac_only E2E tests)
- ✅ **FOCUS**: Python unit/integration tests for data validation and business logic

**Parallelization**: Can run with T005 (different system types), but coordinate on `schemas.py` edits.

T007 — ~~Add Python Unit Tests for Climate Entity & Data Structure Validation~~ ❌ **REMOVED - DUPLICATE** — ~~[GitHub Issue #417](https://github.com/swingerman/ha-dual-smart-thermostat/issues/417)~~
- **STATUS**: ❌ **TASK REMOVED** - Acceptance criteria merged into T005/T006
- **RATIONALE**: T005 and T006 already include all required test coverage:
  - Climate entity generation tests (covered in T005/T006 Business Logic Validation)
  - Config entry data structure tests (covered in T005/T006 Data Structure Validation)
  - System type configuration tests (covered in T005/T006 acceptance criteria)
  - Contract tests and options parity tests (covered in T005/T006 Field-Specific Validation)
- **ACTION**: Tests will be created as part of T005 (heater_cooler) and T006 (heat_pump) implementation
- **GITHUB ISSUE**: Should be closed or updated to reference T005/T006

T007A — Feature Interaction & HVAC Mode Testing 🔥 [NEW - CRITICAL FOR RELEASE] — [GitHub Issue #436](https://github.com/swingerman/ha-dual-smart-thermostat/issues/436)
- **PRIORITY**: 🔥 **HIGH PRIORITY** - Critical for feature completeness
- **DEPENDENCY**: Must complete AFTER T005/T006 (requires all system types working)
- **RATIONALE**: Features affect HVAC modes, which affect other features. This creates a cascade:
  ```
  System Type + Core Settings → Base HVAC modes
      ↓
  Fan Feature → Adds HVACMode.FAN_ONLY
      ↓
  Humidity Feature → Adds HVACMode.DRY
      ↓
  Openings Feature → Needs available HVAC modes for scope configuration
      ↓
  Presets Feature → Needs ALL enabled features to configure properly
  ```

**Why Ordering Matters:**
- **Openings** need to know which HVAC modes exist (heat, cool, fan_only, dry, heat_cool)
- **Presets** need to know:
  - Which HVAC modes are available (from all previous features)
  - Which openings exist (to reference them with validation)
  - If humidity is enabled (to include humidity bounds)
  - If floor_heating is enabled (to include floor temp bounds)
  - If heat_cool_mode is true (to use temp_low/temp_high vs single temperature)

**Implementation Strategy:**
Break into sub-tasks by feature layer:

**Phase 1: Single Feature + System Type (T007A-1)**
- Test fan feature adds FAN_ONLY mode (heater_cooler + fan, heat_pump + fan)
- Test humidity feature adds DRY mode (all system types + humidity)
- Test floor_heating works with compatible system types (simple_heater, heater_cooler, heat_pump - NOT ac_only)
- Verify feature availability per system type matches schemas.py:458-478

**Phase 2: Openings + HVAC Modes (T007A-2)**
- Test openings scope configuration with different HVAC mode combinations
- Test openings work when fan adds FAN_ONLY mode
- Test openings work when humidity adds DRY mode
- Test openings_scope field accepts all available HVAC modes for the configuration

**Phase 3: Presets + All Features (T007A-3)**
- Test presets with heat_cool_mode=True uses temp_low/temp_high
- Test presets with heat_cool_mode=False uses single temperature
- Test presets with humidity enabled includes humidity bounds
- Test presets with floor_heating enabled includes floor temp bounds (min_floor_temp, max_floor_temp)
- Test presets with openings enabled validates opening_refs
- Test preset validation error when referencing non-configured opening

**Files to create/edit:**
- `tests/features/test_feature_hvac_mode_interactions.py` — Test HVAC mode additions
- `tests/features/test_openings_with_hvac_modes.py` — Test openings scope with various modes
- `tests/features/test_presets_with_all_features.py` — Test presets respecting all feature combinations
- `tests/integration/test_complete_feature_flows.py` — End-to-end feature combination tests

**How to run:**
```bash
# Phase 1: Feature + System Type
pytest tests/features/test_feature_hvac_mode_interactions.py -v

# Phase 2: Openings interactions
pytest tests/features/test_openings_with_hvac_modes.py -v

# Phase 3: Presets interactions
pytest tests/features/test_presets_with_all_features.py -v

# Full suite
pytest tests/features -v
pytest tests/integration -v
```

**Acceptance Criteria (Following Universal Template):**

**Test-Driven Development (TDD):**
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in T005/T006 system type tests

**Feature Interaction - Core Requirements:**
1. ✅ **Fan feature adds FAN_ONLY mode** - Verified across all compatible system types
2. ✅ **Humidity feature adds DRY mode** - Verified across all system types
3. ✅ **Floor heating restriction** - Works with heater-based systems, blocked/hidden for ac_only
4. ✅ **Feature availability per system type** - Matches schemas.py definitions

**Openings + HVAC Modes:**
- ✅ Openings scope accepts all available HVAC modes for current configuration
- ✅ Openings configuration appears BEFORE presets in flow order
- ✅ Openings work correctly when FAN_ONLY mode added by fan feature
- ✅ Openings work correctly when DRY mode added by humidity feature

**Presets + All Features (Most Complex):**
- ✅ Presets appear LAST in feature configuration order (after all other features)
- ✅ Presets use temp_low/temp_high when heat_cool_mode=True
- ✅ Presets use single temperature when heat_cool_mode=False
- ✅ Presets include humidity bounds ONLY when humidity feature enabled
- ✅ Presets include floor temp bounds ONLY when floor_heating feature enabled
- ✅ Presets validate opening_refs against configured openings
- ✅ Preset validation fails when referencing non-existent opening
- ✅ Presets configuration form adapts to all enabled features

**Data Structure Validation:**
- ✅ Feature settings saved under correct keys in data-model.md structure
- ✅ HVAC modes correctly populated based on enabled features
- ✅ Climate entity exposes correct HVAC modes based on feature combination

**Business Logic Validation:**
- ✅ Climate entity switches modes correctly with fan feature
- ✅ Climate entity handles humidity/dry mode correctly
- ✅ Openings behavior respects configured HVAC mode scope
- ✅ Presets apply correct settings based on all enabled features

**Quality Gates:**
- ✅ All code must pass linting checks
- ✅ All unit tests must pass
- ✅ All integration tests must pass
- ✅ No regressions in existing system type tests

**Parallelization**: Cannot run in parallel with T005/T006 - requires them complete first

T008 — Normalize collected_config keys and constants — [GitHub Issue #418](https://github.com/swingerman/ha-dual-smart-thermostat/issues/418)
- Files to edit:
  - `custom_components/dual_smart_thermostat/config_flow.py`
  - `custom_components/dual_smart_thermostat/options_flow.py`
  - `custom_components/dual_smart_thermostat/feature_steps/*.py`
  - `custom_components/dual_smart_thermostat/schemas.py`
  - `custom_components/dual_smart_thermostat/const.py`
- Steps:
  1. Grep for inconsistent keys: `grep -R "system_type\|configure_" -n custom_components | sed -n '1,200p'`
  2. Decide on canonical constants (use `CONF_SYSTEM_TYPE`, `CONF_PRESETS`, `configure_<feature>` booleans).
  3. Update code and tests, ensuring `collected_config` shape matches `data-model.md`.
- Acceptance criteria:
  - All modules import constants from `const.py` (no string literals used for persisted keys), and tests ensure shapes match `data-model.md`.
- Parallelization: Not [P] unless changes are limited to separate modules.

T009 — Add `models.py` dataclasses [P] — [GitHub Issue #419](https://github.com/swingerman/ha-dual-smart-thermostat/issues/419)
- Files to create:
  - `custom_components/dual_smart_thermostat/models.py`
  - `tests/unit/test_models.py`
- Description:
  - Implement TypedDicts or dataclasses representing the canonical data-model for each system type (core_settings + features). Include simple `to_dict()`/`from_dict()` helpers.
- How to run tests:
  ```bash
  pytest tests/unit/test_models.py -q
  ```
- Acceptance criteria:
  - `tests/unit/test_models.py` covers serialization of at least one sample config per system type and passes.
- Parallelization: [P]

T010 — Perform test reorganization (REORG) [P] ⚪ **OPTIONAL** — [GitHub Issue #420](https://github.com/swingerman/ha-dual-smart-thermostat/issues/420)
- **PRIORITY**: ⚪ **OPTIONAL** - Nice-to-have, not blocking release
- Files to create:
  - `specs/001-develop-config-and/REORG.md`
- Steps (PoC then single commit):
  1. Inventory tests: `git ls-files 'tests/**/*.py'`
  2. PoC: Move 1 feature folder (e.g., `tests/features/presets*`) to new `tests/features/` layout, run focused tests.
  3. Single-commit reorg: `git mv` as possible, or add new files and remove old ones in same commit.
  4. Update `conftest.py` and imports if fixtures are directory-scoped.
  5. Run `pytest -q` and fix regressions.
- Acceptance criteria:
  - New `tests/` layout exists, test imports updated, full test-suite passes locally.
- **Release Impact**: None - Can be done post-release for better maintainability
- Parallelization: [P] but coordinate with any test-editing PRs.

T011 — Investigate schema duplication (const vs schemas) (Phase 1C-1) ⚪ **OPTIONAL** — [GitHub Issue #421](https://github.com/swingerman/ha-dual-smart-thermostat/issues/421)
- **PRIORITY**: ⚪ **OPTIONAL** - Nice-to-have, not blocking release
- Files to create/edit:
  - `specs/001-develop-config-and/schema-consolidation-proposal.md` (if not already present)
  - PoC: `custom_components/dual_smart_thermostat/metadata.py`
  - Update one schema factory to consume `metadata.py` (e.g., adjust `get_system_type_schema()` in `schemas.py`) and run contract tests.
- Steps:
  1. Audit duplicates: `grep -n "SYSTEM_TYPES\|CONF_PRESETS\|preset" custom_components | sed -n '1,200p'`
  2. Draft 2–3 consolidation options (Option A recommended: metadata module).
  3. Implement a small PoC `metadata.py` with system descriptors and update a single schema factory to use it.
  4. Run `pytest tests/contracts -q` and ensure no change in public keys.
- Acceptance criteria:
  - Proposal file present with recommended option and risk/effort estimates.
  - PoC passes contract tests and does not change persisted keys.
- **Release Impact**: None - Only do if duplication becomes painful during T005/T006/T008
- Parallelization: [P]

T012 — Polish documentation & release prep — [GitHub Issue #422](https://github.com/swingerman/ha-dual-smart-thermostat/issues/422)
- Files to edit:
  - `specs/001-develop-config-and/quickstart.md`
  - `specs/001-develop-config-and/data-model.md` (if minor clarifications needed)
  - `tests/e2e/README.md`
- Steps:
  1. Update quickstart with examples for `simple_heater` and `ac_only`.
  2. Add release checklist: update changelog, bump version in `manifest.json` if needed, and ensure `hacs.json` metadata is accurate.
- Acceptance criteria:
  - Docs provide clear steps to run E2E locally and in CI, and list baseline images regeneration steps.
- Parallelization: [P]

---

Task Ordering and dependency notes (UPDATED 2025-01-06)
- ✅ E2E scaffold (T001), Playwright tests (T002), and complete E2E implementation (T003) COMPLETED — **EXCEEDED ORIGINAL SCOPE**.
- ❌ T007 REMOVED — Duplicate of T005/T006 acceptance criteria
- 🆕 T007A ADDED — Feature interaction & HVAC mode testing (critical for release)

**CURRENT PRIORITIES** (Revised):
1. 🔥 **T004** (Remove Advanced option) — Clean up codebase before heavy development
2. 🔥 **T005** (Complete heater_cooler with TDD) — Includes all unit/integration tests
3. 🔥 **T006** (Complete heat_pump with TDD) — Includes all unit/integration tests
4. 🔥 **T007A** (Feature interaction testing) — **NEW: CRITICAL** - Test feature combinations & HVAC modes
5. ✅ **T008** (Normalize keys) — Clean up after system type implementations
6. ✅ **T009** (models.py) — Add type safety with dataclasses
7. ✅ **T012** (Documentation & release prep) — Essential for release
8. ⚪ **T010** (Test reorg) — **OPTIONAL** - Not blocking release
9. ⚪ **T011** (Schema consolidation) — **OPTIONAL** - Not blocking release

**Updated Parallel execution examples:**
- **Phase 1** 🔥: T004 (Advanced option removal) — Do first, blocks nothing
- **Phase 2** ✅: {T005, T006} — COMPLETED (Parallel implementation, coordinated on `schemas.py` edits)
- **Phase 3** 🔥: T007A (Feature interactions) — CURRENT PRIORITY
- **Phase 4** ✅: T008 (Normalize keys after learning from T005/T006/T007A)
- **Phase 5** ✅: {T009, T012} — Parallel, different files
- **Phase 6** ⚪: {T010, T011} — **OPTIONAL** - Only if time permits

**Recommended Sequential Path (Critical Path to Release):**
```
T004 → {T005, T006} → T007A → T008 → {T009, T012} → RELEASE
✅       ✅            🔥      ⏳      ⏳
       (parallel)      ↑               (parallel)
                   [NEW: Critical
                    for features]
```

**Why T007A is Critical:**
- Features affect HVAC modes (fan→FAN_ONLY, humidity→DRY)
- HVAC modes affect openings (scope configuration)
- All features affect presets (temp fields, humidity, floor, opening refs)
- Without T007A, feature combinations may break in production

**Optional Post-Release:**
```
T010 (test reorg) and T011 (schema consolidation) can be done after release if needed
```

Appendix — Helpful Commands
- Run focused tests:
  ```bash
  # Python unit tests (recommended focus)
  pytest tests/unit -v
  pytest tests/contracts -q
  pytest tests/features -q
  pytest tests/config_flow -q
  # E2E tests (complete and sufficient)
  cd tests/e2e && npx playwright test --headed
  ```
- Grep for keys and types:
  ```bash
  grep -R "CONF_PRESETS\|SYSTEM_TYPES\|CONF_SYSTEM_TYPE\|configure_" -n custom_components || true
  ```
- Run full test-suite and save baseline:
  ```bash
  pytest -q | tee pytest-baseline.log
  ```

## E2E Test Status Summary
**Current E2E Coverage**: ✅ **COMPLETE AND SUFFICIENT**
- ✅ Config flow tests for `simple_heater` and `ac_only`
- ✅ Options flow tests for both system types
- ✅ Integration creation/deletion verification
- ✅ CI integration working
- ✅ **NO FURTHER E2E EXPANSION NEEDED**

**Focus Area**: 🎯 **Python Unit Tests** for business logic and data structure validation

---

Generated by automation from `specs/001-develop-config-and/plan.md`. Reviewers: run T001 then pick T002 or T004 depending on priorities.
