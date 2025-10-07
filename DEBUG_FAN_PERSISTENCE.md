# Debug Logging for Fan Settings Persistence Issue

This document explains how to enable debug logging to diagnose the fan settings persistence issue you're experiencing in the UI.

## What Was Added

Debug logging has been added to track fan settings throughout the config and options flows:

1. **`feature_steps/fan.py`**:
   - Logs when fan config/options form is shown (with current defaults)
   - Logs user input when form is submitted
   - Logs collected_config before and after update

2. **`schemas.py`**:
   - Logs the defaults passed to `get_fan_schema()`
   - Shows what values should be pre-filled in the UI

3. **`options_flow.py`**:
   - Logs fan settings from existing config entry
   - Logs fan settings in collected_config
   - Logs final merged data before saving

## How to Enable Debug Logging

### Method 1: Via Home Assistant UI (Recommended)

1. Go to **Settings** → **System** → **Logs**
2. Click **"Configure"** (top right)
3. Add these log filters:
   ```
   custom_components.dual_smart_thermostat.feature_steps.fan: debug
   custom_components.dual_smart_thermostat.schemas: debug
   custom_components.dual_smart_thermostat.options_flow: debug
   ```
4. Click **Save**

### Method 2: Via configuration.yaml

Add to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.dual_smart_thermostat.feature_steps.fan: debug
    custom_components.dual_smart_thermostat.schemas: debug
    custom_components.dual_smart_thermostat.options_flow: debug
```

Then restart Home Assistant.

## How to Reproduce and Capture Logs

1. **Enable logging** (using Method 1 or 2 above)

2. **Clear existing logs** (optional but recommended):
   - Settings → System → Logs → Click "Clear" button

3. **Reproduce the issue**:
   - Open your thermostat integration
   - Click "Configure"
   - Navigate through the flow to fan settings
   - Toggle "Fan on with AC" to OFF (or whichever setting is not persisting)
   - Complete the flow

4. **Reopen options flow**:
   - Click "Configure" again
   - Navigate to fan settings
   - Observe if the setting reverted

5. **View logs**:
   - Settings → System → Logs
   - Look for lines containing "Fan options", "get_fan_schema", or "Options flow completion"

## What to Look For in Logs

### When Showing Fan Options Form

You should see:
```
Fan options - Showing form with current_config defaults: fan=switch.fan, fan_mode=False, fan_on_with_ac=False, fan_air_outside=False
get_fan_schema called with defaults: fan=switch.fan, fan_mode=False, fan_on_with_ac=False, fan_air_outside=False
```

**Check**: Do the defaults match what you saved? If `fan_on_with_ac=True` here but you set it to False, the config wasn't saved.

### When Submitting Fan Options

You should see:
```
Fan options - user_input received: {'fan': 'switch.fan', 'fan_mode': False, 'fan_on_with_ac': False}
Fan options - collected_config before update: fan_mode=None, fan_on_with_ac=None
Fan options - collected_config after update: fan_mode=False, fan_on_with_ac=False
```

**Check**: Is the setting you changed in `user_input`? If not, the UI didn't send it (voluptuous Optional field issue).

### At Flow Completion

You should see:
```
Options flow completion - entry.data fan settings: fan=switch.fan, fan_mode=False, fan_on_with_ac=True
Options flow completion - collected_config fan settings: fan=switch.fan, fan_mode=None, fan_on_with_ac=None
Options flow completion - updated_data fan settings: fan=switch.fan, fan_mode=False, fan_on_with_ac=True
```

**Check**: Does `updated_data` have the correct values? This is what gets saved.

## Expected Behavior vs Bug

### Expected (Working Correctly)

1. Form shows: `fan_on_with_ac=True` (from config)
2. User changes to: `False`
3. user_input contains: `{'fan_on_with_ac': False}`
4. collected_config updated: `fan_on_with_ac=False`
5. updated_data contains: `fan_on_with_ac=False`
6. Next time form shows: `fan_on_with_ac=False` ✅

### Bug Scenario A: Value Not in user_input

1. Form shows: `fan_on_with_ac=True` (from config)
2. User changes to: `False`
3. user_input MISSING: `{}` or doesn't contain `fan_on_with_ac` ❌
4. collected_config not updated: `fan_on_with_ac=None`
5. updated_data preserves old: `fan_on_with_ac=True`
6. Next time form shows: `fan_on_with_ac=True` (reverted)

### Bug Scenario B: Value Not in Config

1. Form shows: `fan_on_with_ac=True` (default, not from config)
2. User changes to: `False`
3. user_input contains: `{'fan_on_with_ac': False}`
4. collected_config updated: `fan_on_with_ac=False`
5. But entry.data doesn't have it, so merge loses it ❌
6. Next time form shows: `fan_on_with_ac=True` (default)

## Sharing Logs

After reproducing the issue:

1. Go to Settings → System → Logs
2. Click the "Download" button
3. Share the `home-assistant.log` file or copy relevant lines

Look for lines containing:
- `Fan options -`
- `Fan config -`
- `get_fan_schema`
- `Options flow completion -`

## Next Steps

Once you've captured the logs, we can determine:
1. Is the value being sent from UI? (check `user_input`)
2. Is it being saved to collected_config? (check `after update`)
3. Is it in the final config entry? (check `updated_data`)
4. Is it being loaded back? (check `current_config defaults`)

This will pinpoint exactly where the value is being lost!
