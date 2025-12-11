# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Dual Smart Thermostat - An enhanced thermostat component supporting multiple HVAC modes (heating, cooling, heat pump, fan, humidity control), advanced features (floor temperature control, window/door sensors, presets), and sophisticated control logic.

**Target**: Home Assistant 2025.1.0+
**Language**: Python 3.13

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

### Code Quality Requirements

**ALL code MUST pass linting checks before commit:**
- `isort` - Import sorting
- `black` - Code formatting (88 character line length)
- `flake8` - Style/linting
- `codespell` - Spell checking
- `ruff` - Additional linting

**Run `./scripts/docker-lint` before committing. GitHub workflows will reject failing commits.**

## Architecture Overview

### Modular Design Pattern

The codebase uses a **separation of concerns** architecture with distinct layers:

1. **Device Layer** (`hvac_device/`) - Hardware abstraction for different HVAC equipment types
2. **Manager Layer** (`managers/`) - Shared business logic (features, state, environment)
3. **Controller Layer** (`hvac_controller/`) - Orchestration between devices and managers
4. **Climate Entity** (`climate.py`) - Home Assistant integration interface

### Core Components

#### Device Types (`hvac_device/`)
Abstraction layer for different HVAC equipment:
- `heater_device.py` - Basic heating
- `cooler_device.py` - Air conditioning
- `heat_pump_device.py` - Combined heating/cooling (single switch)
- `heater_cooler_device.py` - Dual heating/cooling (separate switches)
- `heater_aux_heater_device.py` - Two-stage heating
- `fan_device.py` - Fan-only operation
- `dryer_device.py` - Humidity control
- `hvac_device_factory.py` - **Factory pattern** creates appropriate device based on configuration

#### Managers (`managers/`)
Shared logic components handling specific responsibilities:
- `state_manager.py` - Persistence and state restoration
- `environment_manager.py` - Environmental condition tracking (temperature, humidity, sensors)
- `feature_manager.py` - Feature enablement and configuration
- `opening_manager.py` - Window/door sensor handling
- `preset_manager.py` - Preset mode management
- `hvac_power_manager.py` - Power cycling and keep-alive logic

#### Controllers (`hvac_controller/`)
Orchestration of control logic:
- `generic_controller.py` - Base controller with common logic
- `heater_controller.py` - Heating-specific control
- `cooler_controller.py` - Cooling-specific control
- `hvac_controller.py` - Top-level coordinator

#### HVAC Action Reasons (`hvac_action_reason/`)
Tracking and reporting why HVAC actions occur:
- `hvac_action_reason_internal.py` - System-triggered reasons (temp reached, opening detected, etc.)
- `hvac_action_reason_external.py` - User/automation-triggered reasons (schedule, presence, emergency)

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

### Configuration Flow Integration

**CRITICAL**: Every added or modified configuration option MUST be integrated into the appropriate configuration flows (config, reconfigure, or options flows). This is mandatory for all configuration changes.

#### When Flow Integration is Required

Flow integration is required whenever you:
1. Add a new configuration parameter to `const.py` or `schemas.py`
2. Modify an existing configuration parameter's behavior or validation
3. Add a new feature that requires user configuration
4. Change how configuration options interact with each other

#### Which Flow(s) to Update

Determine which flow(s) need updates based on the type of change:

1. **Initial Configuration Flow** (`config_flow.py`):
   - New system types or HVAC modes
   - New required entities (heater, cooler, sensors)
   - New features that should be configured during initial setup
   - Core system behavior changes

2. **Reconfigure Flow** (`config_flow.py` - reconfigure handlers):
   - Changes to existing system configuration that require reconfiguration
   - System type switching
   - Entity replacement or updates
   - Any change that affects the initial configuration flow

3. **Options Flow** (`options_flow.py`):
   - Feature toggles (enabling/disabling features)
   - Feature-specific settings (thresholds, timeouts, behaviors)
   - Preset configurations
   - Advanced settings that don't require reconfiguration
   - Any setting that users might want to change after initial setup

**Rule of Thumb**: If users need to configure it during initial setup, add it to config/reconfigure flows. If users might want to adjust it later, add it to options flow. Often, you'll need to add to both.

#### How to Integrate Changes into Flows

Follow this process to integrate configuration changes:

1. **Add Constants and Schema**:
   ```python
   # In const.py - Add configuration key constant
   CONF_NEW_FEATURE = "new_feature"

   # In schemas.py - Add to appropriate schema
   NEW_FEATURE_SCHEMA = vol.Schema({
       vol.Optional(CONF_NEW_FEATURE, default=False): cv.boolean,
   })
   ```

2. **Add Configuration Step** (if needed):
   ```python
   # In feature_steps/ - Create new step file if complex feature
   # Or add to existing step file

   async def async_step_new_feature(self, user_input=None):
       """Handle new feature configuration."""
       # Follow existing patterns from other step handlers
   ```

3. **Update Flow Navigation**:
   ```python
   # In config_flow.py or options_flow.py
   # Update _determine_next_step() or flow handler to include new step
   # Ensure proper step ordering (see Step Ordering section)
   ```

4. **Add Data Validation**:
   ```python
   # Add validation logic in step handler
   # Follow existing validation patterns
   # Provide clear error messages
   ```

5. **Update Translations**:
   ```json
   // In translations/en.json
   "step": {
       "new_feature": {
           "title": "Configure New Feature",
           "description": "Description of what this configures",
           "data": {
               "new_feature": "Enable new feature"
           }
       }
   }
   ```

#### Testing Flow Integration

**REQUIRED**: All flow changes must be tested:

1. **Unit Tests**: Add to `tests/config_flow/`
   - Test step handler logic
   - Test validation
   - Test error handling

2. **Integration Tests**: Add to appropriate integration test file
   - Test complete flow with new option
   - Test persistence (config → options flow)
   - Test edge cases

3. **Manual Testing**:
   - Test initial configuration flow
   - Test reconfigure flow (if applicable)
   - Test options flow with existing configurations
   - Test with different system types

#### Example Flow Integration

When adding a new floor temperature feature:

```python
# 1. Add to const.py
CONF_MAX_FLOOR_TEMP = "max_floor_temp"

# 2. Add to schemas.py
FLOOR_TEMP_SCHEMA = vol.Schema({
    vol.Optional(CONF_MAX_FLOOR_TEMP): vol.Coerce(float),
})

# 3. Add step in feature_steps/floor_heating_steps.py
async def async_step_floor_heating(self, user_input=None):
    """Configure floor heating options."""
    if user_input is not None:
        # Validate and store
        return self.async_create_entry(...)

    # Show form with floor temp options
    return self.async_show_form(...)

# 4. Update navigation in config_flow.py
def _determine_next_step(self):
    if self._has_floor_sensor():
        return "floor_heating"  # Add to flow sequence
    return "next_step"

# 5. Add tests in tests/config_flow/test_floor_heating_integration.py
async def test_floor_heating_config_flow():
    """Test floor heating configuration in flow."""
    # Test implementation
```

#### Clarification Process

If it's unclear how to integrate a configuration change into the flows:

1. **Analyze the Feature**:
   - What does this configuration control?
   - Is it a core feature or an optional enhancement?
   - Does it depend on other configuration?

2. **Review Similar Features**:
   - Find similar existing features in the codebase
   - Review their flow integration
   - Follow the same patterns

3. **Check Dependencies**:
   - Does this feature require other configuration first?
   - Should it be in the main flow or a separate step?
   - Where should it appear in the step ordering?

4. **Ask for Clarification**:
   - If still unclear, document your analysis
   - Ask specifically: "Should this be in config or options flow?"
   - Provide context about the feature and its dependencies

**Remember**: When in doubt, add to both config/reconfigure AND options flows to provide maximum flexibility.

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

### Test Organization

The test suite is organized by functionality with a focus on consolidation and maintainability:

#### Core Functionality Tests
- `tests/test_<mode>_mode.py` - Mode-specific functionality (heater, cooler, heat pump, fan, dry, dual)
- `tests/presets/` - Preset functionality tests
- `tests/openings/` - Opening detection tests
- `tests/features/` - Feature-specific tests
- `tests/conftest.py` - Pytest fixtures and test utilities

#### Config Flow Tests (`tests/config_flow/`)

**IMPORTANT**: The config flow tests have been consolidated to reduce duplication. When adding new tests:

1. **Core Flow Tests** - General configuration and options flow behavior
   - `test_config_flow.py` - Basic config flow, system type selection, validation
   - `test_options_flow.py` - **CONSOLIDATED** - All options flow tests including:
     - Basic flow progression and step navigation
     - Feature persistence (fan, humidity settings pre-filled)
     - Preset detection and toggles
     - Complete flow integration tests
   - `test_advanced_options.py` - Advanced settings configuration

2. **E2E Persistence Tests** - End-to-end config→options flow testing
   - `test_e2e_simple_heater_persistence.py` - **CONSOLIDATED** - Includes:
     - Minimal config + all features persistence tests
     - Openings scope/timeout edge cases
   - `test_e2e_ac_only_persistence.py` - **CONSOLIDATED** - Minimal + all features
   - `test_e2e_heat_pump_persistence.py` - **CONSOLIDATED** - Minimal + all features
   - `test_e2e_heater_cooler_persistence.py` - **CONSOLIDATED** - Includes:
     - Minimal config + all features persistence tests
     - Fan mode persistence edge cases
     - Boolean False value persistence tests

3. **Reconfigure Flow Tests** - System reconfiguration
   - `test_reconfigure_flow.py` - General reconfigure mechanics
   - `test_reconfigure_flow_e2e_<system>.py` - Full reconfigure flow per system type
   - `test_reconfigure_system_type_change.py` - System type switching

4. **Feature Integration Tests** - Feature combinations per system type
   - `test_simple_heater_features_integration.py` - All feature combos for simple_heater
   - `test_ac_only_features_integration.py` - All feature combos for ac_only
   - `test_heat_pump_features_integration.py` - All feature combos for heat_pump
   - `test_heater_cooler_features_integration.py` - All feature combos for heater_cooler

5. **System-Specific Tests** - Unique system type behaviors
   - `test_heat_pump_config_flow.py`, `test_heat_pump_options_flow.py`
   - `test_heater_cooler_flow.py`
   - `test_ac_only_features.py`, `test_ac_only_advanced_settings.py`
   - `test_simple_heater_advanced.py`

6. **Utilities and Validation**
   - `test_integration.py` - **CONSOLIDATED** - Integration tests and transient flag handling
   - `test_step_ordering.py` - Config step dependency validation
   - `test_translations.py` - Localization support
   - `test_options_entry_helpers.py` - Helper function unit tests

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

## File Structure Reference

```
custom_components/dual_smart_thermostat/
├── climate.py                    # Main climate entity
├── config_flow.py               # Initial configuration wizard
├── options_flow.py              # Configuration updates
├── const.py                     # Constants and config keys
├── schemas.py                   # Configuration schemas
├── services.yaml                # Service definitions
├── manifest.json                # Component metadata
├── hvac_device/                 # Device abstraction layer
│   ├── generic_hvac_device.py
│   ├── hvac_device_factory.py
│   └── [specific device types]
├── managers/                    # Business logic layer
│   ├── state_manager.py
│   ├── environment_manager.py
│   ├── feature_manager.py
│   ├── opening_manager.py
│   ├── preset_manager.py
│   └── hvac_power_manager.py
├── hvac_controller/             # Control logic layer
│   ├── generic_controller.py
│   ├── heater_controller.py
│   ├── cooler_controller.py
│   └── hvac_controller.py
├── hvac_action_reason/          # Action reason tracking
├── feature_steps/               # Config flow feature steps
└── translations/                # Localization files
```

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

## Active Technologies
- Python 3.13 + Home Assistant 2025.1.0+, voluptuous (schema validation) (002-separate-tolerances)
- Home Assistant config entries (persistent JSON storage) (002-separate-tolerances)
- Python 3.13 + Home Assistant 2025.1.0+, Home Assistant Template Engine (homeassistant.helpers.template), voluptuous (schema validation) (004-template-based-presets)

## Recent Changes
- 002-separate-tolerances: Added Python 3.13 + Home Assistant 2025.1.0+, voluptuous (schema validation)
- Added Docker-based development workflow with support for testing multiple HA versions

## Development Environment Options

This repository supports **two development approaches**:

1. **Docker Compose Workflow** (Recommended for CI/CD and version testing)
   - Standalone Docker setup without VS Code
   - Easy testing with different Home Assistant versions
   - Ideal for running tests, linting, and CI/CD pipelines
   - See [README-DOCKER.md](README-DOCKER.md) for complete guide
   - Commands: `./scripts/docker-test`, `./scripts/docker-lint`, `./scripts/docker-shell`

2. **VS Code DevContainer** (Recommended for interactive development)
   - Integrated development experience in VS Code
   - Automatic environment setup
   - Full IDE features (debugging, IntelliSense, etc.)
   - Opens directly in container for seamless development

**Both approaches provide:**
- Python 3.13
- Home Assistant 2025.1.0+
- All development dependencies
- Consistent environment across machines

**Choose based on your workflow:**
- Use **Docker Compose** for testing, CI/CD, and multi-version testing
- Use **DevContainer** for daily development with VS Code
- Both can be used together for different tasks