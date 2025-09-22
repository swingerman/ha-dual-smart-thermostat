import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../../playwright/setup';

test.describe('AC-Only Config Flow', () => {
  let haSetup: HomeAssistantSetup;

  test.beforeEach(async ({ page }) => {
    // Navigate to Home Assistant and prepare for config flow
    await page.goto('/', { timeout: 30000 });
    await page.waitForTimeout(2000);

    haSetup = new HomeAssistantSetup(page);
    // Prepare integration for config flow testing (will start config flow if not already configured)
    await haSetup.ensureIntegrationReadyForConfigFlow('Dual Smart Thermostat', 'dual_smart_thermostat');
  });

  test('ac_only system type - complete config flow with features', async ({ page }) => {
    // The beforeEach already started the config flow if needed
    // Step 1: System type selection
    await expect(page.locator('h2')).toContainText('System Type Selection');
    await haSetup.selectOptionByLabel('System Type', 'ac_only');
    await page.screenshot({ path: 'baselines/ac_only/01-system-type-selection.png' });
    await haSetup.clickNext();

    // Step 2: Basic configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Basic Configuration');

    await haSetup.fillFieldByLabel('Name', 'Test AC Only');
    await haSetup.fillFieldByLabel('Temperature Sensor', 'sensor.test_temperature');
    await haSetup.fillFieldByLabel('Cooler', 'switch.test_ac');
    await haSetup.fillFieldByLabel('Cold Tolerance', '0.5');
    await haSetup.fillFieldByLabel('Hot Tolerance', '0.5');

    await page.screenshot({ path: 'baselines/ac_only/02-basic-config.png' });
    await haSetup.clickNext();

    // Step 3: AC Features selection
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('AC Features');

    // Select multiple AC features
    await page.check('input[name="configure_fan"]');
    await page.check('input[name="configure_humidity"]');
    await page.check('input[name="configure_openings"]');
    await page.check('input[name="configure_presets"]');

    await page.screenshot({ path: 'baselines/ac_only/03-ac-features-selection.png' });
    await haSetup.clickNext();

    // Step 4: Fan configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Fan');

    await haSetup.fillFieldByLabel('Fan Entity', 'fan.test_fan');
    await page.check('input[name="fan_on_with_ac"]');

    await page.screenshot({ path: 'baselines/ac_only/04-fan-config.png' });
    await haSetup.clickNext();

    // Step 5: Humidity configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Humidity');

    await haSetup.fillFieldByLabel('Humidity Sensor', 'sensor.test_humidity');
    await haSetup.fillFieldByLabel('Target Humidity', '50');

    await page.screenshot({ path: 'baselines/ac_only/05-humidity-config.png' });
    await haSetup.clickNext();

    // Step 6: Openings configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Openings');

    await haSetup.fillFieldByLabel('Door/Window Sensors', 'binary_sensor.test_door');

    await page.screenshot({ path: 'baselines/ac_only/06-openings-config.png' });
    await haSetup.clickNext();

    // Step 7: Presets configuration
    await haSetup.waitForStep();
    await expect(page.locator('h2')).toContainText('Presets');

    await haSetup.fillFieldByLabel('Away Temperature', '28');
    await haSetup.fillFieldByLabel('Sleep Temperature', '26');

    await page.screenshot({ path: 'baselines/ac_only/07-presets-config.png' });
    await haSetup.clickNext();

    // Wait for completion
    await page.waitForURL('**/config/integrations', { timeout: 30000 });
    await expect(page.locator('.success')).toContainText('Successfully configured');

    // Validate config entry via API
    const api = haSetup.createAPI();
    const configEntry = await api.waitForConfigEntry('dual_smart_thermostat', 'Test AC Only');

    expect(configEntry.data).toMatchObject({
      name: 'Test AC Only',
      sensor: 'sensor.test_temperature',
      ac_mode: 'switch.test_ac',
      system_type: 'ac_only'
    });

    expect(configEntry.options).toMatchObject({
      fan_entity: 'fan.test_fan',
      fan_on_with_ac: true,
      humidity_sensor: 'sensor.test_humidity',
      target_humidity: 50,
      openings: 'binary_sensor.test_door',
      away_temp: 28,
      sleep_temp: 26
    });
  });

  test('ac_only system type - minimal config', async ({ page }) => {
    // The beforeEach already started the config flow if needed
    // System type selection
    await haSetup.selectOptionByLabel('System Type', 'ac_only');
    await haSetup.clickNext();

    // Basic configuration - minimal
    await haSetup.fillFieldByLabel('Name', 'Minimal AC Only');
    await haSetup.fillFieldByLabel('Temperature Sensor', 'sensor.minimal_temp');
    await haSetup.fillFieldByLabel('Cooler', 'switch.minimal_ac');
    await haSetup.clickNext();

    // AC Features - select none
    await haSetup.clickNext();

    // Should complete without additional steps
    await page.waitForURL('**/config/integrations', { timeout: 30000 });

    // Validate minimal config
    const api = haSetup.createAPI();
    const configEntry = await api.waitForConfigEntry('dual_smart_thermostat', 'Minimal AC Only');

    expect(configEntry.data).toMatchObject({
      name: 'Minimal AC Only',
      sensor: 'sensor.minimal_temp',
      ac_mode: 'switch.minimal_ac',
      system_type: 'ac_only'
    });

    // Should have no or minimal options
    expect(Object.keys(configEntry.options || {})).toHaveLength(0);
  });
});