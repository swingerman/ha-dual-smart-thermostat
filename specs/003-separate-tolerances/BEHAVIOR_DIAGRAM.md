# Tolerance Behavior Diagrams

Visual representation of how temperature tolerances work in current vs proposed implementation.

## Current Behavior (Legacy)

### Configuration
```yaml
cold_tolerance: 0.5
hot_tolerance: 0.5
target_temp: 20
```

### Heating Mode
```
Temperature (°C)
    │
22  │                    ┌──── Too hot, turn heater OFF
    │                    │
21  │              ┌─────┴─────┐
    │              │           │
20  ├──────────────┤  TARGET   ├───────────────
    │              │           │
19  │              └─────┬─────┘
    │                    │
18  │                    └──── Too cold, turn heater ON
    │
    └─────────────────────────────────────────► Time

Legend:
- Turn ON threshold:  target - cold_tolerance = 20 - 0.5 = 19.5°C
- Turn OFF threshold: target + hot_tolerance  = 20 + 0.5 = 20.5°C
- Operating range: 19.5°C to 20.5°C (1.0°C span)
```

### Cooling Mode
```
Temperature (°C)
    │
22  │                    ┌──── Too hot, turn AC ON
    │                    │
21  │              ┌─────┴─────┐
    │              │           │
20  ├──────────────┤  TARGET   ├───────────────
    │              │           │
19  │              └─────┬─────┘
    │                    │
18  │                    └──── Too cold, turn AC OFF
    │
    └─────────────────────────────────────────► Time

Legend:
- Turn ON threshold:  target + hot_tolerance  = 20 + 0.5 = 20.5°C
- Turn OFF threshold: target - cold_tolerance = 20 - 0.5 = 19.5°C
- Operating range: 19.5°C to 20.5°C (1.0°C span)
```

**Problem**: Both modes have the same 1.0°C operating range. Can't have tight heating with loose cooling.

---

## Proposed Behavior (Mode-Specific)

### Configuration
```yaml
target_temp: 20
heat_tolerance: 0.3   # Tight control for heating
cool_tolerance: 2.0   # Loose control for cooling
```

### Heating Mode
```
Temperature (°C)
    │
22  │                ┌──── Turn heater OFF
    │                │
21  │          ┌─────┴─────┐
    │          │           │
20  ├──────────┤  TARGET   ├───────────────
    │          │           │
19  │          └─────┬─────┘
    │                │
18  │                └──── Turn heater ON
    │
    └─────────────────────────────────────────► Time

Legend:
- Turn ON threshold:  target - heat_tolerance = 20 - 0.3 = 19.7°C
- Turn OFF threshold: target + heat_tolerance = 20 + 0.3 = 20.3°C
- Operating range: 19.7°C to 20.3°C (0.6°C span)
- Result: TIGHT control, frequent cycling, maximum comfort
```

### Cooling Mode
```
Temperature (°C)
    │
24  │                                    ┌──── Turn AC ON
    │                                    │
22  │                              ┌─────┴─────┐
    │                              │           │
20  ├──────────────────────────────┤  TARGET   │
    │                              │           │
18  │                              └─────┬─────┘
    │                                    │
16  │                                    └──── Turn AC OFF
    │
    └─────────────────────────────────────────► Time

Legend:
- Turn ON threshold:  target + cool_tolerance = 20 + 2.0 = 22.0°C
- Turn OFF threshold: target - cool_tolerance = 20 - 2.0 = 18.0°C
- Operating range: 18.0°C to 22.0°C (4.0°C span)
- Result: LOOSE control, infrequent cycling, energy savings
```

**Solution**: Different operating ranges per mode. Comfort when heating, efficiency when cooling.

---

## Real-World Example

### Winter Heating Scenario
```
Target: 20°C
heat_tolerance: 0.3°C

Timeline:
    │
    │  19.6°C ──► Heater turns ON (below 19.7°C threshold)
    │     │
    │     │ [Heater running]
    │     │
    │  20.4°C ──► Heater turns OFF (above 20.3°C threshold)
    │     │
    │     │ [Heater off, temperature naturally drops]
    │     │
    │  19.6°C ──► Heater turns ON again
    │
    ▼

Result: Room stays between 19.7°C and 20.3°C
User experience: Very comfortable, stable temperature
Energy: Higher usage due to frequent cycling
```

### Summer Cooling Scenario
```
Target: 20°C
cool_tolerance: 2.0°C

Timeline:
    │
    │  22.1°C ──► AC turns ON (above 22.0°C threshold)
    │     │
    │     │ [AC running - cools down significantly]
    │     │
    │  17.8°C ──► AC turns OFF (below 18.0°C threshold)
    │     │
    │     │ [AC off - room slowly warms up]
    │     │
    │     │ ... long period ...
    │     │
    │  22.1°C ──► AC turns ON again
    │
    ▼

Result: Room cycles between 18°C and 22°C
User experience: Acceptable comfort, occasional variation
Energy: Lower usage due to infrequent cycling, longer off periods
```

---

## Backward Compatibility

### Legacy Configuration (Still Works)
```yaml
cold_tolerance: 0.5
hot_tolerance: 0.5
# No mode-specific tolerances specified
```

**Behavior**: Identical to current implementation
- Heating: Uses cold/hot tolerance (19.5-20.5°C range)
- Cooling: Uses hot/cold tolerance (19.5-20.5°C range)

### Mixed Configuration
```yaml
cold_tolerance: 0.5    # Fallback/default
hot_tolerance: 0.5     # Fallback/default
cool_tolerance: 1.5    # Override cooling only
# heat_tolerance not specified
```

**Behavior**:
- Heating: Uses legacy (19.5-20.5°C range)
- Cooling: Uses cool_tolerance (18.5-21.5°C range)

---

## Tolerance Selection Logic

### Decision Tree

```
┌─────────────────────────────────────────────────────────┐
│ User requests HVAC operation in mode X                  │
└────────────────────┬────────────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │ Is mode-specific      │
         │ tolerance configured? │
         └───────┬───────────────┘
                 │
        ┌────────┴────────┐
        │                 │
       YES               NO
        │                 │
        ▼                 ▼
┌───────────────┐  ┌──────────────┐
│ Use mode-     │  │ Use legacy   │
│ specific      │  │ cold/hot     │
│ tolerance     │  │ tolerance    │
└───────────────┘  └──────────────┘
```

### Priority Table

| Mode | 1st Choice | 2nd Choice | 3rd Choice |
|------|------------|------------|------------|
| HEAT | heat_tolerance | cold_tolerance + hot_tolerance | DEFAULT_TOLERANCE |
| COOL | cool_tolerance | hot_tolerance + cold_tolerance | DEFAULT_TOLERANCE |
| HEAT_COOL | heat_cool_tolerance | heat_tolerance / cool_tolerance | cold_tolerance + hot_tolerance |
| FAN_ONLY | cool_tolerance | hot_tolerance + cold_tolerance | DEFAULT_TOLERANCE |

---

## Heat/Cool Mode (Auto) Behavior

### Configuration
```yaml
target_temp_low: 18
target_temp_high: 24
heat_cool_tolerance: 1.0
```

### Operation
```
Temperature (°C)
    │
26  │                                    ┌──── Start Cooling
    │                                    │
24  ├────────────────────────────────────┤ TARGET HIGH
    │                                    │
22  │                              ┌─────┴─────┐
    │                              │           │
20  │                              │   IDLE    │
    │                              │   ZONE    │
18  ├────────────────────────────────────┤ TARGET LOW
    │                              └─────┬─────┘
16  │                                    │
    │                                    └──── Start Heating
    │
    └─────────────────────────────────────────► Time

Legend:
- Cool threshold: target_high + heat_cool_tolerance = 24 + 1.0 = 25.0°C
- Heat threshold: target_low - heat_cool_tolerance  = 18 - 1.0 = 17.0°C
- Idle zone: 17.0°C to 25.0°C (8.0°C span)
- Switches between heating and cooling based on which threshold is crossed
```

---

## Fan Tolerance Interaction

### Configuration
```yaml
target_temp: 20
cool_tolerance: 2.0
fan_hot_tolerance: 1.0
fan: switch.fan
```

### Behavior (Cooling + Fan Mode)
```
Temperature (°C)
    │
24  │                                    ┌──── AC turns ON
    │                                    │
22  │                              ┌─────┴─────┐
    │                              │   FAN     │
21  │                        ┌─────┤   ONLY    │
    │                        │     │   ZONE    │
20  ├────────────────────────┤  TARGET        ├──────
    │                        │     │           │
18  │                        └─────┴───────────┘
    │
    └─────────────────────────────────────────► Time

Legend:
- Fan turns on:  target + cool_tolerance = 20 + 2.0 = 22.0°C
- AC turns on:   target + cool_tolerance + fan_hot_tolerance = 23.0°C
- Fan-only zone: 22.0°C to 23.0°C
- AC zone: Above 23.0°C
```

---

## Validation Rules

### Tolerance Value Constraints
```python
# Minimum tolerance (prevent too-tight control)
MIN_TOLERANCE = 0.1  # °C

# Maximum tolerance (prevent runaway behavior)
MAX_TOLERANCE = 5.0  # °C

# Validation
0.1 <= heat_tolerance <= 5.0
0.1 <= cool_tolerance <= 5.0
0.1 <= heat_cool_tolerance <= 5.0
```

### Recommended Values

| Use Case | heat_tolerance | cool_tolerance |
|----------|----------------|----------------|
| Maximum comfort | 0.3 | 0.3 |
| Balanced | 0.5 | 1.0 |
| Energy saving | 1.0 | 2.0 |
| Maximum efficiency | 1.5 | 3.0 |

---

## Migration Examples

### Before (Legacy)
```yaml
climate:
  - platform: dual_smart_thermostat
    name: Bedroom
    heater: switch.heater
    target_sensor: sensor.bedroom_temp
    cold_tolerance: 0.5
    hot_tolerance: 0.5
```
**Behavior**: ±0.5°C in all modes

### After (Optimized for Comfort + Efficiency)
```yaml
climate:
  - platform: dual_smart_thermostat
    name: Bedroom
    heater: switch.heater
    cooler: switch.ac
    target_sensor: sensor.bedroom_temp
    # Keep legacy as fallback
    cold_tolerance: 0.5
    hot_tolerance: 0.5
    # Optimize per mode
    heat_tolerance: 0.3    # Tight heating for comfort
    cool_tolerance: 1.5    # Loose cooling for efficiency
```
**Behavior**:
- Heating: ±0.3°C (tight)
- Cooling: ±1.5°C (loose)

---

**Summary**: Mode-specific tolerances provide fine-grained control while maintaining full backward compatibility with existing configurations.
