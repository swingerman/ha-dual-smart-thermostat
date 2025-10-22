# Testing Guide

This document provides comprehensive guidance on the test structure and how to add new tests.

## Test Organization Philosophy

The test suite follows a **consolidation-first approach** to:
- Reduce file proliferation
- Keep related tests together
- Make it easier to find and update tests
- Avoid duplication

## Directory Structure

```
tests/
├── conftest.py                      # Shared pytest fixtures
├── test_<mode>_mode.py             # Mode-specific functionality tests
├── config_flow/                     # Configuration flow tests
│   ├── Core Flow Tests
│   ├── E2E Persistence Tests
│   ├── Reconfigure Flow Tests
│   ├── Feature Integration Tests
│   ├── System-Specific Tests
│   └── Utilities and Validation
├── presets/                         # Preset functionality tests
├── openings/                        # Opening detection tests
└── features/                        # Feature-specific tests
```

## Config Flow Test Organization

### 1. Core Flow Tests
Files focused on general configuration and options flow behavior.

#### `test_config_flow.py`
- Basic config flow mechanics
- System type selection
- Validation and error handling
- Entry point testing

**Add tests here for:**
- General config flow bugs
- New validation rules
- System type selection changes

#### `test_options_flow.py` ⭐ **CONSOLIDATED**
Contains ALL options flow tests (21 tests total):
- Basic flow progression and step navigation
- Feature persistence (fan, humidity settings pre-filled)
- Preset detection and toggles
- Complete flow integration tests
- Openings configuration

**Add tests here for:**
- Options flow navigation issues
- Feature settings not pre-filling
- New options flow steps
- Preset detection bugs

#### `test_advanced_options.py`
- Advanced settings toggle behavior
- System type configuration validation

**Add tests here for:**
- Advanced options visibility
- Advanced configuration edge cases

---

### 2. E2E Persistence Tests ⭐ **CONSOLIDATED**
End-to-end tests validating config→options flow data persistence.

Each file contains:
- Minimal configuration tests
- All features enabled tests
- Individual feature isolation tests
- System-specific edge cases

#### `test_e2e_simple_heater_persistence.py`
Tests for SIMPLE_HEATER system:
- Minimal config + fan feature
- All features (floor_heating, openings, presets)
- Floor heating only
- **Openings scope/timeout edge cases** (formerly separate bug fix file)

**Add tests here for:**
- Simple heater persistence issues
- Openings configuration bugs for simple_heater
- New simple_heater features

#### `test_e2e_ac_only_persistence.py`
Tests for AC_ONLY system:
- Minimal config + fan feature
- All features (fan, humidity, openings, presets)
- Fan only

**Add tests here for:**
- AC-only persistence issues
- New AC-only features

#### `test_e2e_heat_pump_persistence.py`
Tests for HEAT_PUMP system:
- Minimal config + fan feature
- All features (floor_heating, fan, humidity, openings, presets)
- Floor heating only
- Partial update tests
- Heat pump cooling sensor edge cases

**Add tests here for:**
- Heat pump persistence issues
- Heat pump cooling sensor bugs
- New heat pump features

#### `test_e2e_heater_cooler_persistence.py`
Tests for HEATER_COOLER system:
- Minimal config + fan feature
- All features (floor_heating, fan, humidity, openings, presets)
- Floor heating only
- **Fan mode persistence edge cases** (formerly separate bug fix file)
- **Boolean False value persistence** (formerly separate bug fix file)

**Add tests here for:**
- Heater/cooler persistence issues
- Fan configuration bugs
- Boolean value persistence issues
- New heater/cooler features

---

### 3. Reconfigure Flow Tests
Tests for system reconfiguration functionality.

#### `test_reconfigure_flow.py`
- General reconfigure mechanics
- Entry point validation
- Step routing

#### `test_reconfigure_flow_e2e_<system>.py` (4 files)
Full reconfigure flow for each system type:
- Minimal flow (no features)
- With individual features
- With all features
- With modifications

**Keep system-specific** - one file per system type.

#### `test_reconfigure_system_type_change.py`
- System type switching scenarios
- Data migration between types

---

### 4. Feature Integration Tests
Tests validating feature combinations per system type.

#### `test_simple_heater_features_integration.py`
#### `test_ac_only_features_integration.py`
#### `test_heat_pump_features_integration.py`
#### `test_heater_cooler_features_integration.py`

Each file tests:
- No features enabled (baseline)
- Individual features enabled
- All available features enabled
- Feature interactions and schema generation

**Keep system-specific** - one file per system type.

**Add tests here for:**
- New feature combinations
- Feature interaction bugs
- Schema generation issues

---

### 5. System-Specific Tests
Tests for unique system type behaviors.

Files:
- `test_heat_pump_config_flow.py`, `test_heat_pump_options_flow.py`
- `test_heater_cooler_flow.py`
- `test_ac_only_features.py`, `test_ac_only_advanced_settings.py`
- `test_simple_heater_advanced.py`

**Add tests here for:**
- System-type-specific configuration steps
- Unique system behaviors
- System-specific validations

---

### 6. Utilities and Validation

#### `test_integration.py` ⭐ **CONSOLIDATED**
- Options flow openings management
- **Transient flags handling** (formerly separate bug fix file)
- Real Home Assistant fixture tests

**Add tests here for:**
- Cross-cutting integration scenarios
- Transient flag issues
- Real-world configuration bugs

#### `test_step_ordering.py`
- Config step dependency validation
- Step ordering rules

#### `test_translations.py`
- Localization support tests

#### `test_options_entry_helpers.py`
- Helper function unit tests

---

## Decision Tree: Where to Add a Test

```
Is this a config flow test?
├─ YES → Continue below
└─ NO → Add to appropriate directory (tests/features/, tests/presets/, etc.)

Is this a bug fix or edge case?
├─ YES → DO NOT create new file, add to existing:
│   ├─ Options flow bug? → test_options_flow.py
│   ├─ Persistence bug? → test_e2e_<system>_persistence.py
│   ├─ Fan edge case? → test_e2e_heater_cooler_persistence.py
│   ├─ Openings edge case? → test_e2e_simple_heater_persistence.py
│   ├─ Transient flags? → test_integration.py
│   └─ General integration? → test_integration.py
└─ NO → Continue below

Is this system-specific behavior?
├─ YES → Add to system-specific file or create if truly unique
└─ NO → Continue below

Is this about feature combinations?
├─ YES → Add to test_<system>_features_integration.py
└─ NO → Continue below

Is this about reconfiguration?
├─ YES → Add to test_reconfigure_flow.py or system-specific reconfigure file
└─ NO → Add to test_config_flow.py or test_options_flow.py
```

## Test Naming Conventions

### Test Function Names
Use descriptive names following the pattern:
```python
async def test_<system>_<feature>_<specific_behavior>(hass):
```

Examples:
- `test_simple_heater_openings_scope_and_timeout_saved`
- `test_heater_cooler_fan_mode_persists_in_config_flow`
- `test_options_flow_fan_settings_prefilled`

### Test Docstrings
Always include a clear docstring:
```python
async def test_simple_heater_openings_scope_and_timeout_saved(hass):
    """Test that opening_scope and timeout_openings_open are saved to config.

    Bug Fix: These values were being lost because async_step_config didn't
    update collected_config with user_input before processing.

    Expected: opening_scope="heat" and timeout_openings_open=300 should
    both be present in the final config.
    """
```

## Common Patterns

### Basic Test Structure
```python
@pytest.mark.asyncio
async def test_name(hass):
    """Docstring explaining what this tests."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    # Step through flow
    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    # Assertions
    assert result["type"] == "create_entry"
```

### Using MockConfigEntry
```python
from pytest_homeassistant_custom_component.common import MockConfigEntry

config_entry = MockConfigEntry(
    domain=DOMAIN,
    data=created_data,
    options={},
    title="Test Thermostat",
)
config_entry.add_to_hass(hass)
```

### Options Flow Testing
```python
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

options_flow = OptionsFlowHandler(config_entry)
options_flow.hass = hass

result = await options_flow.async_step_init()
assert result["type"] == "form"
assert result["step_id"] == "init"
```

## Anti-Patterns to Avoid

### ❌ DON'T: Create Standalone Bug Fix Files
```
# BAD - creates file proliferation
tests/config_flow/test_fan_mode_persistence_bug.py
tests/config_flow/test_openings_timeout_bug.py
tests/config_flow/test_preset_toggle_bug.py
```

### ✅ DO: Add to Consolidated Files
```python
# GOOD - add to existing consolidated file
# In test_e2e_heater_cooler_persistence.py:
async def test_heater_cooler_fan_mode_persists_in_config_flow(hass):
    """Test that fan_mode=True is saved in collected_config during config flow.

    Bug Fix: fan_mode was not persisting through config/options cycles.
    """
    # Test implementation
```

### ❌ DON'T: Create Minimal/All Features Pairs
```
# BAD - creates duplication
tests/config_flow/test_e2e_simple_heater_persistence.py
tests/config_flow/test_e2e_simple_heater_all_features_persistence.py
```

### ✅ DO: Consolidate in Single File
```python
# GOOD - all in one file with clear test names
# In test_e2e_simple_heater_persistence.py:
async def test_simple_heater_minimal_config_persistence(hass):
    """Test minimal SIMPLE_HEATER flow: config → options → verify persistence."""

async def test_simple_heater_all_features_persistence(hass):
    """Test SIMPLE_HEATER with all features: config → options → persistence."""

async def test_simple_heater_floor_heating_only_persistence(hass):
    """Test SIMPLE_HEATER with only floor_heating enabled."""
```

## Running Tests

```bash
# Run all tests
pytest

# Run config flow tests
pytest tests/config_flow/

# Run specific file
pytest tests/config_flow/test_e2e_simple_heater_persistence.py

# Run specific test
pytest tests/config_flow/test_options_flow.py::test_options_flow_fan_settings_prefilled

# Run with verbose output
pytest -v tests/config_flow/

# Run with debug logging
pytest --log-cli-level=DEBUG tests/config_flow/test_options_flow.py
```

## Maintenance Guidelines

### When Consolidating Tests
1. Read all related test files completely
2. Identify common patterns and duplications
3. Organize tests into logical sections with clear comments
4. Update module docstrings to describe coverage
5. Ensure all test scenarios are preserved
6. Update CLAUDE.md and this document

### When Reviewing PRs
- Reject new standalone bug fix test files
- Suggest consolidation into existing files
- Check that new tests follow naming conventions
- Ensure docstrings explain the test purpose
- Verify tests are in the right file

## History

- **2025-10**: Major consolidation reduced config flow tests from 39 to 29 files
  - Merged minimal + all_features persistence tests
  - Integrated all bug fix tests into relevant modules
  - Consolidated options flow tests into single file
  - See commit 6872b89 for details
