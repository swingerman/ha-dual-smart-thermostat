# Data Model: Template-Based Preset Temperatures

**Feature**: 004-template-based-presets
**Date**: 2025-12-01
**Purpose**: Define data structures and relationships for template support in preset temperatures

## Entity Definitions

### 1. PresetConfiguration (Enhanced)

**Location**: `custom_components/dual_smart_thermostat/preset_env/preset_env.py`

**Type**: Python class (`PresetEnv`)

**Purpose**: Represents temperature settings for a specific preset mode, enhanced to support both static values and template strings

**Attributes**:

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| `preset_name` | string | Yes | Preset identifier (away, eco, comfort, home, sleep, activity, boost, anti_freeze) |
| `temperature` | float \| None | No | Single temperature mode target (static value or evaluated template result) |
| `target_temp_low` | float \| None | No | Range mode low threshold (static value or evaluated template result) |
| `target_temp_high` | float \| None | No | Range mode high threshold (static value or evaluated template result) |
| `_template_fields` | dict[str, str] | Internal | Maps field names to template strings (e.g., {"temperature": "{{ states('sensor.temp') }}"}) |
| `_last_good_values` | dict[str, float] | Internal | Stores last successfully evaluated temperature for fallback on error |
| `_referenced_entities` | set[str] | Internal | Set of entity IDs referenced across all templates in this preset |

**Lifecycle**:
```
Created → Template Detection → Entity Extraction → Ready
                ↓                       ↓
          Static: Store value    Template: Store string + extract entities
                ↓                       ↓
           Evaluation on demand (get_temperature())
                ↓
          Success: Update last_good_value | Failure: Use last_good_value
```

**Validation Rules**:
- At least one temperature field must be present (temperature OR target_temp_low + target_temp_high)
- Template strings must be valid Jinja2 syntax (validated at config time)
- Entity references in templates are not validated at config time (runtime only)
- Last good values default to 20.0 if no successful evaluation yet

**State Transitions**:
```
Initial State: No templates detected
   ↓
[_process_field() called]
   ↓
State: Templates identified, entities extracted
   ↓
[get_temperature() called]
   ↓
State: Template evaluated → Success OR Error
   ↓ (Success)                    ↓ (Error)
Update last_good_value      Use previous last_good_value
   ↓                               ↓
Return evaluated temp          Return fallback temp
```

**Relationships**:
- **Used by**: `PresetManager` (calls evaluation methods to get current temperatures)
- **Uses**: `HomeAssistant` instance (for template evaluation context)
- **References**: Home Assistant entities (sensors, input_numbers, etc. via templates)

---

### 2. TemplateEvaluationContext (New Internal)

**Location**: Used internally within `PresetEnv._evaluate_template()` method

**Type**: Implicit context (not a separate class, represented as method variables)

**Purpose**: Tracks the outcome of a single template evaluation attempt for logging and debugging

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `template_string` | string | Original template text being evaluated |
| `result` | float | Evaluated numeric temperature value |
| `success` | bool | Whether evaluation completed without errors |
| `error` | string \| None | Error message if evaluation failed, None if success |
| `timestamp` | datetime | When evaluation occurred (implicit via logging timestamp) |
| `entity_states` | dict[str, any] | Entity IDs and their states at evaluation time (for comprehensive error logging) |

**Lifecycle**:
```
Evaluation Requested
   ↓
Parse template string
   ↓
Render template (async)
   ↓ (Success)              ↓ (Exception)
Convert to float       Log error with context
   ↓                         ↓
Update last_good_value   Return last_good_value
   ↓                         ↓
Return result            Return fallback
```

**Usage**:
This context is used for logging when template evaluation occurs:
```python
_LOGGER.debug(
    "Template evaluation success for %s: %s -> %s",
    field_name,      # Which field (temperature, target_temp_low, etc.)
    template_str,    # Template string
    temp            # Result
)

_LOGGER.warning(
    "Template evaluation failed for %s: %s. "
    "Template: %s, Entities: %s, Keeping previous: %s",
    field_name,              # Which field
    e,                      # Error message
    template_str,           # Template string
    self._referenced_entities,  # Entity IDs
    previous                # Fallback value
)
```

---

### 3. TemplateListener (New Internal)

**Location**: Managed within `DualSmartThermostat` climate entity

**Type**: Implicit structure (represented as stored removal callbacks and entity sets)

**Purpose**: Tracks active entity state change listeners for template-based presets

**Attributes**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `entity_id` | string | Entity being monitored (e.g., "sensor.away_temp") |
| `preset_name` | string | Preset this listener belongs to (implicit via active preset) |
| `remove_callback` | Callable | Function to call to remove/cleanup this listener |
| `active` | bool | Whether listener is currently registered (tracked via list membership) |

**Storage in Climate Entity**:
```python
class DualSmartThermostat(ClimateEntity):
    def __init__(self):
        self._template_listeners: list[Callable] = []  # Removal callbacks
        self._active_preset_entities: set[str] = set()  # Currently monitored entities
```

**Lifecycle**:
```
Preset Activated with Templates
   ↓
Extract referenced entities from PresetEnv
   ↓
For each entity:
   ↓
   Setup listener (async_track_state_change_event)
   ↓
   Store removal callback in _template_listeners
   ↓
   Add entity_id to _active_preset_entities
   ↓
Listener Active (monitoring state changes)
   ↓
[Preset Changes OR Entity Removed]
   ↓
Call all removal callbacks
   ↓
Clear _template_listeners list
   ↓
Clear _active_preset_entities set
   ↓
Listeners Cleaned Up
```

**Memory Management**:
- Removal callbacks MUST be called to prevent memory leaks
- Cleanup occurs on:
  - Preset change (different preset may have different entities)
  - Preset set to None (no active preset)
  - Thermostat entity removed from Home Assistant
- Unit tests verify listener count returns to zero after cleanup

---

## Data Relationships

### Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Home Assistant                           │
│  (provides: Template Engine, Entity Registry, Event Bus)   │
└────────────┬────────────────────────────────────┬───────────┘
             │                                    │
             │ Uses template engine               │ Listens to events
             ↓                                    ↓
┌────────────────────────┐             ┌─────────────────────────┐
│    PresetConfiguration │             │   TemplateListener      │
│      (PresetEnv)       │             │   (Climate Entity)      │
├────────────────────────┤             ├─────────────────────────┤
│ - preset_name          │←────────────│ - entity_id             │
│ - temperature          │  References │ - remove_callback       │
│ - target_temp_low      │             │ - active                │
│ - target_temp_high     │             └─────────────────────────┘
│ - _template_fields     │                        ↑
│ - _last_good_values    │                        │ Monitors
│ - _referenced_entities │                        │
└────────────┬───────────┘                        │
             │                                    │
             │ Provides temperatures              │
             ↓                                    │
┌────────────────────────┐                        │
│     PresetManager      │                        │
├────────────────────────┤                        │
│ - presets dict         │                        │
│ - active preset        │                        │
└────────────┬───────────┘                        │
             │                                    │
             │ Applies preset temps               │
             ↓                                    │
┌────────────────────────┐                        │
│   Environment Manager  │                        │
├────────────────────────┤                        │
│ - target_temp          │                        │
│ - target_temp_low      │                        │
│ - target_temp_high     │                        │
└────────────────────────┘                        │
                                                  │
┌─────────────────────────────────────────────────┘
│
│   Referenced by templates
│
┌────────────────────────┐
│  Home Assistant        │
│  Entities              │
├────────────────────────┤
│ - sensor.away_temp     │
│ - sensor.season        │
│ - input_number.eco     │
│ - etc.                 │
└────────────────────────┘
```

### Data Flow: Template Evaluation

```
User activates Away preset
   ↓
PresetManager.set_preset_mode("away")
   ↓
Get PresetEnv for "away"
   ↓
PresetEnv.get_temperature(hass)
   ↓
Check if field is template: Yes
   ↓
PresetEnv._evaluate_template(hass, "temperature")
   ↓
Template.async_render() → "18.5"
   ↓
Convert to float: 18.5
   ↓
Store in _last_good_values["temperature"] = 18.5
   ↓
Return 18.5
   ↓
PresetManager sets environment.target_temp = 18.5
   ↓
Climate entity triggers control cycle
```

### Data Flow: Reactive Update

```
sensor.away_temp changes from 18 to 20
   ↓
Home Assistant fires state_changed event
   ↓
TemplateListener detects change (entity in _active_preset_entities)
   ↓
Climate._async_template_entity_changed(event)
   ↓
Get current PresetEnv from PresetManager
   ↓
PresetEnv.get_temperature(hass)  [Re-evaluation]
   ↓
Template evaluates with new sensor state: 20
   ↓
Update _last_good_values["temperature"] = 20
   ↓
Return 20
   ↓
Climate entity updates environment.target_temp = 20
   ↓
Climate triggers control cycle (force=True)
   ↓
Climate writes updated state to HA
```

---

## Configuration Storage

### Config Entry JSON Structure

Home Assistant stores configuration as JSON in `.storage/core.config_entries`:

```json
{
  "entry_id": "abc123",
  "version": 1,
  "domain": "dual_smart_thermostat",
  "title": "Living Room Thermostat",
  "data": {
    "name": "Living Room Thermostat",
    "heater": "switch.heater",
    "target_sensor": "sensor.room_temp"
  },
  "options": {
    "presets": ["away", "eco", "comfort"],
    "away_temp": "{{ 16 if is_state('sensor.season', 'winter') else 26 }}",
    "eco_temp": 20,
    "comfort_temp": "{{ states('input_number.comfort_temp') | float }}",
    "heat_cool_mode": true,
    "away_temp_low": 18,
    "away_temp_high": "{{ states('sensor.outdoor_temp') | float + 4 }}"
  }
}
```

**Type Detection**:
- Numeric value (20): Static temperature
- String value with templates ("{{ ... }}"): Template to evaluate
- Auto-detection happens in `PresetEnv.__init__()` when loading from config

---

## Validation Rules

### At Configuration Time (Config Flow)

**Syntax Validation**:
```python
def validate_template_syntax(value: Any) -> Any:
    if isinstance(value, str):
        try:
            Template(value)  # Parse only, don't evaluate
        except TemplateError as e:
            raise vol.Invalid(f"Invalid template syntax: {e}")
    return value
```

**Validated**: Template structure and Jinja2 grammar
**Not Validated**: Entity existence, template evaluation result

### At Runtime (Template Evaluation)

**Evaluation Validation**:
```python
def _evaluate_template(self, hass, field_name):
    try:
        result = template.async_render()
        temp = float(result)  # Must be convertible to float

        # Store as last good value
        self._last_good_values[field_name] = temp
        return temp
    except (ValueError, TypeError, TemplateError) as e:
        # Keep previous value
        previous = self._last_good_values.get(field_name, 20.0)
        _LOGGER.warning("Template evaluation failed: %s", e)
        return previous
```

**Validated**:
- Template evaluation succeeds
- Result is numeric (convertible to float)
- Fallback if validation fails

---

## Constraints

### Performance Constraints

- Template evaluation MUST complete within 1 second
- Temperature update after entity change MUST occur within 5 seconds
- No memory leaks from listeners (cleanup verified in tests)

### Data Constraints

- Temperature values: Typically 5°C to 35°C (system-specific min/max enforced elsewhere)
- Template strings: No length limit (reasonable templates expected <500 chars)
- Entity references: No limit on number of entities per template
- Preset names: Limited to predefined set (away, eco, comfort, etc.)

### Backward Compatibility Constraints

- Existing numeric configs MUST continue working unchanged
- No config migration required
- Mixed static/template values supported in same configuration

---

## Summary

The data model extends existing PresetEnv to support template strings alongside static values. Template evaluation is lazy (on-demand), with reactive updates triggered by entity state changes. The system maintains robustness through fallback values and comprehensive error logging. All data flows through existing architectural patterns (PresetManager → PresetEnv → Environment), with template support as a transparent enhancement.
