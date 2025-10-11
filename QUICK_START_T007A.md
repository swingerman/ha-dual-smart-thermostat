# Quick Start: T007A Feature Testing

**For developers starting work on T007A phases**

---

## Current Status

✅ **Phase 1 Complete** (Contract Tests - RED phase done)
- 48 tests created
- 37 passing (77%)
- 11 failing (documented in `tests/contracts/RED_PHASE_RESULTS.md`)

---

## Quick Commands

### Run Tests

```bash
# All contract tests
pytest tests/contracts/ -v

# Specific category
pytest tests/contracts/test_feature_availability_contracts.py -v  # 100% passing ✅
pytest tests/contracts/test_feature_ordering_contracts.py -v      # 44% passing
pytest tests/contracts/test_feature_schema_contracts.py -v        # 54% passing

# Single test
pytest tests/contracts/test_feature_availability_contracts.py::TestFeatureAvailabilityContracts::test_available_features_per_system_type -v
```

### Lint Code

```bash
# Fix imports and formatting
isort tests/contracts/
black tests/contracts/
flake8 tests/contracts/

# Or all at once
isort . && black . && flake8 .
```

---

## What to Work On Next

### Option 1: Fix Phase 1 Failures (GREEN phase) 🔥 **RECOMMENDED FIRST**

**Why**: Get Phase 1 to 100% passing before moving forward

**Steps**:
1. Read `tests/contracts/RED_PHASE_RESULTS.md` for failure analysis
2. Investigate actual implementation:
   ```bash
   # Check what steps exist
   grep -n "async def async_step_" custom_components/dual_smart_thermostat/config_flow.py
   ```
3. Fix tests or code to make them pass
4. Target: 48/48 tests passing

**Estimated Time**: 1-2 days

---

### Option 2: Start Phase 2 (Integration Tests)

**Why**: Start building per-system-type feature tests

**Steps**:
1. Create `tests/config_flow/test_simple_heater_features_integration.py`
2. Follow patterns from existing tests in `tests/config_flow/`
3. Use contract tests as guidance for what to validate
4. Test feature combinations: none, single, multiple, all

**Example Test Structure**:
```python
class TestSimpleHeaterFeaturesIntegration:
    async def test_floor_heating_only(self, hass):
        """Test simple_heater with only floor_heating enabled."""
        # Complete config flow with floor_heating=True
        # Verify floor_sensor, min/max_floor_temp saved
        # Verify climate entity created

    async def test_all_available_features(self, hass):
        """Test simple_heater with all available features."""
        # Enable: floor_heating + openings + presets
        # Complete all configuration steps
        # Verify complete configuration persists
```

**Estimated Time**: 3-4 days for all system types

---

### Option 3: Start Phase 4 (E2E Tests)

**Why**: Validate feature combinations in real browser

**Steps**:
1. Read `tests/e2e/E2E_FEATURE_TESTING_GUIDE.md`
2. Create `tests/e2e/playwright/feature-helpers.ts`
3. Create first E2E test: `tests/e2e/tests/specs/simple_heater_feature_combinations.spec.ts`
4. Test locally: `cd tests/e2e && npx playwright test --headed`

**Example E2E Test**:
```typescript
test('simple_heater with floor_heating', async ({ page }) => {
  const setup = new HomeAssistantSetup(page);
  await setup.login();
  await setup.navigateToIntegrations();

  // Start config flow
  await setup.startConfigFlow('Dual Smart Thermostat');

  // Select system type
  await page.getByLabel('simple_heater').check();
  await page.getByRole('button', { name: 'Submit' }).click();

  // Configure basic settings
  await page.getByLabel('Name').fill('Test Heater');
  await page.getByLabel('Temperature Sensor').fill('sensor.temp');
  await page.getByLabel('Heater').fill('switch.heater');
  await page.getByRole('button', { name: 'Submit' }).click();

  // Enable floor_heating feature
  await page.getByLabel('configure_floor_heating').check();
  await page.getByRole('button', { name: 'Submit' }).click();

  // Configure floor heating
  await configureFloorHeating(page, {
    sensor: 'sensor.floor_temp',
    min_temp: 5,
    max_temp: 35,
  });

  // Verify integration created
  await setup.verifyIntegrationCreated('Test Heater');
});
```

**Estimated Time**: 4-5 days for all system types

---

## Recommended Path

### Week 1: Fix & Integrate
```
Day 1: Fix Phase 1 failures (GREEN phase) ← START HERE
Day 2: Start Phase 2 - simple_heater integration tests
Day 3: Phase 2 - ac_only integration tests
Day 4: Phase 2 - heater_cooler integration tests
Day 5: Phase 2 - heat_pump integration tests
```

### Week 2: Interactions & E2E Setup
```
Day 1-2: Phase 3 - HVAC mode interaction tests
Day 3: Phase 3 - Openings/presets interaction tests
Day 4: Create E2E feature helpers
Day 5: First E2E test suite (simple_heater)
```

### Week 3: Complete E2E
```
Day 1: ac_only E2E tests
Day 2: heater_cooler E2E tests
Day 3: heat_pump E2E tests
Day 4: feature_interactions E2E tests
Day 5: CI integration + documentation
```

---

## Key Files Reference

### Documentation
- `T007A_IMPLEMENTATION_SUMMARY.md` - Complete overview
- `specs/001-develop-config-and/FEATURE_TESTING_PLAN_EXPANDED.md` - Detailed strategy
- `tests/e2e/E2E_FEATURE_TESTING_GUIDE.md` - E2E implementation guide
- `tests/contracts/RED_PHASE_RESULTS.md` - Phase 1 failure analysis

### Test Files
- `tests/contracts/` - Phase 1 (48 tests created ✅)
- `tests/config_flow/*_features_integration.py` - Phase 2 (to create)
- `tests/features/test_feature_*_interactions.py` - Phase 3 (to create)
- `tests/e2e/tests/specs/*_feature_combinations.spec.ts` - Phase 4 (to create)

### Helper Code
- `tests/e2e/playwright/setup.ts` - Existing E2E helpers
- `tests/e2e/playwright/feature-helpers.ts` - To create for Phase 4

---

## Feature Availability Quick Reference

| Feature | simple_heater | ac_only | heater_cooler | heat_pump |
|---------|---------------|---------|---------------|-----------|
| floor_heating | ✅ | ❌ | ✅ | ✅ |
| fan | ❌ | ✅ | ✅ | ✅ |
| humidity | ❌ | ✅ | ✅ | ✅ |
| openings | ✅ | ✅ | ✅ | ✅ |
| presets | ✅ | ✅ | ✅ | ✅ |

**Use this table** when writing tests to know which features are available!

---

## Getting Help

### Understanding Test Failures
1. Read failure message carefully
2. Check `tests/contracts/RED_PHASE_RESULTS.md` for analysis
3. Run single test with `-v` for more detail
4. Add `--log-cli-level=DEBUG` to see debug output

### Understanding Feature Flow
1. Check `specs/001-develop-config-and/FEATURE_TESTING_PLAN_EXPANDED.md`
2. Look at existing tests in `tests/config_flow/`
3. Check `CLAUDE.md` for architecture overview

### E2E Test Issues
1. Run with `--headed` to see browser
2. Use `--debug` to step through
3. Check `tests/e2e/LESSONS_LEARNED.md` for patterns
4. Look at existing E2E tests in `tests/e2e/tests/specs/`

---

## Success Metrics

### Phase 1 (Contract Tests)
- Target: 48/48 tests passing ✅
- Current: 37/48 passing (77%)
- Remaining: 11 tests to fix

### Phase 2-3 (Python Tests)
- Target: ~60 integration/interaction tests
- Current: 0 (not started)

### Phase 4 (E2E Tests)
- Target: ~29 E2E tests
- Current: 0 (not started)

### Overall
- Target: ~137 total feature tests
- Current: 48 created, 37 passing
- **Progress: 27% complete**

---

## Quick Tips

### Writing Python Tests
- Follow TDD: Write test first (RED), then fix code (GREEN)
- Use existing fixtures from `tests/conftest.py`
- Copy patterns from `tests/config_flow/test_heat_pump_config_flow.py`
- Always lint: `isort . && black . && flake8 .`

### Writing E2E Tests
- Use helpers from `HomeAssistantSetup` class
- Wait for elements before interacting
- Use descriptive test names
- Add comments for clarity
- Test in headed mode first: `--headed`

### Debugging
- Python: `pytest -vvs --log-cli-level=DEBUG`
- E2E: `npx playwright test --debug`
- Add print statements or console.log
- Check actual vs expected carefully

---

**Last Updated**: 2025-10-09
**Status**: Phase 1 RED phase complete, ready for GREEN phase or Phase 2
**Quick Start**: Run `pytest tests/contracts/ -v` to see current status
