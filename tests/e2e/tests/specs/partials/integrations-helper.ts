import test, { expect, Page } from "@playwright/test";
import { INTEGRATIONS_DASHBOARD_URL, CONFIG_FLOW_DIALOG_SELECTOR, INTEGRATION_SEARCH_SELECTOR, INTEGRATION_CARD_SELECTOR, INTEGRATION_NAME } from "../../../playwright/setup";


export async function startIntegrationConfigFlow(page: Page) {

  await test.step('Start integration config flow', async () => {
    // Navigate to integrations page
    await page.goto(INTEGRATIONS_DASHBOARD_URL);
    await page.waitForLoadState('networkidle');
    console.log('📍 Navigated to integrations page');

    // Find and click "Add Integration" button
    const addButton = page.locator('button:has-text("ADD INTEGRATION"), button:has-text("Add Integration")').first();
    await expect(addButton).toBeVisible({ timeout: 10000 });
    await addButton.click();
    console.log('✅ "Add Integration" button clicked');

    // Wait for dialog to open
    await page.waitForSelector(CONFIG_FLOW_DIALOG_SELECTOR, {
      state: 'visible',
      timeout: 15000
    });
    console.log('✅ Add Integration dialog opened');

    // Find search input and search for integration
    const searchInput = page.locator(INTEGRATION_SEARCH_SELECTOR).first();
    await searchInput.waitFor({ state: 'visible', timeout: 10000 });
    await searchInput.fill('');
    await searchInput.pressSequentially(INTEGRATION_NAME, { delay: 50 });
    console.log(`🔍 Searched for: ${INTEGRATION_NAME}`);

    // Wait for search results and click integration
    //await targetPage.waitForTimeout(2000);
    const integrationCard = page.locator(`${INTEGRATION_CARD_SELECTOR}:has-text("${INTEGRATION_NAME}")`).first();
    await integrationCard.waitFor({ state: 'visible', timeout: 10000 });
    await integrationCard.click();
    console.log(`✅ Clicked ${INTEGRATION_NAME} integration`);

    return page;
  });
}
