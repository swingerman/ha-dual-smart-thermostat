import { test, expect } from '@playwright/test';
import { isConfirmationStep, isBasicConfigurationStep, isFeatureConfigurationStep, isSystemTypeStep, OPEN_DIALOG_SELECTOR, HomeAssistantSetup, OPEN_DIALOG_TITLE_SELECTOR, SystemType } from '../../playwright/setup';
import { startIntegrationConfigFlow } from './partials/integrations-helper';

test.describe('Dual Smart Thermostat - Basic Heater Config Flow', () => {
  test('Complete basic heater config flow using reusable helpers', async ({ page }) => {
    console.log('🚀 Starting basic heater config flow test with reusable helpers');

    const helper = new HomeAssistantSetup(page);

    // Use the integrationsHelper object directly (it's not a class)
    // Step 1: Start integration config flow
    await startIntegrationConfigFlow(page);
    console.log('✅ Step 1: Integration config flow started');

    // Wait for the config flow dialog to appear
    console.log('⏳ Waiting for config flow dialog to appear...');

    // Now we should be in the System Type Selection step
    // Let's continue with the config flow steps using our detection helpers
    let currentStep = 1;
    const maxSteps = 10; // Safety limit
    let lastStepName = '';
    let sawSystemType = false;
    let sawBasic = false;
    let sawFeatures = false;
    let sawConfirmation = false;

    while (currentStep <= maxSteps) {
      console.log(`\n🔍 Step ${currentStep}: Analyzing current dialog state`);

      // Get current dialog state
      const dialogOpen = await page.locator(OPEN_DIALOG_SELECTOR).count();

      if (dialogOpen === 0) {
        console.log('❌ No dialog open - config flow may have completed or failed');
        break;
      }

      const dialogText = await page.locator(OPEN_DIALOG_TITLE_SELECTOR).textContent();
      lastStepName = dialogText || '';
      console.log(`📝 Dialog content: ${dialogText?.substring(0, 100)}...`);

      // Check form elements within the dialog
      const hasNameField = await page.locator(`${OPEN_DIALOG_SELECTOR} input[name="name"]`).count() > 0;
      const hasPickerFields = await page.locator(`${OPEN_DIALOG_SELECTOR} ha-picker-field`).count() > 0;
      const hasCheckboxes = await page.locator(`${OPEN_DIALOG_SELECTOR} input[type="checkbox"]`).count() > 0;
      const hasRadioButtons = await page.locator(`${OPEN_DIALOG_SELECTOR} input[type="radio"]`).count() > 0;

      console.log(`🔍 Form elements: name=${hasNameField}, pickers=${hasPickerFields}, checkboxes=${hasCheckboxes}, radio=${hasRadioButtons}`);

      // Use our reusable step detection functions
      const isSystemType = isSystemTypeStep(dialogText, hasRadioButtons);
      const isBasicConfig = isBasicConfigurationStep(dialogText, hasNameField, hasPickerFields);
      const isFeatureConfig = isFeatureConfigurationStep(dialogText);
      const isConfirmation = isConfirmationStep(dialogText, hasNameField, hasPickerFields, hasCheckboxes);

      console.log(`🎯 Step detection: system=${isSystemType}, basic=${isBasicConfig}, features=${isFeatureConfig}, confirmation=${isConfirmation}`);

      // Handle each step type
      if (isSystemType) {
        console.log('✅ System Type Selection step detected');

        // Select Simple Heater Only using helper
        await helper.selectSystemType(SystemType.SIMPLE_HEATER);
        sawSystemType = true;

      } else if (isBasicConfig) {
        console.log('✅ Basic Configuration step detected');
        sawBasic = true;
        // Fill the name field within the dialog
        const nameInput = page.locator(`${OPEN_DIALOG_SELECTOR} input[name="name"]`);
        if (await nameInput.count() > 0) {
          await nameInput.fill('Test Dual Smart Thermostat E2E');
          console.log('✅ Name field filled');
        }

        // Fill temperature sensor within the dialog
        const tempSensorPicker = page.locator(`${OPEN_DIALOG_SELECTOR} ha-picker-field[aria-label*="Temperature sensor"]`);
        if (await tempSensorPicker.count() > 0) {
          await helper.selectEntityInPicker(tempSensorPicker, 'sensor.test_temperature');
        }

        // Fill heater switch within the dialog
        const heaterPicker = page.locator(`${OPEN_DIALOG_SELECTOR} ha-picker-field[aria-label*="Heater switch"]`);
        if (await heaterPicker.count() > 0) {
          await helper.selectEntityInPicker(heaterPicker, 'switch.test_heater');
        }

      } else if (isFeatureConfig) {
        console.log('✅ Features Configuration step detected');
        console.log('📝 Skipping features configuration (using defaults)');
        sawFeatures = true;
      } else if (isConfirmation) {
        console.log('🎉 Confirmation step detected - Config flow completed!');
        sawConfirmation = true;

        // we shut exit here because we want to see the confirmation step
        break;
      } else {
        console.log('⚠️ Unknown step type - taking screenshot for debugging');
      }

      // Check if dialog is still open before submitting
      const dialogStillOpen = await page.locator(OPEN_DIALOG_SELECTOR).count();
      console.log(`🔍 Dialog still open before submit: ${dialogStillOpen > 0}`);

      if (dialogStillOpen === 0) {
        console.log('❌ Dialog closed unexpectedly before submit');
        await page.screenshot({ path: `config-flow-dialog-closed-step-${currentStep}.png` });
        break;
      }

      // Submit the current step using reusable method
      const submitSuccess = await helper.submitStep(currentStep, lastStepName);
      if (!submitSuccess) {
        break;
      }

      currentStep++;
    }

    if (currentStep > maxSteps) {
      console.log('❌ Exceeded maximum steps - possible infinite loop');
      throw new Error('Config flow exceeded maximum steps');
    }

    console.log('🏁 Basic heater config flow finished iterating steps');

    // Enforce that all required steps were seen
    expect(sawSystemType).toBeTruthy();
    expect(sawBasic).toBeTruthy();
    expect(sawFeatures).toBeTruthy();
    expect(sawConfirmation).toBeTruthy();
  });
});
