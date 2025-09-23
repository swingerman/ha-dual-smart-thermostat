# Tasks for Feature: Develop Config & Options Flows (Phase 1 authoritative)

This `tasks.md` is generated from `specs/001-develop-config-and/plan.md`. Each task is actionable, dependency-ordered, and includes file paths, exact commands to run locally, acceptance criteria, and notes about parallelization ([P] = parallelizable with other [P] tasks).

Guidance for reviewers:
- Each task must be reviewed by running the commands in the "How to run" section and confirming the Acceptance Criteria.
- All code tasks follow TDD: create failing tests first, implement changes, then make tests pass.
- Keep PRs small and focused; prefer single responsibility per PR.

Summary: ✅ E2E scaffold (T001) and config flow tests (T002) COMPLETED with comprehensive implementation insights documented. Current priority: Complete options flow implementation in T003, remove Advanced option (T004), complete heater_cooler/heat_pump (T005-T006), contract & parity tests plus models (T007-T009), test reorg (T010), schema consolidation investigation (T011), then polish & release (T012).

---

Task IDs: T001..T012

## Current Status (Updated)

**Completed Tasks:**
- ✅ T001 (E2E Playwright scaffold) — Closed as completed on 2025-09-16
- ✅ T002 (Playwright tests for config & options flows) — Closed as completed on 2025-09-18

**Active Tasks:**
- 🚧 T003 (Add CI job to run E2E) — Issue #413 open
- 🔄 T004-T012 (Remaining tasks) — Issues #414-422 open

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

T003 — Complete E2E implementation: Options Flow + CI — [GitHub Issue #413](https://github.com/swingerman/ha-dual-smart-thermostat/issues/413)
- Files to create/update:
  - ⏳ `tests/e2e/tests/specs/options_flow.spec.ts` — Implement options flow using config flow patterns
  - ✅ `.github/workflows/e2e.yml` — CI workflow (already exists)
- **Current Status**: Config flow complete, options flow pending
- **Key Implementation Requirements** (based on config flow findings):
  - Options flow uses `<select>` dropdown for system type (vs radio buttons in config flow)
  - Must handle existing configuration pre-filling 
  - Apply same form interaction patterns: visibility checks, `ha-picker-field` handling
  - Use same step detection logic: dialog content + form elements analysis
  - Follow same 4-step pattern: system type → basic config → features → confirmation
- **Reference Implementation**: Use `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts` as pattern template (clean implementation with reusable helpers)
- How to run locally:
  ```bash
  cd tests/e2e
  # Test basic heater config flow (recommended implementation)
  npx playwright test tests/specs/basic_heater_config_flow.spec.ts --headed
  # Test legacy config flow (detailed debugging version)
  npx playwright test tests/specs/config_flow.spec.ts --headed
  # Test options flow (to be implemented)
  npx playwright test tests/specs/options_flow.spec.ts --headed
  ```
- Acceptance criteria:
  - ✅ **ACHIEVED**: Config flow test passes consistently
  - ⏳ **PENDING**: Options flow test completes full modification workflow
  - ✅ **ACHIEVED**: CI workflow runs E2E tests automatically
  - ⏳ **PENDING**: REST API validation for both flows
- **Documentation**: Implementation patterns documented in `tests/e2e/LESSONS_LEARNED.md`
- Parallelization: [P] can run while T005/T006 are in progress (E2E covers stable types only).

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

T005 — Complete `heater_cooler` implementation (Phase 1C) — [GitHub Issue #415](https://github.com/swingerman/ha-dual-smart-thermostat/issues/415)
- Files to edit/create:
  - `custom_components/dual_smart_thermostat/schemas.py` (add/complete `get_heater_cooler_schema`)
  - `custom_components/dual_smart_thermostat/feature_steps/` (ensure all per-feature steps handle `heater_cooler` cases)
  - Tests: `tests/features/heater_cooler/test_config_flow.py`, `tests/features/heater_cooler/test_options_flow.py`
- TDD guidance:
  1. Add contract tests under T008 to define expected keys for `heater_cooler`.
  2. Implement schema and per-feature logic to satisfy tests.
- Acceptance criteria:
  - Unit and contract tests for `heater_cooler` pass.
  - E2E tests for `simple_heater`/`ac_only` remain green.
- Parallelization: Can be run in parallel with T006 and T008 if no shared files are edited simultaneously.

T006 — Complete `heat_pump` implementation (Phase 1C) — [GitHub Issue #416](https://github.com/swingerman/ha-dual-smart-thermostat/issues/416)
- Files to edit/create:
  - `custom_components/dual_smart_thermostat/schemas.py` (complete `get_heat_pump_schema` and `heat_pump_cooling` support)
  - `custom_components/dual_smart_thermostat/feature_steps/` handlers
  - Tests: `tests/features/heat_pump/test_config_flow.py`, `tests/features/heat_pump/test_options_flow.py`
- Special notes:
  - The `heat_pump_cooling` field may be an entity selector (preferred) or a boolean; ensure schema supports entity ids and the options flow offers a selector.
- Acceptance criteria:
  - Contract tests for `heat_pump` pass; `pytest -q` passes locally.
- Parallelization: Can run with T005 (different system types), but coordinate on `schemas.py` edits.

T007 — Add contract & options-parity tests [P] — [GitHub Issue #417](https://github.com/swingerman/ha-dual-smart-thermostat/issues/417)
- Files to create:
  - `tests/contracts/test_schemas.py` — tests that load each `get_<system>_schema()` and assert expected keys and types according to `data-model.md`.
  - `tests/options/test_options_parity.py` — tests verifying the options flow pre-fills saved values and preserves unchanged fields.
- Description:
  - Write failing tests first for each missing contract, then implement the code to pass them (TDD).
- How to run:
  ```bash
  pytest tests/contracts -q
  pytest tests/options -q
  ```
- Acceptance criteria:
  - The contract tests fail initially (RED), then after implementation pass (GREEN).
- Parallelization: [P]

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

Task Ordering and dependency notes
- ✅ E2E scaffold (T001) and Playwright tests (T002) COMPLETED — top priority was finished successfully.
- Current priority: E2E CI job (T003) and removal of Advanced option (T004) should be performed before heavy schema edits (T005/T006) to avoid merge conflicts.
- Contract tests (T007) should be created early and used as failing tests (TDD) for T004-T009.
- Test reorg (T010) is low-risk but coordinate with other test edits — do PoC first.
- Schema consolidation (T011) should be done after T004 removal and initial E2E to minimize churn.

Parallel execution examples
- Parallel group A [P]: {T001, T002, T004, T007, T009, T011, T012}
- Sequential group B: {T001 -> T004 -> T007 -> T008 -> T005/T006 -> T010 -> T012}

Appendix — Helpful Commands
- Run focused tests:
  ```bash
  pytest tests/contracts -q
  pytest tests/features -q
  pytest tests/config_flow -q
  ```
- Grep for keys and types:
  ```bash
  grep -R "CONF_PRESETS\|SYSTEM_TYPES\|CONF_SYSTEM_TYPE\|configure_" -n custom_components || true
  ```
- Run full test-suite and save baseline:
  ```bash
  pytest -q | tee pytest-baseline.log
  ```

---

Generated by automation from `specs/001-develop-config-and/plan.md`. Reviewers: run T001 then pick T002 or T004 depending on priorities.
