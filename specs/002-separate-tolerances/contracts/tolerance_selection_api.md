# API Contract: Tolerance Selection Interface

**Version**: 1.0.0
**Date**: 2025-10-29
**Component**: `EnvironmentManager` (managers/environment_manager.py)
**Purpose**: Define interface for mode-aware temperature tolerance selection

---

## Overview

The Tolerance Selection API provides methods for tracking HVAC mode state and determining active temperature tolerances based on current mode and configuration. This enables separate tolerance behavior for heating and cooling operations while maintaining backward compatibility with legacy configurations.

**Key Principles**:
- Priority-based tolerance selection (mode-specific → legacy → default)
- Immediate tolerance updates on mode changes (no restart required)
- Backward compatible with existing `is_too_cold()` / `is_too_hot()` interface
- Tolerances always available (legacy fallback ensures non-null)

---

## Method Signatures

### 1. set_hvac_mode

**Purpose**: Update current HVAC mode for tolerance selection

```python
def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    """
    Set the current HVAC mode for tolerance selection.

    This method should be called by the climate entity whenever the HVAC mode
    changes. The stored mode is used to select appropriate tolerances for
    temperature comparisons.

    Args:
        hvac_mode (HVACMode): Current HVAC mode from Home Assistant climate platform.
            Valid values: HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF

    Returns:
        None

    Raises:
        None (method is fault-tolerant)

    Side Effects:
        - Updates self._hvac_mode internal state
        - Logs debug message with new mode
        - Next is_too_cold/hot call uses new mode for tolerance selection

    Examples:
        >>> environment.set_hvac_mode(HVACMode.HEAT)
        >>> # Next temperature check uses heat_tolerance (or legacy)

        >>> environment.set_hvac_mode(HVACMode.COOL)
        >>> # Next temperature check uses cool_tolerance (or legacy)
    """
```

**Call Sites**:
- `climate.py`: Called in `async_set_hvac_mode()` after mode change
- `climate.py`: Called during state restoration after loading saved mode

**Performance**: O(1), <1μs execution time

---

### 2. _get_active_tolerance_for_mode (Private)

**Purpose**: Determine active tolerance values based on current HVAC mode

```python
def _get_active_tolerance_for_mode(self) -> tuple[float, float]:
    """
    Get active cold and hot tolerance values for current HVAC mode.

    Implements priority-based tolerance selection:
      Priority 1: Mode-specific tolerance (heat_tolerance or cool_tolerance)
      Priority 2: Legacy tolerances (cold_tolerance, hot_tolerance)
      Priority 3: DEFAULT_TOLERANCE (0.3) - already in legacy fallback

    Returns:
        tuple[float, float]: (cold_tolerance, hot_tolerance) to use for comparisons
            Both values are always valid floats (never None)

    Notes:
        - For HEAT mode: Returns (heat_tol, heat_tol) if set, else legacy
        - For COOL mode: Returns (cool_tol, cool_tol) if set, else legacy
        - For HEAT_COOL: Checks current vs target temp to determine operation
        - For FAN_ONLY: Uses cool_tolerance (fan behaves like cooling)
        - For DRY/OFF: Returns legacy (no active tolerance checks)
        - If _hvac_mode is None: Returns legacy (safe fallback)

    Examples:
        >>> # With heat_tolerance=0.3, cool_tolerance=2.0, mode=HEAT
        >>> cold_tol, hot_tol = self._get_active_tolerance_for_mode()
        >>> assert cold_tol == 0.3 and hot_tol == 0.3

        >>> # With no mode-specific, mode=COOL
        >>> cold_tol, hot_tol = self._get_active_tolerance_for_mode()
        >>> assert cold_tol == self._cold_tolerance
        >>> assert hot_tol == self._hot_tolerance
    """
```

**Called By**:
- `is_too_cold()`: Gets active tolerance before temperature comparison
- `is_too_hot()`: Gets active tolerance before temperature comparison

**Performance**: O(1), <5μs execution time (simple conditionals)

---

### 3. is_too_cold (Modified)

**Purpose**: Check if current temperature is below target threshold

```python
def is_too_cold(self, target_attr: str = "_target_temp") -> bool:
    """
    Check if current temperature is below target minus cold tolerance.

    This method now uses mode-aware tolerance selection. The active cold
    tolerance is determined by _get_active_tolerance_for_mode() based on
    current HVAC mode and configured tolerances.

    Args:
        target_attr (str): Attribute name for target temperature.
            Default: "_target_temp"
            Other values: "_target_temp_high", "_target_temp_low"

    Returns:
        bool: True if temperature is too cold (heating needed)
              False if sensor unavailable, target not set, or temp adequate

    Algorithm:
        cold_tol, _ = self._get_active_tolerance_for_mode()
        return target_temp >= current_temp + cold_tol

    Error Handling:
        - Returns False if self._cur_temp is None (sensor failure)
        - Returns False if target_temp is None (no setpoint)
        - Logs debug message with comparison details

    Examples:
        >>> # HEAT mode, heat_tolerance=0.3, target=20, current=19.6
        >>> environment.set_hvac_mode(HVACMode.HEAT)
        >>> assert environment.is_too_cold() == True  # 20 >= 19.6 + 0.3

        >>> # COOL mode, cool_tolerance=2.0, target=20, current=19.6
        >>> environment.set_hvac_mode(HVACMode.COOL)
        >>> assert environment.is_too_cold() == False  # 20 < 19.6 + 2.0
    """
```

**Backward Compatibility**: ✅ Same signature, behavior enhanced with mode awareness

---

### 4. is_too_hot (Modified)

**Purpose**: Check if current temperature is above target threshold

```python
def is_too_hot(self, target_attr: str = "_target_temp") -> bool:
    """
    Check if current temperature is above target plus hot tolerance.

    This method now uses mode-aware tolerance selection. The active hot
    tolerance is determined by _get_active_tolerance_for_mode() based on
    current HVAC mode and configured tolerances.

    Args:
        target_attr (str): Attribute name for target temperature.
            Default: "_target_temp"
            Other values: "_target_temp_high", "_target_temp_low"

    Returns:
        bool: True if temperature is too hot (cooling needed)
              False if sensor unavailable, target not set, or temp adequate

    Algorithm:
        _, hot_tol = self._get_active_tolerance_for_mode()
        return current_temp >= target_temp + hot_tol

    Error Handling:
        - Returns False if self._cur_temp is None (sensor failure)
        - Returns False if target_temp is None (no setpoint)
        - Logs debug message with comparison details

    Examples:
        >>> # COOL mode, cool_tolerance=2.0, target=22, current=24.1
        >>> environment.set_hvac_mode(HVACMode.COOL)
        >>> assert environment.is_too_hot() == True  # 24.1 >= 22 + 2.0

        >>> # HEAT mode, heat_tolerance=0.3, target=20, current=20.1
        >>> environment.set_hvac_mode(HVACMode.HEAT)
        >>> assert environment.is_too_hot() == False  # 20.1 < 20 + 0.3
    """
```

**Backward Compatibility**: ✅ Same signature, behavior enhanced with mode awareness

---

## Tolerance Selection Algorithm

### Pseudocode

```python
def _get_active_tolerance_for_mode() -> tuple[float, float]:
    # HEAT mode: Use heat_tolerance if configured
    if self._hvac_mode == HVACMode.HEAT:
        if self._heat_tolerance is not None:
            return (self._heat_tolerance, self._heat_tolerance)

    # COOL mode: Use cool_tolerance if configured
    elif self._hvac_mode == HVACMode.COOL:
        if self._cool_tolerance is not None:
            return (self._cool_tolerance, self._cool_tolerance)

    # FAN_ONLY: Use cool_tolerance (fan behaves like cooling)
    elif self._hvac_mode == HVACMode.FAN_ONLY:
        if self._cool_tolerance is not None:
            return (self._cool_tolerance, self._cool_tolerance)

    # HEAT_COOL (Auto): Determine operation from temperature
    elif self._hvac_mode == HVACMode.HEAT_COOL:
        if self._cur_temp is not None and self._target_temp is not None:
            if self._cur_temp < self._target_temp:
                # Currently heating
                if self._heat_tolerance is not None:
                    return (self._heat_tolerance, self._heat_tolerance)
            else:
                # Currently cooling
                if self._cool_tolerance is not None:
                    return (self._cool_tolerance, self._cool_tolerance)

    # Fallback: Use legacy tolerances
    return (self._cold_tolerance, self._hot_tolerance)
```

### Decision Matrix

| HVAC Mode | heat_tol Set? | cool_tol Set? | cur < target? | Active Tolerance |
|-----------|---------------|---------------|---------------|------------------|
| HEAT      | Yes           | -             | -             | heat_tol         |
| HEAT      | No            | -             | -             | legacy           |
| COOL      | -             | Yes           | -             | cool_tol         |
| COOL      | -             | No            | -             | legacy           |
| HEAT_COOL | Yes           | -             | Yes           | heat_tol         |
| HEAT_COOL | -             | Yes           | No            | cool_tol         |
| HEAT_COOL | No            | No            | -             | legacy           |
| FAN_ONLY  | -             | Yes           | -             | cool_tol         |
| FAN_ONLY  | -             | No            | -             | legacy           |
| DRY       | -             | -             | -             | legacy           |
| OFF       | -             | -             | -             | N/A (no checks)  |
| None      | -             | -             | -             | legacy           |

---

## Usage Examples

### Example 1: Basic Heating Mode

```python
# Setup
environment = EnvironmentManager(hass, config)
environment._heat_tolerance = 0.3  # User configured
environment._cool_tolerance = None  # Not configured
environment._cold_tolerance = 0.5   # Legacy
environment._hot_tolerance = 0.5    # Legacy
environment._target_temp = 20.0
environment._cur_temp = 19.6

# Set heating mode
environment.set_hvac_mode(HVACMode.HEAT)

# Check if too cold
cold_tol, hot_tol = environment._get_active_tolerance_for_mode()
# Returns: (0.3, 0.3) - uses heat_tolerance

is_cold = environment.is_too_cold()
# Calculation: 20.0 >= 19.6 + 0.3 → 20.0 >= 19.9 → True
# Result: True (heating needed)

is_hot = environment.is_too_hot()
# Calculation: 19.6 >= 20.0 + 0.3 → 19.6 >= 20.3 → False
# Result: False (cooling not needed)
```

### Example 2: Cooling Mode with Loose Tolerance

```python
# Setup
environment._heat_tolerance = 0.3
environment._cool_tolerance = 2.0  # User wants loose cooling control
environment._target_temp = 22.0
environment._cur_temp = 23.5

# Set cooling mode
environment.set_hvac_mode(HVACMode.COOL)

# Check temperatures
cold_tol, hot_tol = environment._get_active_tolerance_for_mode()
# Returns: (2.0, 2.0) - uses cool_tolerance

is_cold = environment.is_too_cold()
# Calculation: 22.0 >= 23.5 + 2.0 → 22.0 >= 25.5 → False
# Result: False (heating not needed)

is_hot = environment.is_too_hot()
# Calculation: 23.5 >= 22.0 + 2.0 → 23.5 >= 24.0 → False
# Result: False (cooling not needed yet - within tolerance)
```

### Example 3: HEAT_COOL Auto Mode Switching

```python
# Setup
environment._heat_tolerance = 0.3
environment._cool_tolerance = 2.0
environment._target_temp = 21.0

# Set auto mode
environment.set_hvac_mode(HVACMode.HEAT_COOL)

# Scenario A: Currently cold (heating operation)
environment._cur_temp = 20.5  # Below target

cold_tol, hot_tol = environment._get_active_tolerance_for_mode()
# cur_temp (20.5) < target (21.0) → heating
# Returns: (0.3, 0.3) - uses heat_tolerance

is_cold = environment.is_too_cold()
# Calculation: 21.0 >= 20.5 + 0.3 → 21.0 >= 20.8 → True
# Result: True (heating needed)

# Scenario B: Temperature crosses target (cooling operation)
environment._cur_temp = 21.5  # Above target

cold_tol, hot_tol = environment._get_active_tolerance_for_mode()
# cur_temp (21.5) >= target (21.0) → cooling
# Returns: (2.0, 2.0) - uses cool_tolerance

is_hot = environment.is_too_hot()
# Calculation: 21.5 >= 21.0 + 2.0 → 21.5 >= 23.0 → False
# Result: False (cooling not needed yet)
```

### Example 4: Backward Compatibility (Legacy Config)

```python
# Setup - Old config without mode-specific tolerances
environment._heat_tolerance = None   # Not configured
environment._cool_tolerance = None   # Not configured
environment._cold_tolerance = 0.5    # Legacy
environment._hot_tolerance = 0.5     # Legacy
environment._target_temp = 20.0
environment._cur_temp = 19.4

# Set any mode
environment.set_hvac_mode(HVACMode.HEAT)

# Get tolerance
cold_tol, hot_tol = environment._get_active_tolerance_for_mode()
# Returns: (0.5, 0.5) - falls back to legacy

is_cold = environment.is_too_cold()
# Calculation: 20.0 >= 19.4 + 0.5 → 20.0 >= 19.9 → True
# Result: True (same as old behavior)
```

---

## Error Handling

### Sensor Failure

**Condition**: Temperature sensor unavailable (`self._cur_temp is None`)

**Behavior**:
```python
# is_too_cold() returns False
if self._cur_temp is None or target_temp is None:
    return False

# No HVAC action taken (safe failure mode)
```

**Rationale**: Prevents equipment damage from operating without temperature feedback

### Missing Target Temperature

**Condition**: No setpoint configured (`target_temp is None`)

**Behavior**:
```python
# is_too_cold() and is_too_hot() return False
if self._cur_temp is None or target_temp is None:
    return False
```

**Rationale**: Requires explicit target before HVAC operation

### HVAC Mode Not Set

**Condition**: `self._hvac_mode is None` (climate entity not yet initialized)

**Behavior**:
```python
# Falls back to legacy tolerances
if self._hvac_mode is None or self._hvac_mode not in [HEAT, COOL, ...]:
    return (self._cold_tolerance, self._hot_tolerance)
```

**Rationale**: Safe fallback ensures system remains operational

### Invalid Tolerance Configuration

**Condition**: Tolerance value outside valid range (caught at config time)

**Behavior**:
- Options flow validation prevents saving invalid values (0.1-5.0 range)
- If somehow stored, runtime uses the value (assumes user knows best)

**Prevention**: voluptuous schema validation in options flow

---

## Performance Characteristics

**Memory Impact**:
- Adds 3 attributes to EnvironmentManager: `_hvac_mode`, `_heat_tolerance`, `_cool_tolerance`
- Size: ~24 bytes (1 enum + 2 optional floats)
- Negligible impact (<0.01% of typical memory usage)

**CPU Impact**:
- `set_hvac_mode()`: O(1), <1μs
- `_get_active_tolerance_for_mode()`: O(1), <5μs (5-10 conditionals)
- `is_too_cold()` / `is_too_hot()`: +5μs overhead (tolerance selection)
- Total impact: <10μs per temperature check

**Call Frequency**:
- `set_hvac_mode()`: Once per mode change (~0-10 times/day)
- `is_too_cold()` / `is_too_hot()`: Every sensor update (~5-60 times/minute)
- Performance: Well within acceptable limits (<10ms budget)

---

## Testing Contract

### Unit Test Requirements

Test coverage must include:

1. **set_hvac_mode()**:
   - Verify mode stored correctly for all HVACMode values
   - Verify debug logging

2. **_get_active_tolerance_for_mode()**:
   - All HVAC modes (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF)
   - Mode-specific tolerance set vs not set
   - HEAT_COOL with cur_temp < target (heating) and cur_temp >= target (cooling)
   - Legacy fallback when mode-specific not set
   - None hvac_mode handling

3. **is_too_cold() / is_too_hot()**:
   - With mode-specific tolerance
   - With legacy tolerance
   - With sensor failure (cur_temp is None)
   - With no target (target_temp is None)
   - Boundary conditions (exactly at threshold)

### Integration Test Requirements

- Tolerance values persist through restart
- Mode changes update active tolerance immediately
- All 4 system types work correctly with new tolerances
- Backward compatibility with legacy configurations

### Expected Test Count

- Unit tests: ~15 test cases
- Integration tests: ~10 test cases
- Total: ~25 test cases

---

## Backward Compatibility Guarantee

✅ **API Compatibility**: `is_too_cold()` and `is_too_hot()` signatures unchanged
✅ **Behavior Compatibility**: Legacy configs (without mode-specific tolerances) work identically
✅ **State Compatibility**: No migration required, old state restores correctly
✅ **Configuration Compatibility**: Old config entries load without modification

**Breaking Changes**: NONE

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-10-29 | Initial API contract definition |

---

## References

- **Implementation**: `custom_components/dual_smart_thermostat/managers/environment_manager.py`
- **Configuration**: `custom_components/dual_smart_thermostat/const.py`
- **User Interface**: `custom_components/dual_smart_thermostat/options_flow.py`
- **Tests**: `tests/managers/test_environment_manager.py`
- **Spec**: `specs/002-separate-tolerances/spec.md`
