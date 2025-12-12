# PresetEnv API Contract

**Module**: `custom_components.dual_smart_thermostat.preset_env.preset_env`
**Class**: `PresetEnv`
**Purpose**: Enhanced preset environment supporting both static and template-based temperatures

## Public API

### Constructor

```python
def __init__(self, **kwargs) -> None:
    """Initialize PresetEnv with temperature values (static or templates).

    Args:
        **kwargs: Keyword arguments including:
            - temperature (float | str | None): Single temp mode target
            - target_temp_low (float | str | None): Range mode low threshold
            - target_temp_high (float | str | None): Range mode high threshold
            - [other existing preset attributes]

    Behavior:
        - Numeric values stored directly as floats (existing behavior)
        - String values treated as templates, parsed and entities extracted
        - Sets up internal tracking for template fields and last good values
    """
```

**Changes from Existing**:
- Now accepts string values for temperature fields (previously float only)
- Adds internal template tracking structures
- Extracts entity references from template strings

---

### Temperature Getters (Modified)

```python
def get_temperature(self, hass: HomeAssistant) -> float | None:
    """Get temperature, evaluating template if needed.

    Args:
        hass: Home Assistant instance for template evaluation context

    Returns:
        float: Evaluated temperature value
        None: If field not configured

    Behavior:
        - Static value: Returns stored float directly
        - Template: Evaluates template, updates last_good_value, returns result
        - Evaluation error: Logs warning, returns last_good_value (or 20.0 default)

    Thread Safety: Safe - uses async_render from HA template engine
    """

def get_target_temp_low(self, hass: HomeAssistant) -> float | None:
    """Get target_temp_low, evaluating template if needed.

    Same contract as get_temperature() but for range mode low threshold.
    """

def get_target_temp_high(self, hass: HomeAssistant) -> float | None:
    """Get target_temp_high, evaluating template if needed.

    Same contract as get_temperature() but for range mode high threshold.
    """
```

**Breaking Changes**: None
- Existing callers passing static values: Unchanged behavior
- New callers can pass templates: Transparent evaluation
- Signature changed: Added `hass` parameter (required for template evaluation)
  - **Migration**: All calls to `get_temperature()` must pass `hass` instance

---

### Template Introspection (New)

```python
@property
def referenced_entities(self) -> set[str]:
    """Return set of entities referenced in templates.

    Returns:
        set[str]: Entity IDs (e.g., {'sensor.away_temp', 'input_number.eco'})
                 Empty set if no templates configured

    Usage: Climate entity uses this to set up state change listeners
    """

def has_templates(self) -> bool:
    """Check if this preset uses any templates.

    Returns:
        bool: True if any temperature field is template-based, False otherwise

    Usage: Climate entity checks this before setting up listeners
    """
```

---

## Internal API (For Implementation)

### Template Processing

```python
def _process_field(self, field_name: str, value: Any) -> None:
    """Process temperature field to determine if static or template.

    Args:
        field_name: Field identifier ('temperature', 'target_temp_low', etc.)
        value: Field value (float, int, string, or None)

    Behavior:
        - None: Ignored
        - Numeric (int/float): Stored as float, added to last_good_values
        - String: Treated as template, stored in _template_fields, entities extracted

    Side Effects:
        - Updates instance attributes (self.temperature, etc.)
        - Updates self._template_fields
        - Updates self._last_good_values
        - Updates self._referenced_entities (via _extract_entities)
    """
```

### Entity Extraction

```python
def _extract_entities(self, template_str: str) -> None:
    """Extract entity IDs from template string.

    Args:
        template_str: Jinja2 template string

    Behavior:
        - Parses template using Home Assistant Template class
        - Calls Template.extract_entities() to get referenced entities
        - Adds entities to self._referenced_entities set

    Error Handling:
        - Extraction errors logged as debug (non-critical)
        - Empty set if extraction fails
    """
```

### Template Evaluation

```python
def _evaluate_template(self, hass: HomeAssistant, field_name: str) -> float:
    """Safely evaluate template with fallback to previous value.

    Args:
        hass: Home Assistant instance for evaluation context
        field_name: Field identifier to evaluate

    Returns:
        float: Successfully evaluated temperature
               OR last_good_value if evaluation fails
               OR 20.0 if no previous value exists

    Behavior:
        1. Retrieve template string from _template_fields
        2. Create Template instance with hass context
        3. Call async_render() to evaluate
        4. Convert result to float
        5. Update _last_good_values with result
        6. Return result

    Error Handling:
        - Template errors: Log warning with template + entities + error
        - Conversion errors: Log warning, use fallback
        - Missing template: Return last_good_value or default

    Logging:
        Success: DEBUG level with template and result
        Failure: WARNING level with template, entities, error, fallback
    """
```

---

## Usage Examples

### Static Value (Existing Behavior)

```python
# Configuration
preset_env = PresetEnv(temperature=20.0)

# Retrieval
temp = preset_env.get_temperature(hass)  # Returns: 20.0
assert temp == 20.0
assert not preset_env.has_templates()
assert len(preset_env.referenced_entities) == 0
```

### Simple Entity Reference Template

```python
# Configuration
preset_env = PresetEnv(
    temperature="{{ states('sensor.away_temp') | float }}"
)

# Template detection
assert preset_env.has_templates()
assert "sensor.away_temp" in preset_env.referenced_entities

# Evaluation (assuming sensor.away_temp is 18)
temp = preset_env.get_temperature(hass)  # Returns: 18.0
assert temp == 18.0

# Re-evaluation after sensor change (sensor.away_temp now 20)
temp = preset_env.get_temperature(hass)  # Returns: 20.0
assert temp == 20.0
```

### Conditional Template

```python
# Configuration
preset_env = PresetEnv(
    temperature="{{ 16 if is_state('sensor.season', 'winter') else 26 }}"
)

# Template detection
assert preset_env.has_templates()
assert "sensor.season" in preset_env.referenced_entities

# Evaluation (assuming sensor.season is 'winter')
temp = preset_env.get_temperature(hass)  # Returns: 16.0

# Re-evaluation (sensor.season changed to 'summer')
temp = preset_env.get_temperature(hass)  # Returns: 26.0
```

### Range Mode with Mixed Values

```python
# Configuration (low is static, high is template)
preset_env = PresetEnv(
    target_temp_low=18.0,
    target_temp_high="{{ states('sensor.outdoor_temp') | float + 4 }}"
)

# Template detection
assert preset_env.has_templates()  # True (high is template)
assert "sensor.outdoor_temp" in preset_env.referenced_entities

# Evaluation
temp_low = preset_env.get_target_temp_low(hass)   # Returns: 18.0 (static)
temp_high = preset_env.get_target_temp_high(hass) # Returns: 24.0 (outdoor=20, +4)
```

### Error Handling

```python
# Configuration with template referencing unavailable entity
preset_env = PresetEnv(
    temperature="{{ states('sensor.nonexistent') | float }}"
)

# First evaluation (no previous value, entity unavailable)
temp = preset_env.get_temperature(hass)  # Returns: 20.0 (default)
# Warning logged: "Template evaluation failed... Keeping previous: 20.0"

# Successful evaluation (entity becomes available with value 18)
temp = preset_env.get_temperature(hass)  # Returns: 18.0
# Now last_good_value is 18.0

# Entity becomes unavailable again
temp = preset_env.get_temperature(hass)  # Returns: 18.0 (last good value)
# Warning logged: "Template evaluation failed... Keeping previous: 18.0"
```

---

## Error Conditions

### Configuration Errors (Constructor)

| Error | Cause | Behavior |
|-------|-------|----------|
| Invalid template syntax | String value with malformed Jinja2 | ValueError raised during entity extraction (caught, logged as debug) |
| None values | All temperature fields None | Valid - preset has no temperature override |

### Evaluation Errors (Getters)

| Error | Cause | Behavior |
|-------|-------|----------|
| Template rendering fails | Entity unavailable, syntax runtime error | Log warning, return last_good_value or 20.0 |
| Result not numeric | Template returns string like "unknown" | Log warning, return last_good_value or 20.0 |
| Template timeout | Evaluation takes >1 second | Home Assistant Template handles timeout, treated as evaluation failure |

---

## Performance Characteristics

- **Static value retrieval**: O(1) - Direct attribute access
- **Template evaluation**: O(n) where n = entities referenced + template complexity
  - Typical: <10ms for simple templates
  - Complex: <100ms for multi-entity conditional templates
  - Target: <1 second (enforced by HA Template engine)
- **Entity extraction**: O(m) where m = template length, performed once at construction

---

## Backward Compatibility

**100% backward compatible with existing PresetEnv usage**:
- Static float values work unchanged
- Existing code passing numeric values sees no behavior change
- Only breaking change: `get_temperature()` now requires `hass` parameter
  - **Migration path**: Update all callers to pass `hass` instance
  - All callers within this component: PresetManager (has hass access)

---

## Thread Safety

- **Safe**: Template evaluation uses Home Assistant's async_render (thread-safe)
- **Safe**: Entity extraction at construction (single-threaded)
- **Safe**: Attribute access (_last_good_values dict updates are atomic in Python)

---

## Testing Contracts

### Unit Tests Required

```python
# Static value behavior (backward compatibility)
def test_static_value_backward_compatible()

# Template detection
def test_template_detection_string_vs_numeric()

# Entity extraction
def test_entity_extraction_simple()
def test_entity_extraction_multiple_entities()
def test_entity_extraction_complex_template()

# Template evaluation
def test_template_evaluation_success()
def test_template_evaluation_entity_unavailable()
def test_template_evaluation_non_numeric_result()
def test_template_evaluation_fallback_to_previous()
def test_template_evaluation_fallback_to_default()

# Properties
def test_has_templates_true_when_template()
def test_has_templates_false_when_static()
def test_referenced_entities_empty_when_static()
def test_referenced_entities_populated_when_template()
```

### Integration Tests Required

```python
# With PresetManager
def test_preset_manager_applies_template_value()
def test_preset_manager_applies_static_value()
def test_preset_manager_handles_evaluation_error()
```

---

## Migration Guide

### For PresetManager (Internal)

**Before**:
```python
# Old code (no hass parameter)
temp = self._preset_env.temperature
```

**After**:
```python
# New code (use getter with hass)
temp = self._preset_env.get_temperature(self.hass)
```

**Why**: Templates require Home Assistant context for evaluation. Static values still work, but now retrieved via getter to maintain consistent interface.

---

## Dependencies

### External Dependencies

- `homeassistant.helpers.template.Template` - Template parsing and rendering
- `homeassistant.core.HomeAssistant` - Required for template evaluation context

### Internal Dependencies

- None (PresetEnv is a data class with minimal dependencies)

---

## Version History

- **v1.0** (Current): Static temperature values only
- **v2.0** (This Feature): Added template support, backward compatible
  - New: `get_temperature(hass)`, `get_target_temp_low(hass)`, `get_target_temp_high(hass)`
  - New: `referenced_entities` property
  - New: `has_templates()` method
  - Internal: `_template_fields`, `_last_good_values`, `_referenced_entities`
