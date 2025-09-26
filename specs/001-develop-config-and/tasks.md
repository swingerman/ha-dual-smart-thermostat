# Tasks for Feature: Develop Config & Options Flows (Phase 1 authoritative)

This `tasks.md` is generated from `specs/001-develop-config-and/plan.md`. Each task is actionable, dependency-ordered, and includes file paths, exact commands to run locally, acceptance criteria, and notes about parallelization ([P] = parallelizable with other [P] tasks).

Guidance for reviewers:
- Each task must be reviewed by running the commands in the "How to run" section and confirming the Acceptance Criteria.
- All code tasks follow TDD: create failing tests first, implement changes, then make tests pass.
- Keep PRs small and focused; prefer single responsibility per PR.

Summary: ✅ E2E scaffold (T001), config flow tests (T002), and complete E2E implementation (T003) COMPLETED with comprehensive implementation insights documented. **T003 ACHIEVED BEYOND ORIGINAL SCOPE**: Full E2E coverage for both system types (config + options flows) with CI integration. Current priority: Remove Advanced option (T004), expand Python unit tests for climate entity validation (T007 - ELEVATED PRIORITY), complete heater_cooler/heat_pump with Python-first approach (T005-T006), then polish & release (T012).

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
- 🔄 T005-T006, T008-T012 (Remaining tasks) — Issues #415-416, #418-422 open

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

T005 — Complete `heater_cooler` implementation (Phase 1C) 📉 [REDUCED SCOPE] — [GitHub Issue #415](https://github.com/swingerman/ha-dual-smart-thermostat/issues/415)
- **SCOPE REDUCTION**: Focus on Python implementation and unit tests only; E2E tests removed from scope
- Files to edit/create:
  - `custom_components/dual_smart_thermostat/schemas.py` (add/complete `get_heater_cooler_schema`)
  - `custom_components/dual_smart_thermostat/feature_steps/` (ensure all per-feature steps handle `heater_cooler` cases)
  - Tests: `tests/features/heater_cooler/test_config_flow.py`, `tests/features/heater_cooler/test_options_flow.py`
  - **NEW**: `tests/unit/test_heater_cooler_climate_entity.py` — Test climate entity generation for heater_cooler
- **REMOVED FROM SCOPE**: E2E Playwright tests (too expensive to maintain)
- TDD guidance:
  1. Add contract tests under T007 to define expected keys for `heater_cooler`.
  2. Implement schema and per-feature logic to satisfy tests.
  3. Focus on Python unit tests for business logic validation.
- Updated Acceptance criteria:
  - ✅ Unit and contract tests for `heater_cooler` pass.
  - ✅ Python tests validate climate entity structure and behavior.
  - ✅ E2E tests for `simple_heater`/`ac_only` remain green.
  - ❌ **REMOVED**: E2E test coverage requirement for `heater_cooler`.
- Parallelization: Can be run in parallel with T006 and T007 if no shared files are edited simultaneously.

T006 — Complete `heat_pump` implementation (Phase 1C) 📉 [REDUCED SCOPE] — [GitHub Issue #416](https://github.com/swingerman/ha-dual-smart-thermostat/issues/416)
- **SCOPE REDUCTION**: Focus on Python implementation and unit tests only; E2E tests removed from scope
- Files to edit/create:
  - `custom_components/dual_smart_thermostat/schemas.py` (complete `get_heat_pump_schema` and `heat_pump_cooling` support)
  - `custom_components/dual_smart_thermostat/feature_steps/` handlers
  - Tests: `tests/features/heat_pump/test_config_flow.py`, `tests/features/heat_pump/test_options_flow.py`
  - **NEW**: `tests/unit/test_heat_pump_climate_entity.py` — Test climate entity generation for heat_pump
- **REMOVED FROM SCOPE**: E2E Playwright tests (too expensive to maintain)
- Special notes:
  - The `heat_pump_cooling` field may be an entity selector (preferred) or a boolean; ensure schema supports entity ids and the options flow offers a selector.
- Updated Acceptance criteria:
  - ✅ Contract tests for `heat_pump` pass; `pytest -q` passes locally.
  - ✅ Python tests validate climate entity structure and behavior.
  - ✅ `heat_pump_cooling` entity selector functionality works correctly.
  - ❌ **REMOVED**: E2E test coverage requirement for `heat_pump`.
- Parallelization: Can run with T005 (different system types), but coordinate on `schemas.py` edits.

T007 — Add Python Unit Tests for Climate Entity & Data Structure Validation 🔥 [HIGH PRIORITY] — [GitHub Issue #417](https://github.com/swingerman/ha-dual-smart-thermostat/issues/417)
- **PRIORITY ELEVATION**: Elevated from medium to HIGH PRIORITY based on refined testing strategy
- **New Focus**: Comprehensive Python unit tests for business logic and data structure validation
- Files to create:
  - `tests/unit/test_climate_entity_generation.py` — **NEW HIGH PRIORITY**: Test actual Home Assistant climate entity creation and configuration
  - `tests/unit/test_config_entry_data_structure.py` — **NEW HIGH PRIORITY**: Test saved config entry data matches canonical `data-model.md`
  - `tests/unit/test_system_type_configs.py` — **NEW HIGH PRIORITY**: Test system-specific configurations are applied correctly
  - `tests/integration/test_integration_behavior.py` — **NEW HIGH PRIORITY**: Test Home Assistant integration behavior
  - `tests/contracts/test_schemas.py` — tests that load each `get_<system>_schema()` and assert expected keys and types according to `data-model.md`.
  - `tests/options/test_options_parity.py` — tests verifying the options flow pre-fills saved values and preserves unchanged fields.
- **Rationale**: E2E tests handle UI journeys; Python tests should handle business logic, data structures, and HA integration behavior
- Description:
  - Write failing tests first for each missing contract, then implement the code to pass them (TDD).
  - Focus on testing actual climate entity generation, not just UI behavior
  - Validate that saved configuration data matches expected structure
  - Test system-specific behavior (AC mode, heater mode, etc.)
- How to run:
  ```bash
  # New high-priority tests
  pytest tests/unit/test_climate_entity_generation.py -v
  pytest tests/unit/test_config_entry_data_structure.py -v
  pytest tests/unit/test_system_type_configs.py -v
  pytest tests/integration/test_integration_behavior.py -v
  # Existing contract tests
  pytest tests/contracts -q
  pytest tests/options -q
  ```
- Acceptance criteria:
  - ✅ Climate entity structure tests validate actual HA entity attributes per system type
  - ✅ Config entry data structure tests ensure saved data matches `data-model.md`
  - ✅ System type configuration tests validate system-specific behavior
  - ✅ Integration behavior tests validate HA core integration
  - ✅ Contract tests fail initially (RED), then after implementation pass (GREEN)
- Parallelization: [P] with T004 (different files)

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

T010 — Perform test reorganization (REORG) [P] — [GitHub Issue #420](https://github.com/swingerman/ha-dual-smart-thermostat/issues/420)
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
- Parallelization: [P] but coordinate with any test-editing PRs.

T011 — Investigate schema duplication (const vs schemas) (Phase 1C-1) — [GitHub Issue #421](https://github.com/swingerman/ha-dual-smart-thermostat/issues/421)
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

Task Ordering and dependency notes (UPDATED)
- ✅ E2E scaffold (T001), Playwright tests (T002), and complete E2E implementation (T003) COMPLETED — **EXCEEDED ORIGINAL SCOPE**.
- **CURRENT HIGH PRIORITIES**: 
  1. 🔥 **T004** (Remove Advanced option) — Clean up codebase before heavy development
  2. 🔥 **T007** (Python unit tests) — **ELEVATED PRIORITY** for business logic validation
- **MEDIUM PRIORITIES**: T008 (normalize keys) → T005/T006 (complete system types with Python-first approach) → T009 (models.py)
- **LOW PRIORITIES**: T010 (test reorg), T011 (schema consolidation), T012 (documentation)
- **SCOPE REDUCTIONS**: T005/T006 no longer require E2E tests; T010/T011 reduced to nice-to-have status

Updated Parallel execution examples
- **Immediate Parallel Group** 🔥: {T004, T007} — High priority, different files
- **Medium-term Parallel Group**: {T005, T006, T008, T009} — Coordinate on `schemas.py` edits
- **Final Parallel Group**: {T010, T011, T012} — Low priority polish tasks
- **Recommended Sequential Path**: T004 → T007 → T008 → {T005, T006} → T009 → T012

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
