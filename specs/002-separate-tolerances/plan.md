# Implementation Plan: Separate Temperature Tolerances for Heating and Cooling Modes

**Branch**: `002-separate-tolerances` | **Date**: 2025-10-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-separate-tolerances/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement separate `heat_tolerance` and `cool_tolerance` optional configuration parameters that override legacy `cold_tolerance` and `hot_tolerance` when specified. Use priority-based tolerance selection in `environment_manager.py` based on current HVAC mode. Add UI fields to existing Advanced Settings step in options flow with 0.3°C defaults. Maintain 100% backward compatibility with existing configurations. Support all HVAC modes (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF) and all system types (simple_heater, ac_only, heat_pump, heater_cooler, dual_stage).

**Key Technical Approach**:
- Add two new configuration constants: `CONF_HEAT_TOLERANCE`, `CONF_COOL_TOLERANCE`
- Extend environment manager with mode-aware tolerance selection logic
- Climate entity passes current HVAC mode to environment manager
- Advanced Settings step in options flow includes new tolerance fields
- Comprehensive testing across all HVAC modes and system types

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Home Assistant 2025.1.0+, voluptuous (schema validation)
**Storage**: Home Assistant config entries (persistent JSON storage)
**Testing**: pytest with pytest-homeassistant-custom-component==0.13.224, async fixtures
**Target Platform**: Home Assistant integration (Linux/Docker/HAOS)
**Project Type**: Home Assistant Custom Component (single integration package)
**Performance Goals**: <10ms tolerance selection (called on every sensor update), zero impact on HVAC cycle timing
**Constraints**: Must pass isort/black/flake8/codespell, 100% backward compatibility, min_cycle_duration safety maintained
**Scale/Scope**: 25 functional requirements, 4 user stories, affects 7 core files (const.py, schemas.py, environment_manager.py, climate.py, options_flow.py, translations/en.json, config_validator.py), ~15 test files

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Configuration Flow Mandation (NON-NEGOTIABLE)
**Status**: ✅ PASS (with implementation requirement)

**Requirements**:
- [x] New parameters (`heat_tolerance`, `cool_tolerance`) will be added to `const.py`
- [x] New parameters will appear in options flow (Advanced Settings step)
- [x] Translations will be added to `translations/en.json`
- [x] Tests will cover step handler, validation, and persistence
- [x] Dependencies tracked in `tools/focused_config_dependencies.json`

**Implementation Plan**:
- Add `CONF_HEAT_TOLERANCE` and `CONF_COOL_TOLERANCE` to `const.py`
- Modify existing `async_step_advanced` in `options_flow.py` to include new fields
- Update `ADVANCED_SCHEMA` in `schemas.py` with tolerance fields
- Add translations with clear override behavior descriptions
- Write unit tests for validation and E2E tests for persistence

### II. Test-Driven Development (NON-NEGOTIABLE)
**Status**: ✅ PASS (with comprehensive test plan)

**Requirements**:
- [x] Unit tests for `environment_manager.py` tolerance selection logic
- [x] Config flow tests in `tests/config_flow/test_options_flow.py`
- [x] E2E persistence tests in existing `test_e2e_*_persistence.py` files (4 system types)
- [x] Integration tests in `test_*_features_integration.py` files (4 system types)
- [x] Functional tests in `tests/test_heater_mode.py`, `tests/test_cooler_mode.py`, etc.
- [x] All existing tests must continue to pass

**Test Consolidation Strategy**:
- Add tolerance selection unit tests to `tests/managers/test_environment_manager.py`
- Add options flow tests to existing `tests/config_flow/test_options_flow.py`
- Add E2E tests to consolidated `test_e2e_*_persistence.py` files
- Add integration tests to existing `test_*_features_integration.py` files
- NO new standalone test files created

### III. Backward Compatibility (NON-NEGOTIABLE)
**Status**: ✅ PASS (explicit requirement)

**Requirements**:
- [x] Existing `cold_tolerance` and `hot_tolerance` configurations work unchanged
- [x] Default values of 0.3°C maintain current behavior
- [x] New parameters are optional (opt-in pattern)
- [x] Priority hierarchy ensures legacy fallback: mode-specific → legacy → DEFAULT_TOLERANCE
- [x] No migration scripts required
- [x] State restoration handles both old and new formats

**Backward Compatibility Strategy**:
- Priority 1: Use `heat_tolerance` or `cool_tolerance` if specified
- Priority 2: Fall back to `cold_tolerance` + `hot_tolerance` (legacy)
- Priority 3: Fall back to `DEFAULT_TOLERANCE` (0.3°C)
- Tolerance selection happens at runtime, no config conversion needed

### IV. Code Quality Standards (NON-NEGOTIABLE)
**Status**: ✅ PASS (standard requirement)

**Requirements**:
- [x] All code will pass `isort` (import sorting)
- [x] All code will pass `black` (formatting, 88 char line length)
- [x] All code will pass `flake8` (linting)
- [x] All code will pass `codespell` (spell checking)
- [x] Pre-commit hooks will be run before commits

### V. Dependency Tracking (MANDATORY)
**Status**: ✅ PASS (with implementation requirement)

**Requirements**:
- [x] Update `tools/focused_config_dependencies.json` with new parameters
- [x] Document in `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`
- [x] Update `tools/config_validator.py` with validation rules
- [x] `python tools/config_validator.py` must pass

**Dependency Documentation**:
- `heat_tolerance`: Optional, no dependencies, overrides legacy for HEAT mode
- `cool_tolerance`: Optional, no dependencies, overrides legacy for COOL mode
- `cold_tolerance`: Defaults to 0.3, serves as fallback for heating
- `hot_tolerance`: Defaults to 0.3, serves as fallback for cooling

### VI. Modular Architecture
**Status**: ✅ PASS (follows established patterns)

**Architecture Compliance**:
- Device logic: No changes to `hvac_device/` (devices call environment manager)
- Manager logic: Tolerance selection in `managers/environment_manager.py`
- Controller logic: No changes needed (controllers use environment manager)
- Entity interface: `climate.py` passes HVAC mode to environment manager
- Dependency injection: Environment manager injected into devices/controllers
- Cross-layer flow: climate.py → environment_manager.py → devices

### Configuration Flow Step Ordering
**Status**: ✅ PASS (no new steps, existing step modified)

**Compliance**:
- Tolerance settings added to existing Advanced Settings step (step 4: feature-specific configuration)
- No impact on step ordering (openings and presets remain last)
- No new dependencies created

### Overall Constitution Verdict
**Status**: ✅ APPROVED - All gates pass. Implementation may proceed.

**Summary**: Feature fully complies with all constitutional principles. No complexity violations. Standard development workflow applies.

## Project Structure

### Documentation (this feature)

```text
specs/002-separate-tolerances/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── tolerance_selection_api.md  # Tolerance selection interface contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Home Assistant Custom Component Structure
custom_components/dual_smart_thermostat/
├── const.py                          # +CONF_HEAT_TOLERANCE, +CONF_COOL_TOLERANCE
├── schemas.py                        # +ADVANCED_SCHEMA tolerance fields
├── climate.py                        # +pass hvac_mode to environment manager
├── options_flow.py                   # +modify async_step_advanced
├── managers/
│   └── environment_manager.py        # +tolerance selection logic
├── config_flow/
│   └── [no changes]                  # Advanced settings already in options flow
├── feature_steps/
│   └── [no changes]                  # No new steps needed
├── translations/
│   └── en.json                       # +tolerance field descriptions
└── [other files unchanged]

tests/
├── managers/
│   └── test_environment_manager.py   # +tolerance selection unit tests
├── config_flow/
│   ├── test_options_flow.py          # +advanced settings tolerance tests
│   ├── test_e2e_simple_heater_persistence.py    # +tolerance persistence
│   ├── test_e2e_ac_only_persistence.py          # +tolerance persistence
│   ├── test_e2e_heat_pump_persistence.py        # +tolerance persistence
│   ├── test_e2e_heater_cooler_persistence.py    # +tolerance persistence
│   ├── test_simple_heater_features_integration.py   # +tolerance integration
│   ├── test_ac_only_features_integration.py         # +tolerance integration
│   ├── test_heat_pump_features_integration.py       # +tolerance integration
│   └── test_heater_cooler_features_integration.py   # +tolerance integration
├── test_heater_mode.py               # +heat_tolerance functional tests
├── test_cooler_mode.py               # +cool_tolerance functional tests
├── test_heat_pump_mode.py            # +heat/cool mode switching tests
└── [other tests unchanged]

tools/
├── focused_config_dependencies.json  # +heat_tolerance, cool_tolerance entries
└── config_validator.py               # +tolerance validation rules

docs/config/
└── CRITICAL_CONFIG_DEPENDENCIES.md   # +tolerance documentation
```

**Structure Decision**: This is a Home Assistant custom component with established modular architecture. Changes are localized to 7 core files and ~15 test files. The existing structure of `hvac_device/`, `managers/`, `hvac_controller/`, and configuration flows is maintained. No new directories or major structural changes required.

## Complexity Tracking

> **No violations - this section intentionally left empty**

All constitution requirements are met without complexity violations. Feature follows standard development patterns for the project.

---

## Phase 0: Research & Unknowns

**Objective**: Resolve all technical unknowns and document design decisions.

### Research Tasks

#### 1. Environment Manager HVAC Mode Tracking
**Question**: How should environment manager receive current HVAC mode?

**Investigation**:
- Review `managers/environment_manager.py` API
- Review how climate entity interacts with environment manager
- Determine if mode should be passed per-call or stored as state

**Decision Criteria**:
- Minimal API changes preferred
- Must support immediate mode switching (no stale state)
- Must work with all device types

#### 2. Tolerance Selection Algorithm
**Question**: What is the exact algorithm for tolerance selection including all edge cases?

**Investigation**:
- Review current `is_too_cold()` and `is_too_hot()` implementations
- Map tolerance selection for each HVAC mode (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF)
- Define behavior when sensors unavailable

**Decision Criteria**:
- Must be deterministic and testable
- Must handle partial configuration (only heat_tolerance set, only cool_tolerance set)
- Must handle FAN_ONLY and DRY modes appropriately

#### 3. Options Flow Advanced Settings Integration
**Question**: How to add fields to existing Advanced Settings step without breaking existing flow?

**Investigation**:
- Review `options_flow.py` `async_step_advanced` implementation
- Review how optional fields are handled in schema
- Determine if step ordering or navigation logic needs changes

**Decision Criteria**:
- Must not break existing advanced settings functionality
- Must support pre-filling current values
- Must handle legacy configurations (no heat/cool tolerance set)

#### 4. Configuration Persistence Strategy
**Question**: How to store optional tolerance values in config entries?

**Investigation**:
- Review existing optional parameter handling
- Review state restoration for optional values
- Determine if None vs absence distinction matters

**Decision Criteria**:
- Must persist through restart cycles
- Must support absence of values (not just None)
- Must work with existing state restoration

#### 5. Testing Strategy for All System Types
**Question**: What is the minimum test coverage to verify all system types work correctly?

**Investigation**:
- Review existing E2E persistence test patterns
- Review existing integration test patterns
- Identify representative test cases that cover all modes and system types

**Decision Criteria**:
- Must test all 4 system types (simple_heater, ac_only, heat_pump, heater_cooler)
- Must test all relevant HVAC modes for each system type
- Must test backward compatibility scenarios

**Output**: `research.md` with decisions documented

---

## Phase 1: Design & Contracts

**Prerequisites:** Phase 0 research complete

### 1. Data Model (`data-model.md`)

**Entities**:

**ConfigurationEntry** (extended)
- **Existing Attributes**:
  - `cold_tolerance`: float, defaults to 0.3
  - `hot_tolerance`: float, defaults to 0.3
- **New Attributes**:
  - `heat_tolerance`: Optional[float], range 0.1-5.0
  - `cool_tolerance`: Optional[float], range 0.1-5.0
- **Validation Rules**:
  - If `heat_tolerance` specified: 0.1 ≤ heat_tolerance ≤ 5.0
  - If `cool_tolerance` specified: 0.1 ≤ cool_tolerance ≤ 5.0
  - No enforced relationship between heat and cool tolerances
- **State Transitions**: None (configuration is static until user modifies)

**EnvironmentManager** (internal state)
- **New State**:
  - `current_hvac_mode`: HVACMode enum
- **Behavior**:
  - Mode updated when climate entity HVAC mode changes
  - Tolerance selection uses current mode to determine priority

**ToleranceSelection** (algorithm)
- **Input**: current_hvac_mode, heat_tolerance, cool_tolerance, cold_tolerance, hot_tolerance
- **Output**: active_tolerance (float)
- **Logic**: Priority-based selection (documented in contracts/)

### 2. API Contracts (`contracts/`)

**File**: `contracts/tolerance_selection_api.md`

Define the interface contract for:
- `EnvironmentManager.set_hvac_mode(mode: HVACMode) -> None`
- `EnvironmentManager.get_active_tolerance() -> float`
- `EnvironmentManager.is_too_cold(temp: float, target: float) -> bool`
- `EnvironmentManager.is_too_hot(temp: float, target: float) -> bool`

Include:
- Method signatures
- Parameter types and validation
- Return types
- Error conditions
- Tolerance selection algorithm pseudocode
- Examples for each HVAC mode

### 3. Quickstart Guide (`quickstart.md`)

**Content**:
- Feature overview (what separate tolerances enable)
- Configuration examples:
  - Legacy configuration (backward compatibility)
  - Simple override (tight heating, loose cooling)
  - Partial override (only cool_tolerance)
  - All modes coverage (HEAT, COOL, HEAT_COOL, FAN_ONLY)
- Testing guide:
  - Running unit tests
  - Running integration tests
  - Manual testing procedure
- Development workflow:
  - Making changes to tolerance logic
  - Adding tests
  - Verifying backward compatibility

### 4. Agent Context Update

Run `.specify/scripts/bash/update-agent-context.sh claude` to update `.specify/memory/agent.claude.md` with:
- Tolerance selection feature overview
- Key files modified
- Testing strategy
- Common pitfalls and debugging tips

**Output**: `data-model.md`, `contracts/tolerance_selection_api.md`, `quickstart.md`, `.specify/memory/agent.claude.md` updated

---

## Phase 2: Task Generation

**Prerequisites:** Phase 1 design complete, Constitution Check re-validated

**Note**: Phase 2 (task generation) is performed by the `/speckit.tasks` command, NOT by `/speckit.plan`.

This plan provides the foundation for task generation:
- Technical context is fully specified
- Design decisions are documented
- Contracts define clear interfaces
- Test strategy is comprehensive

The `/speckit.tasks` command will use this plan to generate `tasks.md` with dependency-ordered, actionable implementation tasks.

---

## Re-evaluation: Constitution Check (Post-Design)

*GATE: Must pass after Phase 1 design before task generation.*

### I. Configuration Flow Mandation
**Status**: ✅ PASS

**Design Validation**:
- Constants added: `CONF_HEAT_TOLERANCE`, `CONF_COOL_TOLERANCE` in `const.py`
- Schema extended: `ADVANCED_SCHEMA` in `schemas.py` includes tolerance fields
- Flow modified: `async_step_advanced` in `options_flow.py` handles new fields
- Translations added: `en.json` includes field descriptions and help text
- Tests planned: Unit, integration, and E2E tests cover all flow scenarios
- Dependencies tracked: `focused_config_dependencies.json` updated

### II. Test-Driven Development
**Status**: ✅ PASS

**Design Validation**:
- Unit tests: `test_environment_manager.py` covers tolerance selection algorithm
- Config flow tests: `test_options_flow.py` covers advanced settings modifications
- E2E persistence tests: All 4 system types covered in existing E2E files
- Integration tests: All 4 system types covered in integration files
- Functional tests: Mode-specific tests added to existing test files
- Test consolidation: No new test files created, using existing consolidated structure

### III. Backward Compatibility
**Status**: ✅ PASS

**Design Validation**:
- Legacy configurations work unchanged (priority hierarchy ensures fallback)
- Default values (0.3°C) match current behavior
- Optional parameters use opt-in pattern (None when not specified)
- No migration required (runtime tolerance selection handles all cases)
- State restoration supports old and new formats

### IV. Code Quality Standards
**Status**: ✅ PASS

**Design Validation**:
- All Python code follows Home Assistant style guidelines
- Import organization with isort
- Formatting with black (88 char)
- Linting with flake8
- Spell checking with codespell

### V. Dependency Tracking
**Status**: ✅ PASS

**Design Validation**:
- `focused_config_dependencies.json` includes new parameters
- `CRITICAL_CONFIG_DEPENDENCIES.md` documents tolerance relationships
- `config_validator.py` validates tolerance value ranges
- No complex dependencies (parameters are independent)

### VI. Modular Architecture
**Status**: ✅ PASS

**Design Validation**:
- Changes localized to appropriate layers
- Manager layer handles tolerance selection logic
- Entity layer passes mode to manager
- Configuration flow layer handles UI
- No cross-layer violations

### Overall Post-Design Verdict
**Status**: ✅ APPROVED - Design complies with all constitutional principles. Ready for task generation.

---

## Next Steps

1. Review this plan for completeness and accuracy
2. Execute Phase 0 research to resolve unknowns
3. Execute Phase 1 design to generate data model and contracts
4. Re-validate Constitution Check after design
5. Run `/speckit.tasks` to generate actionable implementation tasks
6. Begin implementation following generated tasks

**Estimated Timeline**:
- Phase 0 Research: 1-2 hours
- Phase 1 Design: 2-3 hours
- Phase 2 Task Generation: Automated (via `/speckit.tasks`)
- Implementation: 11-17 hours (per spec estimate)

**Deliverables from `/speckit.plan`**:
- ✅ `plan.md` (this file) - Complete
- ⏳ `research.md` - Generated in Phase 0
- ⏳ `data-model.md` - Generated in Phase 1
- ⏳ `contracts/` - Generated in Phase 1
- ⏳ `quickstart.md` - Generated in Phase 1
- ⏳ Agent context updated - Generated in Phase 1
- ❌ `tasks.md` - Generated by `/speckit.tasks` (not this command)
