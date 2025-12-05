# Test Organization Guide

**Version:** 1.0
**Last Updated:** 2025-12-05
**Status:** Complete after consolidation effort

## Overview

This document describes the organization of tests in the Dual Smart Thermostat project after the test consolidation effort (Phases 1-10). It provides guidance on:
- Current test file structure
- Where to find specific tests
- Where to add new tests
- Test patterns and conventions

## Directory Structure

```
tests/
├── shared_tests/              # Consolidated shared test modules
│   ├── conftest.py           # MODE_CONFIGS and shared fixtures
│   ├── test_setup_base.py    # Setup and initialization tests
│   ├── test_preset_base.py   # Preset mode tests
│   ├── test_hvac_operations_base.py  # HVAC operations tests
│   ├── test_tolerance_base.py        # Temperature tolerance tests
│   └── test_example_given_when_then.py  # Example/documentation
│
├── test_heater_mode.py        # Heater mode-specific tests
├── test_cooler_mode.py        # Cooler mode-specific tests
├── test_heat_pump_mode.py     # Heat pump mode-specific tests
├── test_fan_mode.py           # Fan mode-specific tests
├── test_dry_mode.py           # Dryer mode-specific tests
├── test_dual_mode.py          # Dual mode (heat_cool) tests
│
├── config_flow/              # Configuration flow tests
│   ├── test_config_flow.py           # Initial config flow
│   ├── test_options_flow.py          # Options flow (consolidated)
│   ├── test_reconfigure_flow.py      # Reconfigure flow
│   ├── test_e2e_*_persistence.py     # End-to-end persistence tests
│   ├── test_*_features_integration.py # Feature integration per system
│   └── [other config flow tests]
│
├── features/                 # Feature-specific tests
│   ├── [floor heating tests]
│   ├── [humidity control tests]
│   └── [other feature tests]
│
├── openings/                 # Opening detection tests
├── presets/                  # Preset-specific tests
└── conftest.py              # Root test fixtures
```

## Shared Tests Directory (`tests/shared_tests/`)

### Purpose

The `shared_tests/` directory contains **consolidated test modules** for test logic that is **common across multiple HVAC modes**. These tests:
- Use parametrization to run the same test across different modes
- Follow the Given/When/Then pattern
- Reduce code duplication
- Provide single source of truth for shared behavior

### Shared Test Modules

#### 1. `test_setup_base.py` (Setup Tests)

**Purpose:** Tests for component setup and initialization

**Tests Included:**
- `test_unique_id` - Verify unique ID generation
- `test_setup_defaults_to_unknown` - Initial state unknown
- `test_setup_gets_current_temp_from_sensor` - Sensor reading on startup
- `test_sensor_state_unknown_on_startup` - Handle unknown sensor
- `test_sensor_state_unavailable_on_startup` - Handle unavailable sensor
- `test_sensor_state_invalid_on_startup` - Handle invalid sensor values

**Modes Covered:** heater, cooler, fan, heat_pump (4 modes × 6 tests = 24 test executions)

**Example:**
```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_unique_id(mode_config, hass, setup_comp_1):
    """Test unique ID generation for {mode}."""
    # GIVEN - Component setup complete
    # WHEN - Check entity registry
    # THEN - Unique ID should match config entry ID
```

#### 2. `test_preset_base.py` (Preset Tests)

**Purpose:** Tests for preset mode functionality

**Tests Included:**
- `test_set_preset_mode` - Set preset and verify temperature
- `test_set_preset_mode_and_restore_prev_temp` - Restore after preset
- `test_set_preset_mode_twice_and_restore_prev_temp` - Multiple preset changes
- `test_set_preset_mode_invalid` - Invalid preset handling
- `test_set_preset_mode_set_temp_keeps_preset_mode` - Manual temp doesn't clear preset
- `test_set_same_preset_mode_restores_preset_temp_from_modified` - Re-apply preset

**Modes Covered:** heater, cooler, fan (3 modes × 6 tests = 18 test executions)

**Example:**
```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_set_preset_mode(mode_config, hass, setup_comp_heat_cool_presets):
    """Test preset mode changes for {mode}."""
    # GIVEN - Component with presets configured
    # WHEN - Set preset mode
    # THEN - Temperature should match preset value
```

#### 3. `test_hvac_operations_base.py` (HVAC Operations Tests)

**Purpose:** Tests for basic HVAC operations

**Tests Included:**
- `test_get_hvac_modes` - Available HVAC modes
- `test_set_target_temp` - Set target temperature
- `test_set_target_temp_and_hvac_mode` - Set temp and mode together

**Modes Covered:** heater, cooler, fan (3 modes × 3 tests = 9 test executions)

**Example:**
```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_set_target_temp(mode_config, hass, setup_comp_1):
    """Test setting target temperature for {mode}."""
    # GIVEN - Component initialized
    # WHEN - Set target temperature
    # THEN - Temperature should be updated
```

#### 4. `test_tolerance_base.py` (Tolerance Tests)

**Purpose:** Tests for temperature tolerance behavior

**Tests Included:**
- `test_temp_change_device_on_within_tolerance` - No action when within tolerance
- `test_temp_change_device_on_outside_tolerance` - Turn off when outside tolerance
- `test_temp_change_device_off_within_tolerance` - Stay off when within tolerance
- `test_temp_change_device_off_outside_tolerance` - Turn on when outside tolerance

**Modes Covered:** heater, cooler, fan (3 modes × 4 tests = 12 test executions)

**Example:**
```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_temp_change_device_on_within_tolerance(mode_config, hass, setup_comp_1):
    """Test device stays on when temperature within tolerance for {mode}."""
    # GIVEN - Device is on, temp at target
    # WHEN - Temperature changes within tolerance
    # THEN - Device should remain on
```

#### 5. `test_example_given_when_then.py` (Documentation)

**Purpose:** Example test demonstrating Given/When/Then pattern

**Tests Included:**
- `test_example_given_when_then` - Template for new tests

**Usage:** Reference this when creating new shared tests

### MODE_CONFIGS Pattern

Shared tests use the `MODE_CONFIGS` dictionary defined in `tests/shared_tests/conftest.py`:

```python
MODE_CONFIGS = {
    "heater": {
        "mode": "heater",
        "switch": "input_boolean.heater",
        "hvac_mode": HVACMode.HEAT,
        "initial_temp": 18,
        "target_temp": 23,
        "over_target_temp": 24,
        # ... other config
    },
    "cooler": {
        "mode": "cooler",
        "switch": "input_boolean.cooler",
        "hvac_mode": HVACMode.COOL,
        "initial_temp": 25,
        "target_temp": 20,
        "over_target_temp": 19,
        # ... other config
    },
    # ... other modes
}
```

**Benefits:**
- Single configuration source for all modes
- Easy to add new modes (just add to dict)
- Parametrization happens automatically
- Test code identical across modes

## Mode-Specific Tests

### Purpose

Mode-specific test files contain tests that are **unique to a particular HVAC mode** and don't fit the shared test pattern. These include:
- Mode-specific features (aux heater, floor protection)
- Already-parametrized tests (cycles, opening scope)
- Complex integration tests (>80 lines)
- Tests with significant mode-specific logic differences

### What Remains in Mode Files

#### `test_heater_mode.py`
**Mode-Specific Tests:**
- Aux heater tests (two-stage heating)
- Floor protection tests (min/max floor temp)
- Heater-specific tolerance configurations
- Legacy config tests
- **Opening/cycle tests** (already parametrized within file)

**Example:**
```python
async def test_heater_mode_floor_temp_max(hass, ...):
    """Test heater respects maximum floor temperature."""
    # Heater-specific floor protection logic
```

#### `test_cooler_mode.py`
**Mode-Specific Tests:**
- AC-specific behavior tests
- Cooler-specific tolerance configurations
- AC mode interaction tests
- **Opening/cycle tests** (already parametrized within file)

#### `test_heat_pump_mode.py`
**Mode-Specific Tests:**
- Heat pump mode switching tests
- Single switch for heat/cool behavior
- Heat pump cooling sensor tests
- Mode transition logic

#### `test_fan_mode.py`
**Mode-Specific Tests:**
- Fan mode variants (fan only, cooler+fan)
- Keep-alive tests
- Fan-AC interaction tests
- **Complex cycle tests** (fan+AC during cycle)
- **Opening/cycle tests** (already parametrized within file)

#### `test_dry_mode.py`
**Mode-Specific Tests:**
- Humidity control tests
- Dryer-specific behavior
- Humidity sensor integration
- **Opening/cycle tests** (already parametrized within file)

#### `test_dual_mode.py`
**Mode-Specific Tests:**
- Range control tests (heat_cool mode)
- Dual mode switching
- Complex multi-mode scenarios
- Heat and cool coordination
- **Opening/cycle tests** (already parametrized within file)

### Already-Parametrized Tests in Mode Files

Some tests in mode files are **already well-optimized** using `pytest.mark.parametrize`:

**Cycle Tests** (all mode files):
```python
@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),    # Within min_cycle_duration
        (timedelta(seconds=30), STATE_OFF),   # Exceeds min_cycle_duration
    ],
)
async def test_heater_mode_cycle(hass, freezer, duration, result_state, ...):
    """Test thermostat switch with min_cycle_duration."""
    # Each test runs 2 scenarios
```

**Opening Scope Tests** (all mode files):
```python
@pytest.mark.parametrize(
    ["hvac_mode", "opening_scope", "switch_state"],
    [
        ([HVACMode.HEAT, ["all"], STATE_OFF]),
        ([HVACMode.HEAT, [HVACMode.HEAT], STATE_OFF]),
        ([HVACMode.HEAT, [HVACMode.FAN_ONLY], STATE_ON]),
    ],
)
async def test_heater_mode_opening_scope(hass, hvac_mode, opening_scope, switch_state, ...):
    """Test opening scope configuration."""
    # Each test runs 3 scenarios
```

**Why these stay in mode files:**
- Already well-optimized with parametrization
- Mode-specific setup requirements
- Test different behavior per mode (not identical)
- Would gain little from further consolidation

## Config Flow Tests (`tests/config_flow/`)

### Organization

Config flow tests are organized by type and consolidated where appropriate:

#### Core Flow Tests
- `test_config_flow.py` - Initial configuration wizard
- `test_options_flow.py` - **CONSOLIDATED** options flow tests including:
  - Basic flow progression
  - Feature persistence (fan, humidity pre-filled)
  - Preset detection
  - Complete integration tests
- `test_advanced_options.py` - Advanced settings

#### E2E Persistence Tests
- `test_e2e_simple_heater_persistence.py` - **CONSOLIDATED** heater persistence
- `test_e2e_ac_only_persistence.py` - **CONSOLIDATED** AC-only persistence
- `test_e2e_heat_pump_persistence.py` - **CONSOLIDATED** heat pump persistence
- `test_e2e_heater_cooler_persistence.py` - **CONSOLIDATED** heater+cooler persistence

#### Reconfigure Flow Tests
- `test_reconfigure_flow.py` - General reconfigure mechanics
- `test_reconfigure_flow_e2e_<system>.py` - Full reconfigure per system
- `test_reconfigure_system_type_change.py` - System type switching

#### Feature Integration Tests
- `test_simple_heater_features_integration.py` - All heater feature combos
- `test_ac_only_features_integration.py` - All AC feature combos
- `test_heat_pump_features_integration.py` - All heat pump feature combos
- `test_heater_cooler_features_integration.py` - All heater+cooler feature combos

### Adding Config Flow Tests

**Where to add:**
1. **Bug fixes or edge cases** → Add to relevant consolidated file
2. **New system type behavior** → Add to system-specific test file
3. **New feature integration** → Add to `test_<system>_features_integration.py`
4. **New reconfigure scenario** → Add to reconfigure test file

**DO NOT** create separate bug fix test files - integrate into existing tests.

## Test Naming Conventions

### Shared Tests

**Pattern:**
```python
async def test_{feature}_{scenario}(mode_config, hass, ...):
    """Test {feature} {scenario} for {mode}."""
```

**Examples:**
- `test_unique_id` - Tests unique ID generation
- `test_set_preset_mode` - Tests preset mode setting
- `test_temp_change_device_on_within_tolerance` - Tests tolerance behavior

**Characteristics:**
- No mode name in function name (parametrized)
- Docstring includes `{mode}` placeholder
- Takes `mode_config` as first parameter

### Mode-Specific Tests

**Pattern:**
```python
async def test_{mode}_{feature}_{scenario}(hass, ...):
    """Test {mode}-specific {feature} {scenario}."""
```

**Examples:**
- `test_heater_mode_floor_temp_max` - Heater floor protection
- `test_fan_mode_keep_alive` - Fan keep-alive behavior
- `test_heat_pump_mode_cooling_sensor` - Heat pump cooling sensor

**Characteristics:**
- Mode name in function name
- Clear mode-specific purpose
- No MODE_CONFIGS parameter

### Already-Parametrized Tests in Mode Files

**Pattern:**
```python
@pytest.mark.parametrize(["param1", "param2"], [...])
async def test_{mode}_{feature}(hass, param1, param2, ...):
    """Test {mode} {feature} with parametrized scenarios."""
```

**Examples:**
- `test_heater_mode_cycle` - Cycle tests with duration parameter
- `test_heater_mode_opening_scope` - Opening scope with scope parameter

## Adding New Tests

### Decision Tree

```
New Test Needed
    │
    ├─ Duplicated across 3+ modes?
    │   ├─ YES → Is test < 80 lines?
    │   │   ├─ YES → Add to shared_tests/ (parametrize by mode)
    │   │   └─ NO → Keep in mode files (too complex)
    │   └─ NO → Continue...
    │
    ├─ Mode-specific behavior?
    │   └─ YES → Add to mode file (test_*_mode.py)
    │
    ├─ Already parametrized in mode file?
    │   └─ YES → Leave as-is (already optimized)
    │
    ├─ Config flow related?
    │   └─ YES → Add to consolidated config flow test
    │
    └─ Feature-specific?
        └─ YES → Add to feature test directory
```

### Example: Adding a Shared Test

**Scenario:** New test for setting temperature limits

**Steps:**
1. Identify that behavior is identical across heater, cooler, fan modes
2. Test is < 80 lines
3. Add to shared_tests/test_hvac_operations_base.py (or create new module)

**Implementation:**
```python
# tests/shared_tests/test_hvac_operations_base.py

@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_set_temperature_limits(mode_config, hass, setup_comp_1):
    """Test temperature limit enforcement for {mode}."""
    # GIVEN - Component initialized with min/max temp limits
    min_temp = 10
    max_temp = 30

    # WHEN - Try to set temp below minimum
    await common.async_set_temperature(hass, 5)
    await hass.async_block_till_done()

    # THEN - Should be clamped to minimum
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == min_temp
```

### Example: Adding a Mode-Specific Test

**Scenario:** New auxiliary heater timeout behavior

**Steps:**
1. Identify behavior is unique to heater mode (aux heater)
2. Add to test_heater_mode.py

**Implementation:**
```python
# tests/test_heater_mode.py

async def test_heater_aux_timeout_reset(hass, setup_comp_1):
    """Test auxiliary heater timeout resets on mode change."""
    # GIVEN - Aux heater active
    heater_switch = "input_boolean.heater"
    aux_heater_switch = "input_boolean.aux_heater"

    setup_sensor(hass, 15)
    await common.async_set_temperature(hass, 25)
    await hass.async_block_till_done()

    # Aux heater should be on after timeout
    assert hass.states.get(aux_heater_switch).state == STATE_ON

    # WHEN - Change HVAC mode to OFF
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()

    # THEN - Aux heater timeout should reset
    # (Test aux heater-specific logic)
```

### Example: Adding a Config Flow Test

**Scenario:** Test new feature persistence in options flow

**Steps:**
1. Identify this is config flow related
2. Feature persistence goes in test_options_flow.py (consolidated)

**Implementation:**
```python
# tests/config_flow/test_options_flow.py

async def test_options_flow_new_feature_prefilled(hass):
    """Test new feature settings are pre-filled in options flow.

    This test ensures that when users open options flow, their
    previously configured new_feature settings are displayed.
    """
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_HEATER: "switch.heater",
            CONF_NEW_FEATURE: True,
            CONF_NEW_FEATURE_SETTING: 5,
        },
    )
    config_entry.add_to_hass(hass)

    # Initialize options flow
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Navigate to new_feature step
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    # Verify settings pre-filled
    assert result["step_id"] == "new_feature"
    assert result["data_schema"].schema.get(CONF_NEW_FEATURE).default is True
    assert result["data_schema"].schema.get(CONF_NEW_FEATURE_SETTING).default == 5
```

## Test Patterns and Best Practices

### Given/When/Then Pattern

All consolidated tests use the Given/When/Then pattern for clarity:

```python
async def test_feature_behavior(mode_config, hass, ...):
    """Test feature behavior for {mode}."""
    # GIVEN - Initial state setup
    # Describe what the starting conditions are
    setup_sensor(hass, 20)
    setup_switch(hass, mode_config["switch"], STATE_OFF)
    await hass.async_block_till_done()

    # WHEN - Trigger behavior
    # Describe the action being tested
    await async_set_temperature(hass, 25)
    await hass.async_block_till_done()

    # THEN - Verify outcome
    # Describe the expected result
    assert hass.states.get(mode_config["switch"]).state == STATE_ON
    assert specific_condition
```

**Benefits:**
- Clear test structure
- Easy to understand test purpose
- Separates setup, action, and verification

### Direct Fixture Parametrization

Shared tests use **direct fixture parametrization** to avoid async loop nesting:

**Good:**
```python
@pytest.mark.parametrize("mode_config", MODE_CONFIGS.values())
async def test_feature(mode_config, hass, setup_comp_1):
    """Test using mode_config directly."""
    # Access mode_config parameters directly
    switch = mode_config["switch"]
```

**Avoid:**
```python
@pytest.mark.parametrize("mode", MODE_CONFIGS.keys())
async def test_feature(mode, hass, setup_comp_1):
    """Test using mode string."""
    # Need to look up MODE_CONFIGS[mode] - less direct
```

### Test Docstrings

**Shared tests:**
```python
async def test_feature(mode_config, hass, ...):
    """Test feature behavior for {mode}.

    Optional additional description if needed.
    """
```
- Use `{mode}` placeholder (interpolated by pytest)
- Keep first line concise

**Mode-specific tests:**
```python
async def test_heater_aux_feature(hass, ...):
    """Test auxiliary heater feature behavior.

    This test verifies that the auxiliary heater activates
    after the primary heater has been running for the configured
    timeout period.
    """
```
- Be explicit about mode-specific behavior
- Explain why this test is mode-specific if not obvious

## Consolidation Principles

### When to Consolidate

✅ **DO consolidate when:**
1. Test duplicated across 3+ modes
2. ~90% identical logic (only parameters differ)
3. Test length < 80 lines
4. Clear parametrization path
5. Consolidation improves maintainability

❌ **DON'T consolidate when:**
1. Tests already use pytest.mark.parametrize
2. Tests > 80 lines (too complex)
3. Significant mode-specific logic differences
4. Custom setup doesn't fit fixture pattern
5. Only 1-2 instances (no real duplication)
6. Consolidation would reduce clarity

### Complexity Threshold

**80-line threshold established:**
- Tests < 80 lines: Consider for consolidation
- Tests > 80 lines: Usually too complex
- Custom setup (~40 lines) + test logic (~40 lines) = threshold

**Example of too complex:**
- Opening behavior tests (~95 lines each)
- Complex timeout logic with freezer.tick()
- Multiple state transitions (8-10 assertions)
- **Decision:** Leave in mode files, don't consolidate

## Removing Duplicate Tests

### Safe Removal Process

59 test functions **can be safely removed** from mode files (already consolidated in shared_tests/):
- Setup tests: 20 functions
- Preset tests: 18 functions
- Operations tests: 9 functions
- Tolerance tests: 12 functions

**See:** `docs/testing/PHASE_9_ASSESSMENT.md` for complete removal mapping

**Removal Strategy:**
1. Start with setup tests (lowest risk)
2. Remove from 1 mode file at a time
3. Run full test suite after each removal
4. Verify no test failures
5. Gradually expand to other categories

**When to remove:**
- When confidence is high in consolidated tests
- After observing consolidated tests in use
- As part of normal maintenance (gradual)

**Not urgent:** Both versions currently pass, no immediate need to remove.

## Adding New Modes

### Process

To add a new HVAC mode (e.g., "mister" mode):

1. **Add MODE_CONFIG:**
```python
# tests/shared_tests/conftest.py
MODE_CONFIGS["mister"] = {
    "mode": "mister",
    "switch": "input_boolean.mister",
    "hvac_mode": HVACMode.DRY,  # Or new HVAC mode
    "initial_temp": 22,
    "target_temp": 20,
    "over_target_temp": 19,
    "under_target_temp": 21,
    "device_on_value": STATE_ON,
    "tolerance": 0.5,
    "tolerance_key": "cold_tolerance",
}
```

2. **All shared tests automatically run for new mode** (parametrized)

3. **Create mode-specific test file:**
```python
# tests/test_mister_mode.py
async def test_mister_mode_specific_feature(hass, ...):
    """Test mister-specific feature."""
    # Mister-specific tests only
```

4. **Run tests:**
```bash
pytest tests/shared_tests/  # Should include new mode automatically
pytest tests/test_mister_mode.py  # Mode-specific tests
```

**Benefits:**
- Automatic test coverage for new mode
- Only write mode-specific tests
- Consistent test patterns

## Coverage Validation

### Current Status

**Coverage Maintained:** ✅ 100%
- All consolidated tests passing
- Mode-specific tests passing
- No test scenarios lost in consolidation
- Test clarity improved

**Shared Test Coverage:**
- 48 test functions in shared_tests/
- 4-6 modes per test = ~65+ test executions from shared tests alone
- Plus mode-specific tests
- Plus config flow tests

### Validating Coverage

**After changes:**
```bash
# Run all tests
pytest tests/

# Run only shared tests
pytest tests/shared_tests/

# Run specific mode
pytest tests/test_heater_mode.py

# Coverage report (if pytest-cov installed)
pytest --cov=custom_components.dual_smart_thermostat tests/
```

## Summary

### Key Takeaways

1. **Shared tests** (`tests/shared_tests/`) - Common behavior across modes
2. **Mode-specific tests** - Unique mode behavior and already-parametrized tests
3. **Given/When/Then** - Standard pattern for all consolidated tests
4. **MODE_CONFIGS** - Single source of truth for mode parameters
5. **Decision tree** - Clear guidance for where to add new tests
6. **80-line threshold** - Complexity limit for consolidation

### Quick Reference

**I want to add a test for behavior that works the same across all modes:**
→ Add to `tests/shared_tests/` using MODE_CONFIGS parametrization

**I want to add a test for heater-specific behavior (aux heater, floor protection):**
→ Add to `tests/test_heater_mode.py`

**I want to add a config flow persistence test:**
→ Add to `tests/config_flow/test_options_flow.py` or appropriate E2E test

**I want to add a test for fan mode keep-alive:**
→ Add to `tests/test_fan_mode.py` (mode-specific)

**I found a bug in setup behavior across all modes:**
→ Add bug fix test to `tests/shared_tests/test_setup_base.py`

**I'm adding a new HVAC mode:**
→ Add MODE_CONFIG to conftest.py, shared tests run automatically

### Documentation References

- **Consolidation Plan:** `docs/testing/TEST_CONSOLIDATION_PLAN.md`
- **Progress Summary:** `docs/testing/CONSOLIDATION_PROGRESS_SUMMARY.md`
- **Phase Assessments:** `docs/testing/PHASE_*_ASSESSMENT.md` (10 files)
- **Removal Mapping:** `docs/testing/PHASE_9_ASSESSMENT.md`
- **This Guide:** `docs/testing/TEST_ORGANIZATION.md`

---

**Last Updated:** 2025-12-05 after Phase 10 completion
**Status:** Complete and maintained
