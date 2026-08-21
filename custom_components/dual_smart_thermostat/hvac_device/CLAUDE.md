# Fan device notes

Loaded when working under `hvac_device/`. Design rationale and test patterns for
fan speed control; the implementation itself is in `fan_device.py`.

Native fan speed control provides variable speed operation for fan-only mode. The implementation uses automatic capability detection to support different fan entity types.

##### Design Trade-offs

1. **Automatic Detection vs Configuration**: Detection is automatic to reduce configuration complexity. Trade-off: Cannot manually override detected capabilities.

2. **Fallback to Percentage**: Default modes (`["auto", "low", "medium", "high"]`) used for percentage-based fans. Trade-off: Less precise than native preset modes, but provides consistent UX.

3. **Runtime Capability Check**: Detection runs at startup and is retried when the fan entity's state changes, so a fan provided by an integration that connects late (ESPHome, MQTT) is picked up without a reload (#636).

4. **Switch Domain Exclusion**: Switch-based fans cannot use speed control. Trade-off: Simpler implementation, but requires users to use fan domain entities for speed control.

##### Testing Patterns

Test fan speed control using these patterns (see `tests/test_fan_mode.py`):

```python
# Test capability detection
async def test_fan_speed_control_preset_modes(hass):
    """Test detection of preset mode capability."""
    # Mock fan entity with preset_modes attribute
    # Verify supports_fan_mode = True
    # Verify fan_modes matches entity preset_modes

# Test state persistence
async def test_fan_mode_persistence(hass):
    """Test fan mode is persisted and restored."""
    # Set fan mode
    # Restart thermostat
    # Verify mode restored from extra_state_attributes

# Test mode application
async def test_fan_mode_applied_on_turn_on(hass):
    """Test fan mode is applied when fan turns on."""
    # Set fan mode
    # Turn on fan
    # Verify correct service call (set_preset_mode or set_percentage)
```

