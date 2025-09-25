import { test, expect } from '@playwright/test';
import {
  isConfirmationStep,
  isBasicConfigurationStep,
  isFeatureConfigurationStep,
  isSystemTypeStep,
  OPEN_DIALOG_SELECTOR,
  OPEN_DIALOG_TITLE_SELECTOR,
  SystemType,
  HomeAssistantSetup,
} from '../../playwright/setup';

test.describe('Dual Smart Thermostat - Basic Heater Options Flow', () => {
  let helper: HomeAssistantSetup;
  const integrationName = `Test Basic Heater E2E Options ${Date.now()}`;

  test.beforeEach(async ({ page }) => {
    helper = new HomeAssistantSetup(page);
  });

  test.afterEach(async ({ page }) => {
    // Clean up the test integration
    try {
      await helper.deleteConfigEntry(integrationName);
    } catch (error) {
      console.log('⚠️ Cleanup failed (integration may not exist):', error);
    }
  });

  test('Complete basic heater options flow', async ({ page }) => {
    console.log('🚀 Starting basic heater options flow test');

    // First, create a config entry for basic heater
    console.log('📝 Creating basic heater config entry...');
    const entryId = await helper.createConfigEntry(SystemType.SIMPLE_HEATER, integrationName);
    expect(entryId).toBeTruthy();

    // Now start the options flow
    console.log('🔧 Starting options flow...');
    await helper.startOptionsFlow(integrationName);

    // Navigate through options flow steps (same as config flow but without name field)
    await helper.navigateOptionsFlowSteps(SystemType.SIMPLE_HEATER);

    console.log('✅ Basic heater options flow completed');

    // Verify we're back on the integrations page
    await expect(page).toHaveURL(/.*\/config\/integrations/);
  });

  // test('Options flow - modify only basic settings', async ({ page }) => {
  //   console.log('🚀 Starting basic heater options flow test (basic settings only)');

  //   // Create a config entry
  //   const entryId = await helper.createConfigEntry(SystemType.SIMPLE_HEATER, integrationName);
  //   expect(entryId).toBeTruthy();

  //   // Start options flow
  //   await helper.startOptionsFlow(integrationName);

  //   // Navigate through options flow steps
  //   await helper.navigateOptionsFlowSteps(SystemType.SIMPLE_HEATER);

  //   console.log('✅ Basic heater options flow (basic settings only) completed');

  //   // Verify completion
  //   await expect(page).toHaveURL(/.*\/config\/integrations/);
  // });
});
