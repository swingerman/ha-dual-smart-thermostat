import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../../playwright/setup';

test.describe('Dual Smart Thermostat Config Flow', () => {
  let haSetup: HomeAssistantSetup;

  test.beforeEach(async ({ page }) => {
    haSetup = new HomeAssistantSetup(page);
  });

  test('simple_heater system type - complete config flow', async ({ page }) => {
    // Start the integration setup
    await haSetup.startAddingIntegration('Dual Smart Thermostat');
    
    // Step 1: System type selection (user step)
    await expect(page.locator('h2')).toContainText('System Type Selection');
    await haSetup.selectOptionByLabel('System Type', 'simple_heater');
    await page.screenshot({ path: 'baselines/simple_heater/01-system-type-selection.png' });
    await haSetup.clickNext();

    // Step 2: Basic configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Basic Configuration');
    
    // Fill deterministic values for testing
    await haSetup.fillFieldByLabel('Name', 'Test Simple Heater');
    await haSetup.fillFieldByLabel('Temperature Sensor', 'sensor.test_temperature');
    await haSetup.fillFieldByLabel('Heater', 'switch.test_heater');
    await haSetup.fillFieldByLabel('Cold Tolerance', '0.5');
    await haSetup.fillFieldByLabel('Hot Tolerance', '0.5');
    await haSetup.fillFieldByLabel('Minimum Cycle Duration', '300');
    
    await page.screenshot({ path: 'baselines/simple_heater/02-basic-config.png' });
    await haSetup.clickNext();

    // Step 3: Features selection
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Features');
    
    // For simple heater, select minimal features
    await page.check('input[name="configure_presets"]');
    await page.screenshot({ path: 'baselines/simple_heater/03-features-selection.png' });
    await haSetup.clickNext();

    // Step 4: Preset configuration (since we selected presets)
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Preset');
    
    // Configure basic presets
    await haSetup.fillFieldByLabel('Away Temperature', '16');
    await haSetup.fillFieldByLabel('Sleep Temperature', '18');
    await page.screenshot({ path: 'baselines/simple_heater/04-preset-config.png' });
    await haSetup.clickNext();

    // Wait for completion
    await page.waitForURL('**/config/integrations', { timeout: 30000 });
    await expect(page.locator('.success')).toContainText('Successfully configured');

    // Poll HA REST API for the created config entry
    const api = haSetup.createAPI();
    const configEntry = await api.waitForConfigEntry('dual_smart_thermostat', 'Test Simple Heater');

    // Validate the config entry structure matches data model
    expect(configEntry).toMatchObject({
      domain: 'dual_smart_thermostat',
      title: 'Test Simple Heater',
      data: {
        name: 'Test Simple Heater',
        sensor: 'sensor.test_temperature',
        heater: 'switch.test_heater',
        cold_tolerance: 0.5,
        hot_tolerance: 0.5,
        min_cycle_duration: 300,
        system_type: 'simple_heater'
      }
    });

    // Validate preset options are configured
    expect(configEntry.options).toMatchObject({
      away_temp: 16,
      sleep_temp: 18
    });
  });

  test('simple_heater system type - minimal config (no features)', async ({ page }) => {
    await haSetup.startAddingIntegration('Dual Smart Thermostat');
    
    // System type selection
    await haSetup.selectOptionByLabel('System Type', 'simple_heater');
    await haSetup.clickNext();

    // Basic configuration with minimal values
    await haSetup.fillFieldByLabel('Name', 'Minimal Simple Heater');
    await haSetup.fillFieldByLabel('Temperature Sensor', 'sensor.minimal_temp');
    await haSetup.fillFieldByLabel('Heater', 'switch.minimal_heater');
    await haSetup.clickNext();

    // Features - select none
    await haSetup.clickNext();

    // Should complete without additional steps
    await page.waitForURL('**/config/integrations', { timeout: 30000 });

    // Validate minimal config entry
    const api = haSetup.createAPI();
    const configEntry = await api.waitForConfigEntry('dual_smart_thermostat', 'Minimal Simple Heater');

    expect(configEntry.data).toMatchObject({
      name: 'Minimal Simple Heater',
      sensor: 'sensor.minimal_temp',
      heater: 'switch.minimal_heater',
      system_type: 'simple_heater'
    });

    // Should have minimal or no options
    expect(Object.keys(configEntry.options || {})).toHaveLength(0);
  });

  test('config flow - validation errors', async ({ page }) => {
    await haSetup.startAddingIntegration('Dual Smart Thermostat');
    
    // System type selection
    await haSetup.selectOptionByLabel('System Type', 'simple_heater');
    await haSetup.clickNext();

    // Try to submit without required fields
    await haSetup.clickNext();

    // Should show validation errors
    await expect(page.locator('.error, [role="alert"]')).toBeVisible();
    await expect(page.locator('text=required', { strict: false })).toBeVisible();
    
    await page.screenshot({ path: 'baselines/simple_heater/validation-errors.png' });
  });

  test('config flow - back navigation', async ({ page }) => {
    await haSetup.startAddingIntegration('Dual Smart Thermostat');
    
    // System type selection
    await haSetup.selectOptionByLabel('System Type', 'simple_heater');
    await haSetup.clickNext();

    // Basic config
    await haSetup.fillFieldByLabel('Name', 'Back Navigation Test');
    await haSetup.fillFieldByLabel('Temperature Sensor', 'sensor.test_temp');
    await haSetup.fillFieldByLabel('Heater', 'switch.test_heater');
    await haSetup.clickNext();

    // Go to features, then back
    await page.click('button:has-text("Back")');

    // Should be back at basic config
    await expect(page.locator('h2')).toContainText('Basic Configuration');
    await expect(page.locator('input[name="name"]')).toHaveValue('Back Navigation Test');
  });
});