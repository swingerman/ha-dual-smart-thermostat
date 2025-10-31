# Issue #407: Separate Tolerances - IMPLEMENTATION COMPLETE ✅

**Status**: Fully Implemented and Tested
**Branch**: 002-separate-tolerances
**Completion Date**: 2025-10-31
**Test Coverage**: 1,184 tests passing (100%)

---

## 🎉 Feature Summary

Successfully implemented mode-specific temperature tolerances for dual-mode HVAC systems (heater+cooler and heat pump). Users can now configure different temperature tolerances for heating vs cooling operations.

### Key Implementation Decision

**IMPORTANT**: Mode-specific tolerances (`heat_tolerance`, `cool_tolerance`) are **only available for dual-mode systems**:

- ✅ **Heater + Cooler** (`heater_cooler`)
- ✅ **Heat Pump** (`heat_pump`)
- ❌ **Simple Heater** (`simple_heater`) - uses legacy tolerances only
- ❌ **AC Only** (`ac_only`) - uses legacy tolerances only

This was an architectural decision made during implementation - single-mode systems don't need separate tolerances per mode.

---

## 📊 What Was Implemented

### Core Features

1. **Mode-Specific Tolerance Parameters**
   ```yaml
   heat_tolerance: 0.3  # Tolerance for heating mode
   cool_tolerance: 2.0  # Tolerance for cooling mode
   ```

2. **System-Type Aware UI**
   - Config flow only shows tolerances for dual-mode systems
   - Options flow conditionally displays based on system type
   - Prevents user confusion by hiding irrelevant options

3. **Intelligent Fallback Hierarchy**
   ```
   1. Mode-specific tolerance (if configured for dual-mode system)
   2. Legacy tolerance (cold_tolerance/hot_tolerance)
   3. Default tolerance (0.3°C/°F)
   ```

### Configuration Examples

**Heater + Cooler System**:
```yaml
system_type: heater_cooler
heater: switch.heater
cooler: switch.ac_unit
target_sensor: sensor.temperature
heat_tolerance: 0.3   # Tight heating control
cool_tolerance: 2.0   # Loose cooling for energy savings
```

**Heat Pump System**:
```yaml
system_type: heat_pump
heater: switch.heat_pump
heat_pump_cooling: binary_sensor.heat_pump_mode
target_sensor: sensor.temperature
heat_tolerance: 0.5
cool_tolerance: 1.5
```

**Single-Mode System** (uses legacy):
```yaml
system_type: simple_heater
heater: switch.heater
target_sensor: sensor.temperature
cold_tolerance: 0.3  # Legacy tolerance still works
```

---

## 📁 Files Modified

### Core Implementation (6 files)
1. `custom_components/dual_smart_thermostat/const.py` - Added constants
2. `custom_components/dual_smart_thermostat/schemas.py` - Dual-mode schema integration
3. `custom_components/dual_smart_thermostat/options_flow.py` - System-type aware UI
4. `custom_components/dual_smart_thermostat/managers/environment_manager.py` - Tolerance logic
5. `custom_components/dual_smart_thermostat/climate.py` - HVAC mode tracking
6. `custom_components/dual_smart_thermostat/translations/en.json` - Dual-mode translations

### Test Coverage (51 tests added)
- 14 unit tests for tolerance selection logic
- 20 config flow integration tests
- 10 E2E persistence tests
- 7 functional runtime tests

### Documentation
- `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` - Added system-type constraints section

---

## ✅ All Success Criteria Met

### Functionality ✅
- ✅ Legacy configurations work unchanged
- ✅ Mode-specific tolerances override legacy behavior (dual-mode only)
- ✅ All HVAC modes work correctly
- ✅ Tolerance values persist through restarts and reconfiguration

### Code Quality ✅
- ✅ Passes all linting (isort, black, flake8, codespell, mypy)
- ✅ All 1,184 tests pass (100%)
- ✅ Comprehensive test coverage added
- ✅ Follows project architecture patterns

### Documentation ✅
- ✅ Configuration dependencies documented with system-type constraints
- ✅ Translations complete (en.json - dual-mode systems only)
- ✅ Implementation fully documented

### Testing ✅
- ✅ Unit tests for tolerance selection logic
- ✅ Config flow integration tests
- ✅ E2E persistence tests
- ✅ Functional runtime tests

---

## 🔧 Technical Implementation Details

### Tolerance Selection Algorithm

Location: `custom_components/dual_smart_thermostat/managers/environment_manager.py:289-356`

```python
def _get_active_tolerance_for_mode(self, hvac_mode: HVACMode):
    """Get tolerance based on current HVAC mode with priority-based selection."""

    # Priority 1: Mode-specific tolerances (dual-mode systems only)
    if hvac_mode == HVACMode.HEAT and self._heat_tolerance is not None:
        return (self._heat_tolerance, self._heat_tolerance)
    elif hvac_mode == HVACMode.COOL and self._cool_tolerance is not None:
        return (self._cool_tolerance, self._cool_tolerance)

    # Priority 2: Legacy tolerances
    if self._cold_tolerance is not None or self._hot_tolerance is not None:
        cold_tol = self._cold_tolerance if self._cold_tolerance is not None else DEFAULT_TOLERANCE
        hot_tol = self._hot_tolerance if self._hot_tolerance is not None else DEFAULT_TOLERANCE
        return (cold_tol, hot_tol)

    # Priority 3: Default
    return (DEFAULT_TOLERANCE, DEFAULT_TOLERANCE)
```

### System-Type Awareness

Location: `custom_components/dual_smart_thermostat/options_flow.py:282-317`

```python
# Only show mode-specific tolerances for dual-mode systems
if system_type in (SYSTEM_TYPE_HEATER_COOLER, SYSTEM_TYPE_HEAT_PUMP):
    advanced_dict[vol.Optional(CONF_HEAT_TOLERANCE)] = selector.NumberSelector(...)
    advanced_dict[vol.Optional(CONF_COOL_TOLERANCE)] = selector.NumberSelector(...)
```

---

## 🐛 Critical Bugs Fixed

### 1. DEFAULT_TOLERANCE Fallback Bug
**Issue**: Returned `(None, None)` when legacy tolerances weren't configured
**Fix**: Proper fallback to DEFAULT_TOLERANCE (0.3)
**Location**: `environment_manager.py:347-355`

### 2. Async Timing Test Failures
**Issue**: State changes didn't propagate before assertions
**Fix**: Added explicit service calls and cleanup, pytest marker for lingering timers
**Location**: `tests/test_heat_pump_mode.py:840-960`

### 3. Invalid Tests for Single-Mode Systems
**Issue**: Tests validated mode-specific tolerances on systems that don't support them
**Fix**: Removed 7 invalid tests
**Files**: `test_e2e_ac_only_persistence.py`, `test_e2e_simple_heater_persistence.py`, `test_options_flow.py`

---

## 📚 Key Architectural Decisions

### Decision 1: System-Type Constraints vs Parameter Dependencies

**Choice**: Implemented as system-type architectural constraints, not parameter dependencies

**Rationale**:
- Single-mode systems fundamentally don't need separate tolerances per mode
- Prevents user confusion by hiding irrelevant options in UI
- Cleaner architecture than complex dependency validation

**Implementation**:
- Schema integration: Only dual-mode schemas include tolerance fields
- Options flow: Conditional display based on system type
- Documentation: Clear explanation of availability by system type

### Decision 2: Priority-Based Tolerance Selection

**Choice**: Mode-specific → Legacy → Default

**Rationale**:
- Backward compatible (legacy still works)
- Opt-in (mode-specific only when configured)
- Clear fallback chain prevents undefined behavior

### Decision 3: No heat_cool_tolerance Parameter

**Original Plan**: Include `heat_cool_tolerance` for HEAT_COOL mode

**Final Decision**: Removed from scope

**Rationale**:
- HEAT_COOL mode uses HEAT or COOL internally based on operation
- Existing heat_tolerance and cool_tolerance suffice
- Simplifies configuration and reduces complexity
- Can be added later if needed

---

## 🎓 Lessons Learned

### 1. System-Type Awareness is Critical
Initial implementation added tolerances to all system types. User testing revealed confusion when options appeared for systems that didn't need them. System-type filtering prevents this.

### 2. Async State Propagation Requires Care
Test failures revealed timing issues with async state changes. Solution: explicit service calls and proper cleanup.

### 3. Test Consolidation Reduces Maintenance
Rather than creating separate test files for each bug fix, integrated tests into existing consolidated test files for better maintainability.

---

## 🚀 Future Enhancements

### Potential Additions
1. **heat_cool_tolerance** - If users request it for HEAT_COOL mode
2. **Preset-Specific Tolerances** - Different tolerances per preset
3. **Time-Based Tolerances** - Different tolerances by time of day

### Migration Path
All enhancements can build on the existing architecture:
- Add new optional parameters
- Extend tolerance selection logic
- Maintain backward compatibility

---

## 📞 References

### Original Issue
- **GitHub Issue**: [#407](https://github.com/swingerman/ha-dual-smart-thermostat/issues/407)
- **User Request**: Separate tolerances for heating and cooling
- **Use Case**: Tight heating control + loose cooling for energy savings

### Documentation
- `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` - Configuration constraints
- `CLAUDE.md` - Project coding standards
- `docs/config_flow/step_ordering.md` - Configuration flow rules

### Code Locations
- `custom_components/dual_smart_thermostat/const.py:82` - Constants
- `custom_components/dual_smart_thermostat/managers/environment_manager.py:289-356` - Tolerance logic
- `custom_components/dual_smart_thermostat/schemas.py:298-404` - Schema integration
- `custom_components/dual_smart_thermostat/options_flow.py:282-317` - System-type aware UI

---

## ✨ Summary

Successfully implemented mode-specific temperature tolerances with:
- **100% test pass rate** (1,184 tests)
- **System-type aware configuration** (prevents user confusion)
- **Backward compatible** (legacy tolerances still work)
- **Well documented** (code, tests, user docs)
- **Production ready** (all quality checks pass)

The feature is complete, tested, and ready for merge.

**Next Steps**: Create pull request to merge `002-separate-tolerances` branch to master.
