<!--
Sync Impact Report:
- Version Change: N/A → 1.0.0
- Initial constitution establishment
- Principles defined:
  1. Configuration Flow Mandation (new)
  2. Test-Driven Development (new)
  3. Backward Compatibility (new)
  4. Code Quality Standards (new)
  5. Dependency Tracking (new)
  6. Modular Architecture (new)
- Templates Alignment:
  ✅ plan-template.md - Constitution Check section aligns with principles
  ✅ spec-template.md - User stories and testing align with TDD principle
  ✅ tasks-template.md - Task organization aligns with architecture principle
  ✅ agent-file-template.md - Generic template, no agent-specific references
- Follow-up Actions: None
-->

# Home Assistant Dual Smart Thermostat Constitution

## Core Principles

### I. Configuration Flow Mandation (NON-NEGOTIABLE)

Every configuration parameter MUST be integrated into appropriate configuration flows (config, reconfigure, or options flows). This is mandatory for all configuration changes.

**Rules:**
- New parameters in `const.py` or `schemas.py` MUST appear in UI flows
- Parameters requiring initial setup MUST be in config/reconfigure flows
- Parameters users may adjust later MUST be in options flows
- All flow changes MUST include translations in `translations/en.json`
- All flow changes MUST be tested with unit tests and integration tests
- Configuration dependencies MUST be tracked in `tools/focused_config_dependencies.json`

**Rationale:** Home Assistant integrations are user-facing products. Configuration that cannot be set through the UI creates a poor user experience and violates Home Assistant integration standards.

### II. Test-Driven Development (NON-NEGOTIABLE)

Comprehensive testing MUST precede and validate all implementations. Tests are not optional.

**Rules:**
- Unit tests MUST exist for all new logic in `managers/`, `hvac_device/`, and `hvac_controller/`
- Config flow tests MUST exist for all UI changes in `tests/config_flow/`
- E2E persistence tests MUST verify configuration survives restarts
- Integration tests MUST verify feature combinations work correctly
- All existing tests MUST pass before any commit
- Test consolidation MUST be preferred over creating many small test files
- Tests MUST follow pytest patterns and use fixtures from `conftest.py`

**Rationale:** The thermostat controls physical HVAC equipment. Bugs can cause equipment damage, energy waste, or user discomfort. Comprehensive testing prevents regressions and ensures safety.

### III. Backward Compatibility (NON-NEGOTIABLE)

Existing user configurations MUST continue to work without modification after any update.

**Rules:**
- YAML configurations MUST maintain backward compatibility
- Configuration migrations MUST handle old and new formats gracefully
- State restoration MUST support old state formats
- Deprecated parameters MAY be removed only after multi-version deprecation period
- Breaking changes MUST be explicitly versioned and documented
- Default values MUST maintain existing behavior when parameters are not specified
- New optional parameters MUST use opt-in pattern, not opt-out

**Rationale:** Users rely on their thermostat configurations for home comfort. Breaking existing configurations violates user trust and Home Assistant integration quality standards.

### IV. Code Quality Standards (NON-NEGOTIABLE)

All code MUST pass linting and formatting checks before commit.

**Rules:**
- `isort` MUST pass (import sorting, configuration in `setup.cfg`)
- `black` MUST pass (code formatting, 88 character line length)
- `flake8` MUST pass (style/linting, ignores configured in `setup.cfg`)
- `codespell` MUST pass (spell checking)
- `pre-commit run --all-files` MUST pass before any commit
- GitHub workflow rejections for linting failures MUST be fixed immediately

**Rationale:** Consistent code style reduces cognitive load during code review and maintenance. Automated quality checks prevent trivial issues from consuming reviewer time.

### V. Dependency Tracking (MANDATORY)

Configuration parameter dependencies MUST be documented and validated.

**Rules:**
- New parameters with dependencies MUST update `tools/focused_config_dependencies.json`
- Dependencies MUST be documented in `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` with examples
- Validation rules MUST be added to `tools/config_validator.py`
- `python tools/config_validator.py` MUST pass before any configuration change is committed
- Conditional dependencies (e.g., `max_floor_temp` requires `floor_sensor`) MUST be explicitly tracked

**Rationale:** Configuration parameters often have complex interdependencies. Explicit tracking prevents invalid configurations and helps users understand parameter relationships.

### VI. Modular Architecture

Code MUST follow the established layered architecture with clear separation of concerns.

**Rules:**
- Device logic MUST reside in `hvac_device/` (hardware abstraction)
- Shared business logic MUST reside in `managers/` (features, state, environment)
- Orchestration logic MUST reside in `hvac_controller/` (coordination)
- Home Assistant integration MUST reside in `climate.py` (entity interface)
- Factory pattern MUST be used for device creation (`hvac_device_factory.py`)
- Managers MUST use dependency injection pattern
- Cross-layer dependencies MUST flow downward (entity → controller → device/managers)

**Rationale:** Layered architecture enables independent testing of components, simplifies reasoning about code, and facilitates feature additions without cascading changes.

## Configuration Flow Requirements

### Step Ordering (MANDATORY)

Configuration steps MUST follow this dependency order:

1. System type and basic entities (heater, cooler, sensors)
2. System-specific configuration (heat pump, dual stage)
3. Feature toggles (floor heating, fan, humidity)
4. Feature-specific configuration
5. **Openings configuration** (depends on system type and entities)
6. **Presets configuration** (depends on ALL previous configuration)

**Openings and presets MUST always be the last configuration steps** because they depend on all previously configured features.

**Reference:** `docs/config_flow/step_ordering.md` contains detailed step ordering rules.

### Flow Integration Process (MANDATORY)

When adding or modifying configuration parameters:

1. **Add constants and schema** in `const.py` and appropriate schema file
2. **Add configuration step** in `feature_steps/` or existing flow file if needed
3. **Update flow navigation** in `config_flow.py` or `options_flow.py` via `_determine_next_step()`
4. **Add data validation** with clear error messages
5. **Update translations** in `translations/en.json`
6. **Write tests** covering step handler, validation, persistence, and edge cases

### Testing Requirements (MANDATORY)

Flow changes MUST include:

1. **Unit Tests** in `tests/config_flow/` testing step handler logic, validation, and error handling
2. **Integration Tests** testing complete flows with new option and persistence
3. **E2E Tests** added to existing `test_e2e_*_persistence.py` files for all system types
4. **Manual Testing** with initial config, reconfigure, and options flows

## Testing Strategy

### Test Organization (MANDATORY)

- **Core functionality tests**: `tests/test_<mode>_mode.py` for mode-specific functionality
- **Config flow tests**: `tests/config_flow/` organized by flow type and system type
- **Feature tests**: `tests/features/` for feature-specific logic
- **Preset tests**: `tests/presets/` for preset functionality
- **Opening tests**: `tests/openings/` for window/door sensor handling

### Test Consolidation (PREFERRED)

- Add tests to existing consolidated files rather than creating new small test files
- Bug fix tests MUST be added to relevant consolidated files, not separate bug-specific files
- E2E persistence tests MUST be added to appropriate `test_e2e_<system>_persistence.py` files
- Options flow tests MUST be added to `test_options_flow.py` when possible

### Test Patterns (MANDATORY)

- Use async test fixtures from `conftest.py`
- Follow existing pytest patterns for consistency
- Include clear docstrings explaining test purpose
- Cover success and failure scenarios
- Test feature interactions, not just isolated features

## Development Workflow

### Adding New Features

1. Identify component layer (device/manager/controller/entity)
2. Add configuration constants and schema
3. **Integrate into configuration flows** (config, reconfigure, and/or options)
4. **Update configuration dependencies** tracking
5. Implement logic following existing patterns
6. Write comprehensive tests (unit, integration, E2E)
7. Run linting: `isort .`, `black .`, `flake8 .`, `codespell`
8. Run tests: `pytest`
9. Run pre-commit: `pre-commit run --all-files`

### Modifying Existing Features

1. Understand the change and identify affected components
2. Check configuration dependencies and update if needed
3. Update tests first to reflect new behavior (TDD)
4. Implement changes with minimal modifications
5. Verify all affected tests pass and full test suite passes
6. Run linting and pre-commit checks

### Debugging HVAC Logic

Use structured logging at appropriate levels:
- `_LOGGER.debug()` - Detailed flow and variable values
- `_LOGGER.info()` - State changes and important events
- `_LOGGER.warning()` - Recoverable issues and potential problems
- `_LOGGER.error()` - Failed operations and errors

Enable debug logging in Home Assistant configuration to trace execution flow.

## Important Constraints

### Home Assistant Integration

- Use Home Assistant's async patterns (`async def`, `await`)
- Respect entity lifecycle (setup, update, remove)
- Follow Home Assistant coding standards and integration quality requirements
- Target Home Assistant 2025.1.0+ and Python 3.13

### Device Safety

- Always check device availability before operations
- Handle sensor failures gracefully (stale detection via `sensor_stale_duration`)
- Respect `min_cycle_duration` to prevent equipment damage from rapid cycling
- Floor temperature limits (`max_floor_temp`, `min_floor_temp`) prevent overheating/undercooling

### Performance

- Tolerance checks happen frequently (every sensor update) - keep logic efficient
- Avoid complex computations in hot paths
- State tracking must have minimal overhead
- No blocking operations in async methods

## Governance

This constitution supersedes all other development practices and documentation. All code changes, pull requests, and reviews MUST verify compliance with these principles.

**Amendment Process:**
- Amendments require documented justification and impact analysis
- Breaking changes to principles require MAJOR version increment
- New principles or expanded guidance require MINOR version increment
- Clarifications and wording improvements require PATCH version increment
- Amendments MUST be propagated to all dependent templates and documentation

**Compliance Review:**
- All PRs MUST demonstrate adherence to configuration flow mandation
- All PRs MUST include tests as required by TDD principle
- All PRs MUST pass linting and code quality checks
- All PRs MUST maintain backward compatibility or explicitly version breaking changes
- Complexity MUST be justified with clear rationale in PR description

**Runtime Development Guidance:**
See `CLAUDE.md` for comprehensive development guidelines, architecture patterns, and detailed examples of applying these principles in practice.

**Version**: 1.0.0 | **Ratified**: 2025-10-29 | **Last Amended**: 2025-10-29
