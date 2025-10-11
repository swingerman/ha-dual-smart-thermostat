# Feature Testing Plan: EXPANDED with E2E Tests

## Executive Summary

**Problem**: Features have strict ordering dependencies and system-type-specific availability, but comprehensive tests validating these contracts are missing - including E2E validation of feature combinations in the actual UI.

**Solution**: Implement 4-phase test-driven development (TDD) approach with layered test coverage:
1. **Contract Tests (Python)**: Feature availability per system type
2. **Integration Tests (Python)**: Feature configuration persistence per system type
3. **Interaction Tests (Python)**: Features affecting other features (HVAC modes, presets, openings)
4. **E2E Feature Combination Tests (Playwright)**: End-to-end validation of feature combinations in real Home Assistant UI

**Priority**: 🔥 HIGH - Critical for feature completeness and release stability

**Scope Change**: Added Phase 4 (E2E tests) to validate feature combinations work correctly in the actual browser UI.

---

## Why E2E Tests Matter for Features

### What Python Tests Cannot Validate

1. **UI Element Visibility**: Do feature toggles actually appear/disappear based on system type?
2. **Dynamic Form Updates**: Does enabling a feature immediately show its configuration fields?
3. **Step Transitions**: Does the UI correctly navigate through feature configuration steps?
4. **Scope Selector Updates**: Does openings_scope selector update when fan/humidity features are enabled?
5. **Preset Field Adaptation**: Do preset forms show correct fields based on heat_cool_mode?
6. **Real User Workflows**: Can users actually complete feature configurations without errors?

### Real-World Example
**Scenario**: User selects heater_cooler, enables fan + humidity, then configures openings.

**Python test**: ✅ Validates data structure is correct
**E2E test**: ✅ Validates user can actually click through the UI and see:
- Fan and humidity toggles are visible and checkable
- After enabling fan, fan configuration step appears
- After enabling humidity, humidity configuration step appears
- Openings scope selector includes "fan_only" and "dry" options
- All data persists correctly after submission

---

## Phase 4: E2E Feature Combination Tests (NEW)

### Test Strategy

**Goal**: Validate critical feature combinations work end-to-end in real Home Assistant UI.

**Approach**: Test matrix covering:
- Each system type with its available feature combinations
- Critical feature interactions (fan→FAN_ONLY, humidity→DRY)
- Dependency chains (features → openings → presets)

### Test Matrix

#### 4.1 System Type: simple_heater

**Test File**: `tests/e2e/tests/specs/simple_heater_feature_combinations.spec.ts`

**Test Cases**:
1. ✅ **No features enabled** (baseline)
   - Complete flow with all features disabled
   - Verify no feature config steps appear

2. ✅ **Floor heating only**
   - Enable configure_floor_heating
   - Complete floor heating configuration
   - Verify floor sensor, min/max temps saved

3. ✅ **Openings only**
   - Enable configure_openings
   - Add 2 openings with different timeouts
   - Configure openings_scope (should only show: all, heat)
   - Verify openings persist correctly

4. ✅ **Presets only**
   - Enable configure_presets
   - Select 3 presets (home, away, eco)
   - Configure single temperature per preset (heat_cool_mode=False)
   - Verify preset temperatures persist

5. 🔥 **ALL features enabled** (critical path)
   - Enable: floor_heating + openings + presets
   - Complete all configuration steps in order
   - Verify complete configuration persists
   - Verify step ordering: floor → openings → presets

**Blocked Features to Verify**:
- ❌ Fan toggle not visible
- ❌ Humidity toggle not visible

---

#### 4.2 System Type: ac_only

**Test File**: `tests/e2e/tests/specs/ac_only_feature_combinations.spec.ts`

**Test Cases**:
1. ✅ **No features enabled** (baseline)

2. ✅ **Fan only**
   - Enable configure_fan
   - Complete fan configuration (entity, fan_on_with_ac)
   - Verify FAN_ONLY mode added to climate entity

3. ✅ **Humidity only**
   - Enable configure_humidity
   - Complete humidity configuration
   - Verify DRY mode added to climate entity

4. ✅ **Fan + Humidity** (HVAC mode interaction)
   - Enable both fan and humidity
   - Complete both configurations
   - Verify climate entity has: COOL, FAN_ONLY, DRY, OFF modes

5. ✅ **Fan + Humidity + Openings** (scope interaction)
   - Enable fan, humidity, openings
   - Complete configurations
   - Verify openings_scope shows: all, cool, fan_only, dry
   - Select "fan_only" scope and verify persistence

6. 🔥 **ALL features enabled** (critical path)
   - Enable: fan + humidity + openings + presets
   - Complete all configuration steps
   - Verify preset configuration includes humidity bounds
   - Verify complete configuration persists
   - Test options flow modification (toggle features on/off)

**Blocked Features to Verify**:
- ❌ Floor heating toggle not visible

---

#### 4.3 System Type: heater_cooler

**Test File**: `tests/e2e/tests/specs/heater_cooler_feature_combinations.spec.ts`

**Test Cases**:
1. ✅ **No features enabled** (baseline)

2. ✅ **Single feature: floor_heating**
3. ✅ **Single feature: fan**
4. ✅ **Single feature: humidity**

5. ✅ **Floor + Fan** (compatible features)
   - Enable floor_heating + fan
   - Complete both configurations
   - Verify both feature settings persist

6. ✅ **Fan + Humidity** (HVAC mode additions)
   - Enable fan + humidity
   - Verify climate entity adds: FAN_ONLY + DRY modes
   - Complete configurations

7. ✅ **Openings with all HVAC modes**
   - Enable fan + humidity + openings
   - Verify openings_scope selector shows ALL options:
     - all, heat, cool, heat_cool, fan_only, dry
   - Test selecting each scope option

8. 🔥 **ALL features enabled** (critical path)
   - Enable: floor_heating + fan + humidity + openings + presets
   - Complete all configuration steps in order
   - Verify step sequence: floor → fan → humidity → openings → presets
   - Verify preset configuration includes:
     - Temperature fields (dual if heat_cool_mode=True)
     - Humidity bounds (min/max)
     - Floor temp bounds (min/max)
     - Opening references (if openings configured)
   - Complete configuration and verify persistence
   - Test options flow:
     - Pre-filled values correct
     - Can modify feature settings
     - Can toggle features on/off
     - Changes persist correctly

9. ✅ **heat_cool_mode preset temperature adaptation**
   - Enable presets with heat_cool_mode=False
   - Configure presets with single temperature
   - Reopen options flow, change heat_cool_mode=True
   - Verify preset configuration now shows temp_low/temp_high

**All Features Available**:
- ✅ All 5 feature toggles should be visible

---

#### 4.4 System Type: heat_pump

**Test File**: `tests/e2e/tests/specs/heat_pump_feature_combinations.spec.ts`

**Test Cases**:
1. ✅ **No features enabled** (baseline)

2. ✅ **Dynamic HVAC mode switching**
   - Configure heat_pump with heat_pump_cooling sensor
   - Enable fan feature
   - Verify FAN_ONLY mode appears when cooling is active
   - Test toggling heat_pump_cooling sensor state
   - Verify HVAC modes update dynamically

3. ✅ **Fan + Humidity with heat pump**
   - Enable fan + humidity
   - Complete configurations
   - Verify modes adapt to heat_pump_cooling state

4. 🔥 **ALL features enabled** (critical path)
   - Similar to heater_cooler but with heat_pump_cooling handling
   - Verify all features work with dynamic cooling state
   - Test switching cooling state and verifying mode updates

**All Features Available**:
- ✅ All 5 feature toggles should be visible

---

### 4.5 Cross-Feature Interaction Tests

**Test File**: `tests/e2e/tests/specs/feature_interactions.spec.ts`

**Test Cases**:

1. ✅ **Fan feature adds FAN_ONLY mode**
   - Test with: ac_only, heater_cooler, heat_pump
   - Enable fan, verify FAN_ONLY appears in climate entity
   - Disable fan (options flow), verify FAN_ONLY removed

2. ✅ **Humidity feature adds DRY mode**
   - Test with: ac_only, heater_cooler, heat_pump
   - Enable humidity, verify DRY appears
   - Disable humidity, verify DRY removed

3. ✅ **Openings scope adapts to HVAC modes**
   - Start with heater_cooler (only heat/cool modes)
   - Verify openings_scope shows: all, heat, cool, heat_cool
   - Enable fan, verify "fan_only" added to scope options
   - Enable humidity, verify "dry" added to scope options
   - Disable features, verify options removed

4. ✅ **Presets depend on all features**
   - Configure heater_cooler with all features
   - Verify preset configuration form shows:
     - Temperature fields
     - Humidity bounds (because humidity enabled)
     - Floor bounds (because floor_heating enabled)
     - Opening selector (because openings configured)
   - Disable humidity in options flow
   - Verify preset configuration no longer shows humidity bounds

5. ✅ **Preset temperature field switching**
   - Configure presets with heat_cool_mode=False
   - Verify single temperature field per preset
   - Change heat_cool_mode=True (options flow)
   - Verify presets now show temp_low + temp_high
   - Change back to False, verify single temp field

---

### E2E Test Implementation Details

#### Test File Structure
```
tests/e2e/tests/specs/
├── simple_heater_feature_combinations.spec.ts
├── ac_only_feature_combinations.spec.ts
├── heater_cooler_feature_combinations.spec.ts
├── heat_pump_feature_combinations.spec.ts
└── feature_interactions.spec.ts
```

#### Reusable Helpers (to create)
```
tests/e2e/playwright/
├── setup.ts (already exists, enhance)
└── feature-helpers.ts (NEW)
    ├── enableFeature(page, feature_name)
    ├── configureFloorHeating(page, options)
    ├── configureFan(page, options)
    ├── configureHumidity(page, options)
    ├── configureOpenings(page, openings_list)
    ├── configurePresets(page, presets_config)
    ├── verifyHVACModes(page, expected_modes)
    ├── verifyOpeningsScope(page, expected_options)
    └── verifyPresetFields(page, expected_fields)
```

#### Test Pattern Example
```typescript
test('heater_cooler with all features enabled', async ({ page }) => {
  const setup = new HomeAssistantSetup(page);
  await setup.login();
  await setup.navigateToIntegrations();

  // Start config flow
  await setup.startConfigFlow('Dual Smart Thermostat');

  // Step 1: Select system type
  await setup.selectSystemType('heater_cooler');

  // Step 2: Configure core settings
  await setup.configureHeaterCooler({
    name: 'Test HVAC',
    sensor: 'sensor.temperature',
    heater: 'switch.heater',
    cooler: 'switch.cooler',
  });

  // Step 3: Enable all features
  await enableFeature(page, 'floor_heating');
  await enableFeature(page, 'fan');
  await enableFeature(page, 'humidity');
  await enableFeature(page, 'openings');
  await enableFeature(page, 'presets');
  await setup.submitFeatures();

  // Step 4: Configure floor heating
  await configureFloorHeating(page, {
    sensor: 'sensor.floor_temp',
    min_temp: 5,
    max_temp: 35,
  });

  // Step 5: Configure fan
  await configureFan(page, {
    fan: 'switch.fan',
    fan_on_with_ac: true,
  });

  // Step 6: Configure humidity
  await configureHumidity(page, {
    sensor: 'sensor.humidity',
    dryer: 'switch.dehumidifier',
    target: 50,
  });

  // Step 7: Configure openings
  await configureOpenings(page, [
    { entity: 'binary_sensor.door', timeout_open: 300 },
    { entity: 'binary_sensor.window', timeout_open: 600 },
  ]);

  // Verify openings scope includes all options
  await verifyOpeningsScope(page, [
    'all', 'heat', 'cool', 'heat_cool', 'fan_only', 'dry'
  ]);

  // Step 8: Configure presets
  await configurePresets(page, {
    selected: ['home', 'away', 'eco'],
    home: { temp: 21, humidity_min: 30, humidity_max: 60 },
    away: { temp: 18, humidity_min: 20, humidity_max: 70 },
    eco: { temp: 19, humidity_min: 25, humidity_max: 65 },
  });

  // Verify preset fields include humidity (because humidity enabled)
  await verifyPresetFields(page, [
    'temperature', 'humidity_min', 'humidity_max', 'floor_min', 'floor_max'
  ]);

  // Submit and verify creation
  await setup.submitConfiguration();
  await setup.verifyIntegrationCreated('Test HVAC');

  // Verify climate entity has correct HVAC modes
  await verifyHVACModes(page, ['heat', 'cool', 'heat_cool', 'fan_only', 'dry', 'off']);
});
```

---

## Updated Phase Summary

### Phase 1: Contract Tests (Python) ✅ COMPLETED
- **Duration**: 1 day
- **Status**: 37/48 tests passing (RED phase complete)
- **Files**: `tests/contracts/`

### Phase 2: Integration Tests (Python) 🔄 NEXT
- **Duration**: 3-4 days
- **Deliverables**: Per-system-type feature integration tests
- **Files**: `tests/config_flow/test_*_features_integration.py`

### Phase 3: Interaction Tests (Python) ⏳ PENDING
- **Duration**: 2-3 days
- **Deliverables**: Cross-feature interaction tests
- **Files**: `tests/features/test_feature_*_interactions.py`

### Phase 4: E2E Feature Combination Tests (Playwright) 🆕 PENDING
- **Duration**: 4-5 days
- **Deliverables**:
  - 4 system-type-specific test files (25+ tests total)
  - 1 interaction test file (5+ tests)
  - Enhanced feature helpers (`feature-helpers.ts`)
- **Files**: `tests/e2e/tests/specs/*_feature_combinations.spec.ts`

---

## Total Timeline Estimate

| Phase | Type | Duration | Priority |
|-------|------|----------|----------|
| 1 | Contract Tests (Python) | 1 day | ✅ Done |
| 2 | Integration Tests (Python) | 3-4 days | 🔥 High |
| 3 | Interaction Tests (Python) | 2-3 days | 🔥 High |
| 4 | E2E Feature Tests (Playwright) | 4-5 days | 🔥 High |
| **TOTAL** | | **10-13 days** | |

---

## Acceptance Criteria (Updated)

### Phase 1 (Contract Tests) - ✅ COMPLETE
- ✅ All contract tests written (48 tests)
- ✅ Feature availability matrix validated (26/26 passing)
- ⚠️ Feature ordering tests reveal implementation gaps (4/9 passing)
- ⚠️ Feature schema tests reveal missing steps (7/13 passing)

### Phase 2 (Integration Tests)
- ✅ Each system type has complete feature integration test coverage
- ✅ Config and options flows tested for all feature combinations
- ✅ Feature persistence validates against data-model.md

### Phase 3 (Interaction Tests)
- ✅ Fan feature adds FAN_ONLY mode
- ✅ Humidity feature adds DRY mode
- ✅ Openings scope adapts to enabled features
- ✅ Presets adapt to all enabled features

### Phase 4 (E2E Tests) - 🆕 NEW
- ✅ Each system type tested with critical feature combinations
- ✅ All features enabled test passes for each system type
- ✅ Feature toggles visibility validated per system type
- ✅ HVAC mode additions validated in real climate entity
- ✅ Openings scope selector adapts to features in real UI
- ✅ Preset form fields adapt to features in real UI
- ✅ Options flow modifications work correctly
- ✅ All E2E tests pass in CI

### Overall Quality Gates
- ✅ All Python tests pass locally (`pytest -q`)
- ✅ All E2E tests pass locally (`npx playwright test`)
- ✅ All tests pass in CI
- ✅ No regressions in existing tests
- ✅ Code coverage > 90% for feature-related code
- ✅ All code passes linting checks

---

## Why This Expansion is Critical

### Bugs E2E Tests Will Catch (that Python tests won't)

1. **UI Element Missing**: Feature toggle doesn't appear in UI even though backend expects it
2. **Selector Not Updating**: Openings scope selector doesn't update when fan enabled
3. **Form Validation Issues**: Client-side validation prevents valid configuration
4. **Step Navigation Bugs**: Flow gets stuck between steps
5. **State Persistence UI Bugs**: Data saved but UI doesn't reflect it on reload
6. **Dynamic Field Updates**: Preset form doesn't update when heat_cool_mode changes
7. **Real Browser Issues**: Works in mocks but fails in real browser (timing, async, etc.)

### Real-World Confidence

- **Before**: "Tests pass, should work" 🤞
- **After**: "Tests pass, proven to work in real browser" ✅

---

## Implementation Order (Recommended)

### Sprint 1: Foundation (Week 1)
- ✅ Day 1: Phase 1 Contract Tests (DONE)
- Days 2-5: Phase 2 Integration Tests (Python)

### Sprint 2: Interactions (Week 2)
- Days 1-3: Phase 3 Interaction Tests (Python)
- Days 4-5: Create E2E feature helpers + first test file

### Sprint 3: E2E Coverage (Week 2-3)
- Days 1-2: simple_heater + ac_only E2E tests
- Days 3-4: heater_cooler + heat_pump E2E tests
- Day 5: feature_interactions E2E tests + CI integration

---

## Success Metrics

**Current Progress**:
- ✅ Phase 1 complete (37/48 passing)
- ⏳ Phase 2-4 pending

**Target**:
- ✅ 100% contract tests passing
- ✅ 100% integration tests passing
- ✅ 100% interaction tests passing
- ✅ 100% E2E feature combination tests passing
- ✅ All tests green in CI
- ✅ Zero feature-related bugs in production

---

**Document Version**: 2.0 (EXPANDED)
**Date**: 2025-10-09
**Status**: Phase 1 Complete, Phases 2-4 Ready to Start
**Scope Change**: Added Phase 4 (E2E Feature Combination Tests)
