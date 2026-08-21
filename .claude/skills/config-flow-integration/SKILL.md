---
name: config-flow-integration
description: 'How to integrate a new or changed configuration option into the config, reconfigure and options flows for dual_smart_thermostat. Use when adding a config parameter to const.py or schemas.py, adding a feature that needs user configuration, changing how an existing option behaves, or wiring a new step into feature_steps/.'
---

# Configuration flow integration

Required reading whenever a configuration option is added or changed. See also `docs/config_flow/step_ordering.md`.

#### Configuration Flow Integration

**CRITICAL**: Every added or modified configuration option MUST be integrated into the appropriate configuration flows (config, reconfigure, or options flows). This is mandatory for all configuration changes.

##### When Flow Integration is Required

Flow integration is required whenever you:
1. Add a new configuration parameter to `const.py` or `schemas.py`
2. Modify an existing configuration parameter's behavior or validation
3. Add a new feature that requires user configuration
4. Change how configuration options interact with each other

##### Which Flow(s) to Update

Determine which flow(s) need updates based on the type of change:

1. **Initial Configuration Flow** (`config_flow.py`):
   - New system types or HVAC modes
   - New required entities (heater, cooler, sensors)
   - New features that should be configured during initial setup
   - Core system behavior changes

2. **Reconfigure Flow** (`config_flow.py` - reconfigure handlers):
   - Changes to existing system configuration that require reconfiguration
   - System type switching
   - Entity replacement or updates
   - Any change that affects the initial configuration flow

3. **Options Flow** (`options_flow.py`):
   - Feature toggles (enabling/disabling features)
   - Feature-specific settings (thresholds, timeouts, behaviors)
   - Preset configurations
   - Advanced settings that don't require reconfiguration
   - Any setting that users might want to change after initial setup

**Rule of Thumb**: If users need to configure it during initial setup, add it to config/reconfigure flows. If users might want to adjust it later, add it to options flow. Often, you'll need to add to both.

##### How to Integrate Changes into Flows

Follow this process to integrate configuration changes:

1. **Add Constants and Schema**:
   ```python
   # In const.py - Add configuration key constant
   CONF_NEW_FEATURE = "new_feature"

   # In schemas.py - Add to appropriate schema
   NEW_FEATURE_SCHEMA = vol.Schema({
       vol.Optional(CONF_NEW_FEATURE, default=False): cv.boolean,
   })
   ```

2. **Add Configuration Step** (if needed):
   ```python
   # In feature_steps/ - Create new step file if complex feature
   # Or add to existing step file

   async def async_step_new_feature(self, user_input=None):
       """Handle new feature configuration."""
       # Follow existing patterns from other step handlers
   ```

3. **Update Flow Navigation**:
   ```python
   # In config_flow.py or options_flow.py
   # Update _determine_next_step() or flow handler to include new step
   # Ensure proper step ordering (see Step Ordering section)
   ```

4. **Add Data Validation**:
   ```python
   # Add validation logic in step handler
   # Follow existing validation patterns
   # Provide clear error messages
   ```

5. **Update Translations**:
   ```json
   // In translations/en.json
   "step": {
       "new_feature": {
           "title": "Configure New Feature",
           "description": "Description of what this configures",
           "data": {
               "new_feature": "Enable new feature"
           }
       }
   }
   ```

##### Testing Flow Integration

**REQUIRED**: All flow changes must be tested:

1. **Unit Tests**: Add to `tests/config_flow/`
   - Test step handler logic
   - Test validation
   - Test error handling

2. **Integration Tests**: Add to appropriate integration test file
   - Test complete flow with new option
   - Test persistence (config → options flow)
   - Test edge cases

3. **Manual Testing**:
   - Test initial configuration flow
   - Test reconfigure flow (if applicable)
   - Test options flow with existing configurations
   - Test with different system types

##### Example Flow Integration

When adding a new floor temperature feature:

```python
# 1. Add to const.py
CONF_MAX_FLOOR_TEMP = "max_floor_temp"

# 2. Add to schemas.py
FLOOR_TEMP_SCHEMA = vol.Schema({
    vol.Optional(CONF_MAX_FLOOR_TEMP): vol.Coerce(float),
})

# 3. Add step in feature_steps/floor_heating_steps.py
async def async_step_floor_heating(self, user_input=None):
    """Configure floor heating options."""
    if user_input is not None:
        # Validate and store
        return self.async_create_entry(...)

    # Show form with floor temp options
    return self.async_show_form(...)

# 4. Update navigation in config_flow.py
def _determine_next_step(self):
    if self._has_floor_sensor():
        return "floor_heating"  # Add to flow sequence
    return "next_step"

# 5. Add tests in tests/config_flow/test_floor_heating_integration.py
async def test_floor_heating_config_flow():
    """Test floor heating configuration in flow."""
    # Test implementation
```

##### Clarification Process

If it's unclear how to integrate a configuration change into the flows:

1. **Analyze the Feature**:
   - What does this configuration control?
   - Is it a core feature or an optional enhancement?
   - Does it depend on other configuration?

2. **Review Similar Features**:
   - Find similar existing features in the codebase
   - Review their flow integration
   - Follow the same patterns

3. **Check Dependencies**:
   - Does this feature require other configuration first?
   - Should it be in the main flow or a separate step?
   - Where should it appear in the step ordering?

4. **Ask for Clarification**:
   - If still unclear, document your analysis
   - Ask specifically: "Should this be in config or options flow?"
   - Provide context about the feature and its dependencies

**Remember**: When in doubt, add to both config/reconfigure AND options flows to provide maximum flexibility.

