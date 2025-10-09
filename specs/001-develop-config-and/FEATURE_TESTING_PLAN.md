# Feature Testing Plan: TDD Approach for Config & Options Flows

## Executive Summary

**Problem**: Features have strict ordering dependencies and system-type-specific availability, but comprehensive tests validating these contracts are missing.

**Solution**: Implement test-driven development (TDD) approach with layered test coverage:
1. **Contract Tests**: Feature availability per system type
2. **Ordering Tests**: Step sequence validation
3. **Integration Tests**: Feature configuration persistence
4. **Interaction Tests**: Features affecting other features (HVAC modes, presets, openings)

**Priority**: 🔥 HIGH - Critical for feature completeness and release stability

---

## Feature Availability Matrix (Source of Truth)

Based on code analysis of `config_flow.py:528-650` and `data-model.md`:

| Feature | simple_heater | ac_only | heater_cooler | heat_pump |
|---------|---------------|---------|---------------|-----------|
| **floor_heating** | ✅ | ❌ | ✅ | ✅ |
| **fan** | ❌ | ✅ | ✅ | ✅ |
| **humidity** | ❌ | ✅ | ✅ | ✅ |
| **openings** | ✅ | ✅ | ✅ | ✅ |
| **presets** | ✅ | ✅ | ✅ | ✅ |

**Rationale**:
- `floor_heating`: Heating-based systems only (no cooling-only systems)
- `fan`: Systems with active cooling or heat pumps
- `humidity`: Systems with active cooling (dehumidification capability)
- `openings`: All systems (universal safety feature)
- `presets`: All systems (universal comfort feature)

---

## Feature Ordering Rules (Critical Dependencies)

### Phase 1: System Configuration
```
1. System Type Selection
   └─> system_type: {simple_heater, ac_only, heater_cooler, heat_pump}
```

### Phase 2: Core Settings
```
2. Core Settings (system-type-specific entities and tolerances)
   └─> heater/cooler/sensor entities, tolerances, min_cycle_duration
```

### Phase 3: Feature Selection & Configuration
```
3. Features Selection (unified step)
   └─> configure_floor_heating: bool
   └─> configure_fan: bool
   └─> configure_humidity: bool
   └─> configure_openings: bool
   └─> configure_presets: bool

4. Per-Feature Configuration (conditional, based on toggles)
   4a. Floor Heating Config (if enabled and system supports it)
       └─> floor_sensor, min_floor_temp, max_floor_temp

   4b. Fan Config (if enabled and system supports it)
       └─> fan entity, fan_on_with_ac, fan_air_outside, fan_hot_tolerance_toggle

   4c. Humidity Config (if enabled and system supports it)
       └─> humidity_sensor, dryer, target_humidity, min/max_humidity, tolerances
```

### Phase 4: Dependent Features (Must Be Last)
```
5. Openings Configuration (depends on system type + core entities)
   └─> openings list (entity_id, timeout_open, timeout_close)
   └─> openings_scope: {all, heat, cool, heat_cool, fan_only, dry}
       (scope options depend on available HVAC modes)

6. Presets Configuration (depends on ALL previous configuration)
   └─> presets list: [home, away, eco, ...]
   └─> per-preset temperature fields
       - Single temp: <preset>_temp (when heat_cool_mode=False)
       - Dual temp: <preset>_temp_low, <preset>_temp_high (when heat_cool_mode=True)
   └─> per-preset opening references (if openings configured)
   └─> per-preset humidity bounds (if humidity configured)
   └─> per-preset floor temp bounds (if floor_heating configured)
```

**Critical Ordering Constraints**:
- ❌ INVALID: Presets before Openings (presets reference openings)
- ❌ INVALID: Openings before system entities configured (scope depends on HVAC modes)
- ❌ INVALID: Any feature configuration before features selection step
- ✅ VALID: Features → Floor → Fan → Humidity → Openings → Presets

---

## Test Strategy: TDD Layered Approach

### Layer 1: Contract Tests (Foundation)
**Purpose**: Validate feature availability contracts per system type

**Test Files to Create**:
```
tests/contracts/
├── test_feature_availability_contracts.py
├── test_feature_ordering_contracts.py
└── test_feature_schema_contracts.py
```

**Test Coverage**:

#### 1.1 Feature Availability Contract Tests
```python
# tests/contracts/test_feature_availability_contracts.py

class TestFeatureAvailabilityContracts:
    """Validate which features are available for each system type."""

    @pytest.mark.parametrize("system_type,expected_features", [
        ("simple_heater", ["floor_heating", "openings", "presets"]),
        ("ac_only", ["fan", "humidity", "openings", "presets"]),
        ("heater_cooler", ["floor_heating", "fan", "humidity", "openings", "presets"]),
        ("heat_pump", ["floor_heating", "fan", "humidity", "openings", "presets"]),
    ])
    async def test_available_features_per_system_type(
        self, hass, system_type, expected_features
    ):
        """Test that only expected features are available for each system type."""
        # RED: Write this test FIRST (should fail initially)
        # Verify features step shows only expected feature toggles
        # Assert unavailable features are hidden/disabled
        pass

    @pytest.mark.parametrize("system_type,blocked_features", [
        ("simple_heater", ["fan", "humidity"]),
        ("ac_only", ["floor_heating"]),
    ])
    async def test_blocked_features_per_system_type(
        self, hass, system_type, blocked_features
    ):
        """Test that blocked features cannot be enabled for incompatible system types."""
        # RED: Should fail if blocked features are accessible
        pass
```

#### 1.2 Feature Ordering Contract Tests
```python
# tests/contracts/test_feature_ordering_contracts.py

class TestFeatureOrderingContracts:
    """Validate correct step ordering in config and options flows."""

    async def test_features_selection_comes_after_core_settings(self, hass):
        """Test features step appears after system type and core settings."""
        # RED: Capture actual step sequence and assert features comes after core
        pass

    async def test_openings_comes_before_presets(self, hass):
        """Test openings configuration always precedes presets configuration."""
        # RED: Should fail if presets can appear before openings
        pass

    async def test_presets_is_final_configuration_step(self, hass):
        """Test presets is always the last configuration step."""
        # RED: Should fail if any feature step appears after presets
        pass

    @pytest.mark.parametrize("system_type", [
        "simple_heater", "ac_only", "heater_cooler", "heat_pump"
    ])
    async def test_complete_step_ordering_per_system_type(self, hass, system_type):
        """Test complete step sequence is valid for each system type."""
        # RED: Record actual step sequence and validate against ordering rules
        # Expected sequence: system_type → core → features → {floor,fan,humidity} → openings → presets
        pass
```

#### 1.3 Feature Schema Contract Tests
```python
# tests/contracts/test_feature_schema_contracts.py

class TestFeatureSchemaContracts:
    """Validate feature schemas produce expected keys and types."""

    async def test_floor_heating_schema_keys(self):
        """Test get_floor_heating_schema produces expected keys."""
        # RED: Assert schema contains floor_sensor, min_floor_temp, max_floor_temp
        pass

    async def test_fan_schema_keys(self):
        """Test get_fan_schema produces expected keys."""
        # RED: Assert schema contains fan, fan_on_with_ac, fan_air_outside, fan_hot_tolerance_toggle
        pass

    async def test_humidity_schema_keys(self):
        """Test get_humidity_schema produces expected keys."""
        # RED: Assert schema contains humidity_sensor, dryer, target/min/max_humidity, tolerances
        pass

    async def test_openings_schema_keys(self):
        """Test openings schemas produce expected keys."""
        # RED: Assert openings_selection, openings_config, openings_scope selectors exist
        pass

    async def test_presets_schema_keys(self):
        """Test presets schemas produce expected keys."""
        # RED: Assert preset_selection and dynamic preset temp fields work correctly
        pass
```

---

### Layer 2: Integration Tests (Flow Execution)
**Purpose**: Validate end-to-end feature configuration flows

**Test Files to Create**:
```
tests/config_flow/
├── test_simple_heater_features_integration.py
├── test_ac_only_features_integration.py
├── test_heater_cooler_features_integration.py
└── test_heat_pump_features_integration.py
```

**Test Coverage**:

#### 2.1 Per-System-Type Feature Integration Tests
```python
# tests/config_flow/test_simple_heater_features_integration.py

class TestSimpleHeaterFeaturesIntegration:
    """Test complete feature configuration flow for simple_heater."""

    async def test_simple_heater_with_floor_heating(self, hass):
        """Test simple_heater config flow with floor_heating enabled."""
        # RED: Complete flow: system_type → core → features (floor=True) → floor_config → openings → presets
        # Assert floor_sensor, min_floor_temp, max_floor_temp persisted correctly
        pass

    async def test_simple_heater_with_no_features(self, hass):
        """Test simple_heater config flow with all features disabled."""
        # RED: Complete flow with all feature toggles False
        # Assert only core settings persisted, no feature_settings
        pass

    async def test_simple_heater_with_all_available_features(self, hass):
        """Test simple_heater with floor_heating, openings, and presets."""
        # RED: Enable all available features and validate full flow
        pass

    async def test_simple_heater_blocks_fan_feature(self, hass):
        """Test that fan feature is not available for simple_heater."""
        # RED: Assert fan toggle is hidden/disabled in features step
        pass

    async def test_simple_heater_blocks_humidity_feature(self, hass):
        """Test that humidity feature is not available for simple_heater."""
        # RED: Assert humidity toggle is hidden/disabled in features step
        pass
```

#### 2.2 Options Flow Feature Integration Tests
```python
# tests/config_flow/test_simple_heater_features_integration.py (continued)

class TestSimpleHeaterOptionsFlowFeatures:
    """Test options flow feature modification for simple_heater."""

    async def test_options_flow_add_floor_heating(self, hass):
        """Test adding floor_heating feature via options flow."""
        # RED: Create entry without floor_heating, open options, enable floor_heating
        # Assert floor settings added to config entry
        pass

    async def test_options_flow_remove_floor_heating(self, hass):
        """Test removing floor_heating feature via options flow."""
        # RED: Create entry with floor_heating, open options, disable floor_heating
        # Assert floor settings removed from config entry
        pass

    async def test_options_flow_modify_floor_heating_settings(self, hass):
        """Test modifying floor_heating settings via options flow."""
        # RED: Change floor sensor, min/max temps and verify persistence
        pass
```

---

### Layer 3: Feature Interaction Tests (Cross-Feature)
**Purpose**: Validate features affecting other features (HVAC modes, presets dependencies)

**Test Files to Create**:
```
tests/features/
├── test_feature_hvac_mode_interactions.py
├── test_openings_with_hvac_modes.py
└── test_presets_with_all_features.py
```

**Test Coverage**:

#### 3.1 Feature → HVAC Mode Interactions
```python
# tests/features/test_feature_hvac_mode_interactions.py

class TestFeatureHVACModeInteractions:
    """Test how features add HVAC modes."""

    @pytest.mark.parametrize("system_type", ["ac_only", "heater_cooler", "heat_pump"])
    async def test_fan_feature_adds_fan_only_mode(self, hass, system_type):
        """Test that enabling fan feature adds HVACMode.FAN_ONLY."""
        # RED: Create config with fan enabled, assert FAN_ONLY in climate entity's hvac_modes
        pass

    @pytest.mark.parametrize("system_type", ["ac_only", "heater_cooler", "heat_pump"])
    async def test_humidity_feature_adds_dry_mode(self, hass, system_type):
        """Test that enabling humidity feature adds HVACMode.DRY."""
        # RED: Create config with humidity enabled, assert DRY in climate entity's hvac_modes
        pass

    async def test_simple_heater_no_additional_modes(self, hass):
        """Test simple_heater only has HEAT and OFF modes."""
        # RED: Assert simple_heater climate entity only exposes HEAT, OFF (no FAN_ONLY, no DRY)
        pass
```

#### 3.2 Openings + HVAC Modes Interactions
```python
# tests/features/test_openings_with_hvac_modes.py

class TestOpeningsWithHVACModes:
    """Test openings scope configuration with different HVAC mode combinations."""

    async def test_openings_scope_simple_heater(self, hass):
        """Test openings_scope options for simple_heater (heat only)."""
        # RED: Assert openings_scope selector shows: {all, heat}
        pass

    async def test_openings_scope_ac_only_with_fan_and_humidity(self, hass):
        """Test openings_scope options for ac_only with fan+humidity enabled."""
        # RED: Assert openings_scope selector shows: {all, cool, fan_only, dry}
        pass

    async def test_openings_scope_heater_cooler_all_features(self, hass):
        """Test openings_scope options for heater_cooler with all features."""
        # RED: Assert openings_scope shows: {all, heat, cool, heat_cool, fan_only, dry}
        pass
```

#### 3.3 Presets + All Features Interactions
```python
# tests/features/test_presets_with_all_features.py

class TestPresetsWithAllFeatures:
    """Test preset configuration depends on all enabled features."""

    async def test_presets_with_heat_cool_mode_uses_dual_temps(self, hass):
        """Test presets use temp_low/temp_high when heat_cool_mode=True."""
        # RED: Configure heater_cooler, enable presets, verify dual temp fields
        pass

    async def test_presets_with_single_mode_uses_single_temp(self, hass):
        """Test presets use single temp when heat_cool_mode=False."""
        # RED: Configure simple_heater, enable presets, verify single temp field
        pass

    async def test_presets_with_humidity_includes_humidity_bounds(self, hass):
        """Test presets include humidity fields when humidity feature enabled."""
        # RED: Enable humidity, configure presets, verify min/max_humidity fields per preset
        pass

    async def test_presets_with_floor_heating_includes_floor_bounds(self, hass):
        """Test presets include floor temp fields when floor_heating enabled."""
        # RED: Enable floor_heating, configure presets, verify min/max_floor_temp per preset
        pass

    async def test_presets_with_openings_validates_opening_refs(self, hass):
        """Test presets validate opening_refs against configured openings."""
        # RED: Configure openings, then presets with opening_refs
        # Assert validation fails when referencing non-existent opening
        pass

    async def test_presets_without_openings_no_opening_refs(self, hass):
        """Test presets don't show opening_refs when openings not configured."""
        # RED: Configure presets without openings, verify no opening_refs field
        pass
```

---

## Implementation Plan: Phased Rollout

### Phase 1: Contract Tests (Foundation) 🔥 **HIGHEST PRIORITY**
**Duration**: 2-3 days
**Deliverables**:
- `tests/contracts/test_feature_availability_contracts.py`
- `tests/contracts/test_feature_ordering_contracts.py`
- `tests/contracts/test_feature_schema_contracts.py`

**Acceptance Criteria**:
- All contract tests written (RED phase)
- Tests fail with clear error messages showing gaps
- Document exact failures for GREEN phase implementation

**Why First**: Contract tests define the rules. Implementation follows contracts.

---

### Phase 2: Integration Tests (Per System Type) 🔥 **HIGH PRIORITY**
**Duration**: 3-4 days
**Deliverables**:
- Per-system-type feature integration tests (config + options flows)
- Feature availability enforcement per system type
- Feature persistence validation

**Acceptance Criteria**:
- Each system type has complete feature integration test coverage
- Config and options flows tested for all feature combinations
- Tests validate persistence matches `data-model.md` contracts

**Why Second**: Validate complete flows work correctly per system type before testing interactions.

---

### Phase 3: Feature Interaction Tests (Cross-Feature) ✅ **MEDIUM PRIORITY**
**Duration**: 2-3 days
**Deliverables**:
- Feature → HVAC mode interaction tests
- Openings + HVAC modes tests
- Presets + all features dependency tests

**Acceptance Criteria**:
- All feature interaction scenarios tested
- HVAC mode additions validated per feature
- Preset dependencies on other features validated

**Why Third**: After individual features work, validate complex interactions.

---

### Phase 4: Implementation Fixes (GREEN Phase) ✅ **CONTINUOUS**
**Duration**: Concurrent with test writing
**Deliverables**:
- Fix code to make contract tests pass
- Fix code to make integration tests pass
- Fix code to make interaction tests pass

**Approach**:
1. Write test (RED)
2. Run test, capture failure
3. Fix minimal code to make test pass (GREEN)
4. Run full suite to check for regressions (REFACTOR)
5. Commit test + fix together

---

## Test File Organization

```
tests/
├── contracts/                          # Layer 1: Foundation
│   ├── test_feature_availability_contracts.py
│   ├── test_feature_ordering_contracts.py
│   └── test_feature_schema_contracts.py
├── config_flow/                        # Layer 2: Integration
│   ├── test_simple_heater_features_integration.py
│   ├── test_ac_only_features_integration.py
│   ├── test_heater_cooler_features_integration.py
│   └── test_heat_pump_features_integration.py
└── features/                           # Layer 3: Interactions
    ├── test_feature_hvac_mode_interactions.py
    ├── test_openings_with_hvac_modes.py
    └── test_presets_with_all_features.py
```

---

## Acceptance Criteria (Overall)

### Contract Tests Must Validate:
- ✅ Feature availability matrix matches implementation
- ✅ Feature ordering rules enforced in both config and options flows
- ✅ Feature schemas produce expected keys and types

### Integration Tests Must Validate:
- ✅ Each system type's feature combinations work end-to-end
- ✅ Features can be enabled/disabled via config and options flows
- ✅ Feature settings persist correctly (match `data-model.md`)
- ✅ Unavailable features are hidden/disabled per system type

### Interaction Tests Must Validate:
- ✅ Fan feature adds FAN_ONLY mode (affects openings scope)
- ✅ Humidity feature adds DRY mode (affects openings scope)
- ✅ Openings scope options depend on available HVAC modes
- ✅ Presets configuration adapts to enabled features (humidity, floor, openings)
- ✅ Preset validation enforces dependencies (e.g., opening_refs validation)

### Quality Gates:
- ✅ All tests pass locally (`pytest -q`)
- ✅ All tests pass in CI
- ✅ No regressions in existing tests
- ✅ Code coverage > 90% for feature-related code
- ✅ All code passes linting checks

---

## Risk Mitigation

### Risk 1: Changing Feature Availability Breaks Existing Configs
**Mitigation**: Write migration tests that validate old configs still load correctly

### Risk 2: Feature Ordering Changes Break Options Flow
**Mitigation**: Contract tests lock ordering; any change requires explicit test updates

### Risk 3: Feature Interaction Bugs Only Show in Production
**Mitigation**: Comprehensive interaction tests cover all cross-feature scenarios

---

## Related Tasks

This testing plan complements existing tasks:
- **T007A** (Feature Interaction & HVAC Mode Testing) - Covered by Layer 3 tests
- **T005/T006** (System Type Implementation) - Covered by Layer 2 tests
- **T008** (Normalize Keys) - Contract tests will catch key inconsistencies

---

## Success Metrics

**Before**:
- ⚠️ No systematic feature availability validation
- ⚠️ No feature ordering enforcement tests
- ⚠️ Scattered, incomplete feature tests

**After**:
- ✅ 100% feature availability coverage (all system types × all features)
- ✅ Complete feature ordering validation (contract tests)
- ✅ All feature interactions tested (HVAC modes, presets dependencies)
- ✅ Confidence to add new features without breaking existing ones

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Create GitHub issue** for feature testing implementation
3. **Start Phase 1**: Write contract tests (RED phase)
4. **Document failures**: Capture exact test failures for implementation guidance
5. **Implement fixes**: Make tests pass (GREEN phase)
6. **Iterate**: Continue through Phases 2-4

---

**Document Version**: 1.0
**Date**: 2025-01-19
**Status**: Draft - Awaiting Review
