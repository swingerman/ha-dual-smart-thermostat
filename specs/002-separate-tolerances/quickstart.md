# Developer Quickstart: Separate Temperature Tolerances

**Feature**: Separate Temperature Tolerances for Heating and Cooling Modes
**Branch**: `002-separate-tolerances`
**Date**: 2025-10-29

---

## Overview

This feature adds optional `heat_tolerance` and `cool_tolerance` parameters that enable users to configure different temperature control precision for heating vs cooling operations. For example: tight control in heating mode (±0.3°C) for comfort, loose control in cooling mode (±2.0°C) for energy savings.

**Key Benefits**:
- Separate tolerance values for heating and cooling
- 100% backward compatible with existing configurations
- No migration required
- Configurable through Home Assistant UI

---

## Quick Start (5 Minutes)

### 1. Setup Development Environment

```bash
# Clone and setup
cd /workspaces/dual_smart_thermostat
git checkout 002-separate-tolerances

# Install dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### 2. Run Existing Tests

```bash
# Verify current state
pytest tests/

# Expected: All tests pass
```

### 3. Explore Key Files

```bash
# Configuration constants
cat custom_components/dual_smart_thermostat/const.py | grep -A5 "CONF_.*_TOLERANCE"

# Environment manager (tolerance logic)
cat custom_components/dual_smart_thermostat/managers/environment_manager.py | grep -A20 "is_too_cold"

# Options flow (UI configuration)
cat custom_components/dual_smart_thermostat/options_flow.py | grep -A30 "advanced"
```

---

## Configuration Examples

### Example 1: Legacy Configuration (Backward Compatible)

```yaml
# Existing configuration - NO CHANGES NEEDED
climate:
  - platform: dual_smart_thermostat
    name: Living Room
    heater: switch.heater
    target_sensor: sensor.temperature
    cold_tolerance: 0.5  # Used for both heating and cooling
    hot_tolerance: 0.5
```

**Behavior**: Works identically to previous versions. Heating and cooling both use ±0.5°C tolerance.

### Example 2: Tight Heating, Loose Cooling

```yaml
# New configuration with mode-specific tolerances
climate:
  - platform: dual_smart_thermostat
    name: Living Room
    heater: switch.heater
    cooler: switch.ac
    target_sensor: sensor.temperature
    cold_tolerance: 0.5      # Legacy fallback
    hot_tolerance: 0.5       # Legacy fallback
    heat_tolerance: 0.3      # Override: tight heating control
    cool_tolerance: 2.0      # Override: loose cooling control
```

**Behavior**:
- **Heating mode**: Uses ±0.3°C (heat_tolerance)
- **Cooling mode**: Uses ±2.0°C (cool_tolerance)
- **Auto mode**: Switches between heat and cool tolerances based on temperature

### Example 3: Partial Override (Cooling Only)

```yaml
# Override only cooling tolerance
climate:
  - platform: dual_smart_thermostat
    name: Bedroom
    heater: switch.heater
    cooler: switch.ac
    target_sensor: sensor.temperature
    cold_tolerance: 0.5
    hot_tolerance: 0.5
    cool_tolerance: 1.5      # Override cooling only
    # heat_tolerance not set - uses legacy for heating
```

**Behavior**:
- **Heating mode**: Uses ±0.5°C (legacy cold/hot tolerance)
- **Cooling mode**: Uses ±1.5°C (cool_tolerance)

---

## Testing Guide

### Running Unit Tests

```bash
# Test tolerance selection logic
pytest tests/managers/test_environment_manager.py -v

# Test specific tolerance test cases
pytest tests/managers/test_environment_manager.py::test_mode_specific_tolerance -v
```

### Running Config Flow Tests

```bash
# Test options flow integration
pytest tests/config_flow/test_options_flow.py -v

# Test advanced settings step
pytest tests/config_flow/test_options_flow.py::test_advanced_settings_tolerance -v
```

### Running E2E Persistence Tests

```bash
# Test all system types
pytest tests/config_flow/test_e2e_simple_heater_persistence.py -v
pytest tests/config_flow/test_e2e_ac_only_persistence.py -v
pytest tests/config_flow/test_e2e_heat_pump_persistence.py -v
pytest tests/config_flow/test_e2e_heater_cooler_persistence.py -v

# Or run all E2E tests
pytest tests/config_flow/ -k "e2e" -v
```

### Running Integration Tests

```bash
# Test feature combinations
pytest tests/config_flow/test_simple_heater_features_integration.py -v
pytest tests/config_flow/test_ac_only_features_integration.py -v
pytest tests/config_flow/test_heat_pump_features_integration.py -v
pytest tests/config_flow/test_heater_cooler_features_integration.py -v
```

### Running Functional Tests

```bash
# Test mode-specific behavior
pytest tests/test_heater_mode.py -v
pytest tests/test_cooler_mode.py -v
pytest tests/test_heat_pump_mode.py -v

# Run with debug logging
pytest tests/test_heater_mode.py --log-cli-level=DEBUG -v
```

### Running All Tests

```bash
# Full test suite
pytest

# With coverage report
pytest --cov=custom_components/dual_smart_thermostat --cov-report=html
```

---

## Development Workflow

### Making Changes to Tolerance Logic

**File**: `custom_components/dual_smart_thermostat/managers/environment_manager.py`

1. **Locate the tolerance selection method**:
   ```python
   def _get_active_tolerance_for_mode(self) -> tuple[float, float]:
       """Get active tolerance based on HVAC mode."""
   ```

2. **Make your changes** following the priority hierarchy:
   - Priority 1: Mode-specific tolerance (heat_tolerance or cool_tolerance)
   - Priority 2: Legacy tolerances (cold_tolerance, hot_tolerance)

3. **Update is_too_cold() and is_too_hot()**:
   ```python
   def is_too_cold(self, target_attr="_target_temp") -> bool:
       cold_tol, _ = self._get_active_tolerance_for_mode()
       # ... use cold_tol in comparison
   ```

4. **Test your changes**:
   ```bash
   pytest tests/managers/test_environment_manager.py -v
   ```

### Adding Tests

**Location**: `tests/managers/test_environment_manager.py`

1. **Add unit test**:
   ```python
   async def test_heat_tolerance_priority(hass):
       """Test heat_tolerance takes priority over legacy in HEAT mode."""
       config = {
           CONF_COLD_TOLERANCE: 0.5,
           CONF_HOT_TOLERANCE: 0.5,
           CONF_HEAT_TOLERANCE: 0.3,  # Should take priority
       }
       env = EnvironmentManager(hass, config)
       env.set_hvac_mode(HVACMode.HEAT)

       cold_tol, hot_tol = env._get_active_tolerance_for_mode()
       assert cold_tol == 0.3
       assert hot_tol == 0.3
   ```

2. **Run the test**:
   ```bash
   pytest tests/managers/test_environment_manager.py::test_heat_tolerance_priority -v
   ```

### Verifying Backward Compatibility

1. **Create test with legacy config**:
   ```python
   async def test_legacy_config_unchanged(hass):
       """Test legacy config without mode-specific tolerances works."""
       config = {
           CONF_COLD_TOLERANCE: 0.5,
           CONF_HOT_TOLERANCE: 0.5,
           # No heat_tolerance or cool_tolerance
       }
       env = EnvironmentManager(hass, config)
       env.set_hvac_mode(HVACMode.HEAT)

       cold_tol, hot_tol = env._get_active_tolerance_for_mode()
       assert cold_tol == 0.5  # Uses legacy
       assert hot_tol == 0.5   # Uses legacy
   ```

2. **Run E2E test with existing config**:
   ```bash
   pytest tests/config_flow/test_e2e_simple_heater_persistence.py::test_legacy_config -v
   ```

---

## Manual Testing Procedure

### 1. Setup Test Environment

```bash
# Start Home Assistant dev environment
# (Assumes you have Home Assistant dev setup)

# Copy integration to custom_components/
cp -r custom_components/dual_smart_thermostat ~/.homeassistant/custom_components/

# Restart Home Assistant
```

### 2. Test Basic Configuration

1. Add thermostat through UI:
   - Settings → Devices & Services → Add Integration
   - Search for "Dual Smart Thermostat"
   - Complete setup wizard

2. Verify advanced settings:
   - Select thermostat → Configure → Options
   - Scroll to Advanced Settings (collapsed section)
   - Verify `heat_tolerance` and `cool_tolerance` fields present
   - Fields should be optional with range 0.1-5.0°C

### 3. Test Mode-Specific Tolerance

1. **Configure tolerances**:
   - Options → Advanced Settings
   - Set `heat_tolerance` = 0.3
   - Set `cool_tolerance` = 2.0
   - Save

2. **Test heating mode**:
   - Set mode to Heat
   - Set target temperature to 20°C
   - Observe: Heater activates at ~19.7°C, deactivates at ~20.3°C
   - Check logs for tolerance selection

3. **Test cooling mode**:
   - Set mode to Cool
   - Set target temperature to 22°C
   - Observe: AC activates at ~24°C, deactivates at ~20°C
   - Check logs for tolerance selection

### 4. Test Backward Compatibility

1. **Remove mode-specific tolerances**:
   - Options → Advanced Settings
   - Clear `heat_tolerance` and `cool_tolerance` fields
   - Save

2. **Verify legacy behavior**:
   - Both heating and cooling use `cold_tolerance` and `hot_tolerance`
   - Behavior identical to previous version

### 5. Check Logs

```bash
# View Home Assistant logs
tail -f ~/.homeassistant/home-assistant.log | grep dual_smart_thermostat

# Look for:
# - "HVAC mode updated to HVACMode.HEAT"
# - "is_too_cold - ... tolerance: 0.3"
# - "is_too_hot - ... tolerance: 2.0"
```

---

## Common Pitfalls and Debugging

### Pitfall 1: Forgetting to Call set_hvac_mode()

**Problem**: Tolerance doesn't change when mode changes

**Solution**:
```python
# In climate.py, ensure this is called:
async def async_set_hvac_mode(self, hvac_mode):
    self._hvac_mode = hvac_mode
    self._environment.set_hvac_mode(hvac_mode)  # ← Must be called
```

**Debug**: Check logs for "HVAC mode updated to..." messages

### Pitfall 2: HEAT_COOL Mode Not Switching Tolerances

**Problem**: In auto mode, tolerance doesn't switch between heating and cooling

**Solution**: Ensure current_temp vs target_temp comparison is correct:
```python
if self._cur_temp < self._target_temp:
    # Heating operation
else:
    # Cooling operation
```

**Debug**: Add logging to show which branch is taken

### Pitfall 3: Tolerance Not Persisting

**Problem**: Tolerance values lost after restart

**Solution**: Verify options flow flattens advanced settings:
```python
if "advanced_settings" in user_input:
    advanced_settings = user_input.pop("advanced_settings")
    if advanced_settings:
        user_input.update(advanced_settings)  # ← Must flatten
```

**Debug**: Check `.storage/core.config_entries` for tolerance values

### Pitfall 4: Validation Not Working

**Problem**: Can set invalid tolerance values (e.g., 10.0)

**Solution**: Check voluptuous schema in options_flow.py:
```python
selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.1,  # ← Enforce minimum
        max=5.0,  # ← Enforce maximum
        step=0.1,
    )
)
```

**Debug**: Test with boundary values (0.09, 5.1) and verify rejection

---

## Code Quality Checklist

Before committing changes:

```bash
# 1. Sort imports
isort .

# 2. Format code
black .

# 3. Lint code
flake8 .

# 4. Check spelling
codespell

# 5. Run all pre-commit hooks
pre-commit run --all-files

# 6. Run full test suite
pytest

# 7. Verify configuration validator
python tools/config_validator.py
```

All must pass before creating PR.

---

## File Modification Checklist

When implementing this feature, you'll modify:

- [ ] `const.py` - Add `CONF_HEAT_TOLERANCE`, `CONF_COOL_TOLERANCE`
- [ ] `schemas.py` - Add tolerance fields to advanced schema
- [ ] `environment_manager.py` - Add mode tracking and tolerance selection
- [ ] `climate.py` - Call `set_hvac_mode()` on mode changes
- [ ] `options_flow.py` - Add tolerance fields to advanced settings
- [ ] `translations/en.json` - Add UI strings for new fields
- [ ] `tools/focused_config_dependencies.json` - Document parameters
- [ ] `tools/config_validator.py` - Add validation rules
- [ ] `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` - Document behavior
- [ ] `tests/managers/test_environment_manager.py` - Add unit tests
- [ ] `tests/config_flow/test_options_flow.py` - Add UI tests
- [ ] `tests/config_flow/test_e2e_*_persistence.py` - Add E2E tests (4 files)
- [ ] `tests/config_flow/test_*_features_integration.py` - Add integration tests (4 files)
- [ ] `tests/test_heater_mode.py` - Add functional tests
- [ ] `tests/test_cooler_mode.py` - Add functional tests
- [ ] `tests/test_heat_pump_mode.py` - Add functional tests

**Total**: 7 core files + 9 test files = 16 files

---

## Useful Commands

```bash
# Find all references to cold_tolerance
grep -r "cold_tolerance" custom_components/dual_smart_thermostat/

# Find all HVAC mode usages
grep -r "HVACMode\." custom_components/dual_smart_thermostat/

# Run tests matching pattern
pytest -k "tolerance" -v

# Run tests with coverage for specific file
pytest --cov=custom_components/dual_smart_thermostat/managers/environment_manager.py tests/managers/

# Check test coverage summary
pytest --cov=custom_components/dual_smart_thermostat --cov-report=term-missing

# Run specific test with detailed output
pytest tests/managers/test_environment_manager.py::test_tolerance_selection -vvs --log-cli-level=DEBUG
```

---

## Resources

- **Feature Spec**: [`specs/002-separate-tolerances/spec.md`](./spec.md)
- **Implementation Plan**: [`specs/002-separate-tolerances/plan.md`](./plan.md)
- **Research Findings**: [`specs/002-separate-tolerances/research.md`](./research.md)
- **Data Model**: [`specs/002-separate-tolerances/data-model.md`](./data-model.md)
- **API Contract**: [`specs/002-separate-tolerances/contracts/tolerance_selection_api.md`](./contracts/tolerance_selection_api.md)
- **Project Guidelines**: [`CLAUDE.md`](../../CLAUDE.md)
- **Constitution**: [`.specify/memory/constitution.md`](../../.specify/memory/constitution.md)

---

## Getting Help

1. **Read the spec**: Start with `spec.md` for requirements
2. **Check research**: Review `research.md` for design decisions
3. **Review API contract**: See `contracts/tolerance_selection_api.md` for interfaces
4. **Run tests**: Tests document expected behavior
5. **Check logs**: Enable DEBUG logging for detailed execution trace

**Happy coding!** 🚀
