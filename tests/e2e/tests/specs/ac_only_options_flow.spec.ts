import { test, expect } from '@playwright/test';
import { HomeAssistantSetup, SystemType } from '../../playwright/setup';

test.describe('Dual Smart Thermostat - AC Only Options Flow', () => {
  let helper: HomeAssistantSetup;
  const integrationName = `Test AC Only E2E Options ${Date.now()}`;

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

  test('Complete AC-only options flow', async ({ page }) => {
    console.log('🚀 Starting AC-only options flow test');

    // First, create a config entry for AC-only
    console.log('📝 Creating AC-only config entry...');
    const entryId = await helper.createConfigEntry(SystemType.AC_ONLY, integrationName);
    expect(entryId).toBeTruthy();

    // Now start the options flow
    console.log('🔧 Starting options flow...');
    await helper.startOptionsFlow(integrationName);

    // Navigate through options flow steps (same as config flow but without name field)
    await helper.navigateOptionsFlowSteps(SystemType.AC_ONLY);

    console.log('✅ AC-only options flow completed');

    // Verify we're back on the integrations page
    await expect(page).toHaveURL(/.*\/config\/integrations/);
  });

  // test('Options flow - modify only basic settings', async ({ page }) => {
  //   console.log('🚀 Starting AC-only options flow test (basic settings only)');

  //   // Create a config entry
  //   const entryId = await helper.createConfigEntry(SystemType.AC_ONLY, integrationName);
  //   expect(entryId).toBeTruthy();

  //   // Start options flow
  //   await helper.startOptionsFlow(integrationName);

  //   // Navigate through options flow steps
  //   await helper.navigateOptionsFlowSteps(SystemType.AC_ONLY);

  //   console.log('✅ AC-only options flow (basic settings only) completed');

  //   // Verify completion
  //   await expect(page).toHaveURL(/.*\/config\/integrations/);
  // });

  // test('Options flow - cancel and return to integrations', async ({ page }) => {
  //   console.log('🚀 Starting AC-only options flow test (cancel flow)');

  //   // Create a config entry
  //   const entryId = await helper.createConfigEntry(SystemType.AC_ONLY, integrationName);
  //   expect(entryId).toBeTruthy();

  //   // Start options flow
  //   await helper.startOptionsFlow(integrationName);

  //   // Make some changes in the first step
  //   const dialogOpen = await page.locator(OPEN_DIALOG_SELECTOR).count();
  //   if (dialogOpen > 0) {
  //     const coldToleranceField = page.locator(`${OPEN_DIALOG_SELECTOR} input[name="cold_tolerance"]`);
  //     if (await coldToleranceField.count() > 0) {
  //       await coldToleranceField.fill('0.9');
  //     }
  //   }

  //   // Cancel the flow
  //   const cancelButton = page.locator(`${OPEN_DIALOG_SELECTOR} button:has-text("Cancel")`);
  //   if (await cancelButton.count() > 0) {
  //     await cancelButton.click();
  //   }

  //   // Should return to integrations page without saving
  //   await expect(page).toHaveURL(/.*\/config\/integrations/);
  //   console.log('✅ Successfully cancelled options flow');
  // });
});
