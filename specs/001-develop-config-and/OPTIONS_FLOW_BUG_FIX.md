# Options Flow Bug Fix: Feature Settings Not Persisting

## UPDATE: Second Bug Found and Fixed

After the initial fix, manual testing revealed a second bug where the options flow would show the wrong system type fields. This was caused by improperly merging transient flow state flags into the collected_config, which confused the flow navigation logic.

### The Second Bug
When opening options flow for a heater_cooler system, it would show AC-only fields instead. This happened because transient flags like "fan_options_shown" were being copied from the saved config into collected_config, which broke the flow navigation.

### The Second Fix
Modified `async_step_basic` to exclude transient flow state flags when merging current_config into collected_config. These flags control flow navigation and should never be persisted or copied between flow sessions.

---

## The Problem (Original)

When users configured features like Fan or Humidity in the options flow and saved their changes, those settings would not persist. When they reopened the options flow, the settings would revert to defaults or show incorrect values.

### Root Cause

Home Assistant's `OptionsFlow` saves changes to `config_entry.options`, NOT to `config_entry.data`. However, the options flow code was only reading from `config_entry.data`, which contains the original configuration from the initial setup (ConfigFlow).

This created a mismatch:
- **Saved location**: `config_entry.options` (where HA stores option changes)
- **Read location**: `config_entry.data` (original config, never updated)

### Example Scenario

1. User creates a Heater/Cooler system with a fan during initial setup
   - Sets `fan_mode=False` and `fan_on_with_ac=True`
   - Saved to `config_entry.data`

2. User opens options flow and changes `fan_mode=True`
   - Changes saved to `config_entry.options`
   - `config_entry.data` remains unchanged

3. User reopens options flow
   - Code reads from `config_entry.data` (old values)
   - Shows `fan_mode=False` instead of `True`
   - User's changes appear to be lost!

## The Fix

Created a new helper method `_get_current_config()` that properly merges both sources:

```python
def _get_current_config(self) -> dict[str, Any]:
    """Get current configuration merging data and options.

    Home Assistant OptionsFlow saves to entry.options, not entry.data.
    This method merges both, with options taking precedence.
    """
    entry = self._get_entry()
    options = getattr(entry, "options", {}) or {}
    # Handle both real ConfigEntry objects and test Mocks
    data = entry.data if isinstance(entry.data, dict) else {}
    options = options if isinstance(options, dict) else {}
    return {**data, **options}
```

This method:
1. Gets the original config from `entry.data`
2. Gets any saved changes from `entry.options`
3. Merges them with options taking precedence
4. Handles test Mocks gracefully

### Changed Locations

Replaced all 10 occurrences of `self._get_entry().data` with `self._get_current_config()` in:

- `async_step_init()` - Initial options flow step
- `async_step_basic()` - Basic settings step
- `_determine_options_next_step()` - Flow navigation logic
- `async_step_dual_stage_options()` - Dual stage system options
- `async_step_features()` - Feature selection
- `async_step_fan_options()` - Fan configuration
- `async_step_floor_options()` - Floor sensor options

## Testing

### Unit Tests (All Pass ✅)

1. **test_fan_boolean_false_persistence.py** - 5 tests
   - Verifies boolean False values persist correctly
   - Tests that `fan_on_with_ac=False` shows in options flow
   - Tests that `fan_mode=True` persists and displays

2. **test_options_flow_feature_persistence.py** - 6 tests
   - Fan settings prefilled correctly for all system types
   - Humidity settings prefilled correctly
   - Default values when features not configured

3. **All config_flow tests** - 72 tests total
   - No regressions in existing functionality

### Manual Testing Steps

To verify the fix works in Home Assistant:

1. **Initial Setup**:
   ```
   - Create a new Heater/Cooler system
   - Add a fan with specific settings:
     * fan_mode: Enable (checkbox checked)
     * fan_on_with_ac: Enable (checkbox checked)
   - Complete the setup
   ```

2. **Modify via Options**:
   ```
   - Open Integration → Configure (options flow)
   - Navigate to Fan Options
   - Change fan_mode to Disabled (uncheck)
   - Save changes
   ```

3. **Verify Persistence**:
   ```
   - Reopen Integration → Configure
   - Navigate to Fan Options
   - ✅ Expected: fan_mode checkbox is UNCHECKED
   - ❌ Bug (before fix): fan_mode checkbox was CHECKED (reverted to default)
   ```

4. **Check Storage File** (optional):
   ```bash
   # Check what's actually saved
   cat config/.storage/core.config_entries | python3 -m json.tool | grep -A 30 "dual_smart_thermostat"
   ```

   Should see:
   ```json
   {
     "data": {
       "fan_mode": true,  // Original config
       ...
     },
     "options": {
       "fan_mode": false,  // Updated via options flow
       ...
     }
   }
   ```

## Files Changed

- `custom_components/dual_smart_thermostat/options_flow.py`
  - Added `_get_current_config()` helper method that merges entry.data and entry.options
  - Replaced 10 occurrences of `self._get_entry().data` with `self._get_current_config()`
  - Modified `async_step_basic()` to preserve unmodified fields while excluding transient flags
  - Added debug logging for troubleshooting

- `tests/config_flow/test_heater_cooler_flow.py`
  - Fixed test to check behavior (form fields) instead of implementation details (collected_config)

## Impact

- ✅ Feature settings now persist correctly across options flow sessions
- ✅ Users can modify fan, humidity, and other feature settings reliably
- ✅ No breaking changes - fully backward compatible
- ✅ All 72 existing tests pass
- ✅ 11 new tests specifically for persistence scenarios

## Related Issues

This fix addresses the core persistence problem discovered during T005 (heater_cooler implementation) testing. This is a critical bug that affects ALL feature configuration in the options flow, not just fan settings.
