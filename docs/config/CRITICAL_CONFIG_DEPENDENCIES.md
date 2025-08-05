# Critical Configuration Parameter Dependencies

## Overview

This document focuses **exclusively** on configuration parameters that have conditional dependencies - parameters that only make sense when other specific parameters are configured. These are the critical relationships you need to understand for proper thermostat configuration.

## 🎯 Key Principle

**Conditional Parameters**: These parameters are ignored or non-functional unless their required "enabling" parameter is configured first.

## 📋 Critical Dependencies (22 Total)

### 🔥 Secondary Heating Dependencies

**Enabling Parameter**: `secondary_heater`

When you configure a secondary heater, these additional parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `secondary_heater_timeout` | Delay before activating secondary heater | `00:05:00` |
| `secondary_heater_dual_mode` | Enable dual operation mode | `true` |

**Configuration Example**:
```yaml
secondary_heater: switch.aux_heater
secondary_heater_timeout: "00:05:00"  # ← Only works with secondary_heater
secondary_heater_dual_mode: true      # ← Only works with secondary_heater
```

---

### 🌡️ Floor Heating Dependencies

**Enabling Parameter**: `floor_sensor`

When you configure a floor sensor, these temperature protection parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `max_floor_temp` | Maximum allowed floor temperature | `28` |
| `min_floor_temp` | Minimum allowed floor temperature | `5` |

**Configuration Example**:
```yaml
floor_sensor: sensor.floor_temperature
max_floor_temp: 28  # ← Only works with floor_sensor
min_floor_temp: 5   # ← Only works with floor_sensor
```

---

### ❄️🔥 Heat/Cool Mode Dependencies

**Enabling Parameter**: `heat_cool_mode`

When you enable heat/cool mode, these temperature range parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `target_temp_low` | Lower temperature threshold | `18` |
| `target_temp_high` | Upper temperature threshold | `24` |

**Configuration Example**:
```yaml
heat_cool_mode: true
target_temp_low: 18   # ← Only works with heat_cool_mode
target_temp_high: 24  # ← Only works with heat_cool_mode
```

---

### 💨 Fan Control Dependencies

**Enabling Parameter**: `fan`

When you configure a fan entity, these fan control parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `fan_mode` | Enable fan-only operation | `true` |
| `fan_on_with_ac` | Auto-start fan with cooling | `true` |
| `fan_hot_tolerance` | Temperature difference for fan activation | `1.0` |
| `fan_hot_tolerance_toggle` | Toggle entity for fan tolerance | `input_boolean.fan_auto` |

**Configuration Example**:
```yaml
fan: switch.ceiling_fan
fan_mode: true              # ← Only works with fan
fan_on_with_ac: true        # ← Only works with fan
fan_hot_tolerance: 1.0      # ← Only works with fan
```

**Additional Fan Dependency**: `fan_air_outside` requires `outside_sensor`
```yaml
outside_sensor: sensor.outdoor_temperature
fan_air_outside: true  # ← Only works with outside_sensor
```

---

### 💧 Humidity Control Dependencies

**Enabling Parameter**: `humidity_sensor`

When you configure a humidity sensor, these humidity parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `target_humidity` | Target humidity level | `50` |
| `min_humidity` | Minimum humidity level | `30` |
| `max_humidity` | Maximum humidity level | `70` |

**Enabling Parameter**: `dryer`

When you configure a dryer/dehumidifier entity, these tolerance parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `dry_tolerance` | Humidity difference before dryer starts | `5` |
| `moist_tolerance` | Humidity difference before dryer stops | `3` |

**Configuration Example**:
```yaml
humidity_sensor: sensor.room_humidity
target_humidity: 50    # ← Only works with humidity_sensor
min_humidity: 30       # ← Only works with humidity_sensor
max_humidity: 70       # ← Only works with humidity_sensor

dryer: switch.dehumidifier
dry_tolerance: 5       # ← Only works with dryer
moist_tolerance: 3     # ← Only works with dryer
```

---

### ⚡ Power Management Dependencies

**Enabling Parameter**: `hvac_power_levels`

When you configure HVAC power levels, these power control parameters become available:

| Parameter | Description | Example |
|-----------|-------------|---------|
| `hvac_power_min` | Minimum power level | `20` |
| `hvac_power_max` | Maximum power level | `100` |
| `hvac_power_tolerance` | Temperature tolerance for power adjustment | `0.5` |

**Configuration Example**:
```yaml
hvac_power_levels: 5
hvac_power_min: 20         # ← Only works with hvac_power_levels
hvac_power_max: 100        # ← Only works with hvac_power_levels
hvac_power_tolerance: 0.5  # ← Only works with hvac_power_levels
```

---

## ⚠️ Critical Conflicts (3 Total)

These parameters **cannot** have the same values or conflict with each other:

### 1. Entity Conflicts
```yaml
# ❌ WRONG - Same entity used for different purposes
heater: switch.main_device
target_sensor: switch.main_device  # Cannot be the same!

# ✅ CORRECT - Different entities
heater: switch.heater
target_sensor: sensor.temperature
```

### 2. Heater/Cooler Conflicts
```yaml
# ❌ WRONG - Same entity for heating and cooling
heater: switch.main_device
cooler: switch.main_device  # Cannot be the same!

# ✅ CORRECT - Different entities
heater: switch.heater
cooler: switch.ac_unit
```

### 3. AC Mode Override
```yaml
# When cooler is defined, ac_mode is ignored
cooler: switch.ac_unit
ac_mode: true  # ← This setting is IGNORED when cooler is defined
```

---

## 🛠️ Configuration Validation

### Quick Check Questions:

1. **Secondary Heating**: If you set `secondary_heater_timeout`, do you have `secondary_heater` defined?
2. **Floor Protection**: If you set `max_floor_temp`, do you have `floor_sensor` defined?
3. **Heat/Cool Mode**: If you set `target_temp_low` or `target_temp_high`, is `heat_cool_mode: true`?
4. **Fan Control**: If you set any `fan_*` parameters, do you have `fan` defined?
5. **Humidity**: If you set humidity parameters, do you have `humidity_sensor` and/or `dryer` defined?
6. **Power Management**: If you set power parameters, do you have `hvac_power_levels` defined?

### Common Configuration Mistakes:

❌ **Setting conditional parameters without enabling parameters**:
```yaml
# This won't work - max_floor_temp is ignored without floor_sensor
max_floor_temp: 28
# Missing: floor_sensor: sensor.floor_temp
```

❌ **Using the same entity for different purposes**:
```yaml
heater: switch.main_unit
cooler: switch.main_unit  # Conflict!
```

✅ **Correct conditional configuration**:
```yaml
# Enable the feature first
floor_sensor: sensor.floor_temperature
# Then configure its parameters
max_floor_temp: 28
min_floor_temp: 5
```

---

## 📝 Complete Working Examples

### Basic Heat-Only with Floor Protection
```yaml
name: "Floor Heating Thermostat"
heater: switch.floor_heater
target_sensor: sensor.room_temperature
floor_sensor: sensor.floor_temperature    # Enables floor protection
max_floor_temp: 28                        # ← Conditional on floor_sensor
```

### Advanced Heat/Cool with Fan
```yaml
name: "Advanced Climate Control"
heater: switch.heater
cooler: switch.ac_unit
target_sensor: sensor.room_temperature
heat_cool_mode: true                      # Enables temperature ranges
target_temp_low: 18                       # ← Conditional on heat_cool_mode
target_temp_high: 24                      # ← Conditional on heat_cool_mode
fan: switch.ceiling_fan                   # Enables fan features
fan_on_with_ac: true                      # ← Conditional on fan
```

### Complete System with All Features
```yaml
name: "Full Featured Thermostat"
heater: switch.main_heater
cooler: switch.ac_unit
target_sensor: sensor.room_temperature

# Secondary heating
secondary_heater: switch.aux_heater       # Enables secondary features
secondary_heater_timeout: "00:05:00"      # ← Conditional on secondary_heater

# Floor protection
floor_sensor: sensor.floor_temperature    # Enables floor protection
max_floor_temp: 28                        # ← Conditional on floor_sensor

# Heat/Cool mode
heat_cool_mode: true                      # Enables temperature ranges
target_temp_low: 18                       # ← Conditional on heat_cool_mode
target_temp_high: 24                      # ← Conditional on heat_cool_mode

# Fan control
fan: switch.ceiling_fan                   # Enables fan features
fan_mode: true                            # ← Conditional on fan
fan_on_with_ac: true                      # ← Conditional on fan

# Humidity control
humidity_sensor: sensor.room_humidity     # Enables humidity features
target_humidity: 50                       # ← Conditional on humidity_sensor
dryer: switch.dehumidifier               # Enables dryer features
dry_tolerance: 5                         # ← Conditional on dryer
```

---

## 🎯 Summary

**22 conditional dependencies** across **6 feature areas**:

- **Secondary Heating** (2 parameters): Need `secondary_heater`
- **Floor Protection** (2 parameters): Need `floor_sensor`
- **Heat/Cool Mode** (2 parameters): Need `heat_cool_mode`
- **Fan Control** (4 parameters): Need `fan` (+ 1 needs `outside_sensor`)
- **Humidity Control** (5 parameters): Need `humidity_sensor` + `dryer`
- **Power Management** (3 parameters): Need `hvac_power_levels`

**3 critical conflicts** to avoid:
- Heater ≠ Temperature sensor
- Heater ≠ Cooler (when both defined)
- AC mode ignored when cooler defined

This focused dependency analysis ensures you configure only the parameters that will actually function together, avoiding common configuration mistakes.
