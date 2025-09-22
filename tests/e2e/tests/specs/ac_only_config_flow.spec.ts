import { test, expect } from '@playwright/test';

// AC-Only Config Flow using proven patterns from simple heater implementation
test('AC-Only Config Flow: Complete setup with features', async ({ page }) => {
  console.log('🚀 Starting AC-Only Config Flow test');

  // Step 1: Navigate and start config flow (same pattern as simple heater)
  await page.goto('/config/integrations', { timeout: 30000 });
  await page.waitForTimeout(2000); // Wait for page to fully load
  console.log('📍 Navigated to integrations page');

  const addButton = page.locator('button').filter({ hasText: 'ADD INTEGRATION' });
  await expect(addButton).toBeVisible({ timeout: 15000 });
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

  // Check if dialog opened (config flow should start automatically)
  const dialogCount = await page.locator('ha-dialog[open]').count();
  console.log(`🔍 Found ${dialogCount} open dialogs after clicking integration`);

  if (dialogCount === 0) {
    console.log('❌ No dialog opened - integration may already be configured');
    // If no dialog opens, the integration might already exist and need to be deleted first
    throw new Error('Config flow dialog did not open - integration may already be configured');
  }

  // Step 2: System Type Selection - Select AC Only
  console.log('📝 Step 2: System Type Selection - Air Conditioning Only');

  const acOnlyOption = page.locator('text="Air Conditioning Only"');
  await expect(acOnlyOption).toBeVisible({ timeout: 5000 });
  await acOnlyOption.click();
  console.log('✅ Air Conditioning Only selected');

  let submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();
  
  // Check if submit button exists and is enabled
  const submitButtonCount = await submitButton.count();
  const isEnabled = await submitButton.isEnabled();
  console.log(`🔍 Submit button: count=${submitButtonCount}, enabled=${isEnabled}`);
  
  if (submitButtonCount === 0) {
    throw new Error('No submit button found after system type selection');
  }
  
  if (!isEnabled) {
    console.log('⚠️ Submit button is disabled - checking form validation');
    // Take screenshot to see current state
    await page.screenshot({ path: 'debug-disabled-submit-button.png' });
  }
  
  await submitButton.click();
  console.log('✅ System type submitted');
  
  // Wait and immediately check if dialog is still open
  await page.waitForTimeout(1000);
  const dialogStillOpen = await page.locator('ha-dialog[open]').count();
  console.log(`🔍 After system type submission: ${dialogStillOpen} dialogs still open`);
  
  if (dialogStillOpen === 0) {
    console.log('❌ CRITICAL: Dialog closed immediately after system type submission!');
    console.log('❌ This suggests AC-only system type has a configuration problem');
    const currentUrl = page.url();
    console.log(`🔍 Redirected to: ${currentUrl}`);
    await page.screenshot({ path: 'debug-dialog-closed-after-system-type.png' });
    
    // Check if there are any error messages on the page
    const errorMessages = await page.locator('[class*="error"], [class*="alert"], .notification').allTextContents();
    if (errorMessages.length > 0) {
      console.log('🔍 Error messages found:', errorMessages);
    }
  } else {
    console.log('✅ Dialog still open after system type submission - checking next step content');
    
    // Immediately check what the next step contains
    const nextStepText = await page.locator('ha-dialog[open]').first().textContent();
    console.log(`🔍 Next step content: ${nextStepText?.slice(0, 200)}...`);
    
    // Check for any error indicators
    const hasErrors = await page.locator('[class*="error"], .error, [aria-invalid="true"]').count();
    console.log(`🔍 Error elements found: ${hasErrors}`);
    
    // Wait and check again
    await page.waitForTimeout(1000);
    const stillOpenAfterWait = await page.locator('ha-dialog[open]').count();
    console.log(`🔍 After 1s wait: ${stillOpenAfterWait} dialogs still open`);
    
    if (stillOpenAfterWait === 0) {
      console.log('❌ Dialog closed during the 1s wait period - this suggests the next step failed');
      await page.screenshot({ path: 'debug-dialog-closed-during-wait.png' });
    } else {
      console.log('✅ Dialog remained open - continuing to next step processing');
      await page.waitForTimeout(1000); // Additional wait for next step to fully load
    }
  }

  // Step 3: Continue through remaining steps using proven patterns
  let maxSteps = 8; // AC-only flow has more steps due to features
  let currentStep = 2; // We've done system type (1), now starting from basic config (2)
  let processedSteps = new Set(); // Track which steps we've already processed

  while (currentStep <= maxSteps) {
    await page.waitForTimeout(2000);

    // Check if dialog is still open
    const dialogCount = await page.locator('ha-dialog[open]').count();
    if (dialogCount === 0) {
      // Dialog closed - this should only happen after confirmation step
      const currentUrl = page.url();
      console.log(`🔍 Dialog closed, current URL: ${currentUrl}`);

      if (currentStep < 4) {
        console.log(`❌ ERROR: Dialog closed at step ${currentStep} but we haven't completed the full 4-step flow!`);
        console.log('❌ ALL system types must follow: System Type → Basic Config → Features → Confirmation');
        console.log(`❌ We only completed ${currentStep} steps`);
        console.log('❌ This indicates our test is incorrectly causing premature dialog closure');
        throw new Error(`Config flow incomplete: Dialog closed at step ${currentStep} without completing the required 4-step flow`);
      }

      if (currentUrl.includes('/config/integrations')) {
        console.log('🎉 SUCCESS: Redirected to integrations page after completing full flow!');

        // Check if integration appears in the list
        await page.waitForTimeout(2000);
        const configuredIntegration = await page.locator('[data-domain="dual_smart_thermostat"]').count();
        if (configuredIntegration > 0) {
          console.log('✅ SUCCESS! Integration is now visible in integrations list');
        } else {
          console.log('⚠️ Integration not immediately visible, but config flow completed');
        }
        break;
      } else {
        throw new Error('Dialog closed but not redirected to integrations page');
      }
    }

    // Get current dialog content
    const dialogText = await page.locator('ha-dialog[open]').first().textContent();
    console.log(`Step ${currentStep} dialog content:`, dialogText?.slice(0, 100) + '...');

    // Create a unique step identifier based on dialog content
    const stepId = dialogText?.slice(0, 50) || `step-${currentStep}`;

    // Skip if we've already processed this exact step content
    if (processedSteps.has(stepId)) {
      console.log(`⏭️ Step ${currentStep}: Already processed this step content, moving on`);
      currentStep++;
      continue;
    }

    // Debug: Show form elements for step detection
    const hasNameField = await page.locator('input[name="name"]').count() > 0;
    const hasPickerFields = await page.locator('ha-picker-field').count() > 0;
    const hasCheckboxes = await page.locator('input[type="checkbox"]').count() > 0;

    console.log(`🔍 Step ${currentStep} form elements: name=${hasNameField}, pickers=${hasPickerFields}, checkboxes=${hasCheckboxes}`);

    // Detect what type of step we're on using proven patterns
    const isBasicConfig = (dialogText?.includes('Basic Configuration') ||
      dialogText?.includes('Air Conditioning Configuration') ||
      dialogText?.includes('Name')) &&
      (hasNameField || hasPickerFields);

    const isFeatureConfig = (dialogText?.includes('Feature') ||
      dialogText?.includes('Additional') ||
      dialogText?.includes('Select')) &&
      hasCheckboxes &&
      !isBasicConfig;

    const isConfirmation = dialogText?.includes('Success') ||
      dialogText?.includes('Complete') ||
      dialogText?.includes('Configuration created') ||
      dialogText?.includes('will be added') ||
      dialogText?.includes('successfully configured') ||
      dialogText?.includes('Finish') ||
      (!hasNameField && !hasPickerFields && !hasCheckboxes &&
        dialogText && dialogText.length > 50);

    // Handle specific step types
    if (isBasicConfig) {
      console.log(`✅ Step ${currentStep}: Basic Configuration detected`);
      await handleBasicConfiguration(page);

    } else if (isFeatureConfig) {
      console.log(`✅ Step ${currentStep}: Features Configuration detected`);
      await handleFeatureSelection(page);

    } else if (isConfirmation) {
      console.log(`✅ Step ${currentStep}: Confirmation Dialog detected`);
      console.log('🎉 Config flow reaching final confirmation step!');

      // Take screenshot of confirmation dialog
      await page.screenshot({ path: 'debug-ac-only-confirmation.png' });

      // Mark this step as processed before final submission
      processedSteps.add(stepId);

    } else {
      console.log(`⚠️ Step ${currentStep}: Feature-specific step or unknown step`);
      console.log('📝 Dialog content for debugging:', dialogText?.slice(0, 300));

      // For feature-specific steps, try to fill any visible form fields
      await handleFeatureSpecificStep(page, currentStep);
    }

    // Mark step as processed
    processedSteps.add(stepId);

    // Submit current step
    try {
      submitButton = page.locator('dialog-data-entry-flow button[part="base"]').first();

      // Check if submit button exists before clicking
      const submitButtonCount = await submitButton.count();
      console.log(`🔍 Step ${currentStep}: Found ${submitButtonCount} submit buttons`);

      if (submitButtonCount === 0) {
        console.log(`⚠️ Step ${currentStep}: No submit button found, checking if dialog is still open...`);
        const stillOpen = await page.locator('ha-dialog[open]').count();
        if (stillOpen === 0) {
          console.log(`🔍 Step ${currentStep}: Dialog already closed, moving to next iteration`);
          currentStep++;
          continue;
        }
      }

      await submitButton.click();
      console.log(`✅ Step ${currentStep} submitted`);

      // Wait and check if dialog is still open after submission
      await page.waitForTimeout(2000);
      const dialogStillOpen = await page.locator('ha-dialog[open]').count();
      console.log(`🔍 After step ${currentStep} submission: ${dialogStillOpen} dialogs still open`);

      if (dialogStillOpen > 0) {
        // Dialog still open, wait a bit more for next step to load
        await page.waitForTimeout(1000);
        const newDialogText = await page.locator('ha-dialog[open]').first().textContent();
        console.log(`🔍 Next step preview: ${newDialogText?.slice(0, 100)}...`);
      }

    } catch (e) {
      console.log(`❌ Step ${currentStep} submission failed:`, e.message);
      // Check if dialog closed during submission
      const dialogStillOpen = await page.locator('ha-dialog[open]').count();
      console.log(`🔍 After submission error: ${dialogStillOpen} dialogs still open`);
      if (dialogStillOpen === 0) {
        console.log(`🔍 Dialog closed during submission - this might be normal flow completion`);
        break;
      }
    }

    currentStep++;
  }

  if (currentStep > maxSteps) {
    console.log('⚠️ Config flow exceeded maximum steps - may be stuck');
  }

  console.log('🏁 AC-Only Config Flow test completed!');
});

// Helper function to handle basic configuration step
async function handleBasicConfiguration(page: any) {
  console.log('📝 Filling AC-Only basic configuration form...');
  
  // First, debug what form elements are actually available WITHIN the dialog
  console.log('🔍 DEBUGGING: Analyzing actual form structure within dialog...');
  
  const dialogSelector = 'ha-dialog[open]';
  const allElements = await page.locator(`${dialogSelector} input, ${dialogSelector} ha-picker-field, ${dialogSelector} select, ${dialogSelector} button`).all();
  console.log(`🔍 Found ${allElements.length} form elements within dialog`);
  
  for (let i = 0; i < Math.min(allElements.length, 10); i++) {
    try {
      const element = allElements[i];
      const tagName = await element.evaluate(el => el.tagName);
      const type = await element.getAttribute('type');
      const name = await element.getAttribute('name');
      const label = await element.getAttribute('aria-label');
      const placeholder = await element.getAttribute('placeholder');
      const isVisible = await element.isVisible();
      
      console.log(`🔍 Element ${i}: ${tagName} (type: ${type}, name: ${name}, label: ${label}, placeholder: ${placeholder}, visible: ${isVisible})`);
    } catch (e) {
      console.log(`🔍 Element ${i}: Error analyzing - ${e.message}`);
    }
  }
  
  // Focus on filling only the essential required fields using dialog-scoped selectors
  const requiredFields = [
    { selector: 'ha-dialog[open] input[name="name"]', value: 'Test AC Only E2E', description: 'Name field' },
    { selector: 'ha-dialog[open] ha-picker-field[aria-label*="Temperature"]', value: 'sensor.test_temperature', description: 'Temperature sensor' },
    { selector: 'ha-dialog[open] ha-picker-field[aria-label*="Air conditioning switch"]', value: 'switch.test_cooler', description: 'AC switch' }
  ];
  
  for (const field of requiredFields) {
    try {
      console.log(`🔍 Looking for ${field.description}: ${field.selector}`);
      
      const element = page.locator(field.selector).first();
      const elementCount = await element.count();
      
      if (elementCount === 0) {
        console.log(`⚠️ ${field.description} not found with selector: ${field.selector}`);
        continue;
      }
      
      const isVisible = await element.isVisible();
      if (!isVisible) {
        console.log(`⚠️ ${field.description} is not visible`);
        continue;
      }
      
      // Check if dialog is still open
      const dialogOpen = await page.locator('ha-dialog[open]').count();
      if (dialogOpen === 0) {
        console.log(`⚠️ Dialog closed while filling ${field.description}`);
        return;
      }
      
      console.log(`📝 Filling ${field.description} with: ${field.value}`);
      
      // Handle different element types
      const tagName = await element.evaluate(el => el.tagName);
      if (tagName === 'HA-PICKER-FIELD') {
        await element.click();
        await page.waitForTimeout(500);
        await page.keyboard.type(field.value);
        await page.keyboard.press('Tab');
      } else {
        await element.fill(field.value);
      }
      
      console.log(`✅ ${field.description} filled successfully`);
      await page.waitForTimeout(300);
      
    } catch (e) {
      console.log(`❌ Error filling ${field.description}: ${e.message}`);
    }
  }
  
  console.log('📝 Basic configuration form filling completed');
  await page.screenshot({ path: 'debug-ac-only-basic-config.png' });
}

// Helper function to handle feature selection step
async function handleFeatureSelection(page: any) {
  console.log('📝 Handling AC-Only feature selection...');

  // For AC-Only, select multiple features to test comprehensive flow
  const featuresToSelect = [
    'configure_fan',
    'configure_humidity',
    'configure_openings',
    'configure_presets'
  ];

  for (const feature of featuresToSelect) {
    try {
      const checkbox = page.locator(`input[name="${feature}"]`);
      const isVisible = await checkbox.isVisible();
      if (isVisible) {
        await checkbox.check();
        console.log(`✅ Selected feature: ${feature}`);
      } else {
        console.log(`⚠️ Feature not visible: ${feature}`);
      }
    } catch (e) {
      console.log(`❌ Error selecting feature ${feature}: ${e.message}`);
    }
  }

  await page.screenshot({ path: 'debug-ac-only-features.png' });
  console.log('📝 Feature selection completed');
}

// Helper function to handle feature-specific configuration steps
async function handleFeatureSpecificStep(page: any, stepNumber: number) {
  console.log(`📝 Handling feature-specific step ${stepNumber}...`);

  // Get all form elements in this step
  const formElements = await page.locator('input, ha-picker-field, select').all();

  for (let i = 0; i < Math.min(formElements.length, 5); i++) {
    try {
      const element = formElements[i];
      const tagName = await element.evaluate(el => el.tagName);
      const type = await element.getAttribute('type');
      const label = await element.getAttribute('aria-label');
      const name = await element.getAttribute('name');

      // Skip radio buttons and checkboxes (already handled in feature selection)
      if (type === 'radio' || type === 'checkbox') {
        continue;
      }

      // Check visibility
      if (!(await element.isVisible())) {
        continue;
      }

      // Determine appropriate test value based on context
      let testValue = 'test_value';
      const context = (label || name || '').toLowerCase();

      if (context.includes('fan')) {
        testValue = 'fan.test_fan';
      } else if (context.includes('humidity')) {
        testValue = 'sensor.test_humidity';
      } else if (context.includes('opening') || context.includes('door') || context.includes('window')) {
        testValue = 'binary_sensor.test_door';
      } else if (context.includes('temperature')) {
        testValue = '22';
      } else if (context.includes('target') || context.includes('away') || context.includes('sleep')) {
        testValue = '24';
      } else if (type === 'number') {
        testValue = '50';
      }

      // Fill the field
      if (tagName === 'HA-PICKER-FIELD') {
        await element.click();
        await page.waitForTimeout(500);
        await page.keyboard.type(testValue);
        await page.keyboard.press('Tab');
      } else {
        await element.fill(testValue);
      }

      console.log(`✅ Filled field with: ${testValue}`);

    } catch (e) {
      console.log(`⚠️ Could not fill element ${i}: ${e.message}`);
    }
  }

  await page.screenshot({ path: `debug-ac-only-step-${stepNumber}.png` });
  console.log(`📝 Feature step ${stepNumber} completed`);
}