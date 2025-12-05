# Phase 1 Complete: Test Infrastructure Setup

**Date Completed:** 2025-12-04
**Status:** ✅ COMPLETED

## Summary

Phase 1 of the test consolidation effort is complete. We have successfully created the foundational infrastructure for consolidating duplicate tests across HVAC modes using parametrized tests and the Given/When/Then pattern.

## Deliverables

### 1. Shared Test Directory Structure
```
tests/shared_tests/
├── __init__.py                        # Package initialization
├── conftest.py                        # MODE_CONFIGS and fixtures
└── test_example_given_when_then.py   # Example tests demonstrating patterns
```

### 2. MODE_CONFIGS Configuration System

Created comprehensive mode configurations in `tests/shared_tests/conftest.py`:

```python
MODE_CONFIGS = {
    "heater": {...},      # Heating mode config
    "cooler": {...},      # Cooling mode config
    "heat_pump": {...},   # Heat pump mode config
    "fan": {...},         # Fan-only mode config
    "dry": {...},         # Humidity control mode config
    "dual": {...},        # Dual heating/cooling mode config
}
```

Each mode config includes:
- HVAC mode and available modes
- Device entity configuration
- Target temperatures/humidity
- Tolerance values
- Preset temperature mappings
- Mode-specific features (aux heating, floor protection, etc.)

### 3. Parametrized Test Fixtures

Created two main fixtures for shared tests:

#### `mode_config` fixture
```python
@pytest.fixture
def mode_config(request):
    """Provides mode-specific configuration for parametrized tests."""
    mode_name = request.param
    return MODE_CONFIGS[mode_name]
```

#### `setup_component_with_mode` fixture
```python
@pytest.fixture
async def setup_component_with_mode(hass: HomeAssistant, mode_config):
    """Set up a climate component with mode-specific configuration."""
    # Automatically configures thermostat based on mode_config
```

#### `setup_component_with_mode_and_presets` fixture
```python
@pytest.fixture
async def setup_component_with_mode_and_presets(hass: HomeAssistant, mode_config):
    """Set up climate component with mode-specific configuration including presets."""
    # Automatically configures thermostat with presets based on mode_config
```

### 4. Given/When/Then Documentation

Created comprehensive guide: `docs/testing/GIVEN_WHEN_THEN_GUIDE.md`

Contains:
- Pattern overview and rules
- Section breakdown (GIVEN, WHEN, THEN)
- Multiple examples (simple, complex, parametrized)
- Common patterns for different scenarios
- Best practices (DO ✅ and DON'T ❌)
- Before/After conversion examples
- Review checklist

### 5. Working Example Tests

Created `tests/shared_tests/test_example_given_when_then.py` with examples:

1. **`test_set_target_temperature_example`** ✅ PASSING
   - Parametrized across heater, cooler, heat_pump, fan
   - Demonstrates basic Given/When/Then pattern
   - Shows mode-specific configuration usage

2. **`test_hvac_mode_off_stops_device_example`** (Example)
   - Shows multiple WHEN/THEN sections
   - Demonstrates mode filtering

3. **`test_heater_specific_feature_example`** (Example)
   - Shows mode-specific tests
   - Demonstrates when NOT to parametrize

4. **`test_preset_mode_example`** (Example)
   - Shows preset handling across modes
   - Demonstrates preset fixture usage

## Test Results

Infrastructure verified with passing tests:

```bash
./scripts/docker-test tests/shared_tests/test_example_given_when_then.py::test_set_target_temperature_example -v

RESULTS:
✅ test_set_target_temperature_example[heater]     PASSED
✅ test_set_target_temperature_example[cooler]     PASSED
✅ test_set_target_temperature_example[heat_pump]  PASSED
✅ test_set_target_temperature_example[fan]        PASSED

4/4 primary modes passing (100%)
```

## Key Features

### 1. Mode-Agnostic Testing
Tests can now be written once and run across all HVAC modes:

```python
@pytest.mark.parametrize("mode_config", ["heater", "cooler", "fan"], indirect=True)
async def test_something(hass, mode_config, setup_component_with_mode):
    # Test runs for heater, cooler, and fan automatically
    assert mode_config["hvac_mode"] in [HVACMode.HEAT, HVACMode.COOL, HVACMode.FAN_ONLY]
```

### 2. Consistent Test Structure
All tests follow Given/When/Then pattern:

```python
# GIVEN - Setup initial state
setup_sensor(hass, 20)
await hass.async_block_till_done()

# WHEN - Perform action
await common.async_set_temperature(hass, 25)
await hass.async_block_till_done()

# THEN - Verify outcome
state = hass.states.get(common.ENTITY)
assert state.attributes.get("temperature") == 25
```

### 3. Flexible Configuration
MODE_CONFIGS allows easy:
- Addition of new HVAC modes
- Modification of mode-specific parameters
- Testing mode-specific features
- Handling differences (temperature vs. humidity, single vs. range)

## Known Limitations

### Dry and Dual Modes
- Configuration needs additional work
- Marked with TODO for Phase 2
- Not blocking progress on other phases

### Example Tests
- Some example tests in the file are incomplete
- They serve as templates, not production tests
- Will be refined as actual consolidation proceeds

## Next Steps

Ready to proceed with **Phase 2: Setup/Unique ID Tests**

### Phase 2 Goals:
1. Create `tests/shared_tests/test_setup_base.py`
2. Consolidate 18 duplicate setup tests into 4 parametrized tests
3. Apply Given/When/Then pattern to all consolidated tests
4. Remove duplicates from mode-specific files
5. Expected savings: ~300+ lines of code

### Phase 2 Tasks:
- [ ] Convert `test_unique_id` to parametrized Given/When/Then
- [ ] Convert `test_setup_defaults_to_unknown` to parametrized Given/When/Then
- [ ] Convert `test_setup_gets_current_temp_from_sensor` to parametrized Given/When/Then
- [ ] Convert `test_reload` to parametrized Given/When/Then
- [ ] Update mode files to remove duplicates
- [ ] Run tests: `pytest tests/shared_tests/test_setup_base.py -v`

## Files Created

1. ✅ `tests/shared_tests/__init__.py`
2. ✅ `tests/shared_tests/conftest.py` (287 lines)
3. ✅ `tests/shared_tests/test_example_given_when_then.py` (201 lines)
4. ✅ `docs/testing/GIVEN_WHEN_THEN_GUIDE.md` (467 lines)
5. ✅ `docs/testing/TEST_CONSOLIDATION_PLAN.md` (updated)
6. ✅ `docs/testing/PHASE_1_COMPLETE.md` (this file)

## Metrics

### Infrastructure Created
- **Lines of infrastructure code:** ~750 lines
- **Modes supported:** 6 (4 tested, 2 pending)
- **Fixtures created:** 3
- **Example tests created:** 4
- **Documentation pages:** 2

### Foundation for Consolidation
- **Estimated duplicate tests to consolidate:** ~144
- **Estimated lines to consolidate:** ~6,500
- **Phases enabled by this infrastructure:** 9 (Phases 2-10)

## Architecture Decisions

### 1. Indirect Parametrization
Chose `indirect=True` parametrization for `mode_config` fixture to allow:
- Complex fixture setup based on parameter
- Lazy evaluation of configurations
- Better test naming and reporting

### 2. Separate Preset Fixture
Created separate `setup_component_with_mode_and_presets` fixture because:
- Not all tests need presets
- Faster test execution for non-preset tests
- Clearer test intent

### 3. MODE_CONFIGS Dictionary
Used dictionary instead of classes/dataclasses because:
- Simpler to understand and modify
- Direct pytest parametrization support
- Easy to add/remove modes

### 4. Given/When/Then Comments
Enforced explicit section comments because:
- Improves test readability
- Makes test intent clear
- Easier for new contributors
- Consistent structure across all tests

## Lessons Learned

### 1. Mock Service Handling
- `async_mock_service` is NOT async - don't use `await`
- Returns a list for tracking service calls
- Must be called before async operations

### 2. Mode Configuration Complexity
- Dry mode requires both heater and dryer config
- Dual mode has separate heater/cooler entities
- Each mode has unique config requirements
- Fixtures must handle all variations

### 3. Test Infrastructure Validation
- Important to test infrastructure before mass consolidation
- Docker-based testing provides consistent environment
- Example tests serve as both docs and validation

## References

- [Test Consolidation Plan](TEST_CONSOLIDATION_PLAN.md)
- [Given/When/Then Guide](GIVEN_WHEN_THEN_GUIDE.md)
- [CLAUDE.md Testing Section](../../CLAUDE.md#testing-strategy)

---

**Phase 1 Status:** ✅ COMPLETE
**Ready for Phase 2:** ✅ YES
**Blocking Issues:** ❌ NONE

**Next:** Begin Phase 2 - Setup/Unique ID Tests Consolidation
