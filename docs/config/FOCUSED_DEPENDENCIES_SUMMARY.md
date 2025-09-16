# Dual Smart Thermostat - Focused Configuration Dependencies

## 🎯 Executive Summary

This analysis identifies **22 critical configuration dependencies** where parameters only function when specific "enabling" parameters are configured. Understanding these relationships prevents common configuration mistakes and ensures all parameters work as expected.

## 📊 Quick Reference

### Conditional Dependencies by Feature

| **Feature** | **Enabling Parameter** | **Dependent Parameters** | **Count** |
|-------------|------------------------|--------------------------|-----------|
| **Secondary Heating** | `secondary_heater` | `secondary_heater_timeout`, `secondary_heater_dual_mode` | 2 |
| **Floor Protection** | `floor_sensor` | `max_floor_temp`, `min_floor_temp` | 2 |
| **Heat/Cool Mode** | `heat_cool_mode` | `target_temp_low`, `target_temp_high` | 2 |
| **Fan Control** | `fan` | `fan_mode`, `fan_on_with_ac`, `fan_hot_tolerance`, `fan_hot_tolerance_toggle` | 4 |
| **Fan Air Control** | `outside_sensor` | `fan_air_outside` | 1 |
| **Humidity Sensing** | `humidity_sensor` | `target_humidity`, `min_humidity`, `max_humidity` | 3 |
| **Humidity Control** | `dryer` | `dry_tolerance`, `moist_tolerance` | 2 |
| **Power Management** | `hvac_power_levels` | `hvac_power_min`, `hvac_power_max`, `hvac_power_tolerance` | 3 |

### Critical Conflicts (Must Avoid)

| **Parameter 1** | **Parameter 2** | **Issue** |
|-----------------|-----------------|-----------|
| `heater` | `target_sensor` | Cannot be the same entity |
| `heater` | `cooler` | Cannot be the same entity |
| `cooler` | `ac_mode` | AC mode ignored when cooler defined |

## 🔧 Implementation Files

1. **`focused_config_dependencies.py`** - Analysis script that identifies conditional dependencies
2. **`focused_config_dependencies.json`** - Machine-readable dependency data with examples
3. **`CRITICAL_CONFIG_DEPENDENCIES.md`** - Complete user guide with examples
4. **`config_validator.py`** - Validation script to check configurations

## ✅ Validation Tool Usage

```bash
python config_validator.py
```

The validator checks:
- ✅ All conditional parameters have their enabling parameters
- ❌ No entity conflicts (same entity used for different purposes)
- ⚠️  Warnings for parameter overrides

## 🎯 Key Takeaways for Development

### For Config Flow Implementation
1. **Dynamic Parameter Visibility**: Hide conditional parameters until their enabling parameter is configured
2. **Validation Logic**: Implement the 22 dependency rules in config flow validation
3. **User Guidance**: Show helpful messages explaining why parameters are disabled

### For YAML Configuration
1. **Documentation**: Clearly mark conditional parameters in documentation
2. **Error Messages**: Reference the enabling parameter when validation fails
3. **Examples**: Always show enabling parameter with conditional parameters

### For Testing
1. **Positive Tests**: Verify conditional parameters work when enabled
2. **Negative Tests**: Verify conditional parameters are ignored when not enabled
3. **Conflict Tests**: Verify entity conflicts are caught and prevented

## 📝 Common Configuration Patterns

### ✅ Correct Patterns
```yaml
# Pattern 1: Enable feature first, then configure
floor_sensor: sensor.floor_temp    # Enable floor protection
max_floor_temp: 28                 # Configure the feature

# Pattern 2: Group related parameters
fan: switch.ceiling_fan            # Enable fan control
fan_mode: true                     # Configure fan operation
fan_on_with_ac: true              # Additional fan behavior
```

### ❌ Common Mistakes
```yaml
# Mistake 1: Conditional parameter without enabler
max_floor_temp: 28                 # Won't work without floor_sensor

# Mistake 2: Same entity for different purposes
heater: switch.main_unit
target_sensor: switch.main_unit    # Conflict!
```

## 🚀 Next Steps

1. **Integrate into Config Flow**: Use dependency data to implement dynamic parameter visibility
2. **Enhance Validation**: Add dependency validation to existing config flow steps
3. **Improve Documentation**: Update README with clear conditional parameter guidance
4. **Testing**: Create comprehensive test cases covering all 22 dependencies

This focused analysis provides everything needed to implement proper conditional parameter handling in the Dual Smart Thermostat configuration system.
