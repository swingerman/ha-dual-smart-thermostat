# Dual Smart Thermostat Examples

This directory contains practical examples and use cases for the Dual Smart Thermostat integration.

## Quick Navigation

### 📋 Basic Configurations
Simple, ready-to-use configurations for common setups:
- [Heater Only](basic_configurations/heater_only.yaml) - Basic heating mode
- [Cooler Only (AC)](basic_configurations/cooler_only.yaml) - Air conditioning only
- [Heat Pump](basic_configurations/heat_pump.yaml) - Single switch heat/cool
- [Heater + Cooler (Dual)](basic_configurations/heater_cooler.yaml) - Separate heating and cooling

### 🚀 Advanced Features
Complex feature configurations:
- [Floor Heating with Temperature Limits](advanced_features/floor_heating_with_limits.yaml) - Floor temp protection
- [Two-Stage Heating](advanced_features/two_stage_heating.yaml) - AUX/emergency heating
- [Opening Detection](advanced_features/openings_with_timeout.yaml) - Window/door sensors
- [Advanced Presets](advanced_features/presets_advanced.yaml) - Multiple preset configurations

### 🔧 Integration Patterns
Real-world integration examples:
- [Single-Mode Thermostat Wrapper](single_mode_wrapper/) - Nest-like "Keep Between" for single-mode thermostats
- [Smart Scheduling](integrations/smart_scheduling.yaml) - Time-based automation examples

## How to Use These Examples

1. **Browse the examples** to find one that matches your needs
2. **Copy the YAML** configuration to your Home Assistant
3. **Modify entity IDs** to match your devices
4. **Adjust settings** like temperatures and tolerances
5. **Test thoroughly** before relying on it

## Contributing

Have a useful example or integration pattern? We'd love to include it! Please open a pull request or issue with your example.

## Need Help?

- Check the [main README](../README.md) for detailed documentation
- Visit the [GitHub Issues](https://github.com/swingerman/ha-dual-smart-thermostat/issues) for support
- Review the [Configuration Documentation](../docs/config/)

## Example Categories

### Basic Configurations
These are simple, single-file configurations you can copy directly into your `configuration.yaml`.

### Advanced Features
These examples demonstrate specific features with more complex configurations.

### Integration Patterns
These are complete solutions showing how to integrate the dual smart thermostat with other systems or create specific behaviors (may include helpers, automations, and scripts).
