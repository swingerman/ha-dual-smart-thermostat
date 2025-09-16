import { test, expect } from '@playwright/test';

/**
 * Config Flow E2E Tests for Dual Smart Thermostat
 * 
 * This test suite validates the configuration flow for the Dual Smart Thermostat
 * integration, following TDD approach to ensure the config entry matches the
 * expected data model.
 */

// Expected data model keys for simple_heater system type
const EXPECTED_CONFIG_KEYS = {
  // Core required configuration
  name: 'string',
  heater: 'string', // entity_id
  target_sensor: 'string', // entity_id
  
  // System type
  system_type: 'simple_heater',
  
  // Default tolerances
  cold_tolerance: 'number',
  hot_tolerance: 'number',
  
  // Optional configuration that should be present with defaults
  ac_mode: 'boolean',
  initial_hvac_mode: 'string',
  min_temp: 'number',
  max_temp: 'number',
  target_temp: 'number',
  precision: 'number',
  target_temp_step: 'number',
};

test.describe('Config Flow - Simple Heater', () => {
  
  test.beforeEach(async ({ page }) => {
    // Ensure we're authenticated with Home Assistant
    await page.goto('/');
    
    // Wait for Home Assistant to load
    await page.waitForSelector('[data-panel="lovelace"]', { timeout: 10000 });
  });

  test.skip('should complete simple_heater configuration flow with valid data', async ({ page }) => {
    // NOTE: This test is written following TDD approach
    // The current config_flow.py implementation is minimal and would need
    // enhancement to support the multi-step flow tested here.
    // This test validates what the final implementation should achieve.
    // Navigate to integrations page
    await page.goto('/config/integrations');
    
    // Wait for integrations page to load
    await page.waitForSelector('ha-config-integrations', { timeout: 10000 });
    
    // Click "Add Integration" button
    await page.click('ha-fab[label="Add integration"]');
    
    // Wait for integration selection dialog
    await page.waitForSelector('ha-config-integration-page');
    
    // Search for "Dual Smart Thermostat"
    await page.fill('ha-textfield input', 'Dual Smart Thermostat');
    await page.waitForTimeout(1000); // Wait for search results
    
    // Click on Dual Smart Thermostat integration
    await page.click('text=Dual Smart Thermostat');
    
    // Wait for config flow to start
    await page.waitForSelector('ha-config-flow');
    
    // Step 1: Select system type
    await page.waitForSelector('ha-radio[value="simple_heater"]');
    await page.click('ha-radio[value="simple_heater"]');
    await page.click('mwc-button[label="Submit"]');
    
    // Step 2: Core configuration
    await page.waitForSelector('ha-textfield[label="Name"]');
    
    // Fill in deterministic test values
    await page.fill('ha-textfield[label="Name"] input', 'Test Simple Heater');
    
    // Select heater entity (assume we have a test switch)
    await page.click('ha-entity-picker[label="Heater"] ha-combo-box');
    await page.click('mwc-list-item[value="switch.test_heater"]');
    
    // Select temperature sensor
    await page.click('ha-entity-picker[label="Temperature Sensor"] ha-combo-box');
    await page.click('mwc-list-item[value="sensor.test_temperature"]');
    
    // Set tolerances
    await page.fill('ha-textfield[label="Cold Tolerance"] input', '0.5');
    await page.fill('ha-textfield[label="Hot Tolerance"] input', '0.5');
    
    // Submit core configuration
    await page.click('mwc-button[label="Submit"]');
    
    // Step 3: Advanced options (if present)
    // This step might be optional depending on the flow
    try {
      await page.waitForSelector('ha-textfield[label="Target Temperature"]', { timeout: 3000 });
      await page.fill('ha-textfield[label="Target Temperature"] input', '21');
      await page.click('mwc-button[label="Submit"]');
    } catch {
      // Advanced options step might not be present
    }
    
    // Wait for configuration to complete
    await page.waitForSelector('ha-config-flow-preview', { timeout: 15000 });
    
    // Finish the configuration
    await page.click('mwc-button[label="Finish"]');
    
    // Wait for redirect back to integrations page
    await page.waitForURL('**/config/integrations');
    
    // Verify the integration appears in the list
    await page.waitForSelector('text=Test Simple Heater');
    
    // Get the config entry ID from the page (this would require implementation-specific selectors)
    // For now, we'll use a mock validation approach
    
    // Poll Home Assistant REST API to validate config entry
    await validateConfigEntryViaAPI(page, 'Test Simple Heater');
  });
  
  test.skip('should handle validation errors gracefully', async ({ page }) => {
    // NOTE: This test is written following TDD approach
    // The current config_flow.py implementation is minimal and would need
    // enhancement to support the validation logic tested here.
    // Navigate to integrations page
    await page.goto('/config/integrations');
    
    // Start config flow
    await page.click('ha-fab[label="Add integration"]');
    await page.fill('ha-textfield input', 'Dual Smart Thermostat');
    await page.click('text=Dual Smart Thermostat');
    
    // Select simple_heater
    await page.click('ha-radio[value="simple_heater"]');
    await page.click('mwc-button[label="Submit"]');
    
    // Try to submit without required fields
    await page.click('mwc-button[label="Submit"]');
    
    // Should show validation errors
    await page.waitForSelector('.error, ha-alert[alert-type="error"]');
    
    // Verify specific error messages
    expect(await page.textContent('.error, ha-alert')).toContain('required');
  });

  test('smoke test - should be able to navigate to Home Assistant', async ({ page }) => {
    // This is a basic smoke test to validate the E2E test setup works
    await page.goto('/');
    
    // Should see some Home Assistant UI elements
    // This test will pass if HA is running, or be skipped if not available
    try {
      await page.waitForSelector('body', { timeout: 5000 });
      expect(await page.title()).toBeTruthy();
    } catch (error) {
      test.skip(!process.env.HA_URL, 'Home Assistant not available for testing');
      throw error;
    }
  });

});

/**
 * Validates the config entry via Home Assistant REST API
 */
async function validateConfigEntryViaAPI(page: any, entryTitle: string) {
  // Get authentication token from storage state
  const storageState = await page.context().storageState();
  const haTokens = storageState.origins[0]?.localStorage?.find(
    (item: any) => item.name === 'hassTokens'
  );
  
  if (!haTokens) {
    throw new Error('No authentication token found');
  }
  
  const tokens = JSON.parse(haTokens.value);
  const accessToken = tokens.access_token;
  
  // Make API request to get config entries
  const response = await page.request.get('/api/config/config_entries/entry', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
  
  expect(response.ok()).toBeTruthy();
  
  const configEntries = await response.json();
  
  // Find our config entry
  const ourEntry = configEntries.find((entry: any) => 
    entry.title === entryTitle && entry.domain === 'dual_smart_thermostat'
  );
  
  expect(ourEntry).toBeDefined();
  
  // Validate the config entry data structure
  expect(ourEntry.data).toBeDefined();
  
  // Validate required keys are present with correct types
  for (const [key, expectedType] of Object.entries(EXPECTED_CONFIG_KEYS)) {
    expect(ourEntry.data).toHaveProperty(key);
    
    if (expectedType !== 'simple_heater') { // system_type is a specific string value
      expect(typeof ourEntry.data[key]).toBe(expectedType);
    } else {
      expect(ourEntry.data[key]).toBe(expectedType);
    }
  }
  
  // Validate specific values we set during the test
  expect(ourEntry.data.name).toBe('Test Simple Heater');
  expect(ourEntry.data.heater).toBe('switch.test_heater');
  expect(ourEntry.data.target_sensor).toBe('sensor.test_temperature');
  expect(ourEntry.data.cold_tolerance).toBe(0.5);
  expect(ourEntry.data.hot_tolerance).toBe(0.5);
}