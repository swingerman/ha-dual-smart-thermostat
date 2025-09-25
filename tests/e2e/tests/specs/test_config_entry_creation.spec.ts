import { test, expect } from '@playwright/test';
import { SystemType, HomeAssistantSetup } from '../../playwright/setup';

test.describe('Config Entry Creation Test', () => {
  let helper: HomeAssistantSetup;
  const integrationName = `Test Config Entry Creation ${Date.now()}`;

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

  test('Create and verify basic heater config entry', async ({ page }) => {
    console.log('🚀 Testing config entry creation');

    // Create a config entry for basic heater
    console.log('📝 Creating basic heater config entry...');
    const entryId = await helper.createConfigEntry(SystemType.SIMPLE_HEATER, integrationName);

    expect(entryId).toBeTruthy();
    console.log(`✅ Config entry created with ID: ${entryId}`);

    // Verify the integration appears in the integrations page
    await helper.goToIntegrations();
    const integrationCard = page.locator(`[data-domain="dual_smart_thermostat"]:has-text("${integrationName}")`);
    await expect(integrationCard).toBeVisible();
    console.log('✅ Integration card is visible on integrations page');
  });
});
