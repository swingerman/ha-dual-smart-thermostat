# Research: Template-Based Preset Temperatures

**Feature**: 004-template-based-presets
**Date**: 2025-12-01
**Purpose**: Resolve technical unknowns and establish design patterns for template support in preset temperatures

## Research Areas

### 1. Home Assistant Template Engine Integration

**Question**: How do we integrate with Home Assistant's template engine for parsing, entity extraction, and evaluation?

**Decision**: Use `homeassistant.helpers.template.Template` class with standard patterns

**Rationale**:
- `Template` class provides complete template lifecycle: parse → extract entities → render
- `Template.extract_entities()` returns set of entity IDs referenced in template (no need for manual parsing)
- `template.async_render()` evaluates template asynchronously (thread-safe for HA event loop)
- Error handling: Template parsing throws exceptions for syntax errors, rendering throws for evaluation errors
- Existing HA components use this pattern extensively (template sensor, automation)

**Implementation Pattern**:
```python
from homeassistant.helpers.template import Template

# Parse and validate syntax
template = Template("{{ states('sensor.temp') | float }}", hass)

# Extract referenced entities
entities = template.extract_entities()  # Returns: {'sensor.temp'}

# Evaluate template
try:
    result = template.async_render()
    temp = float(result)
except Exception as e:
    # Handle error, use fallback
    _LOGGER.warning("Template evaluation failed: %s", e)
```

**Alternatives Considered**:
- Manual Jinja2 integration: Rejected - reinvents wheel, misses HA-specific functions (states(), is_state())
- String parsing for entities: Rejected - fragile, doesn't handle nested templates or filters

---

### 2. Template Listener Patterns in Home Assistant

**Question**: What's the best practice for setting up entity state change listeners that cleanup properly?

**Decision**: Use `async_track_state_change_event` with stored removal callbacks

**Rationale**:
- `async_track_state_change_event` is the current HA pattern (replaces deprecated `track_state_change`)
- Returns a removal callback that must be called to cleanup listener
- Supports filtering by specific entity IDs
- Event-based (not polling), efficient for reactive updates
- Used throughout HA core (automation, template binary_sensor, etc.)

**Implementation Pattern**:
```python
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.core import callback, Event

# Setup listener
remove_listener = async_track_state_change_event(
    hass,
    ["sensor.away_temp", "sensor.eco_temp"],
    self._async_template_entity_changed
)

# Store removal callback
self._template_listeners.append(remove_listener)

# Cleanup
for remove in self._template_listeners:
    remove()  # Unregisters listener
self._template_listeners.clear()

@callback
async def _async_template_entity_changed(self, event: Event):
    """Handle entity state change."""
    entity_id = event.data.get("entity_id")
    new_state = event.data.get("new_state")
    # Re-evaluate template...
```

**Memory Leak Prevention**:
- Store all removal callbacks in list
- Call all removals when: preset changes, preset set to None, entity removed from HA
- Unit test: Verify listener count goes to zero after cleanup

**Alternatives Considered**:
- Polling entity states: Rejected - inefficient, not reactive
- Single listener for all entities: Rejected - harder to track which preset's entities
- HA event system directly: Rejected - async_track_state_change_event abstracts complexity

---

### 3. TemplateSelector Configuration

**Question**: How do we integrate template input into Home Assistant config flow UI?

**Decision**: Use `selector.TemplateSelector` with syntax-only validation

**Rationale**:
- Home Assistant 2023.4+ provides built-in `TemplateSelector`
- Provides template editor with syntax highlighting in UI
- Accepts both static values and template strings (flexible input)
- Validation at config time prevents syntax errors from being saved
- Used by core HA integrations (input_text with templates, template helpers)

**Implementation Pattern**:
```python
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import selector
import voluptuous as vol

def get_presets_schema(user_input):
    return vol.Schema({
        vol.Optional("away_temp", default=20): vol.All(
            selector.TemplateSelector(
                selector.TemplateSelectorConfig()
            ),
            validate_template_syntax  # Custom validator
        )
    })

def validate_template_syntax(value):
    """Validate template syntax without evaluation."""
    if isinstance(value, str):
        try:
            Template(value)  # Parse only
        except Exception as e:
            raise vol.Invalid(f"Invalid template syntax: {e}")
    return value  # Return as-is (could be float or string)
```

**UI Behavior**:
- User sees template editor (code input with highlighting)
- Can enter static numeric: `20`
- Can enter template: `{{ states('sensor.temp') }}`
- Validation error shown inline if syntax invalid
- Valid input saved to config entry

**Alternatives Considered**:
- NumberSelector with string support: Rejected - no template editor, user confusion
- Custom selector: Rejected - reinvents wheel, lose HA UI consistency
- TextSelector: Rejected - no syntax highlighting, template-specific features

---

### 4. Test Patterns for Async Home Assistant Components

**Question**: How do we test async template evaluation and reactive state changes in Home Assistant?

**Decision**: Use `pytest-homeassistant-custom-component` fixtures with manual state manipulation

**Rationale**:
- `pytest-homeassistant-custom-component` provides `hass` fixture (full HA instance)
- `hass.states.async_set()` allows manual entity state changes for testing
- `await hass.async_block_till_done()` ensures async operations complete before assertions
- Event triggering: State changes trigger listeners automatically
- Standard pattern across HA custom component tests

**Implementation Pattern**:
```python
import pytest
from homeassistant.core import HomeAssistant

@pytest.mark.asyncio
async def test_template_reactive_update(hass: HomeAssistant):
    """Test that template re-evaluates when entity changes."""

    # Setup entity with initial state
    hass.states.async_set("sensor.away_temp", 18)
    await hass.async_block_till_done()

    # Create thermostat with template preset
    thermostat = create_thermostat(
        hass,
        away_temp="{{ states('sensor.away_temp') | float }}"
    )
    await thermostat.async_added_to_hass()

    # Activate preset
    await thermostat.async_set_preset_mode("away")
    await hass.async_block_till_done()

    # Verify initial temperature
    assert thermostat.target_temperature == 18

    # Change entity state
    hass.states.async_set("sensor.away_temp", 20)
    await hass.async_block_till_done()

    # Verify temperature updated (reactive)
    assert thermostat.target_temperature == 20
```

**Timing and Async**:
- Use `await hass.async_block_till_done()` after state changes
- For timing tests: `asyncio.sleep(0.1)` then check state
- Mock `_async_control_climate` to verify it's called after template update

**Alternatives Considered**:
- Mock Template class: Rejected - doesn't test real integration
- Synchronous tests: Rejected - HA is async, need real event loop
- Real HA instance: Rejected - slow, pytest-homeassistant provides test instance

---

### 5. Backward Compatibility Strategy

**Question**: How do we ensure existing static preset configurations continue working without modification?

**Decision**: Auto-detect value type (float vs string) in PresetEnv, no config migration needed

**Rationale**:
- Config entries store values as-is: floats remain floats, new strings are templates
- `isinstance(value, (int, float))` check distinguishes static from template
- No migration code needed - existing configs load unchanged
- New configs can mix static and template values per preset

**Detection Logic**:
```python
def _process_field(self, field_name: str, value: Any):
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

**Testing Strategy**:
- P1 priority: Test suite verifies static values unchanged
- Load existing test configs (from test fixtures)
- Assert temperature values match exactly
- Run all existing preset tests - should pass without modification

**Alternatives Considered**:
- Explicit type flag: Rejected - requires config migration, adds complexity
- Always treat as template: Rejected - breaks existing configs
- Migration on load: Rejected - unnecessary, auto-detect sufficient

---

## Best Practices Summary

### Template Evaluation
- Always wrap evaluation in try/except
- Keep last known good value for fallback
- Log template string + entities + error for debugging
- Set reasonable timeout (1s) for evaluation

### Listener Management
- Store all removal callbacks
- Clean up on: preset change, set to None, entity removal
- Test listener count after cleanup (should be 0)
- Use `@callback` decorator for event handlers

### Configuration Flow
- Use TemplateSelector for template input fields
- Validate syntax at config time (don't validate entity existence)
- Provide inline help with 2-3 examples
- Support both static and template values in same field

### Testing
- Use pytest-homeassistant-custom-component fixtures
- Manual state manipulation with `hass.states.async_set()`
- `await hass.async_block_till_done()` before assertions
- Test both static and template values in same test file

### Error Handling
- Never crash on template errors
- Keep previous value on evaluation failure
- Log sufficient detail for troubleshooting
- Graceful degradation maintains thermostat service

## References

- Home Assistant Template Documentation: https://www.home-assistant.io/docs/configuration/templating/
- TemplateSelector Source: `homeassistant/helpers/selector.py`
- Template Engine Source: `homeassistant/helpers/template.py`
- Event Tracking: `homeassistant/helpers/event.py`
- pytest-homeassistant-custom-component: https://github.com/MatthewFlamm/pytest-homeassistant-custom-component

## Open Questions

None - all technical unknowns resolved through research.
