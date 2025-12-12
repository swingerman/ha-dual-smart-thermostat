# Feature Specification: Template-Based Preset Temperatures

**Status**: 🟢 Ready
**Issue**: [#96](https://github.com/swingerman/ha-dual-smart-thermostat/issues/96)
**Created**: 2025-12-01
**Target Version**: TBD

---

## Table of Contents
1. [Overview](#overview)
2. [Requirements](#requirements)
3. [Design Decisions](#design-decisions)
4. [Technical Design](#technical-design)
5. [Testing Strategy](#testing-strategy)
6. [Documentation Plan](#documentation-plan)
7. [Implementation Checklist](#implementation-checklist)

---

## Overview

### Problem Statement

Currently, preset temperatures in the Dual Smart Thermostat must be configured as static numeric values. Users cannot dynamically adjust preset temperatures based on:
- Seasonal conditions (winter vs summer)
- Outdoor temperature readings
- Time of day
- Custom sensors or complex logic

**User Request**: "I would like to be able to use a value template to set the preset temperatures. During winter I would like to lower the temperature as an 'Away' preset (say 16 degrees) to not heat excessively when no one is in the house, but during summer I don't wish to cool down to this lower temperature."

### Solution Summary

Implement support for Home Assistant templates in preset temperature configuration, allowing users to:
- Use static values (backward compatible): `20`
- Reference entity values: `{{ states('sensor.away_temp') }}`
- Use complex template logic: `{{ 16 if is_state('sensor.season', 'winter') else 24 }}`

Preset temperatures will **reactively update** when template entities change, ensuring the thermostat automatically adjusts to dynamic conditions.

### Benefits

- **Dynamic presets** - Temperatures automatically adjust based on conditions
- **Simplified automation** - Logic embedded in preset, not external automations
- **Flexibility** - Supports simple entity references and complex calculations
- **Backward compatible** - Existing static configurations continue working

---

## Requirements

### Functional Requirements

1. **FR-1**: Users shall be able to enter Home Assistant templates for preset temperatures
2. **FR-2**: Templates shall support all standard Jinja2 syntax and HA template functions
3. **FR-3**: Templates shall reactively update when referenced entities change state
4. **FR-4**: Template evaluation errors shall not crash the system or prevent preset use
5. **FR-5**: Static numeric values shall continue to work (backward compatibility)
6. **FR-6**: Template support shall be available for:
   - Single temperature mode (`temperature`)
   - Temperature range mode (`target_temp_low`, `target_temp_high`)
7. **FR-7**: Config flow shall validate template syntax before saving
8. **FR-8**: Users shall receive clear guidance on how to use templates

### Non-Functional Requirements

1. **NFR-1**: Template evaluation shall not introduce noticeable performance degradation
2. **NFR-2**: Template listeners shall be properly cleaned up to prevent memory leaks
3. **NFR-3**: System shall remain stable if template evaluation fails
4. **NFR-4**: Existing configurations shall migrate seamlessly without user intervention

### Out of Scope (Future Enhancements)

- Template support for humidity fields (can be added in Phase 2)
- Template support for floor temperature limits (can be added in Phase 2)
- Template testing/preview UI in config flow
- Template performance metrics/monitoring

---

## Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| **D1** | Single unified template field | Simplifies UX, reduces config complexity | Mode selector (static/entity/template) - rejected as too complex |
| **D2** | Reactive template evaluation | Provides truly dynamic presets, matches user expectations | Evaluate only on preset change - rejected as less powerful |
| **D3** | Keep previous value on error | Safest approach, prevents unexpected temperature changes | Use default value, or prevent preset activation - rejected |
| **D4** | Support all temp fields (temp, low, high) | Enables full range mode support from launch | Start with single temp only - rejected, user wants range support |
| **D5** | Auto-detect static vs template | Backward compatible, no migration needed | Explicit type flag - rejected as unnecessary |
| **D6** | Validate syntax only at config time | Catches obvious errors without false negatives | Test evaluation or no validation - balanced approach |
| **D7** | Update translations with template hints | Helps users discover and understand feature | Generic descriptions - rejected, users need guidance |

### Key Technical Choices

**Template Storage**:
- Store templates as strings in config entry
- Auto-detect type: `float` = static, `string` = template
- No explicit type markers needed (keeps config clean)

**Entity Tracking**:
- Use HA's `Template.extract_entities()` to find referenced entities
- Set up state change listeners for those entities only
- Clean up listeners on preset change or entity removal

**Error Handling**:
- Catch template evaluation exceptions
- Log warning with details
- Keep last successfully evaluated value
- Never crash or prevent preset from working

---

## Technical Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Config Flow                          │
│  - TemplateSelector for temperature inputs                 │
│  - Syntax validation before saving                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Configuration saved
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                       PresetEnv                             │
│  - Detects static vs template values                       │
│  - Extracts referenced entities                            │
│  - Evaluates templates with error handling                 │
│  - Maintains last good values as fallback                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Provides temperatures
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                     PresetManager                           │
│  - Calls PresetEnv to get current temperature values       │
│  - Applies evaluated temperatures to environment           │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │ Temperature updates
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Climate Entity                             │
│  - Sets up entity listeners for active preset              │
│  - Monitors template entity state changes                  │
│  - Re-evaluates templates when entities change             │
│  - Triggers control cycle with new temperatures            │
│  - Cleans up listeners on preset change/removal            │
└─────────────────────────────────────────────────────────────┘
```

### Component Changes

#### 1. schemas.py (Config Flow Schema)

**File**: `custom_components/dual_smart_thermostat/schemas.py`
**Function**: `get_presets_schema()` (line 1008)

**Changes**:
```python
def get_presets_schema(user_input: dict[str, Any]) -> vol.Schema:
    """Get presets configuration schema based on selected presets."""
    schema_dict = {}

    # ... existing preset detection logic ...

    for preset in selected_presets:
        if preset in CONF_PRESETS:
            if heat_cool_enabled:
                # Low temperature - accepts static, entity, or template
                schema_dict[vol.Optional(f"{preset}_temp_low", default=20)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax
                )

                # High temperature
                schema_dict[vol.Optional(f"{preset}_temp_high", default=24)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax
                )
            else:
                # Single temperature
                schema_dict[vol.Optional(f"{preset}_temp", default=20)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax
                )

    return vol.Schema(schema_dict)


def validate_template_syntax(value):
    """Validate template syntax if value is a string."""
    if isinstance(value, str):
        try:
            # Basic syntax check - don't evaluate, just parse
            from homeassistant.helpers.template import Template
            Template(value)
        except Exception as e:
            raise vol.Invalid(f"Invalid template syntax: {e}")
    return value
```

**Impact**: Config flow UI now shows template input field instead of number selector.

---

#### 2. preset_env.py (Preset Environment)

**File**: `custom_components/dual_smart_thermostat/preset_env/preset_env.py`
**Class**: `PresetEnv` (line 59)

**New Attributes**:
```python
class PresetEnv(TempEnv, HumidityEnv):
    def __init__(self, **kwargs):
        super(PresetEnv, self).__init__(**kwargs)

        # Template tracking
        self._template_fields = {}       # field_name -> template_string
        self._last_good_values = {}      # field_name -> last_successful_value
        self._referenced_entities = set() # Set of entity_ids used in templates

        # Process temperature values (auto-detect static vs template)
        self._process_field('temperature', kwargs.get(ATTR_TEMPERATURE))
        self._process_field('target_temp_low', kwargs.get(ATTR_TARGET_TEMP_LOW))
        self._process_field('target_temp_high', kwargs.get(ATTR_TARGET_TEMP_HIGH))
```

**New Methods**:

```python
def _process_field(self, field_name: str, value):
    """Process a field value to determine if it's static or template."""
    if value is None:
        return

    if isinstance(value, (int, float)):
        # Static value - backward compatible
        setattr(self, field_name, float(value))
        self._last_good_values[field_name] = float(value)
    elif isinstance(value, str):
        # Template string
        self._template_fields[field_name] = value
        # Extract referenced entities for listener setup
        self._extract_entities(value)


def _extract_entities(self, template_str: str):
    """Extract entity IDs referenced in template."""
    from homeassistant.helpers.template import Template
    try:
        template = Template(template_str)
        # Use HA's built-in method to find referenced entities
        entities = template.extract_entities()
        self._referenced_entities.update(entities)
    except Exception as e:
        _LOGGER.debug("Could not extract entities from template: %s", e)


def get_temperature(self, hass) -> float | None:
    """Get temperature, evaluating template if needed."""
    if 'temperature' in self._template_fields:
        return self._evaluate_template(hass, 'temperature')
    return self.temperature


def get_target_temp_low(self, hass) -> float | None:
    """Get target_temp_low, evaluating template if needed."""
    if 'target_temp_low' in self._template_fields:
        return self._evaluate_template(hass, 'target_temp_low')
    return self.target_temp_low


def get_target_temp_high(self, hass) -> float | None:
    """Get target_temp_high, evaluating template if needed."""
    if 'target_temp_high' in self._template_fields:
        return self._evaluate_template(hass, 'target_temp_high')
    return self.target_temp_high


def _evaluate_template(self, hass, field_name: str) -> float:
    """Safely evaluate template with fallback to previous value."""
    template_str = self._template_fields.get(field_name)
    if not template_str:
        return self._last_good_values.get(field_name, 20.0)

    try:
        from homeassistant.helpers.template import Template
        template = Template(template_str, hass)
        result = template.async_render()

        # Convert to float
        temp = float(result)

        # Store as last good value
        self._last_good_values[field_name] = temp

        _LOGGER.debug(
            "Template evaluation success for %s: %s -> %s",
            field_name, template_str, temp
        )
        return temp

    except Exception as e:
        # Keep previous value on error (Decision D3)
        previous = self._last_good_values.get(field_name, 20.0)
        _LOGGER.warning(
            "Template evaluation failed for %s: %s. Keeping previous: %s",
            field_name, e, previous
        )
        return previous


@property
def referenced_entities(self) -> set:
    """Return set of entities referenced in templates."""
    return self._referenced_entities


def has_templates(self) -> bool:
    """Check if this preset uses any templates."""
    return len(self._template_fields) > 0
```

**Impact**: PresetEnv can now handle both static and template values, with safe evaluation.

---

#### 3. preset_manager.py (Preset Manager)

**File**: `custom_components/dual_smart_thermostat/managers/preset_manager.py`
**Method**: `_set_presets_when_have_preset_mode()` (line 134)

**Changes**:
```python
def _set_presets_when_have_preset_mode(self, preset_mode: str):
    """Sets target temperatures when have preset is not none."""
    _LOGGER.debug("Setting presets when have preset mode")

    if self._features.is_range_mode:
        _LOGGER.debug("Setting preset in range mode")
    else:
        _LOGGER.debug("Setting preset in target mode")
        if self._preset_mode == PRESET_NONE:
            _LOGGER.debug(
                "Saving target temp when target and no preset: %s",
                self._environment.target_temp,
            )
            self._environment.saved_target_temp = self._environment.target_temp

    self._preset_mode = preset_mode
    self._preset_env = self.presets[preset_mode]

    # Evaluate templates to get actual values (NEW)
    if self._features.is_range_mode:
        temp_low = self._preset_env.get_target_temp_low(self.hass)
        temp_high = self._preset_env.get_target_temp_high(self.hass)

        if temp_low is not None:
            self._environment.target_temp_low = temp_low
        if temp_high is not None:
            self._environment.target_temp_high = temp_high
    else:
        temp = self._preset_env.get_temperature(self.hass)
        if temp is not None:
            self._environment.target_temp = temp
```

**Impact**: PresetManager now evaluates templates when applying presets.

---

#### 4. climate.py (Climate Entity - Reactive Listeners)

**File**: `custom_components/dual_smart_thermostat/climate.py`
**Class**: `DualSmartThermostat`

**New Attributes in `__init__`**:
```python
def __init__(self, ...):
    # ... existing init code ...

    self._template_listeners = []      # Store listener removal callbacks
    self._active_preset_entities = set()  # Currently tracked entities
```

**New Methods**:

```python
async def _setup_template_listeners(self):
    """Set up listeners for entities referenced in active preset templates.

    This implements reactive template evaluation (Decision D2).
    When entities referenced in preset templates change, the preset
    temperatures are automatically re-evaluated and updated.
    """
    # Remove old listeners first
    await self._remove_template_listeners()

    # Check if current preset uses templates
    if self.presets.preset_mode == PRESET_NONE:
        return

    preset_env = self.presets.preset_env
    if not preset_env.has_templates():
        return

    # Get entities referenced in templates
    entities = preset_env.referenced_entities
    _LOGGER.debug("Setting up template listeners for entities: %s", entities)

    # Set up listeners for each entity
    from homeassistant.helpers.event import async_track_state_change_event

    for entity_id in entities:
        # Track entity state changes
        remove_listener = async_track_state_change_event(
            self.hass,
            entity_id,
            self._async_template_entity_changed
        )
        self._template_listeners.append(remove_listener)
        self._active_preset_entities.add(entity_id)

    _LOGGER.info(
        "Template listeners active for preset '%s': %s",
        self.presets.preset_mode,
        self._active_preset_entities
    )


async def _remove_template_listeners(self):
    """Remove all template entity listeners.

    Called when:
    - Preset changes (new preset may use different entities)
    - Entity removed from HA
    - Thermostat turned off
    """
    if self._template_listeners:
        _LOGGER.debug(
            "Removing %d template listeners",
            len(self._template_listeners)
        )

    for remove_listener in self._template_listeners:
        remove_listener()

    self._template_listeners.clear()
    self._active_preset_entities.clear()


@callback
async def _async_template_entity_changed(self, event: Event):
    """Handle changes to entities referenced in preset templates.

    This is the core of reactive template evaluation:
    1. Template entity state changes
    2. This callback fires
    3. Templates re-evaluated
    4. New temperatures applied
    5. Control cycle triggered
    """
    entity_id = event.data.get("entity_id")
    new_state = event.data.get("new_state")
    old_state = event.data.get("old_state")

    if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        _LOGGER.debug(
            "Template entity %s unavailable, skipping template update",
            entity_id
        )
        return

    _LOGGER.info(
        "Template entity changed: %s (%s -> %s), re-evaluating preset temperatures",
        entity_id,
        old_state.state if old_state else "unknown",
        new_state.state
    )

    # Re-evaluate templates and update temperatures
    preset_env = self.presets.preset_env

    if self.features.is_range_mode:
        temp_low = preset_env.get_target_temp_low(self.hass)
        temp_high = preset_env.get_target_temp_high(self.hass)

        _LOGGER.debug(
            "Re-evaluated template temps (range): low=%s, high=%s",
            temp_low, temp_high
        )

        if temp_low is not None:
            self.environment.target_temp_low = temp_low
        if temp_high is not None:
            self.environment.target_temp_high = temp_high
    else:
        temp = preset_env.get_temperature(self.hass)

        _LOGGER.debug("Re-evaluated template temp: %s", temp)

        if temp is not None:
            self.environment.target_temp = temp

    # Trigger control update with new temperatures
    await self._async_control_climate(force=True)
    self.async_write_ha_state()
```

**Modified Existing Methods**:

```python
async def async_added_to_hass(self) -> None:
    """Run when entity about to be added to hass."""
    # ... existing code ...

    # NEW: Set up template entity listeners if current preset uses templates
    await self._setup_template_listeners()


async def async_set_preset_mode(self, preset_mode: str) -> None:
    """Set new preset mode."""
    # ... existing preset change code ...

    # NEW: Update template listeners for new preset
    # (Different presets may reference different entities)
    await self._setup_template_listeners()


async def async_will_remove_from_hass(self) -> None:
    """Run when entity will be removed from hass."""
    # ... existing cleanup code ...

    # NEW: Remove template listeners to prevent memory leaks
    await self._remove_template_listeners()
```

**Impact**: Climate entity now reactively updates preset temperatures when template entities change.

---

### Data Flow

#### Scenario 1: Static Value (Backward Compatibility)

```
Config Flow:
  User enters: 20
  Schema receives: 20 (as string "20" from TemplateSelector)
  Validation: Passes (not a template)
  Stored in config: 20 (will be converted to float)

PresetEnv.__init__:
  _process_field sees: 20 (numeric after config loading)
  Action: Sets self.temperature = 20.0
  Template tracking: No template registered

PresetManager applies preset:
  Calls: preset_env.get_temperature(hass)
  Returns: 20.0 (static value)
  No template evaluation needed

Climate entity:
  Listener setup: Skipped (no templates)
  Behavior: Same as current implementation
```

#### Scenario 2: Entity Reference Template

```
Config Flow:
  User enters: {{ states('sensor.away_temp') }}
  Schema receives: "{{ states('sensor.away_temp') }}"
  Validation: Template syntax valid, passes
  Stored in config: "{{ states('sensor.away_temp') }}"

PresetEnv.__init__:
  _process_field sees: "{{ states('sensor.away_temp') }}" (string)
  Action: Stores in _template_fields['temperature']
  Extracts entities: {'sensor.away_temp'} stored in _referenced_entities

PresetManager applies preset:
  Calls: preset_env.get_temperature(hass)
  Template evaluated: states('sensor.away_temp') -> 18.0
  Returns: 18.0
  Stored in _last_good_values['temperature'] = 18.0

Climate entity:
  Listener setup: Creates listener for 'sensor.away_temp'

  When sensor.away_temp changes from 18 to 16:
    _async_template_entity_changed fires
    Template re-evaluated: 16.0
    environment.target_temp updated to 16.0
    Control cycle triggered
    Thermostat adjusts to new target
```

#### Scenario 3: Complex Template with Logic

```
Config Flow:
  User enters: {% if is_state('sensor.season', 'winter') %}16{% else %}24{% endif %}
  Validation: Template syntax valid, passes
  Stored in config: "{% if is_state('sensor.season', 'winter') %}16{% else %}24{% endif %}"

PresetEnv.__init__:
  _process_field sees: Template string
  Extracts entities: {'sensor.season'}

PresetManager applies preset:
  Template evaluated:
    sensor.season is 'winter' -> Returns 16.0
  _last_good_values['temperature'] = 16.0

Climate entity:
  Listener setup: Creates listener for 'sensor.season'

  When sensor.season changes from 'winter' to 'summer':
    Template re-evaluated: Returns 24.0
    Temperature updated from 16 to 24
    Control cycle triggered
```

#### Scenario 4: Template Evaluation Error

```
Runtime:
  sensor.away_temp becomes unavailable
  Template evaluation: states('sensor.away_temp') throws error

PresetEnv._evaluate_template:
  Exception caught
  Logs warning: "Template evaluation failed... Keeping previous: 18.0"
  Returns: 18.0 (from _last_good_values)

Result:
  Thermostat continues using last known good value (18.0)
  No crash, no unexpected behavior
  User sees warning in logs for debugging
```

---

## Testing Strategy

### Test Coverage Goals

- **Unit tests**: 100% coverage of new template-related code
- **Integration tests**: All reactive behavior scenarios
- **Config flow tests**: Template input and validation
- **Backward compatibility tests**: Static values still work

### Test Files

#### 1. Core Template Functionality

**File**: `tests/test_preset_templates.py` (NEW)

```python
"""Test preset template functionality."""

import pytest
from homeassistant.components.climate.const import PRESET_AWAY, PRESET_ECO
from homeassistant.const import STATE_UNAVAILABLE

# Test: Backward compatibility
async def test_preset_static_value_backward_compatible(hass):
    """Test that static float values still work."""
    # Setup thermostat with static preset value
    # Verify preset applies correctly
    # Verify no template listeners created

# Test: Basic template evaluation
async def test_preset_template_evaluation(hass):
    """Test template evaluation for preset temperatures."""
    # Setup sensor with value 18
    # Setup thermostat with template: {{ states('sensor.test') }}
    # Activate preset
    # Verify temperature is 18

# Test: Entity reference
async def test_preset_template_entity_reference(hass):
    """Test simple entity reference in preset template."""
    # Test: {{ states('sensor.away_temp') | float }}

# Test: Complex template logic
async def test_preset_template_complex_logic(hass):
    """Test template with conditional logic."""
    # Test: {% if condition %}16{% else %}24{% endif %}

# Test: Error handling - keep previous value
async def test_preset_template_error_keeps_previous(hass):
    """Test that template errors keep previous value."""
    # Setup template with sensor
    # Activate preset (evaluates to 18)
    # Make sensor unavailable
    # Trigger re-evaluation
    # Verify temperature still 18 (kept previous)
    # Verify warning logged

# Test: Error handling - no previous value
async def test_preset_template_error_no_previous_uses_default(hass):
    """Test fallback to default when no previous value exists."""
    # Setup template that fails immediately
    # Verify falls back to 20.0

# Test: Range mode - both temps as templates
async def test_preset_range_mode_with_templates(hass):
    """Test templates for target_temp_low and target_temp_high."""
    # Setup heat_cool mode
    # Configure preset with templates for both low and high
    # Verify both evaluate correctly

# Test: Range mode - mixed static and template
async def test_preset_range_mode_mixed_static_template(hass):
    """Test one static, one template in range mode."""
    # Low: 18 (static)
    # High: {{ states('sensor.max_temp') }} (template)

# Test: Multiple presets with different templates
async def test_multiple_presets_different_templates(hass):
    """Test multiple presets each with different templates."""
    # Away: {{ states('sensor.away_temp') }}
    # Eco: {{ states('sensor.eco_temp') }}
    # Verify switching presets changes tracked entities

# Test: Template with multiple entities
async def test_template_with_multiple_entities(hass):
    """Test template referencing multiple entities."""
    # Template: {{ (states('sensor.indoor') | float +
    #               states('sensor.outdoor') | float) / 2 }}
    # Verify all entities tracked
    # Verify change to any entity triggers update

# Test: Preset switching clears old listeners
async def test_preset_switching_updates_listeners(hass):
    """Test that changing presets properly updates listeners."""
    # Activate preset with template (sensor A)
    # Verify listener created for sensor A
    # Change to preset with different template (sensor B)
    # Verify listener for sensor A removed
    # Verify listener for sensor B created

# Test: Preset to NONE clears listeners
async def test_preset_none_clears_listeners(hass):
    """Test that setting preset to NONE clears all listeners."""
    # Activate preset with templates
    # Verify listeners created
    # Set preset to NONE
    # Verify all listeners removed
```

#### 2. Reactive Behavior Tests

**File**: `tests/test_preset_templates_reactive.py` (NEW)

```python
"""Test reactive template evaluation behavior."""

# Test: Entity change triggers temperature update
async def test_entity_change_triggers_temperature_update(hass):
    """Test that changing template entity updates temperature."""
    # Setup sensor at 18
    # Setup thermostat with template
    # Activate preset
    # Verify temp is 18
    # Change sensor to 20
    # Verify temp updated to 20
    # Verify control cycle triggered

# Test: Entity change triggers control cycle
async def test_entity_change_triggers_control_cycle(hass):
    """Test that temperature update triggers control cycle."""
    # Mock _async_control_climate
    # Change template entity
    # Verify control cycle called with force=True

# Test: Multiple entity changes
async def test_multiple_entity_changes_sequential(hass):
    """Test multiple sequential entity changes."""
    # Template uses sensor A
    # Change A multiple times
    # Verify each change updates temperature

# Test: Entity unavailable then available
async def test_entity_unavailable_then_available(hass):
    """Test handling entity going unavailable then coming back."""
    # Setup template with sensor at 18
    # Make sensor unavailable
    # Verify temp kept at 18 (previous value)
    # Make sensor available again with value 20
    # Verify temp updates to 20

# Test: Rapid entity changes
async def test_rapid_entity_changes(hass):
    """Test system handles rapid entity changes gracefully."""
    # Setup template
    # Trigger many rapid changes
    # Verify system stable
    # Verify final temperature correct

# Test: Listener cleanup on entity removal
async def test_listener_cleanup_on_entity_removal(hass):
    """Test listeners cleaned up when thermostat removed."""
    # Setup thermostat with template
    # Remove thermostat entity
    # Verify listeners cleaned up
    # Verify no memory leaks
```

#### 3. Config Flow Tests

**File**: `tests/config_flow/test_preset_templates_config_flow.py` (NEW)

```python
"""Test preset template configuration flow."""

# Test: Template input accepted
async def test_config_flow_accepts_template_input(hass):
    """Test that template strings are accepted in config flow."""
    # Go through config flow
    # Enter template string for preset temp
    # Verify config entry created successfully

# Test: Static value still works
async def test_config_flow_static_value_backward_compatible(hass):
    """Test static numeric values still work in config flow."""
    # Enter static value "20"
    # Verify accepted and stored correctly

# Test: Template syntax validation
async def test_config_flow_template_syntax_validation(hass):
    """Test that invalid template syntax is rejected."""
    # Enter invalid template: "{{ invalid syntax"
    # Verify validation error shown
    # Verify helpful error message

# Test: Valid template syntax accepted
async def test_config_flow_valid_template_syntax_accepted(hass):
    """Test that valid template syntax passes validation."""
    # Enter valid template
    # Verify no validation errors

# Test: Template persistence through options flow
async def test_options_flow_template_persistence(hass):
    """Test that templates persist through options flow."""
    # Create config with template
    # Open options flow
    # Verify template pre-filled
    # Save without changes
    # Verify template still in config

# Test: Template modification in options flow
async def test_options_flow_modify_template(hass):
    """Test modifying templates in options flow."""
    # Create config with template A
    # Open options flow
    # Change to template B
    # Verify template B saved

# Test: Change from static to template in options
async def test_options_flow_static_to_template(hass):
    """Test changing from static value to template."""
    # Create config with static value
    # Change to template in options flow
    # Verify works correctly

# Test: Change from template to static in options
async def test_options_flow_template_to_static(hass):
    """Test changing from template to static value."""
    # Create config with template
    # Change to static value in options flow
    # Verify listeners cleaned up
    # Verify static value works
```

#### 4. Integration Tests

**Add to**: `tests/config_flow/test_e2e_simple_heater_persistence.py`

```python
async def test_e2e_preset_templates_full_persistence(hass):
    """Test preset templates persist through full config → options cycle."""
    # Config flow with template-based preset
    # Verify entity works
    # Open options flow
    # Verify template still there
    # Modify template
    # Verify new template works
```

**Add to**: `tests/config_flow/test_e2e_heater_cooler_persistence.py`

```python
async def test_e2e_preset_templates_range_mode_persistence(hass):
    """Test template persistence for range mode (low/high temps)."""
    # Config heater_cooler with heat_cool mode
    # Configure preset with templates for low and high
    # Full persistence test cycle
```

### Test Execution Plan

1. **Phase 1**: Unit tests for PresetEnv template functionality
2. **Phase 2**: Unit tests for PresetManager integration
3. **Phase 3**: Reactive behavior integration tests
4. **Phase 4**: Config flow tests
5. **Phase 5**: End-to-end persistence tests
6. **Phase 6**: Performance and memory leak tests

### Success Criteria

- ✅ All tests pass
- ✅ 100% code coverage on new template-related code
- ✅ No memory leaks (verify listener cleanup)
- ✅ Backward compatibility verified (existing configs work)
- ✅ Performance acceptable (no noticeable lag)

---

## Documentation Plan

### 1. Translation Updates

**File**: `custom_components/dual_smart_thermostat/translations/en.json`

**Changes**:
```json
{
  "config": {
    "step": {
      "presets": {
        "title": "Configure Presets",
        "description": "Set temperature values for each preset. You can use:\n• Static values (e.g., 20)\n• Entity references (e.g., {{ states('sensor.away_temp') }})\n• Templates with logic (e.g., {{ 16 if is_state('binary_sensor.winter', 'on') else 24 }})",
        "data": {
          "away_temp": "Away temperature (static, entity, or template)",
          "away_temp_low": "Away low temperature (static, entity, or template)",
          "away_temp_high": "Away high temperature (static, entity, or template)",
          "eco_temp": "Eco temperature (static, entity, or template)",
          "eco_temp_low": "Eco low temperature (static, entity, or template)",
          "eco_temp_high": "Eco high temperature (static, entity, or template)",
          "comfort_temp": "Comfort temperature (static, entity, or template)",
          "comfort_temp_low": "Comfort low temperature (static, entity, or template)",
          "comfort_temp_high": "Comfort high temperature (static, entity, or template)",
          "home_temp": "Home temperature (static, entity, or template)",
          "sleep_temp": "Sleep temperature (static, entity, or template)",
          "activity_temp": "Activity temperature (static, entity, or template)",
          "boost_temp": "Boost temperature (static, entity, or template)",
          "anti_freeze_temp": "Anti-freeze temperature (static, entity, or template)"
        }
      }
    }
  },
  "options": {
    "step": {
      "presets": {
        "title": "Configure Presets",
        "description": "Set temperature values for each preset. You can use:\n• Static values (e.g., 20)\n• Entity references (e.g., {{ states('sensor.away_temp') }})\n• Templates with logic (e.g., {{ 16 if is_state('binary_sensor.winter', 'on') else 24 }})\n\n⚠️ Templates are evaluated dynamically and will update when referenced entities change.",
        "data": {
          "away_temp": "Away temperature (static, entity, or template)",
          "eco_temp": "Eco temperature (static, entity, or template)",
          "comfort_temp": "Comfort temperature (static, entity, or template)"
        }
      }
    }
  }
}
```

### 2. Example Configurations

**File**: `examples/advanced_features/presets_with_templates.yaml` (NEW)

```yaml
# ============================================================================
# Preset Temperatures with Templates
# ============================================================================
#
# This example shows how to use Home Assistant templates for preset
# temperatures, allowing them to dynamically adjust based on sensors,
# conditions, time, or any other Home Assistant state.
#
# Documentation: https://github.com/swingerman/ha-dual-smart-thermostat
# ============================================================================

# ============================================================================
# Example 1: Seasonal Away Temperature
# ============================================================================
# Use case: Different away temperatures for winter (heat conservation)
# and summer (cooling conservation)

climate:
  - platform: dual_smart_thermostat
    name: Seasonal Smart Thermostat
    unique_id: seasonal_thermostat
    heater: switch.living_room_heater
    cooler: switch.living_room_ac
    target_sensor: sensor.living_room_temperature

    # Away preset adjusts based on season
    # Winter: 16°C (save heating when away)
    # Summer: 26°C (save cooling when away)
    # Spring/Fall: 20°C (moderate)
    away_temp: >
      {% if is_state('sensor.season', 'winter') %}
        16
      {% elif is_state('sensor.season', 'summer') %}
        26
      {% else %}
        20
      {% endif %}

# ============================================================================
# Example 2: Outdoor Temperature Based Presets
# ============================================================================
# Use case: Adjust eco preset based on outdoor temperature

climate:
  - platform: dual_smart_thermostat
    name: Weather Responsive Thermostat
    unique_id: weather_thermostat
    heater: switch.heater
    target_sensor: sensor.indoor_temp

    # Eco preset uses outdoor temp with offset
    # When outdoor is 5°C, eco is 18°C (5 + 13)
    # When outdoor is 15°C, eco is 28°C (15 + 13)
    eco_temp: >
      {{ (states('sensor.outdoor_temperature') | float + 13) | round(1) }}

# ============================================================================
# Example 3: Simple Entity Reference
# ============================================================================
# Use case: Temperature controlled by a separate sensor/input_number

climate:
  - platform: dual_smart_thermostat
    name: Sensor Controlled Thermostat
    unique_id: sensor_controlled
    heater: switch.heater
    target_sensor: sensor.room_temp

    # Away temperature directly from sensor
    away_temp: "{{ states('sensor.my_away_temperature') | float }}"

    # Or from an input_number helper
    eco_temp: "{{ states('input_number.eco_temperature') | float }}"

# ============================================================================
# Example 4: Heat/Cool Mode with Template Ranges
# ============================================================================
# Use case: Dynamic temperature ranges based on outdoor conditions

climate:
  - platform: dual_smart_thermostat
    name: Range Mode Thermostat
    unique_id: range_thermostat
    heater: switch.heater
    cooler: switch.ac
    target_sensor: sensor.room_temp
    heat_cool_mode: true

    # Eco preset with outdoor-based range
    # Outdoor 10°C -> Range: 18-24°C
    # Outdoor 20°C -> Range: 20-26°C
    eco_temp_low: >
      {{ (states('sensor.outdoor_temp') | float - 2) | round(1) }}

    eco_temp_high: >
      {{ (states('sensor.outdoor_temp') | float + 4) | round(1) }}

# ============================================================================
# Example 5: Time-Based Preset
# ============================================================================
# Use case: Different away temperatures for day vs night

climate:
  - platform: dual_smart_thermostat
    name: Time Aware Thermostat
    unique_id: time_aware
    heater: switch.heater
    target_sensor: sensor.temp

    # Away temp depends on time of day
    # Night (10pm-6am): 15°C (deeper conservation)
    # Day: 18°C (moderate conservation)
    away_temp: >
      {% set hour = now().hour %}
      {% if hour >= 22 or hour < 6 %}
        15
      {% else %}
        18
      {% endif %}

# ============================================================================
# Example 6: Complex Multi-Condition Template
# ============================================================================
# Use case: Combine multiple factors

climate:
  - platform: dual_smart_thermostat
    name: Smart Complex Thermostat
    unique_id: complex_thermostat
    heater: switch.heater
    cooler: switch.ac
    target_sensor: sensor.temp

    # Away temp based on multiple conditions:
    # - Season
    # - Time of day
    # - Outdoor temperature
    away_temp: >
      {% set outdoor = states('sensor.outdoor_temp') | float %}
      {% set hour = now().hour %}
      {% set season = states('sensor.season') %}

      {% if season == 'winter' %}
        {% if hour >= 22 or hour < 6 %}
          14
        {% else %}
          16
        {% endif %}
      {% elif season == 'summer' %}
        {% if outdoor > 30 %}
          28
        {% else %}
          26
        {% endif %}
      {% else %}
        20
      {% endif %}

# ============================================================================
# How It Works
# ============================================================================
#
# 1. Templates are evaluated when:
#    - Preset is first activated
#    - Any entity referenced in the template changes state
#
# 2. Example: away_temp uses {{ states('sensor.outdoor_temp') }}
#    - When you activate Away preset, temperature is set from sensor
#    - When sensor.outdoor_temp changes, Away temperature automatically updates
#    - Thermostat adjusts to new target immediately
#
# 3. Error handling:
#    - If template fails (sensor unavailable, syntax error), the previous
#      temperature value is kept
#    - No crashes or unexpected behavior
#    - Errors logged for debugging
#
# 4. Backward compatibility:
#    - Static values still work: away_temp: 18
#    - You can mix static and templates in same configuration
#
# ============================================================================
# Tips & Best Practices
# ============================================================================
#
# 1. Test templates in Developer Tools → Template before using
# 2. Always include | float filter when using numeric sensors
# 3. Use | round(1) to limit decimal places
# 4. Provide fallback values for edge cases
# 5. Keep templates simple for easier debugging
# 6. Consider using input_number helpers for user-adjustable values
#
# ============================================================================
```

### 3. README Updates

**File**: `README.md`

**Add new section**:

```markdown
### Template-Based Preset Temperatures

Preset temperatures can be dynamically set using Home Assistant templates, allowing them to adjust based on sensors, conditions, time, or any other state.

#### Static Values (Traditional)
```yaml
away_temp: 16  # Fixed temperature
```

#### Entity References
```yaml
away_temp: "{{ states('sensor.away_temperature') | float }}"
```

#### Conditional Logic
```yaml
away_temp: >
  {% if is_state('sensor.season', 'winter') %}
    16
  {% else %}
    24
  {% endif %}
```

#### Reactive Behavior

Templates automatically re-evaluate when referenced entities change:
- When `sensor.season` changes from 'winter' to 'summer'
- The away_temp automatically updates from 16 to 24
- The thermostat adjusts to the new target immediately

See [examples/advanced_features/presets_with_templates.yaml](examples/advanced_features/presets_with_templates.yaml) for more examples.
```

### 4. Troubleshooting Documentation

**File**: `docs/troubleshooting.md`

**Add section**:

```markdown
## Template-Based Presets Issues

### Templates Not Updating

**Symptom**: Preset temperature doesn't change when sensor changes

**Causes & Solutions**:
1. **Template syntax error**
   - Check logs for template evaluation warnings
   - Test template in Developer Tools → Template

2. **Entity not properly referenced**
   - Use full entity ID: `sensor.my_temp` not `my_temp`
   - Verify entity exists and is available

3. **Template listener not set up**
   - Check logs for "Setting up template listeners" message
   - Restart Home Assistant if listeners not working

### Template Evaluation Errors

**Symptom**: Warning in logs: "Template evaluation failed"

**Solutions**:
1. **Sensor unavailable**
   - System keeps previous value (safe)
   - Check sensor availability

2. **Invalid template syntax**
   - Fix syntax in options flow
   - Use template editor to test

3. **Type conversion error**
   - Always use `| float` filter for numeric sensors
   - Example: `{{ states('sensor.temp') | float }}`

### Debug Template Issues

1. Enable debug logging:
```yaml
logger:
  default: warning
  logs:
    custom_components.dual_smart_thermostat.preset_env: debug
    custom_components.dual_smart_thermostat.managers.preset_manager: debug
```

2. Check logs for:
   - "Template evaluation success" - Shows evaluated values
   - "Template evaluation failed" - Shows errors
   - "Setting up template listeners" - Shows which entities are tracked
```

---

## Implementation Checklist

### Phase 1: Core Template Support
- [ ] Update `schemas.py` - Add TemplateSelector and validation
- [ ] Enhance `PresetEnv` class with template processing
- [ ] Add template evaluation methods to `PresetEnv`
- [ ] Add entity extraction to `PresetEnv`
- [ ] Update `PresetManager` to call evaluation methods
- [ ] Write unit tests for `PresetEnv` template functionality
- [ ] Write unit tests for `PresetManager` integration

### Phase 2: Reactive Evaluation
- [ ] Add listener tracking attributes to `DualSmartThermostat`
- [ ] Implement `_setup_template_listeners()` method
- [ ] Implement `_remove_template_listeners()` method
- [ ] Implement `_async_template_entity_changed()` callback
- [ ] Update `async_added_to_hass()` to set up listeners
- [ ] Update `async_set_preset_mode()` to update listeners
- [ ] Update `async_will_remove_from_hass()` to clean up listeners
- [ ] Write integration tests for reactive behavior
- [ ] Test listener cleanup and memory management

### Phase 3: Config Flow Integration
- [ ] Add `validate_template_syntax()` function
- [ ] Apply validation to preset temperature fields
- [ ] Test config flow with template input
- [ ] Test config flow with static input (backward compat)
- [ ] Test config flow validation errors
- [ ] Write config flow tests

### Phase 4: Documentation
- [ ] Update `translations/en.json` with template hints
- [ ] Create `examples/advanced_features/presets_with_templates.yaml`
- [ ] Add seasonal temperature example
- [ ] Add outdoor-based temperature example
- [ ] Update README with template section
- [ ] Add troubleshooting docs for templates
- [ ] Review all documentation for clarity

### Phase 5: Testing
- [ ] Write all unit tests from testing strategy
- [ ] Write all integration tests
- [ ] Write config flow tests
- [ ] Write E2E persistence tests
- [ ] Verify 100% code coverage
- [ ] Test backward compatibility thoroughly
- [ ] Performance testing (template evaluation speed)
- [ ] Memory leak testing (listener cleanup)

### Phase 6: Code Quality
- [ ] Run `isort .` - Sort imports
- [ ] Run `black .` - Format code
- [ ] Run `flake8 .` - Check style
- [ ] Run `codespell` - Check spelling
- [ ] Run `pytest` - All tests pass
- [ ] Code review - Check against CLAUDE.md guidelines

### Phase 7: Final Verification
- [ ] Manual testing - Config flow with templates
- [ ] Manual testing - Template reactivity
- [ ] Manual testing - Error handling
- [ ] Manual testing - Backward compatibility
- [ ] Update CHANGELOG
- [ ] Create PR with clear description
- [ ] Link PR to issue #96

---

## Success Metrics

### Functionality
- ✅ Templates work for single temperature mode
- ✅ Templates work for range mode (low/high)
- ✅ Templates reactively update on entity changes
- ✅ Static values work (backward compatible)
- ✅ Error handling prevents crashes
- ✅ Config flow validates template syntax

### Quality
- ✅ 100% test coverage on new code
- ✅ All linting checks pass
- ✅ No memory leaks
- ✅ Performance acceptable (<100ms template evaluation)
- ✅ Documentation complete and clear

### User Experience
- ✅ Config flow provides clear guidance
- ✅ Examples cover common use cases
- ✅ Errors provide helpful messages
- ✅ Feature easy to discover and use

---

## Future Enhancements (Out of Scope)

These features are not part of the current implementation but could be added later:

1. **Template support for humidity** (Issue #96 Phase 2)
   - `target_humidity` field
   - Same template + reactivity approach

2. **Template support for floor temperature limits** (Issue #96 Phase 2)
   - `min_floor_temp` and `max_floor_temp` fields
   - Useful for seasonal floor temp limits

3. **Template testing UI in config flow**
   - Button to test template evaluation
   - Shows preview of evaluated value
   - Helps users verify templates before saving

4. **Template performance metrics**
   - Track evaluation time
   - Warn if templates are slow
   - Help debug performance issues

5. **Template suggestions in UI**
   - Common template patterns
   - Auto-complete for entity IDs
   - Syntax help

6. **HVAC mode in presets** (Related Issue #78)
   - Allow presets to change HVAC mode
   - E.g., "Away" preset sets mode to "off"
   - Separate feature, more complex

---

## Notes

- This spec is based on extensive analysis and user feedback
- All design decisions have been validated and approved
- Implementation should follow this spec closely
- Updates to spec should be documented with rationale
- Upon completion, mark status as ✅ **Implemented**
