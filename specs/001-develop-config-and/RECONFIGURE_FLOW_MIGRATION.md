# Migration Plan: Config/Reconfigure/Options Flow Architecture

**Created**: 2025-10-21
**Status**: Planning
**Related Spec**: specs/001-develop-config-and/spec.md
**Related Issue**: Incorrect use of Options Flow for structural changes

---

## Executive Summary

This document outlines the migration plan to properly implement Home Assistant's config flow patterns by introducing a dedicated **reconfigure flow** and simplifying the **options flow** to only handle runtime tuning. This aligns with HA best practices where:

- **Config Flow**: Initial integration setup
- **Reconfigure Flow**: Modify structural configuration (system type, entities, features)
- **Options Flow**: Runtime adjustments (temperatures, tolerances, timeouts)

---

## Current State Assessment

### Problems Identified

1. **Config and Options flows are 99% identical**
   - Both implement the complete multi-step configuration wizard
   - Only difference: config flow includes `CONF_NAME` field
   - Violates HA separation of concerns

2. **Options flow does too much**
   - Allows changing system type (should trigger reload)
   - Allows changing entities (structural change)
   - Allows adding/removing features (structural change)
   - Should only handle runtime parameter tuning

3. **Missing reconfigure flow**
   - HA provides `SOURCE_RECONFIGURE` specifically for structural changes
   - Current options flow is doing what reconfigure should do
   - Users have no clear signal when changes will reload the integration

### Impact

- **User Confusion**: No clear distinction between "tune settings" vs "reconfigure system"
- **Technical Debt**: Massive code duplication between config_flow.py and options_flow.py
- **Maintenance Burden**: Changes must be synchronized across both flows
- **HA Non-Compliance**: Not following recommended patterns

---

## Target Architecture

### Flow Responsibilities

| Flow Type | Purpose | Entry Point | Behavior | Examples |
|-----------|---------|-------------|----------|----------|
| **Config** | Initial setup | Add Integration | Creates new entry | First-time install |
| **Reconfigure** | Structural changes | Reconfigure button | Updates + reloads | Change system type, swap entities, add features |
| **Options** | Runtime tuning | Configure button | Updates without reload | Adjust tolerances, timeouts, temperature limits |

### Code Structure

```
config_flow.py
├── ConfigFlowHandler
│   ├── async_step_user()                    # Config: Initial entry
│   ├── async_step_reconfigure()             # NEW: Reconfigure entry
│   ├── async_step_reconfigure_confirm()     # NEW: Optional confirmation
│   ├── [All existing step methods]          # Shared by config + reconfigure
│   └── _determine_next_step()               # Handles both flows

options_flow.py
├── OptionsFlowHandler
│   ├── async_step_init()                    # SIMPLIFIED: Single step
│   ├── _build_options_schema()              # NEW: Build runtime-only schema
│   └── [Remove all multi-step logic]        # Delete feature toggles, entity selectors
```

---

## Migration Strategy

### Phase 1: Add Reconfigure Flow (Non-Breaking)

**Goal**: Add reconfigure capability while preserving existing options flow

**Tasks**:
1. Add `async_step_reconfigure()` entry point to `ConfigFlowHandler`
2. Add reconfigure detection in `_determine_next_step()`
3. Use `async_update_reload_and_abort()` for reconfigure completion
4. Add tests for reconfigure flow
5. Update translations for reconfigure steps

**Files Modified**:
- `config_flow.py`: Add reconfigure methods
- `translations/en.json`: Add reconfigure step translations
- `tests/config_flow/test_reconfigure_flow.py`: New test file

**Success Criteria**:
- ✅ Reconfigure button appears in HA UI
- ✅ Reconfigure flow completes and reloads integration
- ✅ All existing tests pass
- ✅ Options flow still works (unchanged)

**Timeline**: 1-2 days

---

### Phase 2: Simplify Options Flow (Breaking Change)

**Goal**: Replace complex options flow with simple runtime tuning

**Tasks**:
1. Create backup of `options_flow.py` as `options_flow_legacy.py`
2. Implement new simplified `OptionsFlowHandler`
3. Update options flow tests
4. Add migration guide for users

**Files Modified**:
- `options_flow.py`: Complete rewrite (simplified)
- `tests/options_flow/`: Update all test files
- `docs/migration/reconfigure_flow.md`: User migration guide

**Removed from Options Flow**:
- System type selection
- Entity selectors (heater, cooler, sensor, etc.)
- Feature toggles (configure_fan, configure_humidity, etc.)
- Multi-step wizard logic
- Opening/preset configuration steps

**Retained in Options Flow**:
- Temperature tolerances (`cold_tolerance`, `hot_tolerance`)
- Temperature limits (`min_temp`, `max_temp`)
- Target temperatures (`target_temp`, `target_temp_high`, `target_temp_low`)
- Precision and step (`precision`, `temp_step`)
- Timing (`keep_alive`, `initial_hvac_mode`)
- Timeout values (aux heater, openings)
- Preset temperature overrides (not adding/removing presets)
- Floor temperature limits (if floor heating enabled)

**Success Criteria**:
- ✅ Options flow is single-step
- ✅ No entity selectors in options flow
- ✅ All runtime parameters adjustable
- ✅ Tests cover all system types
- ✅ Documentation updated

**Timeline**: 2-3 days

---

### Phase 3: Documentation Updates

**Goal**: Update all documentation to reflect new architecture

**Tasks**:
1. Update `specs/001-develop-config-and/spec.md`
2. Update `docs/config_flow/architecture.md`
3. Update `.specify/memory/constitution.md`
4. Update `CLAUDE.md` project instructions
5. Create user migration guide

**Files Modified**:
- `specs/001-develop-config-and/spec.md`: Split FR-003, add reconfigure scenarios
- `docs/config_flow/architecture.md`: Add reconfigure section, rewrite options section
- `.specify/memory/constitution.md`: Clarify UX parity across three flows
- `CLAUDE.md`: Update development workflow
- `docs/migration/config_to_reconfigure.md`: NEW user guide

**Success Criteria**:
- ✅ All docs reference three flows correctly
- ✅ Decision tree: when to use which flow
- ✅ Examples for each flow type
- ✅ Migration guide for existing users

**Timeline**: 1 day

---

### Phase 4: Testing & Validation

**Goal**: Comprehensive testing of all three flows

**Tasks**:
1. Integration tests for complete flow sequences
2. Test all system types in each flow
3. Test upgrade path from old options flow
4. Manual testing in HA dev environment

**Test Coverage**:
- Config flow: All system types, all features
- Reconfigure flow: Change system type, modify entities, add/remove features
- Options flow: All runtime parameters for each system type
- Upgrade: Existing installations work with new flows

**Files Created**:
- `tests/integration/test_three_flow_architecture.py`
- `tests/config_flow/test_reconfigure_all_systems.py`
- `tests/options_flow/test_simplified_options.py`

**Success Criteria**:
- ✅ All tests pass
- ✅ Test coverage > 95% for flow handlers
- ✅ No regressions in existing functionality
- ✅ Manual testing checklist complete

**Timeline**: 2 days

---

## Implementation Details

### Phase 1 Implementation: Reconfigure Flow

#### Step 1.1: Add Reconfigure Entry Point

```python
# config_flow.py

from homeassistant.config_entries import SOURCE_RECONFIGURE

class ConfigFlowHandler(ConfigFlow, domain=DOMAIN):
    # ... existing code ...

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration of the integration.

        This entry point is triggered when the user clicks "Reconfigure"
        in the Home Assistant UI. It allows changing structural configuration
        like system type, entities, and enabled features.
        """
        # Get the existing config entry being reconfigured
        entry = self._get_reconfigure_entry()

        # Initialize collected_config with current data
        # This ensures all existing settings are preserved unless changed
        self.collected_config = dict(entry.data)

        # Start the reconfigure flow with system type selection
        # This mirrors the initial config flow but with current values as defaults
        return await self.async_step_reconfigure_confirm(user_input)

    async def async_step_reconfigure_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reconfiguration and show system type selection.

        This step warns users that reconfiguring will reload the integration
        and allows them to change the system type.
        """
        if user_input is not None:
            self.collected_config.update(user_input)
            # Proceed to the standard system config flow
            return await self._async_step_system_config()

        # Show system type selection with current type as default
        current_system_type = self.collected_config.get(CONF_SYSTEM_TYPE)

        return self.async_show_form(
            step_id="reconfigure_confirm",
            data_schema=get_system_type_schema(default=current_system_type),
            description_placeholders={
                "current_system": current_system_type,
                "warning": "Changing configuration will reload the integration",
            },
        )
```

#### Step 1.2: Modify Flow Completion Logic

```python
# config_flow.py

async def _determine_next_step(self) -> FlowResult:
    """Determine the next step based on configuration dependencies."""

    # ... existing step determination logic ...

    # At the end, when all steps are complete:

    # Check if this is a reconfigure flow
    if self.source == SOURCE_RECONFIGURE:
        # Reconfigure flow: update existing entry
        cleaned_config = self._clean_config_for_storage(self.collected_config)

        # Validate configuration
        if not validate_config_with_models(cleaned_config):
            _LOGGER.warning(
                "Configuration validation failed during reconfigure for %s",
                cleaned_config.get(CONF_NAME, "thermostat"),
            )

        # Update and reload the integration
        return self.async_update_reload_and_abort(
            self._get_reconfigure_entry(),
            data_updates=cleaned_config,
        )
    else:
        # Config flow: create new entry
        cleaned_config = self._clean_config_for_storage(self.collected_config)

        if not validate_config_with_models(cleaned_config):
            _LOGGER.warning(
                "Configuration validation failed for %s",
                cleaned_config.get(CONF_NAME, "thermostat"),
            )

        return self.async_create_entry(
            title=self.async_config_entry_title(self.collected_config),
            data=cleaned_config,
        )
```

#### Step 1.3: Add Translations

```json
// translations/en.json

{
  "config": {
    "step": {
      "reconfigure_confirm": {
        "title": "Reconfigure Dual Smart Thermostat",
        "description": "You are reconfiguring **{current_system}**. This will reload the integration.\n\n{warning}",
        "data": {
          "system_type": "System Type"
        }
      }
    }
  }
}
```

### Phase 2 Implementation: Simplified Options Flow

#### Step 2.1: New Options Flow Structure

```python
# options_flow.py

class OptionsFlowHandler(OptionsFlow):
    """Handle options flow for runtime parameter tuning only.

    This flow is for adjusting operational parameters without structural changes.
    For changing system type, entities, or features, use the Reconfigure flow.
    """

    def __init__(self, config_entry) -> None:
        """Initialize options flow."""
        self._init_config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle options flow - single step for runtime adjustments."""
        if user_input is not None:
            # Validate and merge with existing data
            entry = self._get_entry()
            updated_data = {**entry.data, **user_input}

            # Validate configuration
            if not validate_config_with_models(updated_data):
                _LOGGER.warning(
                    "Configuration validation failed for %s",
                    updated_data.get(CONF_NAME, "thermostat"),
                )
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._build_options_schema(entry.data),
                    errors={"base": "invalid_config"},
                )

            return self.async_create_entry(title="", data=updated_data)

        # Show single-step form with runtime parameters only
        current_config = self._get_current_config()

        return self.async_show_form(
            step_id="init",
            data_schema=self._build_options_schema(current_config),
            description_placeholders={
                "info": "Adjust runtime parameters. To change system type or entities, use Reconfigure.",
            },
        )

    def _build_options_schema(
        self, config: dict[str, Any]
    ) -> vol.Schema:
        """Build schema with only runtime-adjustable parameters.

        This schema includes ONLY parameters that can be changed without
        reloading the integration. Structural changes (system type, entities,
        features) are handled by the reconfigure flow.
        """
        schema_dict: dict[Any, Any] = {}
        system_type = config.get(CONF_SYSTEM_TYPE)

        # --- Core Runtime Parameters (All Systems) ---

        # Temperature Tolerances
        schema_dict[
            vol.Optional(
                CONF_COLD_TOLERANCE,
                default=config.get(CONF_COLD_TOLERANCE, 0.3),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
                min=0.1,
                max=5.0,
                unit_of_measurement="°C",
            )
        )

        schema_dict[
            vol.Optional(
                CONF_HOT_TOLERANCE,
                default=config.get(CONF_HOT_TOLERANCE, 0.3),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                step=0.1,
                min=0.1,
                max=5.0,
                unit_of_measurement="°C",
            )
        )

        # Temperature Limits
        schema_dict[
            vol.Optional(
                CONF_MIN_TEMP,
                default=config.get(CONF_MIN_TEMP, 7),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=5,
                max=35,
                unit_of_measurement=DEGREE,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_MAX_TEMP,
                default=config.get(CONF_MAX_TEMP, 35),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                min=5,
                max=50,
                unit_of_measurement=DEGREE,
            )
        )

        # Target Temperatures (optional)
        schema_dict[
            vol.Optional(
                CONF_TARGET_TEMP,
                default=config.get(CONF_TARGET_TEMP),
            )
        ] = selector.NumberSelector(
            selector.NumberSelectorConfig(
                mode=selector.NumberSelectorMode.BOX,
                unit_of_measurement=DEGREE,
            )
        )

        # Target Temperature Range (for heat_cool mode)
        if system_type != SYSTEM_TYPE_AC_ONLY:
            schema_dict[
                vol.Optional(
                    CONF_TARGET_TEMP_HIGH,
                    default=config.get(CONF_TARGET_TEMP_HIGH),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement=DEGREE,
                )
            )

            schema_dict[
                vol.Optional(
                    CONF_TARGET_TEMP_LOW,
                    default=config.get(CONF_TARGET_TEMP_LOW),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement=DEGREE,
                )
            )

        # Precision and Step
        schema_dict[
            vol.Optional(
                CONF_PRECISION,
                default=config.get(CONF_PRECISION, "0.1"),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["0.1", "0.5", "1.0"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        schema_dict[
            vol.Optional(
                CONF_TEMP_STEP,
                default=config.get(CONF_TEMP_STEP, "1.0"),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=["0.1", "0.5", "1.0"],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # Timing
        schema_dict[
            vol.Optional(
                CONF_KEEP_ALIVE,
                default=config.get(CONF_KEEP_ALIVE),
            )
        ] = selector.DurationSelector(
            selector.DurationSelectorConfig(allow_negative=False)
        )

        schema_dict[
            vol.Optional(
                CONF_INITIAL_HVAC_MODE,
                default=config.get(CONF_INITIAL_HVAC_MODE),
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=self._get_hvac_mode_options(system_type),
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # --- System-Specific Runtime Parameters ---

        # Dual Stage: Aux heater timeout
        if system_type == SYSTEM_TYPE_DUAL_STAGE and config.get(CONF_AUX_HEATER):
            schema_dict[
                vol.Optional(
                    CONF_AUX_HEATING_TIMEOUT,
                    default=config.get(CONF_AUX_HEATING_TIMEOUT),
                )
            ] = selector.DurationSelector(
                selector.DurationSelectorConfig(allow_negative=False)
            )

            schema_dict[
                vol.Optional(
                    CONF_AUX_HEATING_DUAL_MODE,
                    default=config.get(CONF_AUX_HEATING_DUAL_MODE, False),
                )
            ] = selector.BooleanSelector()

        # Floor Heating: Temperature limits
        if config.get(CONF_FLOOR_SENSOR):
            schema_dict[
                vol.Optional(
                    "max_floor_temp",
                    default=config.get("max_floor_temp"),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement=DEGREE,
                )
            )

            schema_dict[
                vol.Optional(
                    "min_floor_temp",
                    default=config.get("min_floor_temp"),
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    unit_of_measurement=DEGREE,
                )
            )

        # Openings: Timeouts
        if config.get("openings"):
            schema_dict[
                vol.Optional(
                    "opening_timeout",
                    default=config.get("opening_timeout"),
                )
            ] = selector.DurationSelector(
                selector.DurationSelectorConfig(allow_negative=False)
            )

            schema_dict[
                vol.Optional(
                    "closing_timeout",
                    default=config.get("closing_timeout"),
                )
            ] = selector.DurationSelector(
                selector.DurationSelectorConfig(allow_negative=False)
            )

        # Presets: Temperature overrides (if presets configured)
        # Note: This allows adjusting preset temperatures, NOT adding/removing presets
        if config.get("presets"):
            for preset in config["presets"]:
                preset_temp_key = f"{preset}_temp"
                if preset_temp_key in config:
                    schema_dict[
                        vol.Optional(
                            preset_temp_key,
                            default=config.get(preset_temp_key),
                        )
                    ] = selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement=DEGREE,
                        )
                    )

        return vol.Schema(schema_dict)

    def _get_hvac_mode_options(self, system_type: str) -> list[str]:
        """Get available HVAC mode options based on system type."""
        options = ["off"]

        if system_type != SYSTEM_TYPE_AC_ONLY:
            options.extend(["heat", "heat_cool"])

        options.extend(["cool", "fan_only", "dry"])

        return options

    def _get_entry(self):
        """Return the active config entry."""
        if "config_entry" in self.__dict__:
            return self.__dict__["config_entry"]
        return self._init_config_entry

    def _get_current_config(self) -> dict[str, Any]:
        """Get current configuration merging data and options."""
        entry = self._get_entry()
        options = getattr(entry, "options", {}) or {}
        try:
            data = dict(entry.data) if entry.data else {}
        except (TypeError, AttributeError):
            data = entry.data if isinstance(entry.data, dict) else {}
        try:
            options = dict(options) if options else {}
        except (TypeError, AttributeError):
            options = options if isinstance(options, dict) else {}
        return {**data, **options}
```

---

## Backwards Compatibility

### Existing Installations

**Challenge**: Users with existing installations use the current options flow

**Solution**:
1. Phase 1 adds reconfigure without breaking options flow
2. Phase 2 simplifies options but preserves data
3. First time user opens options after upgrade, show migration notice

**Migration Notice** (in options flow):
```
The configuration system has been updated. For structural changes
(system type, entities, features), please use the "Reconfigure" button.
This options dialog now focuses on runtime parameters only.
```

### Data Preservation

All existing configuration data is preserved. The simplified options flow just doesn't show fields for structural configuration - those fields remain in entry.data and are only editable via reconfigure flow.

---

## Testing Strategy

### Unit Tests

```python
# tests/config_flow/test_reconfigure_flow.py

async def test_reconfigure_entry_point():
    """Test reconfigure flow entry point."""
    # Given an existing config entry
    # When user starts reconfigure flow
    # Then flow initializes with current config

async def test_reconfigure_updates_entry():
    """Test reconfigure flow updates existing entry."""
    # Given an existing config entry
    # When user completes reconfigure flow
    # Then entry is updated, not created

async def test_reconfigure_preserves_name():
    """Test reconfigure preserves entry name."""
    # Given an existing config entry with name
    # When user reconfigures
    # Then name is preserved

async def test_reconfigure_all_system_types():
    """Test reconfigure for each system type."""
    # For each system type
    # Test reconfigure flow completes successfully
```

```python
# tests/options_flow/test_simplified_options.py

async def test_options_single_step():
    """Test options flow is single-step."""
    # Given an existing entry
    # When user opens options
    # Then single form is shown

async def test_options_no_entity_selectors():
    """Test options flow has no entity selectors."""
    # Given an existing entry
    # When user opens options
    # Then schema has no EntitySelector fields

async def test_options_runtime_params_only():
    """Test options shows only runtime parameters."""
    # Given an existing entry
    # When user opens options
    # Then only tolerances, temps, timeouts shown

async def test_options_preserves_structural_config():
    """Test options doesn't modify system type or entities."""
    # Given an existing entry with system_type and entities
    # When user submits options
    # Then system_type and entities unchanged
```

### Integration Tests

```python
# tests/integration/test_flow_architecture.py

async def test_config_then_reconfigure():
    """Test config flow followed by reconfigure."""
    # 1. Complete config flow
    # 2. Complete reconfigure flow
    # 3. Verify entry updated

async def test_config_then_options():
    """Test config flow followed by options."""
    # 1. Complete config flow
    # 2. Complete options flow
    # 3. Verify only runtime params changed

async def test_reconfigure_then_options():
    """Test reconfigure followed by options."""
    # 1. Complete reconfigure flow
    # 2. Complete options flow
    # 3. Verify changes isolated correctly
```

---

## Risk Assessment

### High Risk

❌ **Breaking existing options flow**: Mitigated by phased rollout, Phase 1 non-breaking

### Medium Risk

⚠️ **User confusion**: Mitigated by clear UI messaging and migration guide

⚠️ **Test gaps**: Mitigated by comprehensive test plan in Phase 4

### Low Risk

✅ **Data loss**: All data preserved, only UI changes

✅ **Regression**: Existing config flow unchanged

---

## Timeline & Resources

### Estimated Timeline

| Phase | Duration | Blocking? |
|-------|----------|-----------|
| Phase 1: Add Reconfigure | 1-2 days | No |
| Phase 2: Simplify Options | 2-3 days | Yes (depends on Phase 1) |
| Phase 3: Documentation | 1 day | No (can parallelize) |
| Phase 4: Testing | 2 days | Yes (final validation) |
| **Total** | **6-8 days** | |

### Resources Needed

- Development: 1 developer (full-time)
- Testing: Manual HA environment for integration testing
- Documentation: Technical writer (optional, can be handled by developer)

---

## Success Metrics

### Technical Metrics

- ✅ Reconfigure flow functional for all system types
- ✅ Options flow is single-step
- ✅ Code reduction: ~60% less code in options_flow.py
- ✅ Test coverage: >95% for flow handlers
- ✅ No CI failures

### User Experience Metrics

- ✅ Clear distinction between reconfigure and options
- ✅ Reduced cognitive load in options flow
- ✅ No data loss in migration
- ✅ Positive user feedback (post-release)

---

## Next Steps

1. **Review this migration plan** with stakeholders
2. **Get approval** to proceed
3. **Create feature branch**: `feature/reconfigure-flow-architecture`
4. **Execute Phase 1**: Add reconfigure flow
5. **Checkpoint**: Review Phase 1, decide to proceed to Phase 2

---

## Appendix: Decision Tree

### When to Use Which Flow?

```
User wants to...
│
├─ Install integration for first time
│  └─ Use: CONFIG FLOW
│
├─ Change system type (simple heater → heat pump)
│  └─ Use: RECONFIGURE FLOW
│
├─ Change entities (different heater switch)
│  └─ Use: RECONFIGURE FLOW
│
├─ Add/remove features (enable fan control)
│  └─ Use: RECONFIGURE FLOW
│
├─ Adjust temperature tolerances
│  └─ Use: OPTIONS FLOW
│
├─ Change target temperature
│  └─ Use: OPTIONS FLOW
│
├─ Adjust timeouts
│  └─ Use: OPTIONS FLOW
│
└─ Modify preset temperatures
   └─ Use: OPTIONS FLOW
```

---

## Appendix: File Changes Summary

### New Files

- `tests/config_flow/test_reconfigure_flow.py`
- `tests/options_flow/test_simplified_options.py`
- `tests/integration/test_flow_architecture.py`
- `docs/migration/config_to_reconfigure.md`
- `specs/001-develop-config-and/RECONFIGURE_FLOW_MIGRATION.md` (this file)

### Modified Files

**Phase 1**:
- `custom_components/dual_smart_thermostat/config_flow.py`
- `custom_components/dual_smart_thermostat/translations/en.json`

**Phase 2**:
- `custom_components/dual_smart_thermostat/options_flow.py` (major rewrite)
- All files in `tests/options_flow/`

**Phase 3**:
- `specs/001-develop-config-and/spec.md`
- `docs/config_flow/architecture.md`
- `.specify/memory/constitution.md`
- `CLAUDE.md`

### Deleted Code

**Phase 2**:
- ~500 lines from `options_flow.py` (multi-step logic, feature steps)
- Feature step handler references in options flow

---

**Migration Plan Version**: 1.0
**Last Updated**: 2025-10-21
**Next Review**: After Phase 1 completion
