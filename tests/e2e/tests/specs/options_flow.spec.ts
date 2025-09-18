import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../../playwright/setup';

test.describe('Dual Smart Thermostat Options Flow', () => {
  let haSetup: HomeAssistantSetup;

  test.beforeEach(async ({ page }) => {
    haSetup = new HomeAssistantSetup(page);
  });

  test('modify existing simple_heater config options', async ({ page }) => {
    // First, create a config entry via API or assume one exists
    // For this test, we'll assume a config entry exists from previous tests
    
    await haSetup.goToIntegrations();
    
    // Find the existing Dual Smart Thermostat integration
    const integrationCard = page.locator('[data-domain="dual_smart_thermostat"]').first();
    await expect(integrationCard).toBeVisible();
    
    // Click the configure/options button
    await integrationCard.locator('button:has-text("Configure"), mwc-button:has-text("Configure")').click();
    
    // Should open options flow
    await expect(page.locator('h2')).toContainText('Configure');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-01-init.png' });
    await haSetup.clickNext();

    // Basic options modification
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Basic Configuration');
    
    // Modify some settings
    await haSetup.fillFieldByLabel('Cold Tolerance', '0.8');
    await haSetup.fillFieldByLabel('Hot Tolerance', '0.3');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-02-basic-modified.png' });
    await haSetup.clickNext();

    // Features modification
    await haSetup.waitForStep();
    
    // Enable additional features
    await page.check('input[name="configure_presets"]');
    await page.check('input[name="configure_advanced"]');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-03-features-modified.png' });
    await haSetup.clickNext();

    // Preset configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Preset');
    
    await haSetup.fillFieldByLabel('Away Temperature', '15');
    await haSetup.fillFieldByLabel('Sleep Temperature', '17');
    await haSetup.fillFieldByLabel('Home Temperature', '21');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-04-presets.png' });
    await haSetup.clickNext();

    // Advanced settings (since we enabled it)
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Advanced');
    
    await haSetup.fillFieldByLabel('Precision', '0.1');
    await haSetup.fillFieldByLabel('Target Temperature Step', '0.5');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-05-advanced.png' });
    await haSetup.clickNext();

    // Wait for completion
    await page.waitForURL('**/config/integrations', { timeout: 30000 });
    await expect(page.locator('.success')).toContainText('Successfully configured');

    // Validate the updated config entry via API
    const api = haSetup.createAPI();
    const entries = await api.getConfigEntries();
    const configEntry = entries.find(e => e.domain === 'dual_smart_thermostat');
    
    expect(configEntry).toBeDefined();
    
    // Check that data was updated
    expect(configEntry?.data).toMatchObject({
      cold_tolerance: 0.8,
      hot_tolerance: 0.3
    });

    // Check that options were updated
    expect(configEntry?.options).toMatchObject({
      away_temp: 15,
      sleep_temp: 17,
      home_temp: 21,
      precision: 0.1,
      target_temp_step: 0.5
    });
  });

  test('options flow - disable features', async ({ page }) => {
    await haSetup.goToIntegrations();
    
    const integrationCard = page.locator('[data-domain="dual_smart_thermostat"]').first();
    await integrationCard.locator('button:has-text("Configure")').click();
    
    await haSetup.clickNext(); // Skip init

    // Basic config - no changes
    await haSetup.clickNext();

    // Features - disable previously enabled features
    await page.uncheck('input[name="configure_presets"]');
    await page.uncheck('input[name="configure_advanced"]');
    
    await page.screenshot({ path: 'baselines/simple_heater/options-disable-features.png' });
    await haSetup.clickNext();

    // Should complete without additional steps since features are disabled
    await page.waitForURL('**/config/integrations', { timeout: 30000 });

    // Validate that options were cleared
    const api = haSetup.createAPI();
    const entries = await api.getConfigEntries();
    const configEntry = entries.find(e => e.domain === 'dual_smart_thermostat');
    
    // Preset and advanced options should be removed or empty
    expect(configEntry?.options.away_temp).toBeUndefined();
    expect(configEntry?.options.precision).toBeUndefined();
  });

  test('options flow - validation in options', async ({ page }) => {
    await haSetup.goToIntegrations();
    
    const integrationCard = page.locator('[data-domain="dual_smart_thermostat"]').first();
    await integrationCard.locator('button:has-text("Configure")').click();
    
    await haSetup.clickNext(); // Skip init

    // Basic config with invalid values
    await haSetup.fillFieldByLabel('Cold Tolerance', '-1'); // Invalid negative value
    await haSetup.fillFieldByLabel('Hot Tolerance', '10');   // Unusually high value
    
    await haSetup.clickNext();

    // Should show validation errors
    await expect(page.locator('.error, [role="alert"]')).toBeVisible();
    await page.screenshot({ path: 'baselines/simple_heater/options-validation-errors.png' });
  });

  test('options flow - cancel and return to integrations', async ({ page }) => {
    await haSetup.goToIntegrations();
    
    const integrationCard = page.locator('[data-domain="dual_smart_thermostat"]').first();
    await integrationCard.locator('button:has-text("Configure")').click();
    
    // Make some changes
    await haSetup.clickNext();
    await haSetup.fillFieldByLabel('Cold Tolerance', '0.9');
    
    // Cancel the flow
    await page.click('button:has-text("Cancel")');
    
    // Should return to integrations page without saving
    await expect(page.url()).toContain('/config/integrations');
    
    // Verify changes were not saved
    const api = haSetup.createAPI();
    const entries = await api.getConfigEntries();
    const configEntry = entries.find(e => e.domain === 'dual_smart_thermostat');
    
    // Cold tolerance should not be 0.9
    expect(configEntry?.data.cold_tolerance).not.toBe(0.9);
  });

  test('options flow - system type preservation', async ({ page }) => {
    await haSetup.goToIntegrations();
    
    const integrationCard = page.locator('[data-domain="dual_smart_thermostat"]').first();
    await integrationCard.locator('button:has-text("Configure")').click();
    
    // The init step should show current system type but not allow changing it
    await expect(page.locator('text=System Type')).toBeVisible();
    
    // System type field should be read-only or not present as editable
    const systemTypeField = page.locator('select[name="system_type"], input[name="system_type"]');
    if (await systemTypeField.isVisible()) {
      await expect(systemTypeField).toBeDisabled();
    }
    
    await page.screenshot({ path: 'baselines/simple_heater/options-system-type-preserved.png' });
  });
});