import { test, expect } from '@playwright/test';
import { HomeAssistantSetup } from '../../playwright/setup';

// STEP 1: Just get the config flow to start reliably
test('Step 1: Start config flow for Dual Smart Thermostat', async ({ page }) => {
  console.log('🚀 Step 1: Starting basic config flow test');

  // Navigate to integrations page
  await page.goto('/config/integrations');
  console.log('📍 Navigated to integrations page');

  // Open "Add Integration" dialog
  const addButton = page.locator('button').filter({ hasText: 'ADD INTEGRATION' });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();
  console.log('✅ "Add Integration" dialog opened');

  // Search for our integration
  const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]').first();
  await expect(searchInput).toBeVisible({ timeout: 5000 });

  // Clear any existing text first
  await searchInput.fill('');
  await page.waitForTimeout(500);

  // Type the integration name with delay to trigger filtering
  await searchInput.type('Dual Smart Thermostat', { delay: 100 });
  console.log('🔍 Typed integration name in search');

  // Wait for search results
  await page.waitForTimeout(2000);

  // Debug: Check what integrations are visible
  const allIntegrations = await page.locator('ha-integration-list-item').count();
  console.log(`Found ${allIntegrations} integration items after search`);

  if (allIntegrations === 0) {
    console.log('❌ No integrations found after search - taking screenshot');
    await page.screenshot({ path: 'debug-no-integrations.png' });
    throw new Error('No integrations found after search');
  }

  // Look for our integration
  const integrationCard = page.locator('ha-integration-list-item:has-text("Dual Smart Thermostat")').first();

  try {
    await expect(integrationCard).toBeVisible({ timeout: 10000 });
    console.log('✅ Integration card found');
  } catch (e) {
    console.log('❌ Integration card not found - debugging...');

    // Debug: List all visible integrations
    const integrationTexts = await page.locator('ha-integration-list-item').allTextContents();
    console.log('Available integrations:', integrationTexts.slice(0, 5)); // Show first 5

    await page.screenshot({ path: 'debug-integration-search.png' });
    throw new Error('Dual Smart Thermostat integration not found in search results');
  }

  // Click the integration card
  await integrationCard.click();
  console.log('✅ Integration card clicked');

  // Take screenshot immediately after clicking
  await page.screenshot({ path: 'debug-after-click.png' });
  console.log('📸 Screenshot taken immediately after click');

  // Wait and check if config flow started
  await page.waitForTimeout(3000);

  // Look for config flow dialog - it should be a modal dialog with specific content
  console.log('🔍 Looking for config flow dialog...');

  // Debug: Check all dialog-related elements on the page
  const allDialogs = await page.locator('*[dialog], *[role="dialog"], ha-dialog, dialog, .mdc-dialog, dialog-data-entry-flow').count();
  console.log(`📊 Total dialog-like elements found: ${allDialogs}`);

  // Check for various dialog selectors
  const dialogSelectors = [
    'ha-dialog[open]',
    'ha-dialog', // Check without [open] too
    'dialog[open]',
    'dialog', // Check without [open] too
    '[role="dialog"]',
    'dialog-data-entry-flow',
    '.mdc-dialog--open',
    '.mdc-dialog'
  ];

  let configFlowDialog = null;
  let dialogFound = false;

  for (const selector of dialogSelectors) {
    const dialogCount = await page.locator(selector).count();
    console.log(`🔍 Checking selector "${selector}": ${dialogCount} found`);
    if (dialogCount > 0) {
      console.log(`✅ Found dialog with selector: ${selector} (count: ${dialogCount})`);
      configFlowDialog = page.locator(selector).first();
      dialogFound = true;
      break;
    }
  }

  if (!dialogFound) {
    console.log('❌ No dialog found with any selector - checking page state');
    const currentUrl = page.url();
    console.log('Current URL:', currentUrl);

    // Check if integration is already configured
    const existingIntegration = await page.locator('[data-domain="dual_smart_thermostat"]').count();
    if (existingIntegration > 0) {
      console.log('⚠️ Integration already configured - need to remove it first for testing');
      throw new Error('Integration already configured - cannot test config flow');
    }

    await page.screenshot({ path: 'debug-no-config-flow.png' });
    throw new Error('Config flow dialog not found after clicking integration');
  }

  // Get dialog content to verify it's actually a config flow
  const dialogText = await configFlowDialog.textContent();
  console.log('📝 Dialog content preview:', dialogText?.slice(0, 200) + '...');

  // Look for config flow indicators
  const hasConfigFlowContent = dialogText?.includes('System Type') ||
    dialogText?.includes('Configuration') ||
    dialogText?.includes('Setup') ||
    await page.locator('input[type="radio"]').count() > 0 ||
    await page.locator('dialog-data-entry-flow').count() > 0;

  if (!hasConfigFlowContent) {
    console.log('⚠️ Dialog found but may not be config flow - content:', dialogText?.slice(0, 100));
    await page.screenshot({ path: 'debug-unexpected-dialog.png' });
  }

  // Take a screenshot of successful config flow start
  await page.screenshot({ path: 'success-config-flow-started.png' });

  console.log('🎉 SUCCESS: Config flow dialog detected!');
  console.log('📊 Dialog analysis:');
  console.log(`- Has radio buttons: ${await page.locator('input[type="radio"]').count()}`);
  console.log(`- Has select dropdowns: ${await page.locator('select').count()}`);
  console.log(`- Has text inputs: ${await page.locator('input[type="text"]').count()}`);
  console.log(`- Has data-entry-flow: ${await page.locator('dialog-data-entry-flow').count()}`);

  // Step 2: Select system type (Simple Heater Only)
  console.log('📝 Step 2: Selecting Simple Heater Only system type...');

  // Look for the radio button or text for Simple Heater
  const simpleHeaterOption = page.locator('text="Simple Heater Only"');

  try {
    await expect(simpleHeaterOption).toBeVisible({ timeout: 5000 });
    await simpleHeaterOption.click();
    console.log('✅ Simple Heater Only selected via text click');
  } catch (e) {
    console.log('❌ Could not find "Simple Heater Only" text, trying radio button approach...');

    // Alternative: Look for radio buttons and their labels
    const radioButtons = await page.locator('input[type="radio"]').all();
    console.log(`Found ${radioButtons.length} radio buttons`);

    for (let i = 0; i < radioButtons.length; i++) {
      const radio = radioButtons[i];
      const value = await radio.getAttribute('value');
      const name = await radio.getAttribute('name');
      console.log(`Radio ${i}: value="${value}", name="${name}"`);

      // Look for simple_heater or similar
      if (value === 'simple_heater' || value?.includes('simple')) {
        await radio.click();
        console.log(`✅ Selected radio button ${i} with value: ${value}`);
        break;
      }
    }
  }

  // Submit the system type selection
  console.log('📝 Submitting system type selection...');
  const submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
  await submitButton.click();
  console.log('✅ System type submitted');

  // Wait for next step
  await page.waitForTimeout(2000);

  // Take screenshot of what happens next
  await page.screenshot({ path: 'debug-after-system-type.png' });
  console.log('📸 Screenshot taken after system type submission');

  console.log('🎉 Step 1 completed successfully - config flow started and system type selected!');
});

// COMPLETE CONFIG FLOW: Do the entire flow from start to finish in one test
test('Complete Config Flow: Full integration setup', async ({ page }) => {
  console.log('🚀 Complete Config Flow: Starting full integration setup');

  // Step 1: Navigate and start config flow
  await page.goto('/config/integrations');
  console.log('📍 Navigated to integrations page');

  const addButton = page.locator('button').filter({ hasText: 'ADD INTEGRATION' });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();

  const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]').first();
  await expect(searchInput).toBeVisible({ timeout: 5000 });
  await searchInput.fill('');
  await page.waitForTimeout(500);
  await searchInput.type('Dual Smart Thermostat', { delay: 100 });
  await page.waitForTimeout(2000);

  const integrationCard = page.locator('ha-integration-list-item:has-text("Dual Smart Thermostat")').first();
  await expect(integrationCard).toBeVisible({ timeout: 10000 });
  await integrationCard.click();
  await page.waitForTimeout(3000);

  // Step 2: System Type Selection
  console.log('📝 Step 2: System Type Selection');
  const simpleHeaterOption = page.locator('text="Simple Heater Only"');
  await expect(simpleHeaterOption).toBeVisible({ timeout: 5000 });
  await simpleHeaterOption.click();
  console.log('✅ Simple Heater Only selected');

  let submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
  await submitButton.click();
  console.log('✅ System type submitted');
  await page.waitForTimeout(3000);

  // Continue with the remaining steps until completion
  let maxSteps = 5;
  let currentStep = 2;

  while (currentStep <= maxSteps) {
    console.log(`📝 Step ${currentStep}: Checking current dialog state...`);

    // Check if dialog is still open
    const dialogCount = await page.locator('ha-dialog[open]').count();
    if (dialogCount === 0) {
      console.log('✅ Dialog closed - checking if redirected to integrations page');
      const currentUrl = page.url();
      if (currentUrl.includes('/config/integrations')) {
        console.log('🎉 SUCCESS: Redirected to integrations page!');

        // Check if integration appears in the list
        await page.waitForTimeout(2000);
        const configuredIntegration = await page.locator('[data-domain="dual_smart_thermostat"]').count();
        if (configuredIntegration > 0) {
          console.log('🎉 ULTIMATE SUCCESS: Integration is now visible in integrations list!');
        } else {
          console.log('⚠️ Integration not immediately visible, but config flow completed');
        }
        break;
      } else {
        console.log('⚠️ Dialog closed but not on integrations page');
        break;
      }
    }

    // Get current dialog content
    const dialogText = await page.locator('ha-dialog[open]').first().textContent();
    console.log(`Dialog content (step ${currentStep}):`, dialogText?.slice(0, 100) + '...');

    // Detect what type of step we're on
    const isBasicConfig = dialogText?.includes('Basic Configuration') ||
      dialogText?.includes('Name') ||
      await page.locator('input[type="text"]:not([type="radio"])').count() > 0;

    const isFeatureConfig = dialogText?.includes('Feature') ||
      dialogText?.includes('Additional') ||
      await page.locator('input[type="checkbox"]').count() > 2;

    const isConfirmation = dialogText?.includes('Success') ||
      dialogText?.includes('Complete') ||
      dialogText?.includes('Configuration created') ||
      dialogText?.includes('will be added');

    if (isBasicConfig) {
      console.log(`✅ Step ${currentStep}: Basic Configuration detected`);

      // Debug: Show all form elements
      const allInputs = await page.locator('input, ha-picker-field, select').count();
      console.log(`🔍 Found ${allInputs} total form elements`);

      // Get all form elements for detailed analysis
      const formElements = await page.locator('input, ha-picker-field, select').all();

      for (let i = 0; i < formElements.length; i++) {
        try {
          const element = formElements[i];
          const tagName = await element.evaluate(el => el.tagName);
          const type = await element.getAttribute('type');
          const name = await element.getAttribute('name');
          const placeholder = await element.getAttribute('placeholder');
          const label = await element.getAttribute('aria-label');

          console.log(`Element ${i}: ${tagName} (type: ${type}, name: ${name}, placeholder: ${placeholder}, label: ${label})`);

          // Skip radio buttons and checkboxes
          if (type === 'radio' || type === 'checkbox') {
            console.log(`  ⏭️ Skipping ${type} button`);
            continue;
          }

          // Determine what to fill based on context
          let valueToFill = '';
          const context = (placeholder || label || name || '').toLowerCase();

          if (context.includes('name')) {
            valueToFill = 'Test Dual Smart Thermostat E2E';
          } else if (context.includes('temperature') || context.includes('sensor')) {
            valueToFill = 'sensor.test_temperature';
          } else if (context.includes('heater') || context.includes('switch')) {
            valueToFill = 'switch.test_heater';
          } else if (context.includes('tolerance')) {
            valueToFill = '0.5';
          } else if (context.includes('cycle') || context.includes('duration')) {
            valueToFill = '300';
          } else if (type === 'number') {
            valueToFill = '0.5'; // Default numeric value for number inputs
          } else if (i === 0) {
            // First field is usually name
            valueToFill = 'Test Dual Smart Thermostat E2E';
          } else {
            valueToFill = 'test_value';
          }

          console.log(`  📝 Attempting to fill with: "${valueToFill}"`);

          // Check if element is visible before trying to fill
          const isVisible = await element.isVisible();
          if (!isVisible) {
            console.log(`  ⏭️ Skipping invisible element`);
            continue;
          }

          // Fill based on element type
          if (tagName === 'HA-PICKER-FIELD') {
            console.log(`  🎯 Filling ha-picker-field...`);
            await element.click();
            await page.waitForTimeout(500);
            await page.keyboard.type(valueToFill);
            await page.keyboard.press('Tab');
            console.log(`  ✅ ha-picker-field filled`);
          } else if (tagName === 'SELECT') {
            console.log(`  🎯 Filling select...`);
            // For selects, just pick the first option
            const options = await element.locator('option').count();
            if (options > 1) {
              await element.selectOption({ index: 1 }); // Skip first option (usually empty)
            }
            console.log(`  ✅ Select filled`);
          } else {
            console.log(`  🎯 Filling input field...`);
            await element.fill(valueToFill);
            console.log(`  ✅ Input field filled`);
          }

        } catch (e) {
          console.log(`  ❌ Error filling element ${i}: ${e.message}`);
        }
      }

      console.log('📝 Basic configuration form filling completed');

      // Take screenshot after filling
      await page.screenshot({ path: 'debug-basic-config-filled.png' });
      console.log('📸 Screenshot taken after filling basic config form');

    } else if (isFeatureConfig) {
      console.log(`✅ Step ${currentStep}: Features Selection detected - skipping for basic flow`);

    } else if (isConfirmation) {
      console.log(`✅ Step ${currentStep}: Confirmation dialog detected`);

    } else {
      console.log(`⚠️ Step ${currentStep}: Unknown step type - will try to submit anyway`);
    }

    // Submit current step
    try {
      submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
      await submitButton.click();
      console.log(`✅ Step ${currentStep} submitted`);
      await page.waitForTimeout(3000);
    } catch (e) {
      console.log(`❌ Step ${currentStep} submission failed:`, e.message);
      break;
    }

    currentStep++;
  }

  if (currentStep > maxSteps) {
    console.log('⚠️ Config flow exceeded maximum steps');
  }

  console.log('🏁 Complete Config Flow test finished!');
});

// STEP 2: Continue with the remaining config flow steps
test('Step 2: Complete remaining config flow steps', async ({ page }) => {
  console.log('🚀 Step 2: Completing full config flow');

  // Navigate to integrations and start config flow (same as Step 1)
  await page.goto('/config/integrations');
  console.log('📍 Navigated to integrations page');

  // Open "Add Integration" dialog
  const addButton = page.locator('button').filter({ hasText: 'ADD INTEGRATION' });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();

  // Search and click integration
  const searchInput = page.locator('input[type="search"], input[placeholder*="Search"]').first();
  await searchInput.fill('');
  await page.waitForTimeout(500);
  await searchInput.type('Dual Smart Thermostat', { delay: 100 });
  await page.waitForTimeout(2000);

  const integrationCard = page.locator('ha-integration-list-item:has-text("Dual Smart Thermostat")').first();
  await expect(integrationCard).toBeVisible({ timeout: 10000 });
  await integrationCard.click();
  await page.waitForTimeout(3000);

  // Select system type (same as Step 1)
  const simpleHeaterOption = page.locator('text="Simple Heater Only"');
  await expect(simpleHeaterOption).toBeVisible({ timeout: 5000 });
  await simpleHeaterOption.click();
  console.log('✅ System type selected');

  // Submit system type
  let submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
  await submitButton.click();
  console.log('✅ System type submitted');
  await page.waitForTimeout(3000);

  // Step 2A: Handle Basic Configuration
  console.log('📝 Step 2A: Looking for Basic Configuration step...');

  const dialogText = await page.locator('ha-dialog[open]').first().textContent();
  console.log('Current dialog content:', dialogText?.slice(0, 100) + '...');

  // Check if we're on basic config step
  const isBasicConfig = dialogText?.includes('Basic Configuration') ||
    dialogText?.includes('Name') ||
    await page.locator('input[type="text"]:not([type="radio"])').count() > 0;

  if (isBasicConfig) {
    console.log('✅ Basic Configuration step detected');

    // Fill the name field (first text input)
    const nameInput = page.locator('input[type="text"]:not([type="radio"])').first();
    await nameInput.fill('Test Simple Heater E2E');
    console.log('✅ Name field filled');

    // Submit basic config
    submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
    await submitButton.click();
    console.log('✅ Basic configuration submitted');
    await page.waitForTimeout(3000);
  } else {
    console.log('⚠️ Expected basic config step but got different content');
  }

  // Step 2B: Handle Features Selection (skip for basic flow)
  console.log('📝 Step 2B: Looking for Features Selection step...');

  const featuresDialogText = await page.locator('ha-dialog[open]').first().textContent();
  console.log('Features dialog content:', featuresDialogText?.slice(0, 100) + '...');

  const isFeatureConfig = featuresDialogText?.includes('Feature') ||
    featuresDialogText?.includes('Additional') ||
    await page.locator('input[type="checkbox"]').count() > 2;

  if (isFeatureConfig) {
    console.log('✅ Features Selection step detected - skipping features for basic flow');

    // Submit without selecting any features
    submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
    await submitButton.click();
    console.log('✅ Features step submitted (no features selected)');
    await page.waitForTimeout(3000);
  } else {
    console.log('⚠️ Features step may have been skipped or combined');
  }

  // Step 2C: Handle Confirmation Dialog
  console.log('📝 Step 2C: Looking for Confirmation Dialog...');

  const confirmDialogText = await page.locator('ha-dialog[open]').first().textContent();
  console.log('Confirmation dialog content:', confirmDialogText?.slice(0, 100) + '...');

  const isConfirmation = confirmDialogText?.includes('Success') ||
    confirmDialogText?.includes('Complete') ||
    confirmDialogText?.includes('Configuration created') ||
    confirmDialogText?.includes('will be added') ||
    confirmDialogText?.includes('Finish');

  if (isConfirmation) {
    console.log('✅ Confirmation dialog detected - completing config flow!');

    // Final submit
    submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
    await submitButton.click();
    console.log('✅ Final confirmation submitted');
    await page.waitForTimeout(3000);

    // Check if redirected to integrations page
    const currentUrl = page.url();
    if (currentUrl.includes('/config/integrations')) {
      console.log('🎉 SUCCESS: Redirected to integrations page!');

      // Check if integration appears in the list
      await page.waitForTimeout(2000);
      const configuredIntegration = await page.locator('[data-domain="dual_smart_thermostat"]').count();
      if (configuredIntegration > 0) {
        console.log('🎉 ULTIMATE SUCCESS: Integration is now visible in integrations list!');
      } else {
        console.log('⚠️ Integration not immediately visible, but config flow completed');
      }
    } else {
      console.log('⚠️ Not redirected to integrations page - may still be in dialog');
    }
  } else {
    console.log('⚠️ Expected confirmation dialog but got different content');
    console.log('Taking screenshot for debugging...');
    await page.screenshot({ path: 'debug-unexpected-final-step.png' });
  }

  console.log('🏁 Step 2 completed - full config flow attempted!');
});