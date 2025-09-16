import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('Home Assistant is accessible', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Home Assistant/);
    
    // Check that the main Home Assistant interface is loaded
    await expect(page.locator('home-assistant-main')).toBeVisible();
  });

  test('Integrations page is accessible', async ({ page }) => {
    await page.goto('/config/integrations');
    
    // Check that integrations page loads
    await expect(page.locator('ha-config-integrations')).toBeVisible();
    
    // Check for the "Add Integration" button
    await expect(page.locator('[data-testid="add-integration"], .add-integration, button:text("Add Integration")')).toBeVisible();
  });

  test('Test entities are available', async ({ page }) => {
    await page.goto('/developer-tools/states');
    
    // Wait for the states page to load
    await page.waitForSelector('ha-dev-states');
    
    // Check that our test entities exist
    const entities = [
      'sensor.room_temp',
      'switch.heater',
      'switch.cooler',
      'binary_sensor.window',
      'climate.e2e_test_thermostat'
    ];
    
    for (const entity of entities) {
      // Search for the entity
      await page.fill('input[placeholder*="Filter"]', entity);
      
      // Expect to find the entity in the list
      await expect(page.locator(`tr:has-text("${entity}")`)).toBeVisible({ timeout: 5000 });
      
      // Clear the filter for next entity
      await page.fill('input[placeholder*="Filter"]', '');
    }
  });

  test('Dual smart thermostat entity is working', async ({ page }) => {
    await page.goto('/developer-tools/states');
    
    // Wait for the states page to load
    await page.waitForSelector('ha-dev-states');
    
    // Filter for our thermostat
    await page.fill('input[placeholder*="Filter"]', 'climate.e2e_test_thermostat');
    
    // Check that the thermostat entity exists and has expected attributes
    const thermostatRow = page.locator('tr:has-text("climate.e2e_test_thermostat")');
    await expect(thermostatRow).toBeVisible();
    
    // Click on the thermostat to see its attributes
    await thermostatRow.click();
    
    // Check for dual smart thermostat specific attributes
    const attributesPanel = page.locator('.attributes');
    await expect(attributesPanel).toContainText('hvac_modes');
    await expect(attributesPanel).toContainText('temperature');
  });
});