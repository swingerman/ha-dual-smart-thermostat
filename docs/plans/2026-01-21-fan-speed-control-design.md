# Fan Speed Control Design

**Issue:** #517 - Support for fan speeds
**Date:** 2026-01-21
**Status:** Design Complete

## Overview

Add native fan speed control to the dual smart thermostat by leveraging Home Assistant's fan entity speed capabilities. This allows users to control their HVAC fan speeds (low, medium, high, auto) directly from the thermostat interface, similar to built-in thermostats.

**Key Principles:**
- Automatic capability detection - no new configuration required
- Backward compatible with existing switch-based fans
- Works with both preset-mode and percentage-based fan entities
- Integrates seamlessly with existing features (FAN_ONLY mode, fan_on_with_ac, etc.)

## Architecture

### Component Overview

**Modified Components:**

1. **Fan Device Layer** (`hvac_device/fan_device.py`)
   - Add fan speed detection and control methods
   - Differentiate between `switch` domain (on/off) and `fan` domain (with speeds)
   - Expose available fan modes from the underlying entity

2. **Climate Entity** (`climate.py`)
   - Add `ClimateEntityFeature.FAN_MODE` to supported features when applicable
   - Implement `fan_mode` property and `set_fan_mode()` method
   - Expose `fan_modes` list to UI

3. **Feature Manager** (`managers/feature_manager.py`)
   - Track whether fan speed control is available
   - Update support flags to include FAN_MODE feature when detected

4. **State Manager** (`managers/state_manager.py`)
   - Add fan mode persistence for restoration after restart

### Detection Logic

```
If CONF_FAN entity is configured:
  - Check entity domain (hass.states.get(entity_id).domain)
  - If domain == "fan":
    - Check for preset_mode or percentage attributes
    - If supported → enable fan_mode control
  - If domain == "switch":
    - Keep existing on/off behavior (backward compatible)
```

**No Configuration Changes Required:**
- Existing `CONF_FAN` entity is analyzed at runtime
- Automatic detection based on entity capabilities
- Zero migration needed for existing users

## Data Flow & State Management

### Fan Mode State Flow

**1. Initialization/Startup:**
```
Climate entity starts → Feature manager checks CONF_FAN entity
→ Fan device detects capabilities → Sets available fan modes
→ Climate entity exposes fan_mode feature if available
```

**2. User Changes Fan Speed:**
```
User selects fan mode in UI → climate.set_fan_mode() called
→ Fan device stores current mode → Next fan operation uses selected speed
→ State persisted for restoration after restart
```

**3. HVAC Operation:**
```
Control cycle triggers → Device needs fan ON
→ Fan device checks: is speed control available?
→ If yes: Turn on fan + set stored fan mode
→ If no: Turn on fan (switch behavior)
```

### State Persistence

The current fan mode must be saved and restored across restarts:
- Add `_fan_mode` attribute to climate entity state
- Store in `StateManager` for restoration
- Default to "auto" or first available mode if not previously set

### Backward Compatibility

- Existing configurations with `switch` entities continue working unchanged
- No migration needed - detection is runtime
- If fan entity doesn't support speeds, feature simply not exposed

### Error Handling

- If fan entity becomes unavailable: disable fan_mode UI but keep setting
- If fan entity changes capabilities: re-detect on next update
- Invalid fan mode requested: log warning, use fallback (auto or first available)

## Fan Capability Detection & Mode Mapping

### Capability Detection

Implemented in `FanDevice.__init__` or setup:

```python
def _detect_fan_capabilities(self):
    """Detect if fan entity supports speed control."""
    fan_state = self.hass.states.get(self.entity_id)

    if not fan_state:
        return False, []

    # Check domain
    entity_domain = fan_state.domain
    if entity_domain == "switch":
        # Legacy switch-based fan, no speed control
        return False, []

    if entity_domain == "fan":
        # Check for preset_mode support
        preset_modes = fan_state.attributes.get("preset_modes")
        if preset_modes:
            return True, preset_modes

        # Check for percentage support
        percentage = fan_state.attributes.get("percentage")
        if percentage is not None:
            # Expose standard modes mapped to percentages
            return True, ["auto", "low", "medium", "high"]

    return False, []
```

### Mode Mapping Strategies

**For Preset-based Fans:**
- Use fan entity's preset_modes directly
- No translation needed - pass through to fan entity
- Example: `["auto", "low", "medium", "high", "sleep", "nature"]`

**For Percentage-based Fans:**
- Map standard modes to percentage ranges:
  - `"auto"` → 100% (or None to let fan decide)
  - `"low"` → 33%
  - `"medium"` → 66%
  - `"high"` → 100%
- Store mapping as constants in `FanDevice`

### Setting Fan Mode

```python
async def async_set_fan_mode(self, fan_mode: str):
    """Set the fan speed mode."""
    if self._uses_preset_modes:
        await self.hass.services.async_call(
            "fan", "set_preset_mode",
            {"entity_id": self.entity_id, "preset_mode": fan_mode}
        )
    else:  # percentage-based
        percentage = self._mode_to_percentage(fan_mode)
        await self.hass.services.async_call(
            "fan", "set_percentage",
            {"entity_id": self.entity_id, "percentage": percentage}
        )
```

## Integration with Existing Features

### Fan Mode Behavior

**Fan speed applies only during active operation:**
- When heater/cooler is ON, fan runs at selected speed
- When heater/cooler is OFF, fan stops (unless in FAN_ONLY mode)
- Fan speed selection persists across heating/cooling cycles

### Interaction with Existing Features

**1. FAN_ONLY HVAC Mode:**
- When user selects FAN_ONLY mode, fan runs at the selected fan speed
- If no fan speed set yet, default to "auto" or first available mode
- Fan mode selection available and functional in FAN_ONLY mode

**2. Fan with AC (`CONF_FAN_ON_WITH_AC`):**
- When this is enabled, fan runs during cooling operations
- Fan runs at the selected fan speed (not just on/off)
- User can change fan speed while AC is running

**3. Fan Tolerance Mode (`CONF_FAN_HOT_TOLERANCE`):**
- When temperature exceeds tolerance, fan activates at selected speed
- Fan mode setting applies here too

**4. Openings (Window/Door Sensors):**
- When opening detected, HVAC stops (including fan per existing logic)
- Fan mode selection preserved for when system resumes

**5. Presets:**
- Fan mode setting is global, not per-preset
- When switching presets, fan speed doesn't change
- This matches typical thermostat behavior (presets control temperature, not fan speed)

**6. Heat Pump Mode:**
- Fan speed control applies to both heating and cooling operations
- Single fan entity with single speed selection

### Feature Flag Updates

```python
# In FeatureManager.set_support_flags()
if self.is_fan_speed_control_available():
    self._supported_features |= ClimateEntityFeature.FAN_MODE
```

## Testing Strategy

### Unit Tests

Extend existing `tests/test_fan_mode.py`:

**1. Fan Capability Detection Tests:**
- Test detection of preset_mode based fans
- Test detection of percentage based fans
- Test switch domain fallback (no speed control)
- Test unavailable fan entity handling
- Test fan entity with no speed support

**2. Fan Mode Control Tests:**
- Test `set_fan_mode()` with preset-based fan
- Test `set_fan_mode()` with percentage-based fan
- Test fan mode persistence across restarts
- Test fan mode changes during active operation
- Test invalid fan mode handling

**3. Integration Tests:**
- Test fan speed with FAN_ONLY mode
- Test fan speed with `fan_on_with_ac` enabled
- Test fan speed with fan tolerance mode
- Test fan mode with heat pump operations
- Test backward compatibility with switch entities

### Config Flow Tests

Add to `tests/config_flow/`:
- Existing fan configuration should work unchanged
- No new configuration steps needed (automatic detection)
- Test that fan speed is detected and exposed properly

### Test Fixtures Needed

- Mock fan entity with preset_modes
- Mock fan entity with percentage attribute
- Mock switch entity (for backward compatibility)

### Test Execution

```bash
./scripts/docker-test tests/test_fan_mode.py  # Run fan-specific tests
./scripts/docker-test --log-cli-level=DEBUG    # Debug failing tests
./scripts/docker-test                          # Full test suite
```

## Implementation Plan

### Phase 1: Core Detection & Device Layer

1. Add fan capability detection to `FanDevice` class
2. Implement `_detect_fan_capabilities()` method
3. Add mode mapping logic (preset vs percentage)
4. Add `async_set_fan_mode()` method to `FanDevice`

### Phase 2: Climate Entity Integration

5. Add `fan_mode` and `fan_modes` properties to climate entity
6. Implement `async_set_fan_mode()` service method
7. Add state persistence for fan mode
8. Update `FeatureManager` to expose FAN_MODE feature flag

### Phase 3: State Management

9. Add fan mode to `StateManager` for restoration
10. Handle fan mode in `apply_old_state()`
11. Ensure fan mode applied during control cycles

### Phase 4: Testing

12. Add unit tests for capability detection
13. Add integration tests with existing features
14. Test backward compatibility with switch entities
15. Run full test suite with `./scripts/docker-test`

### Phase 5: Documentation

16. Update README.md with fan speed control documentation
17. Add template fan examples for switch upgrade
18. Update CLAUDE.md with architecture details
19. Create changelog entry

## Documentation Deliverables

### 1. User Documentation (README.md)

**New Section: "Fan Speed Control"**

- Explain automatic fan speed detection
- Show examples with native `fan` entities
- Clarify backward compatibility with switch entities
- Document behavior with existing features

**Example:**
```yaml
# Native fan entity with speed control (automatic detection)
dual_smart_thermostat:
  name: My Thermostat
  heater: switch.heater
  fan: fan.hvac_fan  # Automatically detects speed capabilities
  target_sensor: sensor.temperature

# Legacy switch-based fan (continues to work as before)
dual_smart_thermostat:
  name: My Thermostat
  heater: switch.heater
  fan: switch.fan_relay  # No speed control, on/off only
  target_sensor: sensor.temperature
```

### 2. Template Fan Documentation (README.md)

**New Section: "Upgrading Switch-Based Fans to Speed Control"**

For users with simple switch entities, provide examples using Home Assistant's template fan platform:

**Example 1: Template Fan with Input Select**
```yaml
# Helper for fan speed selection
input_select:
  hvac_fan_speed:
    name: HVAC Fan Speed
    options:
      - "auto"
      - "low"
      - "medium"
      - "high"
    initial: "auto"

# Template fan wrapping switch + speed control
fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('switch.fan_relay', 'on') }}"
        preset_mode_template: "{{ states('input_select.hvac_fan_speed') }}"
        preset_modes:
          - "auto"
          - "low"
          - "medium"
          - "high"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.fan_relay
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.fan_relay
        set_preset_mode:
          service: input_select.select_option
          target:
            entity_id: input_select.hvac_fan_speed
          data:
            option: "{{ preset_mode }}"

# Use in thermostat
dual_smart_thermostat:
  name: My Thermostat
  heater: switch.heater
  fan: fan.hvac_fan  # Uses template fan with speed control
  target_sensor: sensor.temperature
```

**Example 2: Percentage-Based Control**
```yaml
input_number:
  hvac_fan_speed:
    name: HVAC Fan Speed
    min: 0
    max: 100
    step: 1
    unit_of_measurement: "%"

fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('switch.fan_relay', 'on') }}"
        percentage_template: "{{ states('input_number.hvac_fan_speed') | int }}"
        turn_on:
          service: switch.turn_on
          target:
            entity_id: switch.fan_relay
        turn_off:
          service: switch.turn_off
          target:
            entity_id: switch.fan_relay
        set_percentage:
          - service: input_number.set_value
            target:
              entity_id: input_number.hvac_fan_speed
            data:
              value: "{{ percentage }}"
```

**Example 3: IR/RF Controlled Fans**
```yaml
# For fans controlled via Broadlink, IR blaster, or RF remote
fan:
  - platform: template
    fans:
      hvac_fan:
        friendly_name: "HVAC Fan"
        value_template: "{{ is_state('input_boolean.fan_state', 'on') }}"
        preset_mode_template: "{{ states('input_select.hvac_fan_speed') }}"
        preset_modes: ["low", "medium", "high"]
        turn_on:
          - service: input_boolean.turn_on
            target:
              entity_id: input_boolean.fan_state
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_on"
        turn_off:
          - service: input_boolean.turn_off
            target:
              entity_id: input_boolean.fan_state
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_off"
        set_preset_mode:
          - service: input_select.select_option
            target:
              entity_id: input_select.hvac_fan_speed
            data:
              option: "{{ preset_mode }}"
          - service: remote.send_command
            target:
              entity_id: remote.living_room
            data:
              command: "fan_{{ preset_mode }}"
```

**Benefits:**
- Use existing switch hardware
- Add speed control without new devices
- Automatic detection by thermostat
- Full UI integration

**Reference:** [HA Template Fan Documentation](https://www.home-assistant.io/integrations/fan.template/)

### 3. Developer Documentation (CLAUDE.md)

Update architecture section with:
- Fan capability detection pattern
- Mode mapping strategies (preset vs percentage)
- Integration points with existing features
- Testing requirements for fan features

### 4. Changelog Entry

```markdown
## [Unreleased]

### Added
- Native fan speed control for fan entities with speed capabilities (#517)
- Automatic detection of fan preset_mode and percentage support
- Fan speed control in FAN_ONLY, fan_on_with_ac, and fan tolerance modes
- State persistence for fan mode across restarts

### Changed
- Fan entities now support full speed control when capabilities detected
- Switch-based fans continue to work with on/off behavior (backward compatible)

### Documentation
- Added template fan examples for upgrading switch-based fans
- Documented fan speed integration with existing features
```

## Success Criteria

✅ Fan speed control automatically detected for `fan` domain entities
✅ Preset-mode and percentage-based fans both supported
✅ Switch-based fans continue working unchanged (backward compatible)
✅ Fan mode persists across restarts
✅ Integration with FAN_ONLY, fan_on_with_ac, and tolerance modes
✅ Comprehensive test coverage
✅ User documentation with template fan examples
✅ No configuration changes or migrations required

## Open Questions

None - design validated through Q&A process.

## References

- Issue #517: https://github.com/swingerman/ha-dual-smart-thermostat/issues/517
- HA Climate Entity Documentation: https://developers.home-assistant.io/docs/core/entity/climate/
- HA Template Fan Documentation: https://www.home-assistant.io/integrations/fan.template/
- HA Fan Entity Documentation: https://developers.home-assistant.io/docs/core/entity/fan/
