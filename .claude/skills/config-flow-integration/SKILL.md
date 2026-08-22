---
name: config-flow-integration
description: 'Integrate a new or changed configuration option into the config, reconfigure and options flows. Use when touching const.py, schemas.py, feature_steps/, or adding a feature that needs user configuration.'
---

# Configuration flow integration

The mandate and the rule of thumb are in `CLAUDE.md`; this is the procedure.
See also `docs/config_flow/step_ordering.md`.

## Which flow(s) to update

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

## Worked example - adding a floor-temperature option

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

## Dependency tracking

A parameter that requires another to function must be recorded, or the validator will not
catch a broken combination:

1. `tools/focused_config_dependencies.json` - add the conditional dependency
2. `tools/config_validator.py` - add the validation rule
3. `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` - document it with an example
4. Verify with `python tools/config_validator.py`

Example: `max_floor_temp` requires `floor_sensor`.

## Testing

**REQUIRED**: All flow changes must be tested:

1. **Unit Tests**: Add to `tests/config_flow/`
   - Test step handler logic
   - Test validation
   - Test error handling

2. **Integration Tests**: Add to appropriate integration test file
   - Test complete flow with new option
   - Test persistence (config → options flow)
   - Test edge cases

