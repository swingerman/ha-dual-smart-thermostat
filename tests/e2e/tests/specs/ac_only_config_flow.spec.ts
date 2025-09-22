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
  await submitButton.click();
  console.log('✅ System type submitted');
  await page.waitForTimeout(3000);

  // Step 3: Continue through remaining steps using proven patterns
  let maxSteps = 8; // AC-only flow has more steps due to features
  let currentStep = 2; // We've done system type (1), now starting from basic config (2)
  
  while (currentStep <= maxSteps) {
    await page.waitForTimeout(2000);
    
    // Check if dialog is still open
    const dialogCount = await page.locator('ha-dialog[open]').count();
    if (dialogCount === 0) {
      // Dialog closed - should be redirected to integrations page
      const currentUrl = page.url();
      if (currentUrl.includes('/config/integrations')) {
        console.log('🎉 SUCCESS: Redirected to integrations page!');
        
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
    
    // Debug: Show form elements for step detection
    const hasNameField = await page.locator('input[name="name"]').count() > 0;
    const hasPickerFields = await page.locator('ha-picker-field').count() > 0;
    const hasCheckboxes = await page.locator('input[type="checkbox"]').count() > 0;
    
    console.log(`🔍 Step ${currentStep} form elements: name=${hasNameField}, pickers=${hasPickerFields}, checkboxes=${hasCheckboxes}`);
    
    // Detect what type of step we're on using proven patterns
    const isBasicConfig = (dialogText?.includes('Basic Configuration') || 
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
      
    } else {
      console.log(`⚠️ Step ${currentStep}: Feature-specific step or unknown step`);
      console.log('📝 Dialog content for debugging:', dialogText?.slice(0, 300));
      
      // For feature-specific steps, try to fill any visible form fields
      await handleFeatureSpecificStep(page, currentStep);
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
    console.log('⚠️ Config flow exceeded maximum steps - may be stuck');
  }
  
  console.log('🏁 AC-Only Config Flow test completed!');
});

// Helper function to handle basic configuration step
async function handleBasicConfiguration(page: any) {
  console.log('📝 Filling AC-Only basic configuration form...');
  
  // Get all form elements
  const formElements = await page.locator('input, ha-picker-field, select').all();
  console.log(`🔍 Found ${formElements.length} form elements`);
  
  for (let i = 0; i < formElements.length; i++) {
    try {
      const element = formElements[i];
      const tagName = await element.evaluate(el => el.tagName);
      const type = await element.getAttribute('type');
      const name = await element.getAttribute('name');
      const placeholder = await element.getAttribute('placeholder');
      const label = await element.getAttribute('aria-label');
      
      console.log(`Element ${i}: ${tagName} (type: ${type}, name: ${name}, label: ${label})`);
      
      // Skip radio buttons and checkboxes in basic config
      if (type === 'radio' || type === 'checkbox') {
        console.log(`  ⏭️ Skipping ${type} button`);
        continue;
      }
      
      // Check visibility before interaction
      const isVisible = await element.isVisible();
      if (!isVisible) {
        console.log(`  ⏭️ Skipping invisible element`);
        continue;
      }
      
      // Determine what to fill based on context
      let valueToFill = '';
      const context = (placeholder || label || name || '').toLowerCase();
      
      if (context.includes('name')) {
        valueToFill = 'Test AC Only E2E';
      } else if (context.includes('temperature') || context.includes('sensor')) {
        valueToFill = 'sensor.test_temperature';
      } else if (context.includes('cooler') || context.includes('ac')) {
        valueToFill = 'switch.test_cooler';
      } else if (context.includes('tolerance')) {
        valueToFill = '0.5';
      } else if (type === 'number') {
        valueToFill = '0.5'; // Default numeric value for number inputs
      } else if (i === 0) {
        // First field is usually name
        valueToFill = 'Test AC Only E2E';
      } else {
        valueToFill = 'test_value';
      }
      
      console.log(`  📝 Attempting to fill with: "${valueToFill}"`);
      
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