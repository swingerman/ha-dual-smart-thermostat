# AC-Only Features Configuration

## Overview

AC-only systems have specialized configuration options designed for air conditioning units without heating capability. The configuration uses a progressive disclosure pattern to keep the interface clean while providing access to advanced features.

## Feature Selection Step

### Purpose
The `ac_only_features` step serves as a central hub where users choose which features to configure for their AC system. This approach:
- Reduces cognitive load by showing all choices at once
- Allows users to skip unwanted features
- Provides clear understanding of what will be configured

### Available Features

#### Fan Settings (`configure_fan`)
**What it configures**: Independent fan control separate from the AC unit
- Fan entity selection
- Fan mode options (low, medium, high, auto)
- Fan operation scheduling
- Fan-only mode support

**When to use**:
- When you have a separate fan entity
- For ceiling fans or circulation fans
- To improve air circulation when AC is off

#### Humidity Control (`configure_humidity`)
**What it configures**: Humidity monitoring and control
- Humidity sensor selection
- Target humidity levels
- Humidity-based HVAC control
- Dehumidification settings

**When to use**:
- In humid climates
- For comfort optimization
- To prevent condensation issues
- For energy efficiency

#### Openings Integration (`configure_openings`)
**What it configures**: Door and window sensor integration
- Sensor selection (doors, windows, garage doors)
- Opening detection timeouts
- Closing detection timeouts
- HVAC scope (cooling only, or heating if applicable)

**When to use**:
- To automatically turn off AC when doors/windows open
- For energy savings
- In spaces with frequent door/window usage

#### Temperature Presets (`configure_presets`)
**What it configures**: Custom temperature profiles
- Preset selection (away, home, sleep, eco, comfort, etc.)
- Temperature values for each preset
- Schedule-based preset switching
- Preset-specific fan and humidity settings

**When to use**:
- For automated temperature schedules
- Different comfort levels for different times
- Energy savings during away periods
- Integration with presence detection

#### Advanced Settings (`configure_advanced`)
**What it configures**: Technical fine-tuning options
- Temperature precision (0.1°, 0.5°, 1.0°)
- Default target temperature
- Minimum/maximum temperature limits
- Initial HVAC mode on startup
- Temperature adjustment step size

**When to use**:
- For precise temperature control
- When default settings don't meet needs
- For specialized comfort requirements
- Integration with home automation

## Configuration Flow

### Step 1: Feature Selection
```
AC Features Configuration
Choose which features to configure for your air conditioning system.
Select only the features you want to set up.

☐ Configure fan settings
☐ Configure humidity control
☐ Configure window/door sensors
☐ Configure temperature presets
☐ Configure advanced settings
```

### Step 2: Feature-Specific Configuration
Based on selections in Step 1, users proceed through relevant configuration steps:

#### If Fan Selected → Fan Configuration
- **Fan Toggle**: Enable/disable fan features
- **Fan Options**: Entity selection and settings

#### If Humidity Selected → Humidity Configuration
- **Humidity Toggle**: Enable/disable humidity features
- **Humidity Options**: Sensor and target configuration

#### If Openings Selected → Openings Configuration
- **Entity Selection**: Choose door/window sensors
- **Timeout Settings**: Configure opening/closing detection
- **Scope Settings**: Choose HVAC modes affected

#### If Presets Selected → Preset Configuration
- **Preset Selection**: Choose which presets to enable
- **Preset Values**: Set temperatures for selected presets

#### If Advanced Selected → Advanced Configuration
- **Technical Settings**: Precision, limits, defaults

## User Experience Design

### Progressive Disclosure
The design follows progressive disclosure principles:
1. **Overview First**: Start with feature selection overview
2. **Details on Demand**: Show configuration details only for selected features
3. **Logical Grouping**: Related settings appear together
4. **Skip Unwanted**: Easy to bypass unneeded features

### Non-Destructive Language
The interface uses "configure" rather than "enable/disable" to:
- Reduce anxiety about losing settings
- Focus on setup rather than on/off states
- Encourage exploration of features
- Align with user mental models

### Clear Guidance
Each feature includes:
- **Descriptive Labels**: Clear, user-friendly names
- **Help Text**: Explanation of what the feature does
- **Usage Guidance**: When and why to use the feature
- **Example Scenarios**: Real-world use cases

## Schema Implementation

### Dynamic Generation
The AC features schema is generated dynamically to:
- Show only relevant fields
- Adapt to system capabilities
- Provide appropriate defaults
- Include contextual help

### Field Types
```python
configure_fan: BooleanSelector(default=False)
configure_humidity: BooleanSelector(default=False)
configure_openings: BooleanSelector(default=False)
configure_presets: BooleanSelector(default=False)
configure_advanced: BooleanSelector(default=False)
```

### Validation
- No validation required (all fields optional)
- Selections determine subsequent flow steps
- Default values ensure clean initial state

## Integration Points

### With Options Flow
The AC features step integrates seamlessly with the options flow:
- **Current State Display**: Shows which features are currently configured
- **Modification Support**: Allows enabling/disabling features
- **Preservation**: Maintains existing settings when possible
- **Clean Updates**: Only changes explicitly modified settings

### With Other Components
- **Climate Integration**: Core thermostat functionality
- **Fan Integration**: Independent fan control
- **Humidity Integration**: Humidity sensor support
- **Binary Sensor Integration**: Opening detection
- **Automation Integration**: Preset and schedule support

## Best Practices

### For Users
1. **Start Simple**: Configure basic cooling first, add features later
2. **Test Incrementally**: Add one feature at a time
3. **Use Presets**: Take advantage of automated scheduling
4. **Monitor Energy**: Use opening sensors for efficiency

### For Developers
1. **Feature Flags**: Use boolean selections to control flow
2. **State Management**: Track selections in `collected_config`
3. **Schema Generation**: Build schemas based on selections
4. **Flow Determination**: Route to appropriate next steps
5. **Validation**: Ensure feature dependencies are met

## Troubleshooting

### Common Issues
1. **Missing Features**: Ensure system type is set to `ac_only`
2. **Flow Skipping**: Check that features are properly selected
3. **Schema Errors**: Verify entity selections are valid
4. **State Issues**: Clear browser cache if forms behave unexpectedly

### Debug Information
- Check `collected_config` for current state
- Verify system type in configuration entry
- Review Home Assistant logs for errors
- Test entity availability in Developer Tools
