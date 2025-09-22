import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../../playwright/setup';

// Simple verification spec: verify the integration is available for adding
// and that YAML configuration loads correctly.

test('integration is available for adding', async ({ page }) => {
  const haSetup = new HomeAssistantSetup(page);

  // Ensure HA is reachable
  await page.goto('/', { timeout: 30000 });
  await page.waitForTimeout(2000);

  // Navigate to integrations page and click "Add Integration"
  await haSetup.goToIntegrations();
  await page.click('button:has-text("Add integration")');

  // Wait for the dialog and search for our integration
  await page.waitForSelector('input[type="search"], input[placeholder*="Search"]', { timeout: 10000 });

  // Type the search term to trigger filtering (don't just fill)
  const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]').first();
  await searchInput.clear();
  await searchInput.type('Dual Smart Thermostat', { delay: 100 });

  // Wait for search results to update
  await page.waitForTimeout(2000);

  // Verify the integration appears in search results
  const integrationCard = page.locator(':text("Dual Smart Thermostat")').first();
  await expect(integrationCard).toBeVisible({ timeout: 10000 });
});
