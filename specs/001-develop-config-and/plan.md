# Implementation Plan: [FEATURE]


**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]
**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

## Execution Flow (/plan command scope)
```
1. Load feature spec from Input path
   → If not found: ERROR "No feature spec at {path}"
2. Fill Technical Context (scan for NEEDS CLARI**Current approach**: Direct implementation of remaining tasks from the todo list, prioritizing:
1. **Highest Priority (Phase 1A)**: E2E Playwright scaffold and comprehensive UI testing to harden stable system types
2. **Immediate (Phase 1B)**: Remove "Advanced (Custom Setup)" option and clean up related logic
3. **Medium-term (Phase 1C)**: Complete `heater_cooler` and `heat_pump` system type implementations
4. **Ongoing (Phase 1D)**: Contract tests, models.py, and options-parity validation
5. **Final (Phase 1E)**: Documentation updates and release preparationION)
   → Detect Project Type from context (web=frontend+backend, mobile=app+api)
   → Set Structure Decision based on project type
3. Evaluate Constitution Check section below
   → If violations exist: Document in Complexity Tracking
   → If no justification possible: ERROR "Simplify approach first"
   → Update Progress Tracking: Initial Constitution Check
4. Execute Phase 0 → research.md
   → If NEEDS CLARIFICATION remain: ERROR "Resolve unknowns"
5. Execute Phase 1 → contracts, data-model.md, quickstart.md, agent-specific template file (e.g., `CLAUDE.md` for Claude Code, `.github/copilot-instructions.md` for GitHub Copilot, or `GEMINI.md` for Gemini CLI).
6. Re-evaluate Constitution Check section
   → If new violations: Refactor design, return to Phase 1
   → Update Progress Tracking: Post-Design Constitution Check
7. Plan Phase 2 → Describe task generation approach (DO NOT create tasks.md)
8. STOP - Ready for /tasks command
```

**IMPORTANT**: The /plan command STOPS at step 7. Phases 2-4 are executed by other commands:
- Phase 2: /tasks command creates tasks.md
- Phase 3-4: Implementation execution (manual or via tools)

## Summary
Deliver feature-complete Home Assistant config and options flows for the `dual_smart_thermostat` integration, supporting two production-ready system types (`simple_heater`, `ac_only`) with comprehensive feature coverage. The flows provide a three-step experience: (1) system type selection, (2) core settings configuration, and (3) features selection, followed by ordered per-feature configuration steps. Options flows mirror config flows but omit the `name` field and pre-fill saved values.

**Status**: `simple_heater` and `ac_only` are stable and production-ready. Priority focus on E2E test coverage to harden stable system types, then completing `heater_cooler` and `heat_pump` implementations while removing only the "Advanced (Custom Setup)" option.

Technical approach: centralized schema factories (`schemas.py`), per-feature step modules (`feature_steps/`), domain-only entity selectors, canonical data models (`data-model.md`), and TDD with contract/integration/E2E test coverage.

## Technical Context
**Language/Version**: Python 3.13 (Home Assistant requirement)
**Primary Dependencies**: Home Assistant test helpers, `voluptuous` (schema helpers), `pytest` (testing)
**Storage**: Home Assistant config entries
**Testing**: `pytest` with asyncio/HA test helpers; TDD approach
**Target Platform**: Home Assistant environment on Linux
**Project Type**: Single Python integration (custom component)
**Performance Goals**: Standard HA expectations — minimal CPU/memory and responsive UI
**Constraints**: Must follow the project's constitution (centralized schemas, test-first, permissive selectors)
**Scale/Scope**: Single integration; incremental per-system type implementation

## Constitution Check
*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Simplicity**:
- Projects: Single integration (code under `custom_components/dual_smart_thermostat/`, tests under `tests/`)
- Using framework directly: Yes — rely on Home Assistant APIs without extra wrappers
- Single data model: Yes — store config via HA config entries and use `schemas.py` factories
- Avoiding heavy patterns: Yes — keep modules small and focused

**Architecture**:
- EVERY feature as library? (no direct app code)
- Libraries listed: [name + purpose for each]
- CLI per library: [commands with --help/--version/--format]
- Library docs: llms.txt format planned?

**Testing (NON-NEGOTIABLE)**:
- RED-GREEN-Refactor cycle enforced? (test MUST fail first)
- Git commits show tests before implementation?
- Order: Contract→Integration→E2E→Unit strictly followed?
- Real dependencies used? (actual DBs, not mocks)
- Integration tests for: new libraries, contract changes, shared schemas?
- FORBIDDEN: Implementation before test, skipping RED phase

**Observability**:
- Structured logging: Add logging for critical flow transitions and errors
- Error context: Ensure validation errors include actionable messages for users

**Versioning**:
- Version number assigned? (MAJOR.MINOR.BUILD)
- BUILD increments on every change?
- Breaking changes handled? (parallel tests, migration plan)

## Project Structure

### Documentation (this feature)
```
specs/[###-feature]/
├── plan.md              # This file (/plan command output)
├── research.md          # Phase 0 output (/plan command)
├── data-model.md        # Phase 1 output (/plan command)
├── quickstart.md        # Phase 1 output (/plan command)
├── contracts/           # Phase 1 output (/plan command)
└── tasks.md             # Phase 2 output (/tasks command - NOT created by /plan)
```

### Source Code (repository layout for this integration)

The repository already contains a Home Assistant custom component layout. Follow the existing structure and keep source code under the integration folder:

```
custom_components/dual_smart_thermostat/
├── __init__.py
├── manifest.json
├── config_flow.py
├── options_flow.py
├── schemas.py
├── feature_steps/
│   ├── humidity.py
   │   ├── fan.py
   │   ├── openings.py
   │   ├── presets.py
   │   └── floor_heating.py
├── translations/
└── ...
```

Proposed test re-organization (do not move files automatically; apply gradually):

```
tests/
├── config_flow/            # flow-level tests (step ordering, options, full flows)
├── features/               # per-feature unit/integration tests (fan, humidity, presets)
├── openings/               # specialized openings tests
├── presets/                # presets specific tests
├── integration/            # end-to-end style tests across multiple system types
└── unit/                   # small unit tests (schemas, helpers)
```

Notes:
- Keep existing tests in place; reorganize by moving files in a single commit (if desired) to avoid mixed history.
- Update test imports/paths as needed after moving; run focused test runs to verify.

### Task: Test reorganization (move tests into structured layout)

Goal: Re-organize the repository test layout into the canonical structure shown above while preserving history, test stability, and CI invariants.

Why: A clear test layout (`tests/config_flow/`, `tests/features/`, `tests/integration/`, `tests/unit/`) makes focused test runs faster, simplifies contributor onboarding, and supports the contract-first workflow described in this plan.

High-level steps:
1. Inventory & plan
   - Run a quick discovery (`git ls-files 'tests/**/*.py'` / `pytest --collect-only`) to list current test files and their implicit groupings.
   - Create `specs/001-develop-config-and/REORG.md` describing the proposed per-file moves and any required `conftest.py` adjustments.
2. PoC move (optional but recommended)
   - Move a small subset of tests (one feature or one flow) into the new layout and update imports.
   - Run focused tests to validate the approach and update `REORG.md` with lessons learned.
3. Single-commit reorganization
   - Apply the full reorganization in one commit to preserve history coherence.
   - Use `git mv` where possible to retain history, or add new files and remove old ones in the same commit.
4. Update test infrastructure
   - Update or add `conftest.py` files under new directories if fixtures are directory-scoped.
   - Adjust any test helpers imports (`from tests.helpers import ...` → updated relative paths) and update references in CI/test scripts.
5. Test & stabilize
   - Run focused test groups where possible (e.g., `pytest tests/features -q`) and fix import/fixture regressions.
   - Run full test-suite `pytest -q` and address any regressions or flakiness.
6. PR & CI
   - Open a single PR containing the full reorganization commit and a short migration note referencing `REORG.md`.
   - Ensure CI runs the entire test-suite; fix any CI-only failures.

Acceptance criteria:
- The repository uses the new `tests/` layout as documented in this plan.
- The reorganization is contained in a single PR (single commit preferred) with `REORG.md` explaining the mapping.
- All tests pass locally (`pytest -q`) and on CI after the reorg commit.
- No test behavior changes are introduced aside from path/import updates; any intentional test changes must be documented in the PR and `REORG.md`.

Relation to tracking
- This task is tracked by the todo list entry "Perform test reorganization" (see todo). Start with the PoC approach if the reorg surface area is large; otherwise, perform the single-commit move.

**Structure Decision**: Use the existing `custom_components/dual_smart_thermostat/` layout and adopt the proposed `tests/` structure for clarity and easier focused test runs.

### Quick Implementation Cross-References
For implementers and reviewers, here are exact files and symbols to inspect while following this plan. These map plan concepts to concrete implementation locations.

- Unified features selection step (config & options flows):
   - `custom_components/dual_smart_thermostat/config_flow.py::ConfigFlowHandler.async_step_features`
   - `custom_components/dual_smart_thermostat/options_flow.py::OptionsFlowHandler.async_step_features`
   - Schema: `custom_components/dual_smart_thermostat/schemas.py::get_features_schema`

- Core system schema factories (used by `basic`/`core` steps):
   - `custom_components/dual_smart_thermostat/schemas.py::get_core_schema`
   - Per-system helpers: `get_simple_heater_schema`, `get_basic_ac_schema`, `get_heater_cooler_schema`, `get_grouped_schema`

- Per-feature step handlers and typical call sites:
   - `custom_components/dual_smart_thermostat/feature_steps/humidity.py` — `HumiditySteps.async_step_toggle`, `async_step_config`, `async_step_options`
   - `custom_components/dual_smart_thermostat/feature_steps/fan.py` — `FanSteps` methods
   - `custom_components/dual_smart_thermostat/feature_steps/openings.py` — `OpeningsSteps.async_step_selection`, `async_step_config`, `async_step_options`
   - `custom_components/dual_smart_thermostat/feature_steps/presets.py` — `PresetsSteps` methods

- Flow utilities and validators (implementation helpers to review):
   - `custom_components/dual_smart_thermostat/flow_utils.py` — `EntityValidator`, `OpeningsProcessor`

When implementing tasks, open these files first to understand the current routing and schema APIs used by the flows.

## Phase 0: Outline & Research
1. **Extract unknowns from Technical Context** above:
   - For each NEEDS CLARIFICATION → research task
   - For each dependency → best practices task
   - For each integration → patterns task

2. **Generate and dispatch research agents**:
   ```
   For each unknown in Technical Context:
     Task: "Research {unknown} for {feature context}"
   For each technology choice:
     Task: "Find best practices for {tech} in {domain}"
   ```

3. **Consolidate findings** in `research.md` using format:
   - Decision: [what was chosen]
   - Rationale: [why chosen]
   - Alternatives considered: [what else evaluated]

**Output**: research.md with all NEEDS CLARIFICATION resolved

## Phase 1 (authoritative): E2E Playwright + Dockerized Home Assistant

This section replaces the generic E2E notes with a concrete, implementable plan aligned to the canonical artifacts in this spec set: `data-model.md`, `contracts/step-handlers.md`, and `quickstart.md`.

Objective
- Provide reproducible E2E tests that exercise the integration's config and options flows end-to-end for the first two system types (`simple_heater`, `ac_only`), cover every feature and per-feature form, capture step screenshots, and assert the final persisted config entry matches the canonical data-model.

Concrete deliverables for Phase 1
- tests/e2e/ (directory) containing:
  - `docker-compose.yml` — Home Assistant container with mounts for `tests/e2e/ha_config` and `custom_components/dual_smart_thermostat`.
  - `ha_config/configuration.yaml` — deterministic configuration enabling `http`, `frontend`, `template` entities used by flows, and `logger` configured to `info` for debugging.
  - `ha_init/` — scripts and (optional) committed `storageState.json` for Playwright automatic login. Document steps to rotate/regenerate storage state in README.
  - `playwright.config.ts` — Playwright project configuration (Chromium headless by default) and output directories for artifacts and traces.
  - `playwright/setup.ts` — helper utilities to wait for HA readiness, create initial template entities via REST API, and optionally seed the integrations UI state.
  - `playwright/config_flow.spec.ts` — end-to-end test for `simple_heater` config flow (canonical happy path). Will be duplicated for `ac_only` once stable.
  - `playwright/options_flow.spec.ts` — test that opens the created config entry and validates options pre-fill and persistence.
  - `baselines/` — baseline images for the happy path UI steps (committed after approval) and `artifacts/` produced per-run.
  - `README.md` — how to run locally, how to regenerate baselines, CI notes, and security considerations.

Exact test scenarios (happy-path, deterministic)
- Config flow `simple_heater` (playwright/config_flow.spec.ts)
  1. Wait for HA to be ready and load UI using Playwright `storageState.json` for automatic login.
  2. Open Integrations → Add integration → search and select `Dual Smart Thermostat`.
  3. Select `system_type: simple_heater` and proceed.
  4. Fill core settings using deterministic entities provided by `ha_config` (e.g., `input_number.test_heater`, `sensor.test_temperature`) and set `min_cycle_duration` to a known value. Capture a screenshot.
  5. In the `features` step, toggle each `configure_<feature>` flag on and: for each feature, open its configuration step and fill all fields with known values (use sensors and entities from `ha_config`). Capture screenshots per feature.
  6. Add two presets using the UI (fill temperature/humidity/floor ranges where applicable). Capture screenshot.
  7. Finish flow, poll HA REST API for the created config entry, and assert the persisted data matches the canonical `data-model.md` (key names and types exactly as `custom_components/dual_smart_thermostat/const.py` and `schemas.py` produce).

- Options flow `simple_heater` (playwright/options_flow.spec.ts)
  1. From Integrations list, open created `Dual Smart Thermostat` entry and click Options.
  2. Assert the options form is pre-filled with the values saved during config flow for a subset of fields (core settings + one per-feature set).
  3. Change one feature value and save. Validate the changed value via HA REST API on the updated config entry.

Baseline images and diffs
- Store canonical baseline screenshots under `tests/e2e/baselines/{simple_heater,ac_only}`. Playwright test will capture per-step screenshots to `tests/e2e/artifacts/{run-id}` and run pixel-diff against the baseline. A helper script `scripts/e2e/regenerate_baselines.sh` will be provided to update baselines when UI changes are intentional.

Implementation notes aligned to repo artifacts
- Use selectors and field names matching the schema factories in `custom_components/dual_smart_thermostat/schemas.py`. When validating the persisted entry, assert presence and types of keys listed in `specs/001-develop-config-and/data-model.md`.
- Ensure `playwright/setup.ts` uses HA REST API authentication via stored Playwright `storageState.json` to create any runtime entities or adjust states as needed.

CI integration (GitHub Actions - outline)
- Job steps:
  1. Start services: `docker-compose -f tests/e2e/docker-compose.yml up -d`.
  2. Wait for HA readiness (curl HTTP 200 on port 8123).
  3. Run `npx playwright test --config=tests/e2e/playwright.config.ts --project=chromium`.
  4. Upload `tests/e2e/artifacts` and Playwright traces on failure.

Security & maintenance
- Do NOT commit HA long-lived tokens; prefer committing `storageState.json` only for ephemeral CI runs with rotation instructions in README. Document the regeneration procedure.
- Keep baseline images under `baselines/` small and only for essential screens to reduce repository size.

Acceptance criteria
- Directory `tests/e2e` exists with the files listed in "Concrete deliverables".
- A test run locally (developer machine with Docker) or in CI can execute `playwright test` and complete the `simple_heater` config flow test and validate the persisted config entry.
- Documentation in `tests/e2e/README.md` explains how to run tests, regenerate baselines, and secure tokens.

Next steps after Phase 1
- Duplicate `playwright/config_flow.spec.ts` and adapt for `ac_only` once `simple_heater` tests are stable.
- Add `tests/e2e` GitHub Actions workflow to runs on PRs that modify integration code or tests.



## Phase 1: Feature-Complete Config & Options Flow Plan

*Prerequisites: Canonical data models and spec artifacts complete (✓ done)*

### Current Implementation Status
- **Complete**: `simple_heater` and `ac_only` system types with core settings and features flow
- **Complete**: Centralized schema factories in `schemas.py` (per-system and per-feature)
- **Complete**: Feature steps implementation (`fan`, `humidity`, `openings`, `floor_heating`, `presets`)
- **Complete**: Data model specification aligned with implementation (`data-model.md`)
- **In progress**: E2E test scaffold and comprehensive contract tests
- **Pending**: Advanced system types removal and final polishing

### Scope Adjustment: Remove Advanced Custom Setup, Complete All System Types

**Decision**: Keep and complete all four system types (`simple_heater`, `ac_only`, `heater_cooler`, `heat_pump`); remove only the "Advanced (Custom Setup)" option.

**Rationale**:
- `simple_heater` and `ac_only` are stable and production-ready
- `heater_cooler` and `heat_pump` provide important functionality for comprehensive HVAC coverage
- The "Advanced (Custom Setup)" option adds complexity without clear user value and can be removed
- Prioritize E2E testing to harden the stable system types while completing the remaining ones

**Implementation tasks**:
1. **Remove advanced custom setup option** - Remove `"advanced": "Advanced (Custom Setup)"` from `SYSTEM_TYPES` in `const.py`
2. **Update system type selector** - Ensure only the four concrete system types appear in `get_system_type_schema()`
3. **Remove advanced setup flow logic** - Remove any flow routing or schema logic specific to the advanced custom setup option
4. **Complete heater_cooler implementation** - Finish core schema, feature steps, and tests to match `simple_heater`/`ac_only` completion level
5. **Complete heat_pump implementation** - Finish core schema, feature steps, tests, and `heat_pump_cooling` entity selector functionality
6. **Update data model** - Keep all four system type sections in `data-model.md`; remove references to advanced custom setup### Feature-Complete Acceptance Criteria

**For config flow**:
- ✅ Step 1: System type selection (`simple_heater`, `ac_only`, `heater_cooler`, `heat_pump`) — remove only "Advanced (Custom Setup)"
- ✅ Step 2: Core settings (entity selectors, tolerances, cycle duration) — stable for `simple_heater`/`ac_only`; complete for `heater_cooler`/`heat_pump`
- ✅ Step 3: Features selection (toggles for `fan`, `humidity`, `openings`, `floor_heating`, `presets`)
- ✅ Per-feature steps: Each enabled feature shows configuration step with appropriate selectors and defaults
- ✅ Feature ordering: `openings` before `presets`; `presets` always last
- ✅ Entity selectors: Domain-only for permissiveness; handle empty entity lists gracefully
- ✅ Defaults: Sensible defaults for all numeric inputs (tolerances, timeouts, humidity ranges)
- ✅ Validation: Clear error messages for required fields; non-blocking warnings for recommendations**For options flow**:
- ✅ Same steps as config flow but omit `name` input
- ✅ Pre-fill all inputs with saved values from existing config entry
- ✅ Support changing system type (with appropriate warnings about data loss)
- ✅ Support toggling features on/off and updating per-feature settings
- ✅ Preserve unmodified settings when saving partial changes

**For both flows**:
- ✅ Consistent schema factories used (`schemas.py` as single source of truth)
- ✅ Consistent keys persisted (match `data-model.md` canonical shapes)
- ✅ Responsive UI (minimal delay between steps)
- ✅ Accessibility (proper labels, help text, error context)

### Implementation Roadmap to Feature-Complete

**Phase 1A: E2E Test Coverage (highest priority — hardening stable system types)**
1. Complete Playwright E2E scaffold with Docker HA setup (`tests/e2e/docker-compose.yml`, `ha_config/configuration.yaml`)
2. Implement end-to-end config flow tests for `simple_heater` and `ac_only` (screenshot capture, REST API validation)
3. Implement options flow tests validating pre-fill and update behavior
4. Add CI pipeline running E2E tests on PR changes to prevent regressions

**Phase 1B: Advanced Custom Setup Removal (immediate)**
1. Remove `"advanced": "Advanced (Custom Setup)"` from `SYSTEM_TYPES` in `const.py`
2. Update `config_flow.py` and `options_flow.py` to remove advanced custom setup routing logic
3. Ensure system type selector shows only the four concrete system types
4. Run existing tests to ensure no regressions for stable system types

**Phase 1C: Complete Remaining System Types (medium-term)**
1. Complete `heater_cooler` implementation (core schema, feature steps, tests) to match `simple_heater`/`ac_only` level
2. Complete `heat_pump` implementation (core schema, `heat_pump_cooling` entity selector, feature steps, tests)
3. Add E2E test coverage for `heater_cooler` and `heat_pump` once implementation is complete
4. Update documentation with examples for all four system types

**Phase 1C-1: Investigate schema duplication and consolidation (low-medium priority)**

Why: The codebase currently defines schema-like metadata in two primary places: `custom_components/dual_smart_thermostat/const.py` (system labels, preset mappings, some default keys) and `custom_components/dual_smart_thermostat/schemas.py` (schema factories, feature availability maps). This duplication increases maintenance burden and the risk of drift between config keys, translators, and tests.

What to do:
- Audit duplicated items: `SYSTEM_TYPES`, `CONF_PRESETS`/`CONF_PRESETS_OLD`, default values and feature availability maps living in `schemas.py`.
- Produce a concise proposal with 2–3 consolidation options and trade-offs:
   - Option A (recommended): Introduce a single metadata module (e.g. `metadata.py` or extend `const.py`) that exposes structured metadata (system type descriptors, preset definitions, default values). Update `schemas.py` to build selectors from this metadata. Effort: small→medium. Risk: low. Benefit: clear single source-of-truth for labels, defaults, and translation keys.
   - Option B: Define metadata dataclasses in `models.py` and generate selectors from those dataclasses. Effort: medium. Risk: medium. Benefit: stronger typing and easier reuse in tests/models.
   - Option C: Keep `const.py` minimal and move preset/feature metadata into `data-model.md` + `models.py`, using `schemas.py` to load metadata at runtime. Effort: medium→large. Risk: medium→high (translations and runtime behavior need careful handling).
- For each option list estimated effort (small/medium/large), risk, and required test updates.
- Recommend an approach (prefer Option A: metadata module + selector generators) and a minimal migration path: (1) add metadata module, (2) update `schemas.py` to reference metadata, (3) run tests, (4) remove duplicates from `const.py`.

Acceptance criteria:
- A written proposal file is added under `specs/001-develop-config-and/` (e.g. `schema-consolidation-proposal.md`) capturing chosen approach, effort estimate, and migration steps.
- The first refactor step (introducing metadata and updating `schemas.py` references) does not change public keys or labels and keeps contract tests passing.
- Tests updated as necessary and any translation keys retained or documented for migration.

Priority rationale: Low-medium. Consolidation reduces future maintenance and drift but is not blocking E2E stabilization. Schedule this investigation to begin after Phase 1A (E2E scaffold) and Phase 1B (advanced option removal) complete, and before large refactors to heater_cooler/heat_pump to minimize merge conflicts.

**Phase 1D: Polish and Contract Tests (ongoing)**
1. Implement `models.py` with TypedDicts matching `data-model.md`
2. Add contract tests asserting schema factories produce expected keys/types for all system types
3. Add options-parity tests ensuring pre-fill behavior works for all features across all system types
4. Normalize key usage (`CONF_SYSTEM_TYPE` vs string literals) across flows
5. Perform test reorganization: move existing tests into the new `tests/` layout (`tests/unit/`, `tests/features/`, `tests/config_flow/`, `tests/integration/`) as a single-commit reorganization. See the "Task: Test reorganization" section for detailed steps and acceptance criteria.

**Phase 1E: Documentation and Release Prep (final)**
1. Update `README.md` with configuration examples for all supported system types
2. Update Home Assistant integration manifest and documentation
3. Final acceptance testing using `quickstart.md` scenarios for all system types
4. Performance and accessibility validation

### Key Files and Contracts

**Schema contracts** (centralized in `schemas.py`):
- `get_system_type_schema()` → returns selector with `simple_heater`, `ac_only`, `heater_cooler`, `heat_pump` (no "Advanced (Custom Setup)")
- `get_simple_heater_schema()` → heater + sensor + tolerances + cycle duration (✅ stable)
- `get_basic_ac_schema()` → cooler + sensor + tolerances + cycle duration (ac_mode forced true) (✅ stable)
- `get_heater_cooler_schema()` → heater + cooler + sensor + tolerances + cycle duration (🔄 complete implementation)
- `get_grouped_schema()` with `show_heat_pump_cooling=True` → heater + sensor + heat_pump_cooling entity selector (🔄 complete implementation)
- `get_features_schema()` → unified feature toggles (`configure_fan`, `configure_humidity`, etc.)
- Per-feature schemas: `get_fan_schema()`, `get_humidity_schema()`, `get_openings_selection_schema()`, `get_openings_schema()`, `get_floor_heating_schema()`, `get_preset_selection_schema()`, `get_presets_schema()`

**Flow contracts** (implemented in `config_flow.py`, `options_flow.py`):
- Step routing: `system_type` → `core` → `features` → per-feature steps in order
- Options flow: mirrors config flow steps but omits name, pre-fills from existing entry
- Per-feature step handlers: delegate to `feature_steps/` modules using centralized schemas

**Data persistence contracts** (validated by tests):
- Config entries use exact keys from `data-model.md` canonical shapes
- Feature settings nested under `feature_settings` key with per-feature objects
- Core settings flattened under config entry root matching CONF_* constants

**Test coverage contracts**:
- Contract tests: schema factories produce expected keys and handle defaults
- Options-parity tests: options flow pre-fills and persists correctly
- Integration tests: full config and options flows for both system types
- E2E tests: UI behavior and REST API validation using Playwright

### Test preservation policy

All changes introduced during Phase 1 must preserve the current unit-test baseline. This integration currently has an established suite of unit and integration tests; any refactor or feature work must not regress passing tests.

Requirements:
- Run the full test suite (`pytest -q`) locally before opening a PR and ensure the same number of passing tests (or document intentional changes).
- Add contract tests that pin the schema factories' output (keys and types) to prevent inadvertent drift during refactors.
- Gate refactor PRs with CI that runs the test suite; CI must pass prior to merging.
- For any intentional test expectation changes, provide a migration plan and update the spec `specs/001-develop-config-and/test-preservation.md` with rationale and steps.

Developer guidance:
- Run focused tests while developing using `pytest tests/<module_or_test_file>::<TestClassOrFunction>` to speed the feedback loop.
- Use `pytest -q` for full-suite runs before PRs or on CI. Address any flaky tests by stabilizing the test (not by skipping) and document the fix in the PR.
- When modifying `const.py` or `schemas.py`, add or update contract tests that assert persisted keys and default values remain unchanged unless explicitly planned and documented.

### Linting & pre-commit policy

All changes must be linted and formatted before commit/PR. Enforce linters locally via `pre-commit` and in CI to keep the codebase consistent and catch common issues early.

Required checks (minimum):
- `isort` — import sorting
- `black` or equivalent formatting (project prefers `black` where applicable)
- `flake8` — style and basic static checks
- `mypy` — optional, but required where typing is used; run with `--ignore-missing-imports` if third-party stubs absent
- `codespell` — catch common typos in source and docs

Suggested `.pre-commit-config.yaml` hooks (example):
```yaml
repos:
   - repo: https://github.com/pre-commit/mirrors-isort
      rev: v5.12.0
      hooks:
         - id: isort
   - repo: https://github.com/psf/black
      rev: 24.1.0
      hooks:
         - id: black
   - repo: https://github.com/pre-commit/mirrors-flake8
      rev: 6.0.0
      hooks:
         - id: flake8
   - repo: https://github.com/pre-commit/mirrors-mypy
      rev: v1.5.1
      hooks:
         - id: mypy
   - repo: https://github.com/codespell-project/codespell
      rev: v2.1.0
      hooks:
         - id: codespell
```

Local developer steps:
```bash
# Install pre-commit once per dev environment
pip install pre-commit
pre-commit install

# Run linters locally on changed files
pre-commit run --all-files
# Or run specific tools directly
flake8
isort --check-only --diff
mypy custom_components/dual_smart_thermostat --ignore-missing-imports
```

CI enforcement:
- Add a CI job step to run `pre-commit` or individual linters (recommended: run `pre-commit run --all-files`). Fail the job if linters fail.
- Optionally add a fast check on PRs that runs `pre-commit run --hook-stage push` or `pre-commit run --from-ref origin/main --to-ref HEAD` to avoid long CI cycles.

Acceptance criteria:
- A `.pre-commit-config.yaml` exists in the repo root and `pre-commit` hooks are documented in `specs/001-develop-config-and/`.
- CI runs linters and fails on violations for PRs touching `custom_components/*` or `specs/*`.
- Developers can run `pre-commit run --all-files` and get a clean result on main branch after merging.

Current state: linters (`flake8`, `isort`, `codespell`, `mypy`) and `pre-commit` are already installed and the CI job to run linters is present in this repository. The policy below formalizes enforcement in the specs and points implementers to the existing configuration files.

Repository pointers:
- `.pre-commit-config.yaml` — root of repository (pre-commit hook definitions)
- `pyproject.toml` / `setup.cfg` — linter configuration (flake8/isort/mypy settings)

Enforcement policy (formalized):
- All PRs modifying `custom_components/*`, `specs/*`, or `tests/*` must pass the repository's linters in CI and locally via `pre-commit` prior to merge.
- If a linter rule needs to be changed (e.g., a false positive), open a small PR that updates the corresponding config in `pyproject.toml`/`setup.cfg` with a detailed justification and CI-green run.
- Merge blockers: failing linters in CI are blockers; only the CI bot or a maintainer may relax this after a documented exception in the PR.

### Migration Strategy for Advanced System Types

**If existing config entries use advanced system types**:
1. Add migration logic to handle existing `heater_cooler` and `heat_pump` entries
2. Provide clear user messaging about simplified system types
3. Suggest equivalent configurations using `simple_heater` (most cases) or `ac_only`
4. Preserve all feature settings during migration to minimize user impact

**Output**: Feature-complete config and options flows supporting `simple_heater` and `ac_only` with full test coverage and documentation.

## Phase 2: Implementation Execution Strategy

**Current approach**: Direct implementation of remaining tasks from the todo list, focusing on:
1. **Immediate (Phase 1A)**: Advanced system type removal and core polishing
2. **Near-term (Phase 1B)**: Contract tests, models.py, and options-parity validation
3. **Medium-term (Phase 1C)**: E2E Playwright scaffold and comprehensive UI testing
4. **Final (Phase 1D)**: Documentation updates and releSase preparation

**Ordering principles**:
- Test-first approach: Contract tests before implementation changes
- Risk mitigation: Remove advanced system types early to simplify maintenance
- User value: E2E tests provide confidence for production release
- Dependency resolution: Models and contracts before complex integration tests

**Estimated scope**: 12-15 focused tasks remaining (see todo list), executable in parallel streams for independent files

## Phase 3+: Future Implementation
*These phases are beyond the scope of the /plan command*

**Phase 3**: Task execution (/tasks command creates tasks.md)
**Phase 4**: Implementation (execute tasks.md following constitutional principles)
**Phase 5**: Validation (run tests, execute quickstart.md, performance validation)

## Complexity Tracking
*Fill ONLY if Constitution Check has violations that must be justified*

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |


## Progress Tracking
*This checklist is updated during execution flow*

**Phase Status**:
- [x] Phase 0: Research complete (canonical data models, implementation audit)
- [x] Phase 1: Design complete (feature-complete plan, E2E strategy, advanced system type removal plan)
- [x] Phase 2: Implementation approach defined (todo-driven execution, test-first approach)
- [ ] Phase 1A: E2E Playwright scaffold (highest priority — harden stable system types)
- [ ] Phase 1B: Advanced custom setup removal (immediate priority)
- [ ] Phase 1C: Complete remaining system types (medium-term priority)
- [ ] Phase 1D: Contract tests and models.py (ongoing priority)
- [ ] Phase 1E: Documentation and release prep (final priority)

**Gate Status**:
- [x] Initial Constitution Check: PASS (single integration, HA framework, centralized schemas)
- [x] Post-Design Constitution Check: PASS (TDD approach, contract tests planned)
- [x] All NEEDS CLARIFICATION resolved (data models canonical, implementation audited)
- [x] Feature-complete scope defined (all four system types, advanced custom setup removed, E2E priority)

---
*Based on Constitution v2.1.1 - See `/memory/constitution.md`*