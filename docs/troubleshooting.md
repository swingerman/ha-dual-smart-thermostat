# Troubleshooting Guide

This document provides solutions to common issues with the Dual Smart Thermostat integration.

## Table of Contents

- [General Issues](#general-issues)
  - [AC/Heater Beeping Excessively](#acheater-beeping-excessively)
  - [Thermostat Not Turning On/Off](#thermostat-not-turning-onoff)
  - [Temperature Not Updating](#temperature-not-updating)
- [Template-Based Preset Issues](#template-based-preset-issues)
  - [Template Syntax Errors](#template-syntax-errors)
  - [Temperature Not Updating When Entity Changes](#temperature-not-updating-when-entity-changes)
  - [Template Returns Unexpected Value](#template-returns-unexpected-value)
  - [Template Returns "unknown" or "unavailable"](#template-returns-unknown-or-unavailable)
  - [Config Flow Rejects Valid Template](#config-flow-rejects-valid-template)
  - [Temperature Changes But HVAC Doesn't Respond](#temperature-changes-but-hvac-doesnt-respond)
- [Preset Issues](#preset-issues)
  - [Preset Doesn't Appear in UI](#preset-doesnt-appear-in-ui)
  - [Preset Temperature Doesn't Apply](#preset-temperature-doesnt-apply)
- [Configuration Issues](#configuration-issues)
  - [Integration Fails to Load](#integration-fails-to-load)
  - [Entities Not Showing Up](#entities-not-showing-up)
- [Debugging Tools](#debugging-tools)

---

## General Issues

### AC/Heater Beeping Excessively

**Problem:** Your air conditioner or heater beeps every few minutes (typically every 5 minutes) even when no temperature changes occur.

**Root Cause:** The `keep_alive` feature defaults to 300 seconds (5 minutes) and sends periodic commands to keep devices synchronized. Some HVAC units (like certain Hitachi AC models) beep audibly with each command they receive, including these keep-alive commands.

**Solution:** Disable the keep-alive feature by setting it to `0` in your configuration:

```yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.my_heater
    target_sensor: sensor.my_temperature
    keep_alive: 0  # Disables keep-alive to prevent beeping
```

**When to use keep_alive:** The keep-alive feature is useful for:
- HVAC units that turn off automatically if they don't receive commands regularly
- Switches that might lose state over time
- Maintaining synchronization between the thermostat and physical device

If your HVAC device doesn't have these issues, you can safely disable keep-alive.

**Related:** [GitHub Issue #461](https://github.com/swingerman/ha-dual-smart-thermostat/issues/461)

### Thermostat Not Turning On/Off

**Problem:** The thermostat climate entity shows the correct state, but the physical heater/cooler switch doesn't turn on or off.

**Diagnosis:**
1. Check if the switch entity is working correctly:
   - Go to Developer Tools → States
   - Find your heater/cooler switch entity
   - Try toggling it manually
   - Verify the physical device responds

2. Check for entity mismatches:
   - Verify the `heater` or `cooler` config points to correct entity_id
   - Check for typos in entity names
   - Ensure entity exists and is available

3. Check tolerance settings:
   - If `cold_tolerance` or `hot_tolerance` are set too high, the thermostat may not trigger
   - Default is 0.3°C - try reducing to 0.1°C

**Solution:**
```yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.correct_entity_id  # Verify this is correct
    target_sensor: sensor.my_temperature
    cold_tolerance: 0.1  # Reduce if needed
    hot_tolerance: 0.1
```

### Temperature Not Updating

**Problem:** The thermostat shows stale temperature readings.

**Diagnosis:**
1. Check target sensor is updating:
   - Developer Tools → States
   - Find your temperature sensor
   - Verify `last_updated` timestamp is recent

2. Check sensor availability:
   - Sensor state should not be "unknown" or "unavailable"
   - Check sensor device/integration is working

3. Check for sensor entity mismatches:
   - Verify `target_sensor` config is correct entity_id

**Solution:**
- Fix the underlying sensor issue
- Ensure sensor reports temperature regularly (at least every few minutes)
- If using template sensor, verify template evaluates correctly

---

## Template-Based Preset Issues

Template-based presets allow dynamic temperature targets using Home Assistant templates. These issues are specific to using templates in preset configurations.

### Template Syntax Errors

**Problem:** Home Assistant fails to start or shows configuration error after adding template to preset.

**Symptoms:**
- Error message in logs: `Template syntax error`
- Configuration validation fails
- Integration doesn't load

**Common Causes:**

1. **Unmatched Quotes:**
```yaml
# ❌ Wrong - missing closing quote
away_temp: "{{ states('sensor.temp) }}"

# ✅ Correct
away_temp: "{{ states('sensor.temp') }}"
```

2. **Unmatched Brackets:**
```yaml
# ❌ Wrong - missing closing bracket
away_temp: "{{ states('sensor.temp' }}"

# ✅ Correct
away_temp: "{{ states('sensor.temp') }}"
```

3. **Invalid Jinja2 Syntax:**
```yaml
# ❌ Wrong - invalid filter usage
away_temp: "{{ states('sensor.temp') float }}"

# ✅ Correct - use pipe for filters
away_temp: "{{ states('sensor.temp') | float }}"
```

**How to Fix:**

1. **Test in Developer Tools → Template:**
   - Copy your template
   - Paste into template editor
   - Fix any syntax errors shown
   - Verify template returns a number

2. **Use Template Testing Tool:**
   ```yaml
   # Test template separately first
   template:
     - sensor:
         - name: "Test Preset Temp"
           state: "{{ states('sensor.outdoor') | float + 2 }}"
   ```

3. **Common Template Patterns:**
```yaml
# Simple entity reference
away_temp: "{{ states('input_number.away_temp') | float }}"

# Conditional
eco_temp: "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"

# With calculation
home_temp: "{{ states('sensor.outdoor_temp') | float + 5 }}"

# Multiline with variables
comfort_temp: >
  {% set outdoor = states('sensor.outdoor') | float(20) %}
  {% set base = 20 %}
  {{ base if outdoor > 10 else base + 2 }}
```

### Temperature Not Updating When Entity Changes

**Problem:** You change an entity value (like `input_number.away_temp`) but the preset temperature doesn't update.

**Diagnosis:**

1. **Check if preset is active:**
   - Temperature only updates when preset is selected
   - Developer Tools → States → `climate.your_thermostat`
   - Check `preset_mode` attribute
   - If preset_mode is "none", preset temperatures aren't active

2. **Verify entity changes are detected:**
   ```yaml
   # Check entity in Developer Tools → States
   # Change value and verify "last_updated" timestamp changes
   ```

3. **Check template syntax:**
   ```yaml
   # In Developer Tools → Template, test:
   {{ states('input_number.away_temp') | float }}

   # Should return number, not "unknown"
   ```

**Solution:**

1. **Ensure preset is active:**
   - Set preset mode via UI or service call
   - Only active preset temperatures are evaluated

2. **Verify entity_id in template:**
```yaml
# ❌ Wrong entity_id
away_temp: "{{ states('input_number.away_target') | float }}"

# ✅ Correct - verify entity exists
away_temp: "{{ states('input_number.away_temp') | float }}"
```

3. **Add default value for safety:**
```yaml
# Provides fallback if entity unavailable
away_temp: "{{ states('input_number.away_temp') | float(18) }}"
```

4. **Check logs for listener errors:**
   ```yaml
   # Enable debug logging in configuration.yaml
   logger:
     default: info
     logs:
       custom_components.dual_smart_thermostat: debug
   ```

### Template Returns Unexpected Value

**Problem:** Template evaluates to wrong temperature (too high, too low, or nonsensical).

**Common Causes:**

1. **Forgot to convert to float:**
```yaml
# ❌ Wrong - string concatenation
away_temp: "{{ states('sensor.outdoor') + 5 }}"
# Returns: "205" (string) instead of 25 (number)

# ✅ Correct - numeric addition
away_temp: "{{ states('sensor.outdoor') | float + 5 }}"
# Returns: 25.0
```

2. **Wrong entity state format:**
```yaml
# If entity returns "20°C" instead of "20"
# ❌ Wrong - tries to convert "20°C" to float
away_temp: "{{ states('sensor.outdoor') | float }}"

# ✅ Correct - extract numeric part
away_temp: "{{ states('sensor.outdoor') | replace('°C', '') | float }}"
```

3. **Conditional logic error:**
```yaml
# ❌ Wrong - returns True/False instead of temperature
away_temp: "{{ is_state('sensor.season', 'winter') }}"
# Returns: True (not a temperature!)

# ✅ Correct - returns temperature based on condition
away_temp: "{{ 16 if is_state('sensor.season', 'winter') else 26 }}"
```

**How to Fix:**

1. **Always use | float filter:**
```yaml
away_temp: "{{ states('sensor.outdoor') | float }}"
```

2. **Test template output:**
   - Developer Tools → Template
   - Verify output is numeric
   - Check with different entity states

3. **Add value clamping:**
```yaml
# Ensure reasonable range (10-30°C)
away_temp: "{{ states('sensor.outdoor') | float | min(30) | max(10) }}"
```

4. **Use default values:**
```yaml
# If entity unavailable, use 20°C
away_temp: "{{ states('sensor.outdoor') | float(20) }}"
```

### Template Returns "unknown" or "unavailable"

**Problem:** Climate entity shows target temperature as "unknown" or "unavailable".

**Diagnosis:**

1. **Check referenced entity state:**
```yaml
# In Developer Tools → States
# Find: input_number.away_temp
# State should be numeric, not "unknown"/"unavailable"
```

2. **Check template in Developer Tools:**
```yaml
# Developer Tools → Template
# Test: {{ states('input_number.away_temp') | float }}
# Should return number
```

**Solution:**

1. **Always provide default values:**
```yaml
# ❌ Fragile - breaks if entity unavailable
away_temp: "{{ states('input_number.away_temp') | float }}"

# ✅ Robust - falls back to 18°C if entity unavailable
away_temp: "{{ states('input_number.away_temp') | float(18) }}"
```

2. **Fix underlying entity issue:**
   - Ensure input_number/sensor is properly configured
   - Check entity is not disabled
   - Verify entity integration is loaded

3. **Use fallback chain:**
```yaml
away_temp: >
  {% set temp = states('input_number.away_temp') | float(0) %}
  {% if temp > 0 %}
    {{ temp }}
  {% else %}
    18
  {% endif %}
```

4. **Check entity availability:**
```yaml
# Template with availability check
away_temp: >
  {% if is_state('input_number.away_temp', 'unavailable') %}
    18
  {% else %}
    {{ states('input_number.away_temp') | float(18) }}
  {% endif %}
```

**Fallback Behavior:**

If template evaluation fails completely, the thermostat uses this fallback chain:
1. Last successfully evaluated temperature
2. Previously set manual temperature
3. 20°C (default fallback)

This prevents the thermostat from becoming non-functional if a template has temporary issues.

### Config Flow Rejects Valid Template

**Problem:** When entering template in configuration UI, you get "invalid template" error even though template works in Developer Tools.

**Diagnosis:**

1. **Check template syntax in Developer Tools:**
   - Copy exact template from config flow error
   - Test in Developer Tools → Template
   - Verify no syntax errors

2. **Check for hidden characters:**
   - Spaces, tabs, newlines can cause issues
   - Copy-paste may introduce invisible characters

**Solution:**

1. **Use simple template format in UI:**
```yaml
# ✅ Single line, clean syntax
{{ states('input_number.away_temp') | float }}
```

2. **Avoid multiline templates in UI:**
```yaml
# ❌ May cause issues in UI (works in YAML)
{% set temp = states('sensor.outdoor') | float %}
{{ temp + 5 }}

# ✅ Better for UI - single line
{{ states('sensor.outdoor') | float + 5 }}
```

3. **For complex templates, use YAML configuration:**
```yaml
# In configuration.yaml
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.heater
    target_sensor: sensor.temp
    away_temp: >
      {% set outdoor = states('sensor.outdoor') | float(20) %}
      {% set base = 18 %}
      {{ base + 2 if outdoor < 10 else base }}
```

### Temperature Changes But HVAC Doesn't Respond

**Problem:** You see the target temperature update when entity changes, but heater/cooler doesn't turn on or off accordingly.

**Diagnosis:**

1. **Check tolerance settings:**
   - `cold_tolerance` / `hot_tolerance` may be too wide
   - Current temp must exceed target ± tolerance to trigger

2. **Check current temperature vs target:**
```yaml
# In Developer Tools → States → climate.your_thermostat
# Compare:
# - "temperature" (target from template)
# - "current_temperature" (from sensor)
# - Consider tolerance values
```

3. **Check for opening detection:**
   - If window/door sensor is triggered, HVAC may be paused
   - Check `climate.your_thermostat` attributes for opening status

**Solution:**

1. **Reduce tolerance if needed:**
```yaml
climate:
  - platform: dual_smart_thermostat
    # ... other config ...
    cold_tolerance: 0.1  # More responsive
    hot_tolerance: 0.1
```

2. **Verify control cycle triggered:**
   - Enable debug logging
   - Watch logs when temperature updates
   - Should see "Control cycle triggered" messages

3. **Check for conflicting features:**
   - Opening detection pausing HVAC
   - Floor temperature limits reached
   - Min cycle duration preventing rapid switching

---

## Preset Issues

### Preset Doesn't Appear in UI

**Problem:** You configured a preset but it doesn't show in the Home Assistant UI preset dropdown.

**Diagnosis:**

1. **Check preset is fully configured:**
   - For heating-only: Need `<preset>_temp`
   - For cooling-only: Need `<preset>_temp_high`
   - For heat_cool: Need both `<preset>_temp` and `<preset>_temp_high`

2. **Verify configuration loaded:**
   - Check Configuration → Server Controls → Check Configuration
   - Look for any YAML errors

**Solution:**

1. **Ensure correct preset fields:**
```yaml
# For heat_cool mode, need BOTH
climate:
  - platform: dual_smart_thermostat
    heater: switch.heater
    cooler: switch.cooler
    target_sensor: sensor.temp
    heat_cool_mode: true

    # ❌ Incomplete - won't show
    away_temp: 16

    # ✅ Complete - will show
    away_temp: 16
    away_temp_high: 28
```

2. **Restart Home Assistant:**
   - Preset configuration requires restart
   - Developer Tools → YAML → Restart

### Preset Temperature Doesn't Apply

**Problem:** You select a preset but temperature doesn't change to preset value.

**Diagnosis:**

1. **Check preset is actually selected:**
   - Developer Tools → States → `climate.your_thermostat`
   - Verify `preset_mode` attribute matches what you selected

2. **For templates, check entity states:**
   - Verify referenced entities have valid states
   - Check template evaluates correctly in Developer Tools

3. **Check for manual override:**
   - If you manually set temperature after selecting preset, preset is overridden
   - Preset mode stays active but uses manual temperature

**Solution:**

1. **Reselect preset to reapply:**
   - Select "none" preset
   - Select desired preset again
   - This forces re-evaluation

2. **For templates, verify entities:**
```yaml
# Check each entity referenced in template exists and has valid state
{{ states('input_number.away_temp') }}  # Should return number
```

---

## Configuration Issues

### Integration Fails to Load

**Problem:** After adding configuration, integration doesn't load or Home Assistant shows error.

**Diagnosis:**

1. **Check configuration syntax:**
   - Configuration → Server Controls → Check Configuration
   - Look for YAML syntax errors (indentation, quotes, etc.)

2. **Check logs:**
   - Settings → System → Logs
   - Filter for "dual_smart_thermostat"
   - Look for setup errors

**Common Causes:**

1. **Invalid entity references:**
```yaml
# ❌ Entity doesn't exist
heater: switch.nonexistent_heater

# ✅ Use existing entity
heater: switch.heater
```

2. **Missing required fields:**
```yaml
# ❌ Missing target_sensor
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.heater

# ✅ Include required fields
climate:
  - platform: dual_smart_thermostat
    name: My Thermostat
    heater: switch.heater
    target_sensor: sensor.temperature  # Required
```

3. **Incompatible feature combinations:**
```yaml
# ❌ Can't use both ac_mode and heat_cool_mode
climate:
  - platform: dual_smart_thermostat
    # ...
    ac_mode: true
    heat_cool_mode: true  # Conflict!

# ✅ Choose one mode
climate:
  - platform: dual_smart_thermostat
    # ...
    heat_cool_mode: true
```

### Entities Not Showing Up

**Problem:** Climate entity doesn't appear in Home Assistant after configuration.

**Solution:**

1. **Restart Home Assistant:**
   - Developer Tools → YAML → Restart

2. **Check entity registry:**
   - Settings → Devices & Services → Entities
   - Search for your thermostat name
   - May be disabled - click to enable

3. **Check for duplicate names:**
   - Entity names must be unique
   - If name conflicts, entity won't be created

---

## Debugging Tools

### Enable Debug Logging

Add to `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.dual_smart_thermostat: debug
```

This provides detailed logs for:
- Template evaluation
- Entity state changes
- Control cycle triggers
- Listener registration/cleanup

### Template Testing

**Developer Tools → Template:**

Test templates before using in configuration:

```jinja2
{# Test entity reference #}
{{ states('input_number.away_temp') | float }}

{# Test conditional #}
{{ 16 if is_state('sensor.season', 'winter') else 26 }}

{# Test calculation #}
{{ states('sensor.outdoor') | float + 5 }}

{# Test with default #}
{{ states('sensor.outdoor') | float(20) }}
```

### Check Climate Entity State

**Developer Tools → States:**

Find `climate.your_thermostat` and check:
- `state`: Current HVAC mode (heat, cool, off, etc.)
- `temperature`: Current target temperature (should show evaluated template value, not template string)
- `current_temperature`: Current room temperature
- `preset_mode`: Active preset ("none", "away", "eco", etc.)
- `target_temp_low` / `target_temp_high`: For heat_cool mode

**What to Look For:**
```yaml
# ❌ Problem - showing template string
temperature: "{{ states('sensor.outdoor') | float }}"

# ✅ Correct - showing evaluated number
temperature: 20.5
```

### Monitor Entity Changes

**Developer Tools → Events:**

Listen to `state_changed` events:

```yaml
# Event type: state_changed
# Entity: input_number.away_temp

# Watch for events when you change the input_number
# Climate entity should respond within 1-2 seconds
```

### Check Listener Registration

With debug logging enabled, look for log messages:

```
DEBUG: Setting up template entity listeners for preset: away
DEBUG: Extracted entities from template: ['input_number.away_temp']
DEBUG: Registering state change listener for: input_number.away_temp
```

If you don't see these messages:
- Template may not be detected as template
- Entity extraction may have failed
- Check template syntax

### Verify Template Entities Extracted

Templates are analyzed to extract entity references. Check logs for:

```
DEBUG: Template entities for preset 'away': ['sensor.outdoor_temp', 'sensor.season']
```

If entities not extracted:
- Complex templates may not have entities auto-detected
- Manually verify entities exist and are correct

---

## Getting Help

If you've tried these troubleshooting steps and still have issues:

1. **Check GitHub Issues:**
   - https://github.com/swingerman/ha-dual-smart-thermostat/issues
   - Search for similar issues
   - Check closed issues for solutions

2. **Enable Debug Logging:**
   - Capture relevant log excerpts
   - Include in issue report

3. **Provide Configuration:**
   - Share your YAML configuration (redact sensitive info)
   - Include entity states from Developer Tools
   - Show template test results

4. **Home Assistant Community:**
   - https://community.home-assistant.io/
   - Search for similar questions
   - Post in appropriate category

5. **Report a Bug:**
   - https://github.com/swingerman/ha-dual-smart-thermostat/issues/new
   - Include Home Assistant version
   - Include integration version
   - Include debug logs
   - Include configuration
   - Describe expected vs actual behavior
