# Research: Separate Temperature Tolerances

**Date**: 2025-10-29
**Branch**: `002-separate-tolerances`
**Purpose**: Resolve technical unknowns for implementation

---

## Research Task 1: Environment Manager HVAC Mode Tracking

### Question
How should environment manager receive current HVAC mode?

### Investigation

**Current Implementation Review**:
- `EnvironmentManager` in `managers/environment_manager.py` currently stores tolerances in `__init__`:
  - `self._cold_tolerance = config.get(CONF_COLD_TOLERANCE)`
  - `self._hot_tolerance = config.get(CONF_HOT_TOLERANCE)`
- Methods `is_too_cold()` and `is_too_hot()` directly use these tolerance values
- No current HVAC mode tracking in environment manager
- Climate entity (`climate.py`) maintains `self._hvac_mode` state

**Options Evaluated**:

1. **Pass mode per-call** (e.g., `is_too_cold(target_attr, hvac_mode)`)
   - Pros: No state in environment manager, always current
   - Cons: Changes API signature, requires all callers to pass mode

2. **Store mode as state** (e.g., `set_hvac_mode(mode)` called by climate entity)
   - Pros: Minimal API changes, mode available for tolerance selection
   - Cons: Requires climate entity to notify on mode changes

3. **Store mode-specific tolerances only** (compute at runtime in is_too_cold/hot)
   - Pros: No mode tracking needed
   - Cons: Still need to know current mode for selection, doesn't solve problem

### Decision

**Selected**: Option 2 - Store mode as state

**Rationale**:
- Climate entity already tracks HVAC mode and notifies on changes
- Adding `set_hvac_mode(mode)` is minimal API change
- Environment manager can select tolerance based on stored mode
- No changes needed to device layer (they continue calling `is_too_cold()` / `is_too_hot()`)
- Follows existing pattern where climate entity updates environment manager state

**Implementation**:
```python
# In EnvironmentManager.__init__():
self._hvac_mode = None  # Will be set by climate entity

# New method:
def set_hvac_mode(self, hvac_mode: HVACMode) -> None:
    """Update current HVAC mode for tolerance selection."""
    self._hvac_mode = hvac_mode
    _LOGGER.debug("HVAC mode updated to %s", hvac_mode)

# In Climate entity, call on mode change:
self._environment.set_hvac_mode(self._hvac_mode)
```

---

## Research Task 2: Tolerance Selection Algorithm

### Question
What is the exact algorithm for tolerance selection including all edge cases?

### Investigation

**Current Implementation**:
- `is_too_cold()`: `target_temp >= cur_temp + cold_tolerance`
- `is_too_hot()`: `cur_temp >= target_temp + hot_tolerance`
- Both methods return `False` if `cur_temp is None` or `target_temp is None`

**HVAC Modes to Handle**:
- `HEAT`: Use heat_tolerance (or legacy cold+hot)
- `COOL`: Use cool_tolerance (or legacy hot+cold)
- `HEAT_COOL`: Use heat_tolerance when heating, cool_tolerance when cooling
- `FAN_ONLY`: Use cool_tolerance (similar to cooling operation)
- `DRY`: Use dry_tolerance (existing parameter, no changes)
- `OFF`: No tolerance checks performed

**Edge Cases Identified**:
1. Partial configuration (only heat_tolerance set, not cool_tolerance)
2. HEAT_COOL mode determining if currently heating or cooling
3. Sensor unavailable (cur_temp is None)
4. FAN_ONLY mode (decided: use cool_tolerance)

### Decision

**Tolerance Selection Algorithm**:

```python
def _get_active_tolerance_for_mode(self) -> tuple[float, float]:
    """
    Get active cold and hot tolerance based on current HVAC mode.

    Returns:
        tuple[float, float]: (cold_tolerance, hot_tolerance) to use
    """
    # Priority 1: Mode-specific tolerance if available
    if self._hvac_mode == HVACMode.HEAT:
        if self._heat_tolerance is not None:
            return (self._heat_tolerance, self._heat_tolerance)

    elif self._hvac_mode == HVACMode.COOL:
        if self._cool_tolerance is not None:
            return (self._cool_tolerance, self._cool_tolerance)

    elif self._hvac_mode == HVACMode.FAN_ONLY:
        # FAN_ONLY behaves like cooling
        if self._cool_tolerance is not None:
            return (self._cool_tolerance, self._cool_tolerance)

    elif self._hvac_mode == HVACMode.HEAT_COOL:
        # Determine if currently heating or cooling based on temperature
        if self._cur_temp < self._target_temp:
            # Currently heating
            if self._heat_tolerance is not None:
                return (self._heat_tolerance, self._heat_tolerance)
        else:
            # Currently cooling
            if self._cool_tolerance is not None:
                return (self._cool_tolerance, self._cool_tolerance)

    # Priority 2: Legacy cold_tolerance and hot_tolerance
    return (self._cold_tolerance, self._hot_tolerance)
```

**Rationale**:
- Simple, deterministic algorithm
- Mode-specific tolerance takes priority over legacy
- HEAT_COOL uses current temperature vs target to determine operation
- FAN_ONLY treated like cooling (existing behavior with `fan_hot_tolerance`)
- Always has fallback to legacy tolerances

**Edge Case Handling**:
- **Partial configuration**: Falls back to legacy tolerances for non-configured mode
- **Sensor unavailable**: Existing `is_too_cold()` / `is_too_hot()` already return `False` when `cur_temp is None`
- **HEAT_COOL switching**: Uses instantaneous comparison, switches tolerance when crossing target
- **OFF mode**: No tolerance checks performed (no HVAC action)

---

## Research Task 3: Options Flow Advanced Settings Integration

### Question
How to add fields to existing Advanced Settings step without breaking existing flow?

### Investigation

**Current Options Flow Structure**:
- File: `options_flow.py`
- Uses collapsed `section()` for advanced settings
- Advanced settings built dynamically in `async_step_init()`
- Fields added to `advanced_dict` based on system type
- Section created: `vol.Optional("advanced_settings")` with `{"collapsed": True}`
- On submission, advanced settings extracted and flattened to top level

**Current Advanced Settings Fields** (lines 211-283):
- `CONF_MIN_TEMP` / `CONF_MAX_TEMP`
- `CONF_TARGET_TEMP` / `CONF_TARGET_TEMP_HIGH` / `CONF_TARGET_TEMP_LOW`
- `CONF_PRECISION` / `CONF_TEMP_STEP`
- `CONF_COLD_TOLERANCE` / `CONF_HOT_TOLERANCE` (already there!)
- `CONF_KEEP_ALIVE`
- `CONF_INITIAL_HVAC_MODE`

**Key Code Pattern**:
```python
advanced_dict: dict[Any, Any] = {}

# Add fields conditionally
if some_condition:
    advanced_dict[vol.Optional(CONF_SOMETHING)] = selector.NumberSelector(...)

# Create section
if advanced_dict:
    schema_dict[vol.Optional("advanced_settings")] = section(
        vol.Schema(advanced_dict), {"collapsed": True}
    )

# On submit, flatten
if "advanced_settings" in user_input:
    advanced_settings = user_input.pop("advanced_settings")
    if advanced_settings:
        user_input.update(advanced_settings)
```

### Decision

**Add tolerance fields to existing advanced settings structure**

**Implementation**:
```python
# After existing CONF_COLD_TOLERANCE and CONF_HOT_TOLERANCE:

advanced_dict[
    vol.Optional(
        CONF_HEAT_TOLERANCE,
        description={"suggested_value": self.config_entry.data.get(CONF_HEAT_TOLERANCE)},
    )
] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.1,
        max=5.0,
        step=0.1,
        unit_of_measurement=DEGREE,
        mode=selector.NumberSelectorMode.BOX,
    )
)

advanced_dict[
    vol.Optional(
        CONF_COOL_TOLERANCE,
        description={"suggested_value": self.config_entry.data.get(CONF_COOL_TOLERANCE)},
    )
] = selector.NumberSelector(
    selector.NumberSelectorConfig(
        min=0.1,
        max=5.0,
        step=0.1,
        unit_of_measurement=DEGREE,
        mode=selector.NumberSelectorMode.BOX,
    )
)
```

**Rationale**:
- Minimal changes: Add two fields to existing advanced settings dict
- No new step needed, no navigation changes
- Uses same pattern as existing tolerance fields
- Pre-fills with `suggested_value` from existing config
- Validation range (0.1-5.0) enforced by selector
- Fields are optional (vol.Optional), won't break existing configs

**No Breaking Changes**:
- Existing advanced settings continue to work
- New fields are optional, old configs don't have them
- Flattening logic handles new fields automatically

---

## Research Task 4: Configuration Persistence Strategy

### Question
How to store optional tolerance values in config entries?

### Investigation

**Home Assistant Config Entry Storage**:
- Config entries store data in `.storage/core.config_entries` as JSON
- Optional values can be:
  - Absent (key not in dict) → Preferred for truly optional
  - `None` → Explicit "not set"
  - Default value → Can't distinguish from user-set value

**Existing Pattern in Codebase**:
- `config.get(CONF_SOMETHING)` returns `None` if key absent
- Optional parameters checked with `if value is not None`
- Example: `self._fan_hot_tolerance = config.get(CONF_FAN_HOT_TOLERANCE)` (line 100 in environment_manager.py)

**State Restoration**:
- `StateManager` base class handles restoration
- Restored attributes merged with config
- Missing keys handled gracefully (return None)

### Decision

**Use absence (no key) for unset, store float when set**

**Implementation Pattern**:
```python
# In EnvironmentManager.__init__():
self._heat_tolerance = config.get(CONF_HEAT_TOLERANCE)  # None if absent
self._cool_tolerance = config.get(CONF_COOL_TOLERANCE)  # None if absent

# In tolerance selection:
if self._heat_tolerance is not None:
    # Use mode-specific tolerance
else:
    # Fall back to legacy

# In options flow submit:
if user_input.get(CONF_HEAT_TOLERANCE) is not None:
    # Store in config entry
    self.config_entry.data[CONF_HEAT_TOLERANCE] = user_input[CONF_HEAT_TOLERANCE]
# If None or absent, don't add to config entry (or explicitly store None)
```

**Rationale**:
- Matches existing optional parameter pattern
- `config.get()` naturally returns `None` for absent keys
- Can distinguish between "not configured" (None) and "configured to specific value"
- State restoration handles missing keys gracefully
- No migration needed: old configs simply don't have the keys

**Persistence Verification**:
- Config entry data persisted automatically by Home Assistant
- Tolerance values survive restart (stored in `.storage/`)
- Options flow pre-fills from `self.config_entry.data.get(CONF_HEAT_TOLERANCE)`

---

## Research Task 5: Testing Strategy for All System Types

### Question
What is the minimum test coverage to verify all system types work correctly?

### Investigation

**Existing Test Structure**:
- **Unit tests**: `tests/managers/test_environment_manager.py` (already exists, can extend)
- **Config flow tests**: `tests/config_flow/test_options_flow.py` (consolidated file)
- **E2E persistence tests**: 4 files for each system type:
  - `test_e2e_simple_heater_persistence.py`
  - `test_e2e_ac_only_persistence.py`
  - `test_e2e_heat_pump_persistence.py`
  - `test_e2e_heater_cooler_persistence.py`
- **Integration tests**: 4 files for feature combinations:
  - `test_simple_heater_features_integration.py`
  - `test_ac_only_features_integration.py`
  - `test_heat_pump_features_integration.py`
  - `test_heater_cooler_features_integration.py`
- **Functional tests**: `tests/test_heater_mode.py`, `test_cooler_mode.py`, etc.

**Coverage Required**:
- All 4 system types (simple_heater, ac_only, heat_pump, heater_cooler)
- All relevant HVAC modes for each system type
- Backward compatibility (legacy configs without mode-specific tolerances)
- Forward compatibility (configs with mode-specific tolerances)

### Decision

**Test Coverage Strategy**:

**1. Unit Tests** (`test_environment_manager.py`):
- Test `_get_active_tolerance_for_mode()` with all HVAC modes
- Test tolerance selection priority (mode-specific → legacy → default)
- Test partial configuration (only heat_tolerance set, only cool_tolerance set)
- Test HEAT_COOL mode switching
- Test FAN_ONLY mode using cool_tolerance

**2. Config Flow Tests** (`test_options_flow.py`):
- Test advanced settings step includes heat_tolerance and cool_tolerance fields
- Test field validation (min 0.1, max 5.0)
- Test optional fields can be left empty
- Test pre-filling with existing values

**3. E2E Persistence Tests** (add to existing 4 files):
- Test tolerance values persist through restart
- Test config → options flow → runtime → restart → verification
- Test legacy configs (no mode-specific tolerances) still work
- Test mixed configs (some mode-specific, some legacy)
- One test per system type file (4 tests total)

**4. Integration Tests** (add to existing 4 files):
- Test tolerance settings with different system types
- Test interaction with fan_hot_tolerance
- Test interaction with presets (presets don't override tolerance)
- One test per system type file (4 tests total)

**5. Functional Tests** (add to existing mode files):
- `test_heater_mode.py`: Test heating respects heat_tolerance
- `test_cooler_mode.py`: Test cooling respects cool_tolerance
- `test_heat_pump_mode.py`: Test HEAT_COOL mode switching

**Estimated Test Count**:
- Unit: ~10 test cases
- Config flow: ~5 test cases
- E2E persistence: 4 test cases (1 per system type)
- Integration: 4 test cases (1 per system type)
- Functional: ~6 test cases (2 per mode file × 3 files)
- **Total: ~29 new test cases**

**Rationale**:
- Comprehensive coverage without excessive duplication
- Uses test consolidation strategy (no new test files)
- Tests critical paths and edge cases
- Validates backward compatibility explicitly
- Covers all 4 system types systematically

---

## Summary of Decisions

| Research Question | Decision | Rationale |
|-------------------|----------|-----------|
| HVAC Mode Tracking | Store mode as state in EnvironmentManager via `set_hvac_mode()` | Minimal API change, climate entity notifies on mode change, follows existing patterns |
| Tolerance Selection | Priority-based algorithm: mode-specific → legacy → default | Simple, deterministic, handles all modes and edge cases, always has fallback |
| Options Flow Integration | Add fields to existing advanced settings section | Minimal changes, no new step, uses existing patterns, pre-fills values |
| Configuration Persistence | Use absence (no key) for unset, store float when set | Matches existing optional parameter pattern, no migration needed, natural None handling |
| Testing Strategy | 29 test cases across unit/config/E2E/integration/functional | Comprehensive coverage, no new test files, systematic system type coverage |

## Implementation Readiness

✅ All research questions resolved
✅ Design decisions documented
✅ Implementation patterns identified
✅ Test strategy defined
✅ No blockers or unknowns remain

**Ready for Phase 1: Design & Contracts**
