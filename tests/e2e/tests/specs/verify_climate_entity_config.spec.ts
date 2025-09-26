import { test, expect } from '@playwright/test';
import { HomeAssistantSetup, SystemType } from '../../playwright/setup';

test.describe('Dual Smart Thermostat - Integration Creation Verification', () => {
  let helper: HomeAssistantSetup;
  const integrationName = `Test Climate Entity Config ${Date.now()}`;

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

  test('Verify basic heater integration creation', async ({ page }) => {
    console.log('🚀 Starting basic heater integration creation verification');

    // Create a config entry for basic heater
    console.log('📝 Creating basic heater config entry...');
    const entryId = await helper.createConfigEntry(SystemType.SIMPLE_HEATER, integrationName);
    expect(entryId).toBeTruthy();

    // Wait a moment for the entity to be created
    await page.waitForTimeout(2000);

    // Verify the integration exists
    console.log('🔍 Verifying integration exists...');
    const exists = await helper.verifyIntegrationExists(integrationName);
    expect(exists).toBe(true);

    console.log('✅ Basic heater integration creation verification completed');
  });

  test('Verify AC-only integration creation', async ({ page }) => {
    console.log('🚀 Starting AC-only integration creation verification');

    // Create a config entry for AC-only
    console.log('📝 Creating AC-only config entry...');
    const entryId = await helper.createConfigEntry(SystemType.AC_ONLY, integrationName);
    expect(entryId).toBeTruthy();

    // Wait a moment for the entity to be created
    await page.waitForTimeout(2000);

    // Verify the integration exists
    console.log('🔍 Verifying integration exists...');
    const exists = await helper.verifyIntegrationExists(integrationName);
    expect(exists).toBe(true);

    console.log('✅ AC-only integration creation verification completed');
  });
});
