# Implementation Plan: Template-Based Preset Temperatures

**Branch**: `004-template-based-presets` | **Date**: 2025-12-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-template-based-presets/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Add Home Assistant template support for preset temperatures (away_temp, eco_temp, etc.), enabling dynamic temperature values that react to sensor/condition changes. Templates will automatically re-evaluate when referenced entities change state. The system maintains backward compatibility with static numeric values and supports both single temperature mode and range mode (target_temp_low/high). Configuration includes inline help with 2-3 common template patterns, syntax-only validation at config time, and comprehensive logging for troubleshooting.

## Technical Context

**Language/Version**: Python 3.13
**Primary Dependencies**: Home Assistant 2025.1.0+, Home Assistant Template Engine (homeassistant.helpers.template), voluptuous (schema validation)
**Storage**: Home Assistant config entries (persistent JSON storage)
**Testing**: pytest, pytest-homeassistant-custom-component
**Target Platform**: Home Assistant integration running on Linux/Docker/Home Assistant OS
**Project Type**: Home Assistant custom component (single project structure)
**Performance Goals**: Template evaluation <1 second, temperature update <5 seconds after entity change
**Constraints**: Backward compatibility with existing static preset configurations, no memory leaks from template listeners, graceful degradation on template errors
**Scale/Scope**: ~5 new/modified Python modules (PresetEnv, PresetManager, Climate entity, schemas, config flow), ~500-800 LOC, comprehensive test coverage

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Project Constitution Status**: Template constitution file present - using project-specific constraints from CLAUDE.md

### Critical Project Principles (from CLAUDE.md)

✅ **Modular Design Pattern**: Template support fits existing Manager Layer pattern (PresetManager + PresetEnv)
✅ **Backward Compatibility**: FR-001 explicitly requires existing static configurations continue working
✅ **Linting Requirements**: All code must pass isort, black, flake8, codespell before commit
✅ **Test-First**: Comprehensive test coverage required across unit, integration, and config flow tests
✅ **Configuration Flow Integration**: CRITICAL - All configuration changes must integrate into config/options flows (see CLAUDE.md Configuration Flow Integration section)

### Gates

- [ ] **Gate 1**: Configuration flow step ordering follows dependencies (system → features → openings → presets)
- [ ] **Gate 2**: All configuration parameters tracked in dependency files (focused_config_dependencies.json)
- [ ] **Gate 3**: Translation updates include inline help text for templates
- [ ] **Gate 4**: Test consolidation follows existing patterns (no standalone bug fix test files)
- [ ] **Gate 5**: Memory leak prevention verified (listener cleanup on preset change/entity removal)

**Status**: All gates addressable through existing architecture patterns. No violations requiring justification.

## Project Structure

### Documentation (this feature)

```text
specs/004-template-based-presets/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
├── checklists/          # Quality validation checklists
│   └── requirements.md  # Spec quality checklist (completed)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
custom_components/dual_smart_thermostat/
├── climate.py                    # Main climate entity - ADD template listener setup/cleanup
├── schemas.py                    # Configuration schemas - MODIFY preset schema for TemplateSelector
├── preset_env/
│   └── preset_env.py            # Preset environment - ADD template processing & evaluation
├── managers/
│   └── preset_manager.py        # Preset manager - MODIFY to call template evaluation
├── translations/
│   └── en.json                  # UI strings - ADD inline help text for templates
└── const.py                      # Constants - may need template-related constants

tests/
├── preset_env/
│   └── test_preset_env_templates.py      # NEW - Template processing unit tests
├── managers/
│   └── test_preset_manager_templates.py  # NEW - PresetManager template integration tests
├── test_preset_templates_reactive.py      # NEW - Reactive behavior integration tests
├── config_flow/
│   ├── test_preset_templates_config_flow.py  # NEW - Config flow template validation tests
│   ├── test_e2e_simple_heater_persistence.py # MODIFY - Add template persistence tests
│   ├── test_e2e_heater_cooler_persistence.py # MODIFY - Add template persistence tests
│   └── test_options_flow.py                   # MODIFY - Add template options flow tests
└── conftest.py                    # Shared fixtures - may need template test helpers

examples/
└── advanced_features/
    └── presets_with_templates.yaml  # NEW - Example configurations with templates

docs/
├── troubleshooting.md            # MODIFY - Add template troubleshooting section
└── config/
    └── CRITICAL_CONFIG_DEPENDENCIES.md  # MODIFY - Document template dependencies

tools/
├── focused_config_dependencies.json  # MODIFY - Add template config dependencies
└── config_validator.py               # MODIFY - Add template validation rules
```

**Structure Decision**: Home Assistant custom component follows single project structure. Core changes concentrated in PresetEnv (template processing), PresetManager (evaluation integration), Climate entity (reactive listeners), and schemas (config UI). Testing follows existing consolidation patterns with new test files integrated into appropriate directories.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. All requirements fit within existing architectural patterns:
- Template processing: New capability in existing PresetEnv class
- Reactive updates: Standard Home Assistant event listener pattern (already used for sensors)
- Config flow: Standard TemplateSelector (Home Assistant built-in)
- Testing: Follows existing consolidation patterns

## Phase 0: Research & Design Decisions

### Research Tasks

1. **Home Assistant Template Engine Integration**
   - API: `homeassistant.helpers.template.Template`
   - Entity extraction: `Template.extract_entities()`
   - Async rendering: `template.async_render()`
   - Error handling patterns in HA core

2. **Template Listener Patterns in Home Assistant**
   - Best practice: `async_track_state_change_event`
   - Cleanup: Store removal callbacks for lifecycle management
   - Avoid memory leaks: Remove listeners on preset change/entity removal

3. **TemplateSelector Configuration**
   - Usage: `selector.TemplateSelector(selector.TemplateSelectorConfig())`
   - Validation: Template syntax parsing without evaluation
   - UI: Provides template editor with syntax highlighting

4. **Test Patterns for Async Home Assistant Components**
   - Fixtures: Use `hass` fixture from pytest-homeassistant-custom-component
   - Entity state manipulation: `hass.states.async_set()`
   - Event triggering: Manual state change events for reactive testing

### Design Decisions (from research.md)

**Decision 1: Template Storage Format**
- **Chosen**: Store templates as strings in config entry; auto-detect type (float vs string)
- **Rationale**: Backward compatible (existing floats unchanged), no migration needed, clean config
- **Alternatives**: Explicit type flag (rejected - unnecessary complexity)

**Decision 2: Reactive Evaluation Trigger**
- **Chosen**: Set up entity listeners for all referenced entities when preset active
- **Rationale**: Truly dynamic presets matching user expectations, standard HA pattern
- **Alternatives**: Evaluate only on preset activation (rejected - not truly dynamic)

**Decision 3: Error Handling Strategy**
- **Chosen**: Keep last known good value on evaluation error, log warning with details
- **Rationale**: Safest approach, prevents unexpected temperature changes, maintains service
- **Alternatives**: Use default value (rejected - abrupt changes), prevent activation (rejected - too disruptive)

**Decision 4: Validation Scope**
- **Chosen**: Syntax-only validation at config time (clarification Q3)
- **Rationale**: Prevents brittle UX (entities can be created later), runtime handles missing entities
- **Alternatives**: Validate entity existence (rejected - blocks legitimate workflows)

**Decision 5: Guidance Format**
- **Chosen**: Inline help text with 2-3 common patterns below input field (clarification Q1)
- **Rationale**: Immediate context without navigation, matches HA UX patterns
- **Alternatives**: Link to docs (rejected - extra clicks), wizard (rejected - over-engineered)

**Decision 6: Logging Detail**
- **Chosen**: Log template string, entity IDs, error message, fallback value (clarification Q2)
- **Rationale**: Complete diagnostic context for troubleshooting without excessive verbosity
- **Alternatives**: Minimal logging (rejected - insufficient for debugging), full state dump (rejected - too noisy)

## Phase 1: Data Model & Contracts

### Data Model

See [data-model.md](data-model.md) for complete entity definitions and relationships.

**Key Entities:**

1. **PresetConfiguration** (existing, enhanced)
   - `preset_name`: string (away, eco, comfort, home, sleep, activity, boost, anti_freeze)
   - `temperature`: float | string (template) - single temp mode
   - `target_temp_low`: float | string (template) - range mode low
   - `target_temp_high`: float | string (template) - range mode high
   - `_template_fields`: dict[str, str] - internal tracking of which fields are templates
   - `_last_good_values`: dict[str, float] - fallback values on error
   - `_referenced_entities`: set[str] - entities used in templates

2. **TemplateEvaluationContext** (new internal)
   - `template_string`: string - original template
   - `result`: float - evaluated temperature
   - `success`: bool - evaluation succeeded
   - `error`: string | None - error message if failed
   - `timestamp`: datetime - when evaluated
   - `entity_states`: dict[str, any] - entity states at evaluation time (for logging)

3. **TemplateListener** (new internal)
   - `entity_id`: string - entity being monitored
   - `preset_name`: string - preset this listener belongs to
   - `remove_callback`: Callable - function to remove listener
   - `active`: bool - whether listener is currently active

### API Contracts

See [contracts/](contracts/) for OpenAPI specifications.

**Internal API Changes** (Python module interfaces):

#### PresetEnv Enhancements

```python
# preset_env/preset_env.py

class PresetEnv:
    def __init__(self, **kwargs):
        """Enhanced to process temperature fields for templates."""
        # Existing attributes...

        # NEW: Template tracking
        self._template_fields: dict[str, str] = {}       # field_name -> template_string
        self._last_good_values: dict[str, float] = {}    # field_name -> last_value
        self._referenced_entities: set[str] = set()      # entity_ids in templates

        # Process temperature fields (auto-detect static vs template)
        self._process_field('temperature', kwargs.get(ATTR_TEMPERATURE))
        self._process_field('target_temp_low', kwargs.get(ATTR_TARGET_TEMP_LOW))
        self._process_field('target_temp_high', kwargs.get(ATTR_TARGET_TEMP_HIGH))

    def _process_field(self, field_name: str, value: Any) -> None:
        """Determine if field is static or template and track accordingly."""
        # Implementation in Phase 2

    def _extract_entities(self, template_str: str) -> None:
        """Extract entity IDs from template string."""
        # Implementation in Phase 2

    def get_temperature(self, hass: HomeAssistant) -> float | None:
        """Get temperature, evaluating template if needed."""
        # Implementation in Phase 2

    def get_target_temp_low(self, hass: HomeAssistant) -> float | None:
        """Get target_temp_low, evaluating template if needed."""
        # Implementation in Phase 2

    def get_target_temp_high(self, hass: HomeAssistant) -> float | None:
        """Get target_temp_high, evaluating template if needed."""
        # Implementation in Phase 2

    def _evaluate_template(self, hass: HomeAssistant, field_name: str) -> float:
        """Safely evaluate template with fallback to previous value."""
        # Implementation in Phase 2

    @property
    def referenced_entities(self) -> set[str]:
        """Return set of entities referenced in templates."""
        # Implementation in Phase 2

    def has_templates(self) -> bool:
        """Check if this preset uses any templates."""
        # Implementation in Phase 2
```

#### PresetManager Enhancements

```python
# managers/preset_manager.py

class PresetManager:
    def _set_presets_when_have_preset_mode(self, preset_mode: str):
        """Enhanced to evaluate templates when applying presets."""
        # Existing logic...

        # MODIFIED: Evaluate templates to get actual values
        if self._features.is_range_mode:
            temp_low = self._preset_env.get_target_temp_low(self.hass)  # NEW: Template-aware
            temp_high = self._preset_env.get_target_temp_high(self.hass)  # NEW: Template-aware

            if temp_low is not None:
                self._environment.target_temp_low = temp_low
            if temp_high is not None:
                self._environment.target_temp_high = temp_high
        else:
            temp = self._preset_env.get_temperature(self.hass)  # NEW: Template-aware
            if temp is not None:
                self._environment.target_temp = temp
```

#### Climate Entity Enhancements

```python
# climate.py

class DualSmartThermostat(ClimateEntity):
    def __init__(self, ...):
        """Enhanced to track template listeners."""
        # Existing init...

        # NEW: Template listener tracking
        self._template_listeners: list[Callable] = []
        self._active_preset_entities: set[str] = set()

    async def _setup_template_listeners(self) -> None:
        """Set up listeners for entities referenced in active preset templates."""
        # Implementation in Phase 2

    async def _remove_template_listeners(self) -> None:
        """Remove all template entity listeners."""
        # Implementation in Phase 2

    @callback
    async def _async_template_entity_changed(self, event: Event) -> None:
        """Handle changes to entities referenced in preset templates."""
        # Implementation in Phase 2

    # MODIFIED: Enhanced existing methods
    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        # Existing code...
        await self._setup_template_listeners()  # NEW

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        # Existing code...
        await self._setup_template_listeners()  # NEW: Update for new preset

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        # Existing code...
        await self._remove_template_listeners()  # NEW: Cleanup
```

#### Schema Enhancements

```python
# schemas.py

def get_presets_schema(user_input: dict[str, Any]) -> vol.Schema:
    """Get presets configuration schema - MODIFIED for templates."""
    schema_dict = {}

    for preset in selected_presets:
        if preset in CONF_PRESETS:
            if heat_cool_enabled:
                # MODIFIED: TemplateSelector instead of NumberSelector
                schema_dict[vol.Optional(f"{preset}_temp_low", default=20)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax  # NEW validator
                )
                schema_dict[vol.Optional(f"{preset}_temp_high", default=24)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax  # NEW validator
                )
            else:
                # MODIFIED: TemplateSelector for single temperature
                schema_dict[vol.Optional(f"{preset}_temp", default=20)] = vol.All(
                    selector.TemplateSelector(
                        selector.TemplateSelectorConfig()
                    ),
                    validate_template_syntax  # NEW validator
                )

    return vol.Schema(schema_dict)

def validate_template_syntax(value: Any) -> Any:
    """Validate template syntax if value is a string. NEW function."""
    if isinstance(value, str):
        try:
            from homeassistant.helpers.template import Template
            Template(value)  # Parse only, don't evaluate
        except Exception as e:
            raise vol.Invalid(f"Invalid template syntax: {e}")
    return value
```

### Configuration Contract

**Config Entry Structure** (JSON stored by Home Assistant):

```json
{
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

**Translation Contract** (en.json):

```json
{
  "config": {
    "step": {
      "presets": {
        "data": {
          "away_temp": "Away temperature (static, entity, or template)",
          "away_temp_low": "Away low temperature (static, entity, or template)",
          "away_temp_high": "Away high temperature (static, entity, or template)",
          "eco_temp": "Eco temperature (static, entity, or template)",
          "comfort_temp": "Comfort temperature (static, entity, or template)"
        },
        "data_description": {
          "away_temp": "Examples:\n• Static: 20\n• Entity: {{ states('input_number.away_temp') }}\n• Conditional: {{ 16 if is_state('sensor.season', 'winter') else 26 }}",
          "away_temp_low": "Examples:\n• Static: 18\n• Entity: {{ states('sensor.min_temp') }}\n• Calculated: {{ states('sensor.outdoor_temp') | float - 2 }}",
          "away_temp_high": "Examples:\n• Static: 24\n• Entity: {{ states('sensor.max_temp') }}\n• Calculated: {{ states('sensor.outdoor_temp') | float + 4 }}",
          "eco_temp": "Examples:\n• Static: 19\n• Entity: {{ states('input_number.eco_temp') }}\n• Conditional: {{ 18 if now().hour < 6 or now().hour > 22 else 20 }}",
          "comfort_temp": "Examples:\n• Static: 22\n• Entity: {{ states('input_number.comfort_temp') }}\n• Conditional: {{ 23 if is_state('binary_sensor.someone_home', 'on') else 20 }}"
        }
      }
    }
  }
}
```

**Note**: The above shows the pattern for all preset temperature fields. Each preset (away, eco, comfort, home, sleep, activity, boost, anti_freeze) follows the same pattern with three example types: static numeric value, entity reference, and conditional/calculated template.

## Phase 2: Implementation Sequence

**Note**: Phase 2 task generation occurs via `/speckit.tasks` command (not part of `/speckit.plan`).

### Implementation Order (for tasks.md)

1. **Foundation** (P1 - Backward Compatibility)
   - PresetEnv: Add template detection and static value handling
   - Tests: Verify static values still work unchanged

2. **Template Evaluation** (P2 - Core Dynamic Behavior)
   - PresetEnv: Implement template evaluation with error handling
   - PresetEnv: Entity extraction from templates
   - PresetManager: Call template-aware getters
   - Tests: Basic template evaluation unit tests

3. **Reactive Updates** (P2/P3 - Reactive Behavior)
   - Climate entity: Template listener setup/cleanup
   - Climate entity: Template entity change handler
   - Tests: Reactive behavior integration tests

4. **Configuration Flow** (P2 - UX)
   - schemas.py: Replace NumberSelector with TemplateSelector
   - schemas.py: Add validate_template_syntax
   - translations/en.json: Add inline help text with examples
   - Tests: Config flow validation tests

5. **Options Flow Integration** (P2)
   - Verify template values pre-fill in options flow
   - Verify template modification works
   - Tests: Options flow persistence tests

6. **End-to-End Validation** (P3)
   - Add template test cases to existing E2E persistence tests
   - Range mode template tests
   - Multiple preset template tests
   - Tests: E2E integration tests

7. **Documentation & Examples** (P4)
   - examples/advanced_features/presets_with_templates.yaml
   - docs/troubleshooting.md template section
   - Update CRITICAL_CONFIG_DEPENDENCIES.md

8. **Quality & Cleanup** (Final)
   - Run linting: isort, black, flake8, codespell
   - Verify all tests pass
   - Memory leak validation (listener cleanup)
   - Code review against CLAUDE.md guidelines

### Test Strategy

**Coverage Goals**: 100% of new template-related code

**Test Files** (following consolidation patterns):

1. `tests/preset_env/test_preset_env_templates.py` - NEW
   - Template detection (static vs template)
   - Entity extraction
   - Template evaluation (success/failure)
   - Error handling and fallback

2. `tests/managers/test_preset_manager_templates.py` - NEW
   - PresetManager calls template evaluation
   - Range mode vs single temp mode
   - Template values applied to environment

3. `tests/test_preset_templates_reactive.py` - NEW
   - Entity change triggers temperature update
   - Control cycle triggered on template re-evaluation
   - Multiple entity changes
   - Listener cleanup on preset change

4. `tests/config_flow/test_preset_templates_config_flow.py` - NEW
   - TemplateSelector accepts template strings
   - Syntax validation catches errors
   - Static values still accepted

5. MODIFY existing E2E tests:
   - `test_e2e_simple_heater_persistence.py` - Add template persistence test
   - `test_e2e_heater_cooler_persistence.py` - Add range mode template test
   - `test_options_flow.py` - Add template modification test

**Test Execution**:
```bash
# Unit tests
pytest tests/preset_env/test_preset_env_templates.py
pytest tests/managers/test_preset_manager_templates.py

# Integration tests
pytest tests/test_preset_templates_reactive.py

# Config flow tests
pytest tests/config_flow/test_preset_templates_config_flow.py

# E2E tests
pytest tests/config_flow/test_e2e_simple_heater_persistence.py -k template
pytest tests/config_flow/test_options_flow.py -k template

# All new tests
pytest -k template

# Full test suite
pytest
```

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Memory leaks from template listeners | Medium | High | Comprehensive listener cleanup testing, verify removal on preset change/entity removal |
| Template evaluation performance | Low | Medium | Performance target <1s, timeout protection, logging for slow evaluations |
| Backward compatibility breaks | Low | High | Explicit test coverage for existing static value workflows |
| Template syntax edge cases | Medium | Low | Comprehensive error handling, fallback to previous value |
| Config flow complexity | Low | Medium | Follow existing TemplateSelector patterns from HA core |

### Mitigation Plan

1. **Memory Leak Prevention**:
   - Unit tests verify listener cleanup
   - Integration tests monitor listener count
   - Manual testing with preset switching

2. **Performance Monitoring**:
   - Log template evaluation time
   - Warn if >1 second
   - SC-003 verifies <5 second update target

3. **Backward Compatibility**:
   - Dedicated P1 test suite for static values
   - Run existing preset tests unchanged
   - SC-001 verifies 100% compatibility

## Success Criteria Mapping

Mapping success criteria from spec.md to implementation verification:

- **SC-001** (Backward compatibility): Verified by existing test suite + new static value tests in test_preset_env_templates.py
- **SC-002** (Templates auto-update): Verified by test_preset_templates_reactive.py entity change tests
- **SC-003** (<5 second update): Verified by reactive test timing assertions
- **SC-004** (Stable on error): Verified by error handling tests + fallback value tests
- **SC-005** (95% syntax error catch): Verified by config flow validation tests with invalid template samples
- **SC-006** (Single-step seasonal config): Verified by E2E test with conditional template
- **SC-007** (No memory leaks): Verified by listener cleanup tests + manual validation
- **SC-008** (Discoverable guidance): Verified by translation content review + manual UI testing

## Dependencies

### Internal Dependencies

- PresetEnv → Home Assistant Template Engine
- PresetManager → PresetEnv (existing dependency, enhanced)
- Climate Entity → PresetManager (existing), PresetEnv (new for listener setup)
- schemas.py → Home Assistant selectors (TemplateSelector)

### External Dependencies

- `homeassistant.helpers.template.Template` - Core HA template engine
- `homeassistant.helpers.event.async_track_state_change_event` - Entity listener setup
- `homeassistant.helpers.selector.TemplateSelector` - Config UI component

### Configuration Dependencies

Must update per CLAUDE.md Configuration Dependencies section:

1. `tools/focused_config_dependencies.json`:
   - Template fields depend on HA template engine availability
   - No cross-field dependencies (templates are self-contained)

2. `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`:
   - Document template syntax requirements
   - Note that referenced entities don't need to exist at config time

## Notes

- This plan follows existing Home Assistant custom component patterns
- Template support is a pure enhancement - no breaking changes
- All constitutional gates addressable through existing test/documentation infrastructure
- Implementation complexity managed through phased approach (P1: static, P2: templates, P3: reactive)
- Success criteria directly testable through automated test suite
