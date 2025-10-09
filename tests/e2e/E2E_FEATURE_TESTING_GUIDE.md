# E2E Feature Combination Testing Guide

## Quick Reference for Phase 4 Implementation

**Goal**: Validate that feature combinations work correctly in the real Home Assistant UI using Playwright.

---

## Test Files to Create

```
tests/e2e/tests/specs/
├── simple_heater_feature_combinations.spec.ts      (~5 tests)
├── ac_only_feature_combinations.spec.ts            (~6 tests)
├── heater_cooler_feature_combinations.spec.ts      (~9 tests)
├── heat_pump_feature_combinations.spec.ts          (~4 tests)
└── feature_interactions.spec.ts                    (~5 tests)
                                              TOTAL: ~29 E2E tests
```

---

## Helper Functions to Create

**File**: `tests/e2e/playwright/feature-helpers.ts`

```typescript
import { Page } from '@playwright/test';

// Feature enablement
export async function enableFeature(page: Page, featureName: string): Promise<void> {
  // Click the checkbox for configure_{featureName}
  await page.getByLabel(`configure_${featureName}`).check();
}

// Feature configuration helpers
export async function configureFloorHeating(page: Page, options: {
  sensor: string;
  min_temp: number;
  max_temp: number;
}): Promise<void> {
  // Fill floor heating configuration form
  await page.getByLabel('Floor Sensor').fill(options.sensor);
  await page.getByLabel('Minimum Floor Temperature').fill(options.min_temp.toString());
  await page.getByLabel('Maximum Floor Temperature').fill(options.max_temp.toString());
  await page.getByRole('button', { name: 'Submit' }).click();
}

export async function configureFan(page: Page, options: {
  fan: string;
  fan_on_with_ac: boolean;
}): Promise<void> {
  await page.getByLabel('Fan Entity').fill(options.fan);
  if (options.fan_on_with_ac) {
    await page.getByLabel('Fan On With AC').check();
  }
  await page.getByRole('button', { name: 'Submit' }).click();
}

export async function configureHumidity(page: Page, options: {
  sensor: string;
  dryer: string;
  target: number;
}): Promise<void> {
  await page.getByLabel('Humidity Sensor').fill(options.sensor);
  await page.getByLabel('Dryer Entity').fill(options.dryer);
  await page.getByLabel('Target Humidity').fill(options.target.toString());
  await page.getByRole('button', { name: 'Submit' }).click();
}

export async function configureOpenings(page: Page, openings: Array<{
  entity: string;
  timeout_open: number;
}>) {
  // Implementation will depend on how openings list is built in UI
  for (const opening of openings) {
    // Add opening
    await page.getByRole('button', { name: 'Add Opening' }).click();
    await page.getByLabel('Opening Entity').fill(opening.entity);
    await page.getByLabel('Timeout Open').fill(opening.timeout_open.toString());
    await page.getByRole('button', { name: 'Save' }).click();
  }
  await page.getByRole('button', { name: 'Submit' }).click();
}

export async function configurePresets(page: Page, config: {
  selected: string[];
  [key: string]: any;
}) {
  // Select presets
  for (const preset of config.selected) {
    await page.getByLabel(preset).check();
  }
  await page.getByRole('button', { name: 'Submit' }).click();

  // Configure each preset
  for (const preset of config.selected) {
    const presetConfig = config[preset];
    if (presetConfig) {
      // Fill temperature fields
      if (presetConfig.temp) {
        await page.getByLabel(`${preset} Temperature`).fill(presetConfig.temp.toString());
      }
      // Add more fields as needed
      await page.getByRole('button', { name: 'Submit' }).click();
    }
  }
}

// Verification helpers
export async function verifyHVACModes(page: Page, expectedModes: string[]): Promise<void> {
  // Navigate to climate entity
  // Check that HVAC modes match expected
  // This will require accessing the entity state via REST API or UI inspection
}

export async function verifyOpeningsScope(page: Page, expectedOptions: string[]): Promise<void> {
  // Check that openings scope selector has expected options
  const scopeSelector = page.getByLabel('Openings Scope');
  for (const option of expectedOptions) {
    await expect(scopeSelector).toContainText(option);
  }
}

export async function verifyPresetFields(page: Page, expectedFields: string[]): Promise<void> {
  // Check that preset configuration form has expected fields
  for (const field of expectedFields) {
    await expect(page.getByLabel(field)).toBeVisible();
  }
}

export async function verifyFeatureToggleVisible(
  page: Page,
  featureName: string,
  shouldBeVisible: boolean
): Promise<void> {
  const toggle = page.getByLabel(`configure_${featureName}`);
  if (shouldBeVisible) {
    await expect(toggle).toBeVisible();
  } else {
    await expect(toggle).not.toBeVisible();
  }
}
```

---

## Example Test: heater_cooler with All Features

```typescript
import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../playwright/setup';
import {
  enableFeature,
  configureFloorHeating,
  configureFan,
  configureHumidity,
  configureOpenings,
  configurePresets,
  verifyHVACModes,
  verifyOpeningsScope,
  verifyPresetFields,
} from '../playwright/feature-helpers';

test.describe('Heater/Cooler Feature Combinations', () => {
  test('all features enabled - complete configuration', async ({ page }) => {
    const setup = new HomeAssistantSetup(page);

    // Login and navigate
    await setup.login();
    await setup.navigateToIntegrations();

    // Start config flow
    await setup.startConfigFlow('Dual Smart Thermostat');

    // Step 1: Select system type
    await page.getByLabel('heater_cooler').check();
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 2: Configure core settings
    await page.getByLabel('Name').fill('Test HVAC All Features');
    await page.getByLabel('Temperature Sensor').fill('sensor.temperature');
    await page.getByLabel('Heater').fill('switch.heater');
    await page.getByLabel('Cooler').fill('switch.cooler');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 3: Enable all features
    await enableFeature(page, 'floor_heating');
    await enableFeature(page, 'fan');
    await enableFeature(page, 'humidity');
    await enableFeature(page, 'openings');
    await enableFeature(page, 'presets');
    await page.getByRole('button', { name: 'Submit' }).click();

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

    // Verify openings scope shows all options
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

    // Verify preset fields include humidity and floor bounds
    await verifyPresetFields(page, [
      'temperature',
      'humidity_min',
      'humidity_max',
      'floor_min',
      'floor_max',
    ]);

    // Submit final configuration
    await page.getByRole('button', { name: 'Submit' }).click();

    // Verify integration created
    await expect(page.getByText('Test HVAC All Features')).toBeVisible();

    // Verify climate entity has correct HVAC modes
    await verifyHVACModes(page, [
      'heat', 'cool', 'heat_cool', 'fan_only', 'dry', 'off'
    ]);
  });

  test('toggle features in options flow', async ({ page }) => {
    // Create integration with fan + humidity
    // Open options flow
    // Disable fan
    // Verify FAN_ONLY mode removed from climate entity
    // Verify openings scope no longer shows 'fan_only'
  });
});
```

---

## Critical Test Scenarios

### Must Test for Each System Type

1. ✅ **Baseline**: No features enabled
2. ✅ **Single features**: Each feature individually
3. 🔥 **All features**: Complete kitchen sink test
4. ✅ **Options flow**: Modify features after creation

### Must Test Across System Types

1. ✅ **Feature visibility**: Blocked features not visible
2. ✅ **HVAC mode additions**: Fan→FAN_ONLY, Humidity→DRY
3. ✅ **Openings scope**: Updates with enabled features
4. ✅ **Preset fields**: Adapt to enabled features

---

## Debugging Tips

### Common Issues

**Issue**: Can't find element by label
```typescript
// Debug: Log all labels
const labels = await page.locator('label').allTextContents();
console.log('Available labels:', labels);
```

**Issue**: Form doesn't submit
```typescript
// Wait for form to be ready
await page.waitForSelector('button[type="submit"]:not([disabled])');
```

**Issue**: Step doesn't transition
```typescript
// Log current step
const stepTitle = await page.locator('h1').textContent();
console.log('Current step:', stepTitle);
```

### Useful Playwright Commands

```bash
# Run with headed browser (see what's happening)
npx playwright test --headed

# Run specific test
npx playwright test heater_cooler_feature_combinations.spec.ts

# Debug mode (step through)
npx playwright test --debug

# Update screenshots
npx playwright test --update-snapshots
```

---

## Implementation Checklist

### Before Starting
- [ ] Review existing E2E test patterns in `tests/e2e/tests/specs/`
- [ ] Understand HomeAssistantSetup class in `tests/e2e/playwright/setup.ts`
- [ ] Check actual UI element selectors in Home Assistant

### Phase 4.1: Create Helpers
- [ ] Create `feature-helpers.ts` with basic functions
- [ ] Test helpers with one simple test
- [ ] Refine selectors based on actual UI

### Phase 4.2: System Type Tests
- [ ] simple_heater tests (5 tests)
- [ ] ac_only tests (6 tests)
- [ ] heater_cooler tests (9 tests)
- [ ] heat_pump tests (4 tests)

### Phase 4.3: Interaction Tests
- [ ] feature_interactions.spec.ts (5 tests)

### Phase 4.4: Integration
- [ ] Update CI workflow to run E2E feature tests
- [ ] Add E2E test documentation to README
- [ ] Create baseline screenshots if using visual regression

---

## Expected Timeline

| Task | Duration | Priority |
|------|----------|----------|
| Create feature-helpers.ts | 0.5 days | 🔥 |
| simple_heater tests | 0.5 days | 🔥 |
| ac_only tests | 0.5 days | 🔥 |
| heater_cooler tests | 1 day | 🔥 |
| heat_pump tests | 0.5 days | 🔥 |
| feature_interactions tests | 1 day | 🔥 |
| CI integration + docs | 0.5 days | 🔥 |
| **TOTAL** | **4-5 days** | |

---

## Success Criteria

- [ ] All 29 E2E feature combination tests created
- [ ] All tests pass locally
- [ ] All tests pass in CI
- [ ] Feature helpers are reusable and well-documented
- [ ] Tests cover all critical feature combinations
- [ ] Tests validate HVAC mode additions
- [ ] Tests validate openings scope updates
- [ ] Tests validate preset field adaptation
- [ ] No flaky tests (tests are deterministic)

---

**Document Version**: 1.0
**Date**: 2025-10-09
**Status**: Ready for Implementation
**Phase**: Phase 4 (E2E Feature Combination Tests)
