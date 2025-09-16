import { test, expect } from '@playwright/test';

/**
 * Options Flow E2E Tests for Dual Smart Thermostat
 * 
 * This test suite validates the options flow for existing Dual Smart Thermostat
 * configurations, allowing users to modify advanced settings post-installation.
 */

// Expected options that can be modified
const EXPECTED_OPTIONS = {
  // Temperature settings
  min_temp: 'number',
  max_temp: 'number',
  target_temp_step: 'number',
  precision: 'number',
  
  // Tolerance settings
  cold_tolerance: 'number',
  hot_tolerance: 'number',
  
  // HVAC behavior
  keep_alive: 'number', // seconds
  min_cycle_duration: 'number', // seconds
  
  // Advanced features
  ac_mode: 'boolean',
  initial_hvac_mode: 'string',
};

test.describe('Options Flow', () => {
  
  let configEntryId: string;
  
  test.beforeEach(async ({ page }) => {
    // Ensure we're authenticated
    await page.goto('/');
    await page.waitForSelector('[data-panel="lovelace"]', { timeout: 10000 });
    
    // Set up a test integration if it doesn't exist
    await ensureTestIntegrationExists(page);
  });

  test.skip('should open options flow and modify temperature settings', async ({ page }) => {
    // NOTE: This test is written following TDD approach
    // The current implementation doesn't include options flow yet.
    // Navigate to integrations page
    await page.goto('/config/integrations');
    await page.waitForSelector('ha-config-integrations');
    
    // Find our test integration
    const integrationCard = page.locator('.integration-card').filter({ 
      hasText: 'Test Simple Heater' 
    });
    await expect(integrationCard).toBeVisible();
    
    // Click the options menu
    await integrationCard.locator('ha-button-menu').click();
    
    // Click "Configure" or "Options"
    await page.click('mwc-list-item:has-text("Configure")');
    
    // Wait for options flow to open
    await page.waitForSelector('ha-config-flow');
    
    // Modify temperature range
    await page.fill('ha-textfield[label="Minimum Temperature"] input', '10');
    await page.fill('ha-textfield[label="Maximum Temperature"] input', '30');
    await page.fill('ha-textfield[label="Temperature Step"] input', '0.5');
    
    // Submit changes
    await page.click('mwc-button[label="Submit"]');
    
    // Wait for completion
    await page.waitForSelector('ha-config-flow-preview');
    await page.click('mwc-button[label="Finish"]');
    
    // Validate changes via API
    await validateOptionsViaAPI(page, {
      min_temp: 10,
      max_temp: 30,
      target_temp_step: 0.5,
    });
  });
  
  test.skip('should modify tolerance settings', async ({ page }) => {
    // NOTE: TDD approach - test written before implementation
    await page.goto('/config/integrations');
    await page.waitForSelector('ha-config-integrations');
    
    // Open options for our test integration
    const integrationCard = page.locator('.integration-card').filter({ 
      hasText: 'Test Simple Heater' 
    });
    await integrationCard.locator('ha-button-menu').click();
    await page.click('mwc-list-item:has-text("Configure")');
    
    await page.waitForSelector('ha-config-flow');
    
    // Navigate to tolerance settings (might be on a different step)
    try {
      await page.click('mwc-button[label="Next"]');
      await page.waitForSelector('ha-textfield[label="Cold Tolerance"]');
    } catch {
      // Tolerance settings might be on the first page
    }
    
    // Modify tolerances
    await page.fill('ha-textfield[label="Cold Tolerance"] input', '1.0');
    await page.fill('ha-textfield[label="Hot Tolerance"] input', '1.5');
    
    await page.click('mwc-button[label="Submit"]');
    await page.waitForSelector('ha-config-flow-preview');
    await page.click('mwc-button[label="Finish"]');
    
    // Validate changes
    await validateOptionsViaAPI(page, {
      cold_tolerance: 1.0,
      hot_tolerance: 1.5,
    });
  });
  
  test.skip('should modify HVAC behavior settings', async ({ page }) => {
    // NOTE: TDD approach - test written before implementation
    await page.goto('/config/integrations');
    await page.waitForSelector('ha-config-integrations');
    
    // Open options
    const integrationCard = page.locator('.integration-card').filter({ 
      hasText: 'Test Simple Heater' 
    });
    await integrationCard.locator('ha-button-menu').click();
    await page.click('mwc-list-item:has-text("Configure")');
    
    await page.waitForSelector('ha-config-flow');
    
    // Navigate to HVAC behavior settings
    try {
      // Look for advanced settings section
      while (!(await page.isVisible('ha-textfield[label="Keep Alive"]'))) {
        await page.click('mwc-button[label="Next"]');
        await page.waitForTimeout(1000);
      }
    } catch {
      // Settings might be on current page
    }
    
    // Modify HVAC behavior
    await page.fill('ha-textfield[label="Keep Alive"] input', '300'); // 5 minutes
    await page.fill('ha-textfield[label="Minimum Cycle Duration"] input', '180'); // 3 minutes
    
    // Toggle AC mode if present
    try {
      await page.click('ha-switch[label="AC Mode"]');
    } catch {
      // AC mode toggle might not be present
    }
    
    await page.click('mwc-button[label="Submit"]');
    await page.waitForSelector('ha-config-flow-preview');
    await page.click('mwc-button[label="Finish"]');
    
    // Validate changes
    await validateOptionsViaAPI(page, {
      keep_alive: 300,
      min_cycle_duration: 180,
    });
  });
  
  test.skip('should validate input ranges and show errors', async ({ page }) => {
    // NOTE: TDD approach - test written before implementation
    await page.goto('/config/integrations');
    await page.waitForSelector('ha-config-integrations');
    
    // Open options
    const integrationCard = page.locator('.integration-card').filter({ 
      hasText: 'Test Simple Heater' 
    });
    await integrationCard.locator('ha-button-menu').click();
    await page.click('mwc-list-item:has-text("Configure")');
    
    await page.waitForSelector('ha-config-flow');
    
    // Try to set invalid temperature range (min > max)
    await page.fill('ha-textfield[label="Minimum Temperature"] input', '25');
    await page.fill('ha-textfield[label="Maximum Temperature"] input', '20');
    
    await page.click('mwc-button[label="Submit"]');
    
    // Should show validation error
    await page.waitForSelector('.error, ha-alert[alert-type="error"]');
    expect(await page.textContent('.error, ha-alert')).toContain('minimum');
  });

});

/**
 * Ensures a test integration exists for options testing
 */
async function ensureTestIntegrationExists(page: any) {
  // Check if integration already exists
  await page.goto('/config/integrations');
  
  try {
    // Look for existing test integration
    await page.waitForSelector('text=Test Simple Heater', { timeout: 3000 });
    return; // Integration already exists
  } catch {
    // Need to create the integration
    await createTestIntegration(page);
  }
}

/**
 * Creates a test integration for options testing
 */
async function createTestIntegration(page: any) {
  // Add new integration
  await page.click('ha-fab[label="Add integration"]');
  await page.fill('ha-textfield input', 'Dual Smart Thermostat');
  await page.click('text=Dual Smart Thermostat');
  
  // Quick setup with minimal config
  await page.click('ha-radio[value="simple_heater"]');
  await page.click('mwc-button[label="Submit"]');
  
  await page.fill('ha-textfield[label="Name"] input', 'Test Simple Heater');
  await page.click('ha-entity-picker[label="Heater"] ha-combo-box');
  await page.click('mwc-list-item[value="switch.test_heater"]');
  await page.click('ha-entity-picker[label="Temperature Sensor"] ha-combo-box');
  await page.click('mwc-list-item[value="sensor.test_temperature"]');
  
  await page.click('mwc-button[label="Submit"]');
  await page.waitForSelector('ha-config-flow-preview');
  await page.click('mwc-button[label="Finish"]');
  
  await page.waitForURL('**/config/integrations');
}

/**
 * Validates options changes via Home Assistant REST API
 */
async function validateOptionsViaAPI(page: any, expectedOptions: Record<string, any>) {
  // Get authentication token
  const storageState = await page.context().storageState();
  const haTokens = storageState.origins[0]?.localStorage?.find(
    (item: any) => item.name === 'hassTokens'
  );
  
  if (!haTokens) {
    throw new Error('No authentication token found');
  }
  
  const tokens = JSON.parse(haTokens.value);
  const accessToken = tokens.access_token;
  
  // Get config entries
  const response = await page.request.get('/api/config/config_entries/entry', {
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
  });
  
  expect(response.ok()).toBeTruthy();
  const configEntries = await response.json();
  
  // Find our test entry
  const ourEntry = configEntries.find((entry: any) => 
    entry.title === 'Test Simple Heater' && entry.domain === 'dual_smart_thermostat'
  );
  
  expect(ourEntry).toBeDefined();
  
  // Validate the options were updated
  for (const [key, expectedValue] of Object.entries(expectedOptions)) {
    expect(ourEntry.options).toHaveProperty(key);
    expect(ourEntry.options[key]).toBe(expectedValue);
  }
}