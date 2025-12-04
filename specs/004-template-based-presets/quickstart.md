# Quickstart: Template-Based Preset Temperatures

**Feature**: 004-template-based-presets
**For**: Developers implementing template support in preset temperatures
**Time**: 15 minutes to understand, 2-3 days to implement

## Overview

This feature adds Home Assistant template support to preset temperatures, allowing temperatures to dynamically adjust based on sensor values, time of day, seasons, or any other Home Assistant state. Users can enter templates like `{{ 16 if is_state('sensor.season', 'winter') else 26 }}` instead of static values like `20`.

**Key Points**:
- ✅ Backward compatible - static values still work
- ✅ Reactive - templates re-evaluate when entities change
- ✅ Graceful degradation - errors fallback to previous value
- ✅ Config flow integrated - TemplateSelector with inline help

## Architecture At A Glance

```
User enters template in config flow
    ↓
PresetEnv stores template string
    ↓
Climate entity activates preset
    ↓
PresetEnv evaluates template → returns temperature
    ↓
Climate entity sets up listeners for template entities
    ↓
Entity state changes
    ↓
Template re-evaluates → new temperature
    ↓
Climate entity updates target temperature
```

## 5-Minute Implementation Walkthrough

### 1. PresetEnv: Template Processing (Core Logic)

**File**: `custom_components/dual_smart_thermostat/preset_env/preset_env.py`

**Add to `__init__`**:
```python
def __init__(self, **kwargs):
    # Existing init...

    # NEW: Template tracking
    self._template_fields: dict[str, str] = {}
    self._last_good_values: dict[str, float] = {}
    self._referenced_entities: set[str] = set()

    # Process temperature fields
    self._process_field('temperature', kwargs.get(ATTR_TEMPERATURE))
    self._process_field('target_temp_low', kwargs.get(ATTR_TARGET_TEMP_LOW))
    self._process_field('target_temp_high', kwargs.get(ATTR_TARGET_TEMP_HIGH))
```

**Add method**:
```python
def _process_field(self, field_name: str, value: Any) -> None:
    """Detect static vs template, extract entities."""
    if value is None:
        return

    if isinstance(value, (int, float)):
        # Static value - existing behavior
        setattr(self, field_name, float(value))
        self._last_good_values[field_name] = float(value)
    elif isinstance(value, str):
        # Template string - new behavior
        self._template_fields[field_name] = value
        self._extract_entities(value)
```

**Why**: This is the core detection logic - everything else builds on this.

---

### 2. PresetEnv: Template Evaluation

**Add methods**:
```python
def get_temperature(self, hass: HomeAssistant) -> float | None:
    """Get temperature, evaluating template if needed."""
    if 'temperature' in self._template_fields:
        return self._evaluate_template(hass, 'temperature')
    return self.temperature

def _evaluate_template(self, hass: HomeAssistant, field_name: str) -> float:
    """Safely evaluate with fallback."""
    template_str = self._template_fields.get(field_name)
    if not template_str:
        return self._last_good_values.get(field_name, 20.0)

    try:
        from homeassistant.helpers.template import Template
        template = Template(template_str, hass)
        result = template.async_render()
        temp = float(result)

        self._last_good_values[field_name] = temp
        _LOGGER.debug("Template eval success: %s -> %s", field_name, temp)
        return temp
    except Exception as e:
        previous = self._last_good_values.get(field_name, 20.0)
        _LOGGER.warning("Template eval failed: %s. Keeping: %s", e, previous)
        return previous
```

**Why**: This handles template evaluation with error recovery - critical for stability.

---

### 3. PresetManager: Use Template-Aware Getters

**File**: `custom_components/dual_smart_thermostat/managers/preset_manager.py`

**Modify `_set_presets_when_have_preset_mode`**:
```python
# OLD:
if self._features.is_range_mode:
    self._environment.target_temp_low = self._preset_env.target_temp_low
    self._environment.target_temp_high = self._preset_env.target_temp_high
else:
    self._environment.target_temp = self._preset_env.temperature

# NEW:
if self._features.is_range_mode:
    temp_low = self._preset_env.get_target_temp_low(self.hass)  # Now template-aware
    temp_high = self._preset_env.get_target_temp_high(self.hass)
    if temp_low is not None:
        self._environment.target_temp_low = temp_low
    if temp_high is not None:
        self._environment.target_temp_high = temp_high
else:
    temp = self._preset_env.get_temperature(self.hass)  # Now template-aware
    if temp is not None:
        self._environment.target_temp = temp
```

**Why**: This integrates template evaluation into the preset activation flow.

---

### 4. Climate Entity: Reactive Listeners

**File**: `custom_components/dual_smart_thermostat/climate.py`

**Add to `__init__`**:
```python
def __init__(self, ...):
    # Existing init...

    self._template_listeners: list[Callable] = []
    self._active_preset_entities: set[str] = set()
```

**Add methods**:
```python
async def _setup_template_listeners(self) -> None:
    """Set up listeners for template entities."""
    await self._remove_template_listeners()  # Clean up old

    if self.presets.preset_mode == PRESET_NONE:
        return

    preset_env = self.presets.preset_env
    if not preset_env.has_templates():
        return

    from homeassistant.helpers.event import async_track_state_change_event

    for entity_id in preset_env.referenced_entities:
        remove_listener = async_track_state_change_event(
            self.hass,
            entity_id,
            self._async_template_entity_changed
        )
        self._template_listeners.append(remove_listener)
        self._active_preset_entities.add(entity_id)

async def _remove_template_listeners(self) -> None:
    """Clean up listeners."""
    for remove in self._template_listeners:
        remove()
    self._template_listeners.clear()
    self._active_preset_entities.clear()

@callback
async def _async_template_entity_changed(self, event: Event) -> None:
    """Handle entity change."""
    preset_env = self.presets.preset_env

    if self.features.is_range_mode:
        temp_low = preset_env.get_target_temp_low(self.hass)
        temp_high = preset_env.get_target_temp_high(self.hass)
        if temp_low is not None:
            self.environment.target_temp_low = temp_low
        if temp_high is not None:
            self.environment.target_temp_high = temp_high
    else:
        temp = preset_env.get_temperature(self.hass)
        if temp is not None:
            self.environment.target_temp = temp

    await self._async_control_climate(force=True)
    self.async_write_ha_state()
```

**Integrate into lifecycle**:
```python
async def async_added_to_hass(self) -> None:
    # Existing code...
    await self._setup_template_listeners()  # NEW

async def async_set_preset_mode(self, preset_mode: str) -> None:
    # Existing code...
    await self._setup_template_listeners()  # NEW

async def async_will_remove_from_hass(self) -> None:
    # Existing code...
    await self._remove_template_listeners()  # NEW
```

**Why**: This makes templates reactive - the key user-facing feature.

---

### 5. Config Flow: TemplateSelector

**File**: `custom_components/dual_smart_thermostat/schemas.py`

**Modify `get_presets_schema`**:
```python
# OLD:
from homeassistant.helpers import selector
schema_dict[vol.Optional(f"{preset}_temp", default=20)] = cv.positive_float

# NEW:
schema_dict[vol.Optional(f"{preset}_temp", default=20)] = vol.All(
    selector.TemplateSelector(
        selector.TemplateSelectorConfig()
    ),
    validate_template_syntax  # NEW validator
)
```

**Add validator**:
```python
def validate_template_syntax(value: Any) -> Any:
    """Validate template syntax if string."""
    if isinstance(value, str):
        try:
            from homeassistant.helpers.template import Template
            Template(value)  # Parse only, don't evaluate
        except Exception as e:
            raise vol.Invalid(f"Invalid template syntax: {e}")
    return value
```

**Why**: This provides the UI for users to enter templates with validation.

---

## Testing Checklist

### Unit Tests (tests/preset_env/)

- [ ] Static value backward compatible
- [ ] Template detection (string vs numeric)
- [ ] Entity extraction
- [ ] Template evaluation success
- [ ] Template evaluation error (fallback)

### Integration Tests (tests/)

- [ ] Reactive update on entity change
- [ ] Listener cleanup on preset change
- [ ] Multiple entity references

### Config Flow Tests (tests/config_flow/)

- [ ] TemplateSelector accepts templates
- [ ] Syntax validation catches errors
- [ ] Static values still work

### E2E Tests (tests/config_flow/)

- [ ] Template persists through options flow
- [ ] Range mode with templates
- [ ] Seasonal template example

## Common Pitfalls

### 1. Forgetting `hass` Parameter

❌ **Wrong**:
```python
temp = preset_env.temperature  # Old direct access
```

✅ **Right**:
```python
temp = preset_env.get_temperature(self.hass)  # Template-aware getter
```

### 2. Not Cleaning Up Listeners

❌ **Wrong**:
```python
# Set up listeners but never remove them
async def _setup_template_listeners(self):
    for entity_id in entities:
        async_track_state_change_event(...)  # Leaks!
```

✅ **Right**:
```python
# Store removal callbacks and clean up
remove_listener = async_track_state_change_event(...)
self._template_listeners.append(remove_listener)  # Store for cleanup

async def _remove_template_listeners(self):
    for remove in self._template_listeners:
        remove()  # Clean up
    self._template_listeners.clear()
```

### 3. Validating Entity Existence at Config Time

❌ **Wrong**:
```python
def validate_template_syntax(value):
    template = Template(value)
    entities = template.extract_entities()
    for entity_id in entities:
        if not hass.states.get(entity_id):  # Don't do this!
            raise vol.Invalid(f"Entity {entity_id} not found")
```

✅ **Right**:
```python
def validate_template_syntax(value):
    Template(value)  # Only validate syntax
    # Entity existence checked at runtime
```

**Why**: Users may want to create the template before creating the entity.

---

## Debug Tips

### Enable Debug Logging

Add to `configuration.yaml`:
```yaml
logger:
  default: warning
  logs:
    custom_components.dual_smart_thermostat.preset_env: debug
    custom_components.dual_smart_thermostat.managers.preset_manager: debug
    custom_components.dual_smart_thermostat.climate: debug
```

### Check Logs For

**Template evaluation**:
```
DEBUG: Template eval success: temperature -> 18.5
WARNING: Template eval failed: ... Keeping: 18.0
```

**Listener setup**:
```
INFO: Template listeners active for preset 'away': {'sensor.away_temp'}
DEBUG: Removing 3 template listeners
```

**Entity changes**:
```
INFO: Template entity changed: sensor.away_temp (18 -> 20), re-evaluating
DEBUG: Re-evaluated template temp: 20.0
```

---

## Next Steps

1. **Read full plan**: [plan.md](plan.md)
2. **Review data model**: [data-model.md](data-model.md)
3. **Study API contract**: [contracts/preset_env_api.md](contracts/preset_env_api.md)
4. **Run tests**: `pytest tests/preset_env/ tests/managers/` (create tests first!)
5. **Implement in order**: PresetEnv → PresetManager → Climate → Config Flow → Tests

## Resources

- **Spec**: [spec.md](spec.md) - Complete requirements
- **Research**: [research.md](research.md) - Technical decisions explained
- **CLAUDE.md**: Project guidelines and architecture patterns
- **Home Assistant Templates**: https://www.home-assistant.io/docs/configuration/templating/

## Questions?

- Check existing implementation patterns in codebase
- Refer to research.md for design decisions
- Review test files for usage examples
- Consult CLAUDE.md for project-specific constraints
