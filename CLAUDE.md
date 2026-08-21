# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Dual Smart Thermostat - An enhanced thermostat component supporting multiple HVAC modes (heating, cooling, heat pump, fan, humidity control), advanced features (floor temperature control, window/door sensors, presets), and sophisticated control logic.

**Target**: Home Assistant 2026.3.2+ (dev/CI on 2026.7.4)
**Language**: Python 3.14

## Essential Commands

### Development with Docker (Recommended)

**IMPORTANT: For Claude Code development, always use Docker scripts for testing and linting to ensure consistent environment and avoid local Python dependency issues.**

The project provides convenient Docker scripts in the `scripts/` folder:

```bash
# Testing - Use docker-test for all test runs
./scripts/docker-test                              # Run all tests
./scripts/docker-test tests/test_heater_mode.py    # Run specific test file
./scripts/docker-test -k "heater"                  # Run tests matching pattern
./scripts/docker-test --cov                        # Run with coverage report
./scripts/docker-test --log-cli-level=DEBUG        # Run with debug logging

# Linting - Use docker-lint for all code quality checks (REQUIRED before commit)
./scripts/docker-lint                              # Check all linting (isort, black, flake8, codespell, ruff)
./scripts/docker-lint --fix                        # Auto-fix linting issues

# Interactive Shell - For debugging and exploration
./scripts/docker-shell                             # Open bash shell in container
./scripts/docker-shell python                      # Open Python REPL in container
```

**Why use Docker scripts:**
- Guaranteed consistent Python 3.13 + HA 2025.1.0+ environment
- No local dependency conflicts or version mismatches
- Same environment as CI/CD pipeline
- Automatic image building if needed
- Live source code mounting (changes reflected immediately)

### Local Development (Alternative)

If you prefer local development without Docker:

```bash
# Install dependencies
pip install -r requirements-dev.txt
pre-commit install

# Testing (local alternative)
pytest                                    # Run all tests
pytest tests/test_heater_mode.py          # Run specific test file
pytest --log-cli-level=DEBUG              # Run with debug logging

# Linting (local alternative - ALL must pass before commit)
isort . --check-only --diff               # Import sorting
black --check .                           # Code formatting
flake8 .                                  # Style/linting
codespell                                 # Spell checking
ruff check .                              # Additional linting

# Auto-fix linting issues (local)
isort .
black .
ruff check . --fix
```

### Advanced Docker Usage

```bash
# Build with specific Home Assistant version
HA_VERSION=2025.2.0 docker-compose build dev
HA_VERSION=latest docker-compose build dev

# Run custom commands in container
docker-compose run --rm dev <command>
```

## Architecture Overview

### Modular Design Pattern

The codebase uses a **separation of concerns** architecture with distinct layers:

1. **Device Layer** (`hvac_device/`) - Hardware abstraction for different HVAC equipment types
2. **Manager Layer** (`managers/`) - Shared business logic (features, state, environment)
3. **Controller Layer** (`hvac_controller/`) - Orchestration between devices and managers
4. **Climate Entity** (`climate.py`) - Home Assistant integration interface

### Configuration Flow (`config_flow.py`, `options_flow.py`)

Multi-step wizard for configuration with **feature-based step generation**:
- `feature_steps/` - Modular configuration steps for different features
- Steps are generated dynamically based on system type and enabled features
- **Critical**: Step ordering follows dependency chain (base → features → openings → presets)

## Key Architectural Patterns

### Factory Pattern
Device creation uses factory pattern in `hvac_device_factory.py`:
```python
device = HVACDeviceFactory.create_device(hass, config, hvac_mode)
```

### Manager Coordination
Managers work together through dependency injection:
```python
if self._opening_manager.is_any_opening_open():
    if self._feature_manager.is_floor_protection_enabled():
        # Complex feature interaction
```

### State Machine
Climate entity manages HVAC mode state transitions with validation and callbacks.

## Critical Development Rules

### Before You Write Code

1. State how you will verify this change (test, batch command, browser check, etc.)
2. Write the test verification step first
3. Then implement the code
4. Run verification and iterate until it passes

### Configuration Flow Integration

**CRITICAL**: Every added or modified configuration option MUST be integrated into the
appropriate configuration flows (config, reconfigure, and/or options). A parameter that
is not wired into a flow is unreachable for UI users.

Rule of thumb: needed during initial setup -> config + reconfigure flows; adjustable later
-> options flow; often both. Flow changes require tests in `tests/config_flow/`.

For the full procedure - which flow to update, how to add a step, validation, translations,
and a worked example - use the `config-flow-integration` skill.

### Configuration Dependencies

**CRITICAL**: When adding configuration parameters, update dependency tracking:

1. **Check for dependencies**: Does the new parameter require another parameter to function?
2. **Update tracking files**:
   - `tools/focused_config_dependencies.json` - Add conditional dependencies
   - `tools/config_validator.py` - Add validation rules
   - `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` - Document with examples
3. **Test validation**: `python tools/config_validator.py`

Example dependency: `max_floor_temp` requires `floor_sensor` to function.

### Configuration Flow Step Ordering

**CRITICAL**: Configuration steps MUST follow this order:

1. System type and basic entities (heater, cooler, sensors)
2. System-specific configuration (heat pump, dual stage)
3. Feature toggles (floor heating, fan, humidity)
4. Feature-specific configuration
5. **Openings configuration** (depends on system type and entities)
6. **Presets configuration** (depends on ALL previous configuration)

**Openings and presets must always be the last configuration steps** because they depend on all previously configured features.

See `docs/config_flow/step_ordering.md` for detailed rules.

### Linting Requirements

**ALL code MUST pass these checks before commit**:
- `isort` - Import sorting (configuration in `setup.cfg`)
- `black` - Code formatting (88 character line length)
- `flake8` - Style/linting (ignores configured in `setup.cfg`)
- `codespell` - Spell checking
- `ruff` - Additional linting checks

**Use `./scripts/docker-lint` to check all linting** (or `./scripts/docker-lint --fix` to auto-fix).

GitHub workflows will **reject** commits that fail linting.

## Testing Strategy

### Adding New Config Flow Tests

**Where to add your test:**

1. **Bug fixes or edge cases?**
   - **DO NOT** create separate bug fix test files
   - Add to relevant consolidated file:
     - Feature persistence issues → `test_options_flow.py`
     - System-specific persistence → appropriate `test_e2e_<system>_persistence.py`
     - Openings edge cases → `test_e2e_simple_heater_persistence.py`
     - Fan edge cases → `test_e2e_heater_cooler_persistence.py`

2. **New system type behavior?**
   - Add to system-specific test file or create new if needed
   - Keep system-specific files focused and clear

3. **New feature integration?**
   - Add to appropriate `test_<system>_features_integration.py`

4. **New reconfigure scenario?**
   - Add to `test_reconfigure_flow.py` or system-specific reconfigure file

**Pattern to follow:**
```python
@pytest.mark.asyncio
async def test_descriptive_name_of_what_youre_testing(hass):
    """Clear docstring explaining the test purpose and what it validates.

    If this was a bug fix, mention the original issue here.
    """
    # Test implementation using pytest patterns
    # Use hass fixture from pytest-homeassistant-custom-component
```

### Test Requirements
- **Every new feature MUST have tests** covering success and failure scenarios
- Use async test fixtures from `conftest.py`
- Follow existing test patterns for consistency
- **DO NOT create standalone bug fix test files** - integrate into existing tests
- **Consolidate related tests** - avoid creating many small test files

### Running Tests

**Use Docker scripts for all testing** (recommended):

```bash
# All tests
./scripts/docker-test

# Config flow tests only
./scripts/docker-test tests/config_flow/

# Single test file
./scripts/docker-test tests/config_flow/test_e2e_simple_heater_persistence.py

# Single test function
./scripts/docker-test tests/config_flow/test_options_flow.py::test_options_flow_fan_settings_prefilled

# With debug logging
./scripts/docker-test --log-cli-level=DEBUG tests/test_heater_mode.py

# With coverage report
./scripts/docker-test --cov
```

**Local alternative** (if not using Docker):
```bash
pytest                           # All tests
pytest tests/config_flow/        # Specific directory
pytest --log-cli-level=DEBUG     # With debug logging
```

Configuration: `pytest.ini` sets asyncio mode and test discovery patterns.

## Common Development Workflows

### Adding a New Feature

1. **Identify components**:
   - New device type? → Add to `hvac_device/`
   - Shared logic? → Add to or extend `managers/`
   - Control logic? → Modify `hvac_controller/`

2. **Add configuration**:
   - Constants to `const.py`
   - Schema to `schemas.py`
   - **Integrate into configuration flows** (see Configuration Flow Integration above)
     - Determine which flow(s) to update (config, reconfigure, options)
     - Add configuration steps to `feature_steps/` or flow files
     - Update flow navigation and validation
     - Update translations
   - **Update configuration dependencies** (see Configuration Dependencies above)

3. **Implement logic**:
   - Follow existing patterns
   - Use dependency injection for managers
   - Handle errors gracefully

4. **Add tests** (following consolidation guidelines):
   - **Core functionality**: Add to `tests/features/` or mode-specific test
   - **Config flow integration**: Add to appropriate `test_<system>_features_integration.py`
   - **Persistence**: Add test cases to relevant `test_e2e_<system>_persistence.py`
   - **Options flow**: Add to `test_options_flow.py` if needed
   - **DO NOT** create new small test files - add to existing consolidated tests
   - Cover success and failure cases
   - Test feature interactions

5. **Code quality** (use Docker scripts):
   - Run linting: `./scripts/docker-lint` (checks all linters)
   - Auto-fix linting: `./scripts/docker-lint --fix`
   - Run tests: `./scripts/docker-test`
   - Run specific tests: `./scripts/docker-test tests/features/`

### Modifying Existing Features

1. **Understand the change**: Read relevant code in device/manager/controller layers
2. **Check dependencies**: Identify which components are affected
3. **Update tests first**: Modify tests to reflect new behavior
4. **Implement changes**: Make minimal changes following existing patterns
5. **Verify** (use Docker scripts):
   - Run affected tests: `./scripts/docker-test tests/test_heater_mode.py`
   - Run full test suite: `./scripts/docker-test`
   - Check linting: `./scripts/docker-lint`

### Debugging HVAC Logic

The integration uses structured logging:
```python
_LOGGER.debug("Device operation details")  # Detailed flow
_LOGGER.info("State changes")              # Important events
_LOGGER.warning("Recoverable issues")      # Potential problems
_LOGGER.error("Failed operations")         # Errors
```

Enable debug logging in Home Assistant to trace execution flow.

## Important Constraints

### Backward Compatibility
- Never break existing YAML configurations
- Configuration migrations must be handled gracefully
- State restoration must handle old and new formats

### Home Assistant Integration
- Use Home Assistant's async patterns (`async def`, `await`)
- Respect entity lifecycle (setup, update, remove)
- Follow Home Assistant coding standards

### Device Safety
- Always check device availability before operations
- Handle sensor failures gracefully (stale detection)
- Respect min cycle durations to prevent equipment damage
- Floor temperature limits prevent overheating

## Special Considerations

### Heat Pump Mode
Single switch controls both heating and cooling based on `heat_pump_cooling` sensor state. Requires careful state tracking.

### Two-Stage Heating
Secondary heater activates after timeout if primary heater runs continuously. Day-based memory prevents premature secondary activation.

### Floor Temperature Protection
Min/max floor temperature limits prevent damage. These limits can be set globally and overridden per preset.

### Opening Detection
Window/door sensors pause HVAC operation. Supports timeout and closing_timeout for debouncing. Scope can be limited to specific HVAC modes.

### Preset Modes
Temperature/humidity presets depend on all other configuration. Must be configured last in flow.

### Fan Speed Control

Automatic capability detection drives variable-speed fan support. Design trade-offs and
test patterns live in `custom_components/dual_smart_thermostat/hvac_device/CLAUDE.md`,
loaded automatically when working in that directory.

### Development Rules for Claude Code

**CRITICAL - Testing and Linting Workflow:**

1. **Always use Docker scripts** for testing and linting:
   - `./scripts/docker-test` - Run tests (all or specific)
   - `./scripts/docker-lint` - Check all linting
   - `./scripts/docker-lint --fix` - Auto-fix linting issues
   - `./scripts/docker-shell` - Interactive debugging

2. **Before submitting code:**
   - Run `./scripts/docker-lint` to check all linting
   - Run `./scripts/docker-test` to verify tests pass
   - Fix any failures before showing code to user
   - Docker ensures consistent Python 3.13 + HA 2025.1.0+ environment

3. **Library documentation:**
   - Use context7 MCP tools for library/API documentation when needed
   - Automatically resolve library IDs and get docs without explicit user request

**Why Docker scripts are mandatory for Claude Code:**
- Consistent environment across all development sessions
- No local Python dependency conflicts
- Same environment as CI/CD pipeline
- Automatic dependency installation and caching

## Releases

While writing releases, focus on user value and key changes. Avoid technical jargon unless necessary.
