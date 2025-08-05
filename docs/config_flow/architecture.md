# Configuration Flow Architecture

## Overview

The dual smart thermostat integration uses Home Assistant's config flow pattern to provide a step-by-step configuration experience. The flow adapts dynamically based on the system type and user selections.

## System Types

### AC-Only Systems (`ac_only`)
- **Purpose**: Air conditioning units without heating capability
- **Key Features**:
  - Fan control options
  - Humidity monitoring
  - Advanced cooling settings
  - Door/window sensor integration

### Simple Heater (`simple_heater`)
- **Purpose**: Basic heating-only systems
- **Key Features**:
  - Single heater entity
  - Basic temperature control
  - Minimal configuration options

### Heater + Cooler (`heater_cooler`)
- **Purpose**: Separate heating and cooling entities
- **Key Features**:
  - Independent heater and cooler control
  - Fan options for both heating and cooling
  - Advanced scheduling options

### Heat Pump (`heat_pump`)
- **Purpose**: Systems that use the same entity for heating and cooling
- **Key Features**:
  - Single entity with mode switching
  - Specialized heat pump controls
  - Efficiency optimization settings

### Dual Stage (`dual_stage`)
- **Purpose**: Two-stage heating systems
- **Key Features**:
  - Primary and auxiliary heater configuration
  - Stage switching logic
  - Temperature differential settings

### Floor Heating (`floor_heating`)
- **Purpose**: Radiant floor heating systems
- **Key Features**:
  - Floor temperature sensor
  - Maximum/minimum floor temperature limits
  - Specialized heating curves

## Configuration Flow Steps

### 1. System Type Selection (`user`)
The initial step where users choose their thermostat type. This determines the entire flow path.

### 2. Basic Configuration (`basic`)
Common settings for all system types:
- Thermostat name
- Temperature sensor
- Temperature tolerances
- Minimum cycle duration

### 3. System-Specific Configuration
Each system type has specialized configuration steps:

#### AC-Only Features (`ac_only_features`)
A consolidated step where users select which features to configure:
- **Fan Settings**: Independent fan control
- **Humidity Control**: Humidity sensor and targets
- **Openings Integration**: Door/window sensors
- **Temperature Presets**: Custom temperature profiles
- **Advanced Settings**: Precision, limits, and specialized options

#### Heater+Cooler (`heater_cooler`)
Configuration for dual-entity systems:
- Heater entity selection
- Cooler entity selection
- Heat/cool mode settings

#### Heat Pump (`heat_pump`)
Specialized heat pump configuration:
- Single entity for heating/cooling
- Heat pump specific settings
- Auxiliary heating options

### 4. Feature Configuration Steps
Based on selections in step 3, users proceed through relevant feature configuration:

#### Fan Configuration (`fan_toggle` → `fan_options`)
- Enable/disable fan control
- Fan entity selection
- Fan mode settings

#### Humidity Configuration (`humidity_toggle` → `humidity_options`)
- Enable/disable humidity monitoring
- Humidity sensor selection
- Target humidity settings

#### Openings Configuration (`openings_options`)
- Door/window sensor selection
- Opening/closing timeout settings
- HVAC mode scope (heating, cooling, or both)

#### Advanced Options (`advanced_options`)
Technical settings for fine-tuning:
- Temperature precision
- Default target temperature
- Temperature limits
- Initial HVAC mode
- Temperature step size

#### Preset Configuration (`preset_selection` → `presets`)
- Select which presets to enable
- Configure temperature values for selected presets
- Set preset-specific settings (humidity, fan mode, etc.)

## Options Flow

The options flow allows users to modify their thermostat configuration after initial setup. It follows a similar pattern but:

1. **Preserves System Type**: The original system type determines available options
2. **Shows Current Values**: Forms are pre-populated with existing configuration
3. **Conditional Steps**: Only shows steps relevant to the current system type
4. **Smart Defaults**: Maintains existing settings unless explicitly changed

### Key Options Flow Features

#### System Type Preservation
The options flow respects the original system type and only shows relevant configuration options. For example:
- AC-only systems see fan and humidity options
- Simple heaters see minimal configuration options
- Dual systems see both heating and cooling options

#### Progressive Disclosure
Users only see configuration steps for features they've enabled:
- If fan is not configured, fan options are skipped
- If no presets are selected, preset configuration is skipped
- Advanced options only appear when explicitly requested

#### Advanced Options Toggle
AC-only systems have a special "Configure advanced settings" option that:
- Appears as a simple toggle in the AC features step
- When enabled, redirects to a separate advanced options step
- Keeps the main configuration step clean and simple

## Schema Generation

### Dynamic Schemas
The integration uses dynamic schema generation to:
- Show only relevant fields based on system type
- Adapt field options based on current configuration
- Provide context-appropriate help text

### Field Types
- **EntitySelector**: For choosing Home Assistant entities
- **SelectSelector**: For dropdown menus with predefined options
- **DurationSelector**: For time-based settings
- **NumberSelector**: For numeric values with validation
- **BooleanSelector**: For on/off toggles

### Validation
- Entity existence checking
- Numeric range validation
- Required field enforcement
- Cross-field dependency validation

## Internationalization

### Translation Structure
All user-facing text is externalized to translation files:
- `config.step.*`: Configuration flow steps
- `options.step.*`: Options flow steps
- `config.error.*`: Error messages
- `config.abort.*`: Flow abort reasons

### Multi-language Support
The flow supports Home Assistant's built-in translation system for:
- Step titles and descriptions
- Field labels and help text
- Error messages and validation text
- Success confirmations

## Best Practices

### User Experience
1. **Progressive Disclosure**: Show simple options first, advanced options on request
2. **Clear Labeling**: Use descriptive field names and help text
3. **Logical Grouping**: Group related settings together
4. **Sensible Defaults**: Provide reasonable default values
5. **Non-destructive Language**: Use "configure" rather than "enable/disable"

### Technical Implementation
1. **State Management**: Use `collected_config` to track user selections
2. **Flow Determination**: Dynamic next-step calculation based on system type
3. **Schema Caching**: Generate schemas efficiently
4. **Error Handling**: Graceful handling of configuration errors
5. **Backward Compatibility**: Support existing configurations during upgrades
