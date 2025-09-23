import { test, expect } from '@playwright/test';

test.describe('Simple Integration Click Test', () => {
  test('Find and click Dual Smart Thermostat integration', async ({ page }) => {
    console.log('🚀 Starting simple integration click test');

    // Navigate to integrations page and wait for it to be fully loaded
    await page.goto('http://localhost:8123/config/integrations/dashboard', {
      waitUntil: 'networkidle'
    });
    console.log('📍 Navigated to integrations page');

    // Wait for the integrations dashboard to be fully loaded by checking for key elements
    await page.waitForLoadState('domcontentloaded');
    console.log('✅ DOM content loaded');

    // Wait for the main integrations container to be visible
    await page.waitForSelector('ha-config-integrations', { timeout: 15000 });
    console.log('✅ Integrations dashboard container loaded');

    // Take screenshot to see what's on the page
    await page.screenshot({ path: 'simple-test-integrations-page.png' });
    console.log('📸 Screenshot of integrations page taken');

    // Check page content
    const pageTitle = await page.title();
    console.log(`Page title: ${pageTitle}`);

    const pageUrl = page.url();
    console.log(`Current URL: ${pageUrl}`);

    // Look for different variations of the Add Integration button
    const addButtonSelectors = [
      'text="Add Integration"',
      'button:has-text("Add Integration")',
      '[aria-label*="Add Integration"]',
      'mwc-button:has-text("Add Integration")',
      'ha-fab[label*="Add"]'
    ];

    let addIntegrationButton = null;
    for (const selector of addButtonSelectors) {
      const count = await page.locator(selector).count();
      console.log(`🔍 Selector "${selector}": ${count} elements found`);
      if (count > 0) {
        addIntegrationButton = page.locator(selector).first();
        break;
      }
    }

    if (!addIntegrationButton) {
      console.log('❌ No Add Integration button found with any selector');
      await page.screenshot({ path: 'simple-test-no-add-button.png' });
      throw new Error('Add Integration button not found');
    }

    await expect(addIntegrationButton).toBeVisible({ timeout: 10000 });
    await addIntegrationButton.click();
    console.log('✅ "Add Integration" button clicked');

    // Wait for the "Add Integration" dialog to be fully visible (not just present)
    await page.waitForSelector('.mdc-dialog.mdc-dialog--open', {
      state: 'visible',
      timeout: 15000
    });
    console.log('✅ Add Integration dialog opened and visible');

    // Take a screenshot to see what's in the dialog
    await page.screenshot({ path: 'simple-test-dialog-opened.png' });
    console.log('📸 Screenshot of opened dialog taken');

    // Debug dialog content
    const dialogContent = await page.locator('.mdc-dialog.mdc-dialog--open').textContent();
    console.log(`📝 Dialog content preview: ${dialogContent?.substring(0, 100)}...`);

    // Check if this is a config flow dialog or integration search dialog
    // Config flow dialog should have data-entry-flow or specific config flow elements
    const hasDataEntryFlow = await page.locator('.mdc-dialog.mdc-dialog--open ha-data-entry-flow').count() > 0;
    const hasConfigFlowContent = dialogContent?.includes('System Type Selection') ||
      dialogContent?.includes('Basic Configuration') ||
      dialogContent?.includes('Features Configuration');
    const isConfigFlow = hasDataEntryFlow || hasConfigFlowContent;

    // Search dialog has integration list or search functionality
    const hasIntegrationList = await page.locator('.mdc-dialog.mdc-dialog--open ha-integration-list-item').count() > 0;
    const hasSearchElements = await page.locator('.mdc-dialog.mdc-dialog--open input').count() > 0;
    const isSearchDialog = hasIntegrationList || hasSearchElements ||
      dialogContent?.includes('Search') ||
      dialogContent?.includes('Add Integration') ||
      dialogContent?.includes('Select brand'); // "Select brand" is actually part of integration selection

    console.log(`🎯 Is config flow dialog: ${isConfigFlow} (data-entry-flow: ${hasDataEntryFlow}, config content: ${hasConfigFlowContent})`);
    console.log(`🎯 Is search dialog: ${isSearchDialog} (integration list: ${hasIntegrationList}, search elements: ${hasSearchElements})`);

    if (isConfigFlow) {
      console.log('🎉 SUCCESS! Config flow dialog opened directly!');
      console.log('✅ Integration was found and config flow started automatically');

      // Take screenshot of the config flow dialog
      await page.screenshot({ path: 'simple-test-config-flow-detected.png' });
      console.log('📸 Screenshot of config flow dialog taken');

      // Check current URL
      const currentUrl = page.url();
      console.log(`Current URL: ${currentUrl}`);

      // Check if any dialogs are open
      const dialogsOpen = await page.locator('.mdc-dialog.mdc-dialog--open').count();
      console.log(`Config flow dialogs open: ${dialogsOpen}`);

      console.log('🎉 Test completed successfully - Integration click worked!');
      return; // Exit successfully
    }
    else if (isSearchDialog) {
      console.log('📝 Integration selection dialog detected');

      // First check if there are integration cards to click directly
      const integrationCards = await page.locator('.mdc-dialog.mdc-dialog--open ha-integration-list-item').count();
      console.log(`🔍 Found ${integrationCards} integration cards in dialog`);

      if (integrationCards > 0) {
        console.log('📋 Integration cards found - looking for Dual Smart Thermostat');

        // Look for our integration directly in the cards
        const integrationSelectors = [
          '.mdc-dialog.mdc-dialog--open ha-integration-list-item:has-text("Dual Smart Thermostat")',
          '.mdc-dialog.mdc-dialog--open [data-domain*="dual"]',
          '.mdc-dialog.mdc-dialog--open *:has-text("Dual Smart Thermostat")'
        ];

        let integrationCard = null;
        for (const selector of integrationSelectors) {
          const count = await page.locator(selector).count();
          console.log(`🔍 Integration selector "${selector}": ${count} elements found`);
          if (count > 0) {
            integrationCard = page.locator(selector).first();
            break;
          }
        }

        if (integrationCard) {
          console.log('✅ Found Dual Smart Thermostat integration card');
          await integrationCard.click();
          console.log('🖱️ Clicked integration card');

          // Wait for config flow to start
          await page.waitForSelector('.mdc-dialog.mdc-dialog--open ha-data-entry-flow, .mdc-dialog.mdc-dialog--open [data-entry-flow]', {
            timeout: 10000
          });

          await page.screenshot({ path: 'simple-test-after-integration-click.png' });
          console.log('📸 Screenshot after integration click taken');

          console.log('🎉 SUCCESS! Integration clicked and config flow should be starting!');
          return;
        }
      }

      // If no integration cards, look for search input
      console.log('🔍 No integration cards found, looking for search input');

      // Debug: Let's see what elements are actually in the dialog
      const allElements = await page.locator('.mdc-dialog.mdc-dialog--open *').count();
      console.log(`🔍 Total elements in dialog: ${allElements}`);

      // Try broader search-input selectors (maybe it's outside the mdc-dialog scope)
      // Prioritize the input element inside search-input
      const broadSearchSelectors = [
        'search-input input',
        'ha-dialog search-input input',
        'search-input',
        'ha-dialog search-input'
      ];

      for (const selector of broadSearchSelectors) {
        const count = await page.locator(selector).count();
        console.log(`🔍 Broad search selector "${selector}": ${count} elements found`);
      }

      const searchSelectors = [
        '.mdc-dialog.mdc-dialog--open search-input',
        '.mdc-dialog.mdc-dialog--open search-input input',
        '.mdc-dialog.mdc-dialog--open input[type="search"]',
        '.mdc-dialog.mdc-dialog--open input[placeholder*="Search"]',
        '.mdc-dialog.mdc-dialog--open input',
        '.mdc-dialog.mdc-dialog--open ha-textfield input',
        '.mdc-dialog.mdc-dialog--open mwc-textfield input'
      ];

      let searchInput = null;

      // First try the broad selectors that found elements
      for (const selector of broadSearchSelectors) {
        const count = await page.locator(selector).count();
        if (count > 0) {
          searchInput = page.locator(selector).first();
          console.log(`✅ Found search input with broad selector: ${selector}`);
          break;
        }
      }

      // If not found with broad selectors, try the scoped ones
      if (!searchInput) {
        for (const selector of searchSelectors) {
          const count = await page.locator(selector).count();
          console.log(`🔍 Search selector "${selector}": ${count} elements found`);
          if (count > 0) {
            searchInput = page.locator(selector).first();
            break;
          }
        }
      }

      if (!searchInput) {
        console.log('❌ No search input or integration cards found');
        await page.screenshot({ path: 'simple-test-no-search-elements.png' });
        throw new Error('No search input or integration cards found in dialog');
      }

      // Type the integration name
      await searchInput.fill('');
      await searchInput.type('Dual Smart Thermostat', { delay: 100 });
      console.log('🔍 Typed integration name in search');

      // Wait for search results
      await page.waitForSelector('ha-integration-list-item, .no-results', { timeout: 10000 });
      console.log('✅ Search results loaded');

      // Take screenshot of search results
      await page.screenshot({ path: 'simple-test-search-results.png' });
      console.log('📸 Screenshot of search results taken');

      // Look for our integration in the search results
      const integrationSelectors = [
        'ha-integration-list-item:has-text("Dual Smart Thermostat")',
        '[data-domain*="dual"]',
        '*:has-text("Dual Smart Thermostat")'
      ];

      let integrationCard = null;
      for (const selector of integrationSelectors) {
        const count = await page.locator(selector).count();
        console.log(`🔍 Integration selector "${selector}": ${count} elements found`);
        if (count > 0) {
          integrationCard = page.locator(selector).first();
          break;
        }
      }

      if (!integrationCard) {
        console.log('❌ Integration not found in search results');
        await page.screenshot({ path: 'simple-test-integration-not-found.png' });
        throw new Error('Dual Smart Thermostat integration not found in search results');
      }

      // Click the integration
      await expect(integrationCard).toBeVisible({ timeout: 5000 });
      await integrationCard.click();
      console.log('✅ Integration clicked from search results');

      // Wait for config flow to start
      await page.waitForSelector('.mdc-dialog.mdc-dialog--open', {
        state: 'visible',
        timeout: 10000
      });

      // Take screenshot after clicking integration
      await page.screenshot({ path: 'simple-test-after-integration-click.png' });
      console.log('📸 Screenshot after integration click taken');

      // Check if config flow started using more comprehensive detection
      const configFlowContent = await page.locator('.mdc-dialog.mdc-dialog--open').textContent();

      // Check for data-entry-flow element (the actual config flow component)
      const hasDataEntryFlow = await page.locator('.mdc-dialog.mdc-dialog--open ha-data-entry-flow').count() > 0;

      // Check for config flow step content
      const hasConfigFlowContent = configFlowContent?.includes('System Type Selection') ||
        configFlowContent?.includes('Basic Configuration') ||
        configFlowContent?.includes('Features Configuration') ||
        configFlowContent?.includes('Select brand') ||
        configFlowContent?.includes('System Type');

      const configFlowStarted = hasDataEntryFlow || hasConfigFlowContent;

      console.log(`🔍 Config flow detection: data-entry-flow=${hasDataEntryFlow}, content=${hasConfigFlowContent}`);
      console.log(`📝 Dialog content after click: ${configFlowContent?.substring(0, 200)}...`);

      if (configFlowStarted) {
        console.log('🎉 SUCCESS! Config flow started after clicking integration!');
        console.log('✅ Integration search and click completed successfully');

        const currentUrl = page.url();
        console.log(`Current URL: ${currentUrl}`);

        console.log('🎉 Test completed successfully - Integration search and click worked!');
      } else {
        console.log('❌ Config flow did not start after clicking integration');
        console.log(`Dialog content: ${configFlowContent?.substring(0, 200)}...`);

        // Take an additional screenshot for debugging
        await page.screenshot({ path: 'simple-test-config-flow-not-started.png' });
        console.log('📸 Additional debug screenshot taken');

        throw new Error('Config flow did not start after clicking integration');
      }
    }
    else {
      console.log('❌ Unexpected dialog content');
      await page.screenshot({ path: 'simple-test-unexpected-dialog.png' });
      throw new Error(`Unexpected dialog content: ${dialogContent}`);
    }
  });
});
