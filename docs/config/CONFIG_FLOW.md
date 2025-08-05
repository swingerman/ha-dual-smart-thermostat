# Dual Smart Thermostat Config Flow

This document describes the implementation of the config flow for the Dual Smart Thermostat integration.

## Overview

The config flow provides a user-friendly way to configure the Dual Smart Thermostat through the Home Assistant UI instead of requiring YAML configuration. It follows Home Assistant's best practices and uses the SchemaConfigFlowHandler pattern.

## Flow Structure

The config flow consists of 4 steps:

### Step 1: Basic Configuration
**Required fields:**
- Name: The name of the thermostat
- Heater switch: Switch entity used for heating
- Temperature sensor: Temperature sensor that reflects the current temperature

**Optional fields:**
- Cooler switch: Switch entity used for cooling
- Air conditioning mode: Treat switches as cooling devices instead of heating
- Heat/Cool mode: Enable automatic switching between heating and cooling
- Cold tolerance: Minimum temperature difference before turning on heating (default: 0.3°)
- Hot tolerance: Minimum temperature difference before turning off heating (default: 0.3°)
- Minimum cycle duration: Minimum time switch must be in current state before switching

### Step 2: Additional Sensors
**Optional fields:**
- Secondary heater: Secondary heater switch for auxiliary heating
- Outside temperature sensor: Optional outside temperature sensor for better control
- Floor temperature sensor: Optional floor temperature sensor for floor heating systems
- Humidity sensor: Optional humidity sensor for humidity control
- Maximum floor temperature: Maximum allowed floor temperature when using floor sensor

### Step 3: Advanced Settings
**Optional fields:**
- Keep alive duration: Keep alive duration for periodic switching
- Initial HVAC mode: Initial HVAC mode when starting Home Assistant
- Temperature precision: Temperature precision for display and control (0.1, 0.5, 1.0)
- Temperature step: Temperature step size for adjustments (0.1, 0.5, 1.0)
- Minimum temperature: Minimum allowed temperature setting
- Maximum temperature: Maximum allowed temperature setting
- Target temperature: Initial target temperature

### Step 4: Temperature Presets
**Optional fields:**
- Away: Temperature for away preset
- Comfort: Temperature for comfort preset
- Eco: Temperature for eco preset
- Home: Temperature for home preset
- Sleep: Temperature for sleep preset
- Anti Freeze: Temperature for anti-freeze preset
- Activity: Temperature for activity preset
- Boost: Temperature for boost preset

## Validation

The config flow includes validation to prevent common configuration errors:

- **Same heater and sensor**: Prevents selecting the same entity for both heater and temperature sensor
- **Same heater and cooler**: Prevents selecting the same entity for both heater and cooler

## Options Flow

The options flow allows users to reconfigure the thermostat after initial setup. It follows the same structure as the config flow but excludes the required fields (name, heater, sensor) which cannot be changed.

## Implementation Details

### Files Modified
- `manifest.json`: Added `"config_flow": true` and `"integration_type": "helper"`
- `__init__.py`: Added config entry setup functions
- `config_flow.py`: Complete rewrite with SchemaConfigFlowHandler
- `climate.py`: Added config entry support alongside existing YAML support
- `translations/en.json`: Added comprehensive translations for all steps

### Backward Compatibility
The implementation maintains full backward compatibility with existing YAML configurations. Users can continue to use YAML configuration or migrate to the config flow at their convenience.

### Testing
Comprehensive tests cover:
- Basic config flow completion
- Validation error handling
- Preset configuration
- Options flow functionality

## Usage

### Setting up a new thermostat
1. Go to Settings → Devices & Services
2. Click "Add Integration"
3. Search for "Dual Smart Thermostat"
4. Follow the 4-step configuration process

### Modifying an existing thermostat
1. Go to Settings → Devices & Services
2. Find the Dual Smart Thermostat integration
3. Click "Configure"
4. Modify settings in the options flow

## Technical Notes

- Uses `SchemaConfigFlowHandler` for consistency with Home Assistant core
- Configuration data is stored in `config_entry.options`
- Supports proper entity selectors with domain and device class filtering
- Includes comprehensive error handling and user feedback
- Follows Home Assistant UX guidelines for multi-step flows

## Future Enhancements

The current implementation covers approximately 80% of the dual smart thermostat's configuration options. Future enhancements could include:

- Fan control settings
- Humidity control (dehumidifier/dryer)
- Opening sensors (windows/doors)
- HVAC power management
- Advanced preset configurations

These can be added based on user feedback and usage patterns.