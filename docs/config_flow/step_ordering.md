# Configuration Flow Step Ordering Rules

## Overview

The dual smart thermostat configuration flow must follow specific ordering rules to ensure that configuration steps appear in the correct sequence based on their dependencies.

## Critical Ordering Rules

### 1. Openings Steps Must Be Last Configuration Steps

The openings configuration steps (`openings_toggle`, `openings_selection`, `openings_config`) must always be among the last configuration steps because:

- Their content depends on previously configured system type
- Openings behavior varies based on heating/cooling entities
- Openings configuration needs to know which HVAC modes are available

### 2. Presets Steps Must Be Final Steps

The presets configuration steps (`preset_selection`, `presets`) must always be the absolute final configuration steps because:

- Preset configuration depends on all other system settings
- Preset temperature ranges depend on configured sensors and system capabilities
- Preset behavior varies based on system type and features
- Presets are the natural completion of the configuration process

### 3. Features Configuration Logical Ordering

When adding or modifying feature configuration steps, ensure they are ordered logically:

1. **System type and basic entity configuration** (heater, cooler, sensor)
2. **Core feature toggles** (floor heating, fan, humidity)
3. **Feature-specific configuration steps**
4. **Openings configuration** (depends on system type and entities)
5. **Preset configuration** (depends on all previous steps)

## Implementation

### Config Flow
- The `_determine_next_step()` method in `config_flow.py` enforces this ordering
- Comments in the code reference these rules

### Options Flow
- The `_determine_options_next_step()` method in `options_flow.py` follows the same rules
- Maintains consistency between initial configuration and reconfiguration

## Testing

### Required Tests
- Test that openings configuration steps come after core feature configuration
- Test that preset configuration steps are always the final steps
- Test the complete flow for different system types to verify step ordering
- Add integration tests that verify the dependency-based ordering

### Example Test Flow Verification
```python
# Verify correct step ordering for each system type
def test_config_flow_step_ordering():
    # 1. System type selection
    # 2. Basic entity configuration
    # 3. Feature toggles and configuration
    # 4. Openings configuration (among last steps)
    # 5. Presets configuration (final steps)
```

## Why This Matters

Proper step ordering ensures:
- Users see logically related configuration options together
- Dependent configuration steps have access to previously configured settings
- The configuration flow is intuitive and user-friendly
- No configuration loops or missing dependencies occur

## Violation Prevention

- Always check step dependencies before adding new configuration steps
- Update both config flow and options flow when adding new steps
- Add tests to verify the ordering for new features
- Reference these rules in code comments when implementing flow logic
