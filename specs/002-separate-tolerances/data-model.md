# Data Model: Separate Temperature Tolerances

**Date**: 2025-10-29
**Branch**: `002-separate-tolerances`
**Purpose**: Define entities, attributes, and state transitions

---

## Entity Definitions

### 1. ConfigurationEntry (Extended)

**Description**: Home Assistant configuration entry storing thermostat settings. Extended to include optional mode-specific tolerance parameters.

**Existing Attributes**:
| Attribute | Type | Required | Default | Validation |
|-----------|------|----------|---------|------------|
| `cold_tolerance` | float | Yes | 0.3 | 0.1 ≤ value ≤ 5.0 |
| `hot_tolerance` | float | Yes | 0.3 | 0.1 ≤ value ≤ 5.0 |

**New Attributes**:
| Attribute | Type | Required | Default | Validation |
|-----------|------|----------|---------|------------|
| `heat_tolerance` | Optional[float] | No | None | If set: 0.1 ≤ value ≤ 5.0 |
| `cool_tolerance` | Optional[float] | No | None | If set: 0.1 ≤ value ≤ 5.0 |

**Relationships**:
- Referenced by `EnvironmentManager` during initialization
- Modified through Options Flow UI
- Persisted in Home Assistant config entries storage (`.storage/core.config_entries`)

**Constraints**:
- `heat_tolerance` and `cool_tolerance` are independent (no enforced relationship)
- When absent (None), system falls back to legacy tolerances
- Legacy tolerances always present (backward compatibility)

**State Transitions**: None (configuration is immutable until user modifies through UI)

**Storage Format**:
```json
{
  "data": {
    "cold_tolerance": 0.5,
    "hot_tolerance": 0.5,
    "heat_tolerance": 0.3,  // Optional, may be absent
    "cool_tolerance": 2.0   // Optional, may be absent
    // ... other config
  }
}
```

---

### 2. EnvironmentManager (Internal State Extended)

**Description**: Manager class responsible for tracking environmental conditions and determining if HVAC action is needed. Extended to support mode-aware tolerance selection.

**Existing State**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_cur_temp` | Optional[float] | Current temperature from sensor |
| `_target_temp` | Optional[float] | Target temperature setpoint |
| `_cold_tolerance` | float | Legacy cold tolerance (heating activation threshold) |
| `_hot_tolerance` | float | Legacy hot tolerance (cooling activation threshold) |

**New State**:
| Attribute | Type | Description |
|-----------|------|-------------|
| `_hvac_mode` | Optional[HVACMode] | Current HVAC mode (HEAT, COOL, HEAT_COOL, FAN_ONLY, DRY, OFF) |
| `_heat_tolerance` | Optional[float] | Mode-specific tolerance for heating operations |
| `_cool_tolerance` | Optional[float] | Mode-specific tolerance for cooling operations |

**Behavior**:
- `_hvac_mode` updated via `set_hvac_mode(mode)` called by climate entity
- Tolerance selection queries `_hvac_mode` to determine active tolerance
- Mode changes trigger immediate tolerance re-selection (no restart needed)

**State Transitions**:
```
Initial → HVAC Mode Set → Tolerance Selection Active

Climate Entity Changes Mode
    ↓
set_hvac_mode(new_mode)
    ↓
_hvac_mode = new_mode
    ↓
Next is_too_cold/hot call uses new tolerance
```

**Initialization**:
```python
def __init__(self, hass: HomeAssistant, config: ConfigType):
    # ... existing initialization ...
    self._hvac_mode = None  # Set by climate entity
    self._heat_tolerance = config.get(CONF_HEAT_TOLERANCE)  # None if absent
    self._cool_tolerance = config.get(CONF_COOL_TOLERANCE)  # None if absent
```

---

### 3. ToleranceSelection (Algorithm Logic)

**Description**: Algorithm for selecting active tolerance based on current HVAC mode and configured tolerance values. Implemented as private method in EnvironmentManager.

**Input Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `current_hvac_mode` | HVACMode | Current HVAC mode from climate entity |
| `heat_tolerance` | Optional[float] | Configured heating tolerance (None if not set) |
| `cool_tolerance` | Optional[float] | Configured cooling tolerance (None if not set) |
| `cold_tolerance` | float | Legacy cold tolerance (always present) |
| `hot_tolerance` | float | Legacy hot tolerance (always present) |
| `current_temp` | Optional[float] | Current temperature (for HEAT_COOL switching) |
| `target_temp` | Optional[float] | Target temperature (for HEAT_COOL switching) |

**Output**:
| Output | Type | Description |
|--------|------|-------------|
| `(cold_tol, hot_tol)` | tuple[float, float] | Active tolerances to use for temperature checks |

**Selection Logic**:

```
Priority 1: Mode-Specific Tolerance
  ├─ HEAT mode:     heat_tolerance if set
  ├─ COOL mode:     cool_tolerance if set
  ├─ FAN_ONLY mode: cool_tolerance if set (fan behaves like cooling)
  └─ HEAT_COOL mode:
      ├─ If cur_temp < target_temp (heating): heat_tolerance if set
      └─ If cur_temp >= target_temp (cooling): cool_tolerance if set

Priority 2: Legacy Fallback
  └─ Use (cold_tolerance, hot_tolerance)

Return: tuple[float, float] representing (cold_tol, hot_tol) for checks
```

**Decision Tree**:
```
                        [Current HVAC Mode?]
                               |
        ┌──────────────┬───────┴────────┬───────────────┬──────────┐
        |              |                |               |          |
     [HEAT]        [COOL]         [HEAT_COOL]      [FAN_ONLY]  [DRY/OFF]
        |              |                |               |          |
        |              |                |               |          └─> No checks
        |              |                |               |
        ├─ heat_tol?   ├─ cool_tol?    |               └─ cool_tol?
        |  Yes: Use it |  Yes: Use it  |                  Yes: Use it
        |  No: Legacy  |  No: Legacy   |                  No: Legacy
        |              |                |
        └──────────────┴────────────────┤
                                        |
                           [cur_temp vs target_temp?]
                                        |
                        ┌───────────────┴───────────────┐
                        |                               |
                  [Heating]                         [Cooling]
                 cur < target                      cur >= target
                        |                               |
                  heat_tol?                        cool_tol?
                  Yes: Use it                      Yes: Use it
                  No: Legacy                       No: Legacy
```

**Pseudocode**:
```python
def _get_active_tolerance_for_mode() -> tuple[float, float]:
    if hvac_mode == HEAT and heat_tolerance is not None:
        return (heat_tolerance, heat_tolerance)

    if hvac_mode == COOL and cool_tolerance is not None:
        return (cool_tolerance, cool_tolerance)

    if hvac_mode == FAN_ONLY and cool_tolerance is not None:
        return (cool_tolerance, cool_tolerance)

    if hvac_mode == HEAT_COOL:
        if current_temp < target_temp:
            # Heating
            if heat_tolerance is not None:
                return (heat_tolerance, heat_tolerance)
        else:
            # Cooling
            if cool_tolerance is not None:
                return (cool_tolerance, cool_tolerance)

    # Priority 2: Legacy fallback
    return (cold_tolerance, hot_tolerance)
```

**Edge Cases Handled**:
- **Partial Configuration**: Falls back to legacy for unconfigured mode
- **Sensor Failure**: Returns tolerances, but `is_too_cold/hot` returns `False` if `cur_temp is None`
- **HEAT_COOL Switching**: Instantaneous comparison, switches tolerance when crossing target
- **OFF Mode**: No tolerance checks performed (no HVAC action)
- **Missing HVAC Mode**: If `_hvac_mode is None`, falls back to legacy tolerances

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        User Configuration                           │
│  (Options Flow → Advanced Settings → heat_tolerance, cool_tolerance)│
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ├─> Validates (0.1-5.0)
                               ├─> Saves to Config Entry
                               └─> Triggers entity reload
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       Climate Entity (climate.py)                   │
│  - Loads config from Config Entry                                   │
│  - Initializes EnvironmentManager with config                       │
│  - Calls set_hvac_mode() when mode changes                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ├─> Creates EnvironmentManager
                               └─> Updates HVAC mode
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│              EnvironmentManager (environment_manager.py)            │
│                                                                     │
│  State:                                                             │
│    _cold_tolerance: float (from config, default 0.3)               │
│    _hot_tolerance: float (from config, default 0.3)                │
│    _heat_tolerance: Optional[float] (from config, None if not set) │
│    _cool_tolerance: Optional[float] (from config, None if not set) │
│    _hvac_mode: Optional[HVACMode] (set by climate entity)          │
│                                                                     │
│  Methods:                                                           │
│    set_hvac_mode(mode) → Stores current mode                       │
│    _get_active_tolerance_for_mode() → Returns (cold_tol, hot_tol)  │
│    is_too_cold(target_attr) → Uses active tolerance                │
│    is_too_hot(target_attr) → Uses active tolerance                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ├─> Tolerance Selection (Priority-based)
                               └─> Temperature Comparison
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HVAC Devices (hvac_device/)                      │
│  - Call environment.is_too_cold() / is_too_hot()                    │
│  - Use result to activate/deactivate equipment                      │
│  - No knowledge of tolerance selection logic                        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## State Transitions

### Configuration State Machine

```
┌─────────────────┐
│  Initial Setup  │
│  (New Install)  │
└────────┬────────┘
         │
         ├─> User configures cold_tolerance, hot_tolerance (defaults: 0.3)
         ├─> heat_tolerance, cool_tolerance remain unset (None)
         │
         ▼
┌─────────────────────────┐
│   Legacy Configuration  │
│   (Backward Compatible) │
│  - cold_tolerance: 0.3  │
│  - hot_tolerance: 0.3   │
│  - heat_tolerance: None │
│  - cool_tolerance: None │
└────────┬────────────────┘
         │
         ├─> User opens Options Flow → Advanced Settings
         ├─> Sets heat_tolerance = 0.3, cool_tolerance = 2.0
         │
         ▼
┌──────────────────────────────┐
│ Mode-Specific Configuration  │
│  - cold_tolerance: 0.3       │ (legacy fallback)
│  - hot_tolerance: 0.3        │ (legacy fallback)
│  - heat_tolerance: 0.3       │ (overrides for HEAT)
│  - cool_tolerance: 2.0       │ (overrides for COOL)
└────────┬─────────────────────┘
         │
         ├─> Can modify tolerances anytime via Options Flow
         ├─> Can remove mode-specific (set to empty) → reverts to legacy
         │
         ▼
┌──────────────────────────────┐
│ Partial Override             │
│  - cold_tolerance: 0.5       │
│  - hot_tolerance: 0.5        │
│  - heat_tolerance: None      │ (uses legacy for HEAT)
│  - cool_tolerance: 1.5       │ (overrides for COOL)
└──────────────────────────────┘
```

### Runtime HVAC Mode Transitions

```
┌────────────┐
│    OFF     │
│ No checks  │
└─────┬──────┘
      │
      ├─> User sets mode to HEAT
      │
      ▼
┌────────────────────────┐
│        HEAT            │
│ Uses heat_tolerance    │
│ or legacy cold/hot_tol │
│                        │
│ Activates when:        │
│ cur ≤ target - tol     │
│ Deactivates when:      │
│ cur ≥ target + tol     │
└─────┬──────────────────┘
      │
      ├─> User sets mode to COOL
      │
      ▼
┌────────────────────────┐
│        COOL            │
│ Uses cool_tolerance    │
│ or legacy hot/cold_tol │
│                        │
│ Activates when:        │
│ cur ≥ target + tol     │
│ Deactivates when:      │
│ cur ≤ target - tol     │
└─────┬──────────────────┘
      │
      ├─> User sets mode to HEAT_COOL (Auto)
      │
      ▼
┌────────────────────────────────┐
│        HEAT_COOL (Auto)        │
│                                │
│ If cur_temp < target_temp:     │
│   Uses heat_tolerance          │
│   (or legacy) - HEATING        │
│                                │
│ If cur_temp >= target_temp:    │
│   Uses cool_tolerance          │
│   (or legacy) - COOLING        │
│                                │
│ Switches immediately when      │
│ crossing target temperature    │
└────────────────────────────────┘
```

---

## Validation Rules

### Configuration Validation

**heat_tolerance**:
- Type: `float` or `None`
- Range: `0.1 ≤ value ≤ 5.0` (if not None)
- Optional: Yes
- Default: None
- Error Message: "Heat tolerance must be between 0.1 and 5.0°C"

**cool_tolerance**:
- Type: `float` or `None`
- Range: `0.1 ≤ value ≤ 5.0` (if not None)
- Optional: Yes
- Default: None
- Error Message: "Cool tolerance must be between 0.1 and 5.0°C"

**Cross-Field Validation**:
- No enforced relationship between `heat_tolerance` and `cool_tolerance`
- User can set `heat_tolerance < cool_tolerance` or vice versa
- Legacy `cold_tolerance` and `hot_tolerance` remain required (defaulted to 0.3)

### Runtime Validation

**HVAC Mode**:
- Must be valid HVACMode enum value
- Climate entity ensures valid mode before calling `set_hvac_mode()`

**Temperature Comparisons**:
- Return `False` if `current_temp is None` (sensor unavailable)
- Return `False` if `target_temp is None` (no setpoint)
- Tolerance selection always returns valid tuple (never None due to legacy fallback)

---

## Persistence and State Restoration

**Configuration Persistence**:
- Stored in `.storage/core.config_entries` by Home Assistant core
- Automatic persistence on Options Flow submission
- No manual save required

**State Restoration**:
- Configuration loaded from config entry on startup
- `EnvironmentManager.__init__()` reads tolerances from config
- HVAC mode restored by climate entity from previous state
- Climate entity calls `set_hvac_mode()` during restoration

**Migration**:
- None required
- Old configs don't have `heat_tolerance` or `cool_tolerance` keys
- `config.get()` returns `None` for missing keys
- Legacy fallback handles missing keys gracefully

---

## Dependencies

**Internal Dependencies**:
- `const.py`: Defines `CONF_HEAT_TOLERANCE`, `CONF_COOL_TOLERANCE`
- `schemas.py`: Defines validation schema for tolerance fields
- `climate.py`: Calls `environment.set_hvac_mode()` on mode change
- `environment_manager.py`: Implements tolerance selection logic
- `options_flow.py`: Provides UI for configuration

**External Dependencies**:
- `homeassistant.components.climate.const.HVACMode`: Enum for HVAC modes
- `homeassistant.config_entries`: Config entry storage
- `voluptuous`: Schema validation

**No New Dependencies Introduced**

---

## Summary

**Entities Added**: 0 (existing entities extended)
**Attributes Added**: 2 (`heat_tolerance`, `cool_tolerance`)
**Methods Added**: 2 (`set_hvac_mode()`, `_get_active_tolerance_for_mode()`)
**State Machines**: 2 (Configuration state machine, HVAC mode transitions)
**Validation Rules**: 2 (range validation for each tolerance)
**Storage Impact**: Minimal (2 optional float values in config entry JSON)

**Backward Compatibility**: ✅ Fully maintained through legacy fallback mechanism
**Forward Compatibility**: ✅ Extensible for future tolerance parameters
