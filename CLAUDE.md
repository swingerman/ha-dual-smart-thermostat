# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Dual Smart Thermostat - An enhanced thermostat component supporting multiple HVAC modes (heating, cooling, heat pump, fan, humidity control), advanced features (floor temperature control, window/door sensors, presets), and sophisticated control logic.

**Target**: Home Assistant 2025.1.0+
**Language**: Python 3.13

## Essential Commands

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_heater_mode.py

# Run tests with debug output
pytest --log-cli-level=DEBUG

# Run tests for specific feature
pytest tests/config_flow/
pytest tests/presets/
```

### Code Quality (Required Before Commit)
```bash
# Check all linting (DO NOT commit if any fail)
isort . --recursive --diff    # Import sorting
black --check .               # Code formatting
flake8 .                      # Style/linting
codespell                     # Spell checking

# Auto-fix linting issues
isort .                       # Fix imports
black .                       # Fix formatting

# Run all pre-commit hooks
pre-commit run --all-files
```

### Development Setup
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

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
```bash
# All tests
pytest

# Config flow tests only
pytest tests/config_flow/

# Single test file
pytest tests/config_flow/test_e2e_simple_heater_persistence.py

# Single test function
pytest tests/config_flow/test_options_flow.py::test_options_flow_fan_settings_prefilled

# With debug logging
pytest --log-cli-level=DEBUG tests/test_heater_mode.py
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
   - Config flow steps to `feature_steps/` (if needed)
   - **Update configuration dependencies** (see Critical Rules above)

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

5. **Code quality**:
   - Run linting: `isort .`, `black .`, `flake8 .`, `codespell`
   - Run tests: `pytest`
   - Run pre-commit: `pre-commit run --all-files`

### Modifying Existing Features

1. **Understand the change**: Read relevant code in device/manager/controller layers
2. **Check dependencies**: Identify which components are affected
3. **Update tests first**: Modify tests to reflect new behavior
4. **Implement changes**: Make minimal changes following existing patterns
5. **Verify**: Run affected tests and full test suite

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

### Development rules

- Always use context7 when I need code generation, setup or configuration steps, or
library/API documentation. This means you should automatically use the Context7 MCP
tools to resolve library id and get library docs without me having to explicitly ask.

- Always lint your code before sending it to me. Use `isort`, `black`, `flake8`, and `codespell` to ensure your code meets quality standards.