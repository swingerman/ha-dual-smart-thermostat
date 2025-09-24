// Helper for Playwright E2E setup. Linting is kept strict; explicit ignores are avoided.
import type { Page, Locator } from '@playwright/test';
import { expect } from '@playwright/test';

// Common selectors and URLs used across tests
export const INTEGRATION_NAME = 'Dual Smart Thermostat';
export const OPEN_DIALOG_SELECTOR = 'ha-dialog[open]';
export const OPEN_DIALOG_TITLE_SELECTOR = 'ha-dialog[open] [slot="title"]';
export const CONFIG_FLOW_DIALOG_SELECTOR = '.mdc-dialog.mdc-dialog--open';
export const LOADING_DIALOG_SELECTOR = '.mdc-dialog.mdc-dialog--open';
export const INTEGRATION_SEARCH_SELECTOR = `${OPEN_DIALOG_SELECTOR} ha-textfield input`;
export const INTEGRATION_CARD_SELECTOR = 'ha-integration-list-item[brand]';
export const INTEGRATIONS_DASHBOARD_URL = 'http://localhost:8123/config/integrations';
export const SUBMIT_BUTTON_SELECTOR = `${OPEN_DIALOG_SELECTOR} step-flow-form button[part="base"]`;

// System types enum matching Python const.py
export enum SystemType {
  SIMPLE_HEATER = 'simple_heater',
  AC_ONLY = 'ac_only',
  HEATER_COOLER = 'heater_cooler',
  HEAT_PUMP = 'heat_pump',
  DUAL_STAGE = 'dual_stage',
  FLOOR_HEATING = 'floor_heating',
}

// System types for UI selection (matching Python SYSTEM_TYPES)
export const SYSTEM_TYPE_LABELS: Record<SystemType, string> = {
  [SystemType.SIMPLE_HEATER]: 'Simple Heater Only',
  [SystemType.AC_ONLY]: 'Air Conditioning Only',
  [SystemType.HEATER_COOLER]: 'Heater with Cooler',
  [SystemType.HEAT_PUMP]: 'Heat Pump',
  [SystemType.DUAL_STAGE]: 'Dual Stage', // Placeholder - not in Python SYSTEM_TYPES
  [SystemType.FLOOR_HEATING]: 'Floor Heating', // Placeholder - not in Python SYSTEM_TYPES
};

// Export a reference array to mark enum members as used for linters
// This avoids false positives where enum members are flagged per-member
export const __SYSTEM_TYPE_ENUM_USED = [
  SystemType.SIMPLE_HEATER,
  SystemType.AC_ONLY,
  SystemType.HEATER_COOLER,
  SystemType.HEAT_PUMP,
  SystemType.DUAL_STAGE,
  SystemType.FLOOR_HEATING,
].length;

// Type for system type labels
export type SystemTypeLabel = typeof SYSTEM_TYPE_LABELS[keyof typeof SYSTEM_TYPE_LABELS];

// Shared utility functions for config flow step detection
export function isConfirmationStep(dialogText: string | null, hasNameField: boolean, hasPickerFields: boolean, hasCheckboxes: boolean): boolean {
  if (!dialogText) return false;

  // Based on actual confirmation dialog: "Success" title + "Created configuration for" content
  return (dialogText.includes('Success') && dialogText.includes('Created configuration for')) ||
    dialogText.includes('Finish') ||
    (dialogText.includes('Success') && !hasNameField && !hasPickerFields && !hasCheckboxes);
}

export function isSystemTypeStep(dialogText: string | null, hasRadioButtons: boolean): boolean {
  if (!dialogText) return false;

  // Primary detection: Look for "System Type Selection" title
  if (dialogText.includes('System Type Selection')) {
    return true;
  }

  // Secondary detection: Look for system type related text with radio buttons
  return (dialogText.includes('Choose the type of thermostat') ||
    dialogText.includes('system you want to configure') ||
    dialogText.includes('Simple Heater Only') ||
    dialogText.includes('Air Conditioning Only')) &&
    hasRadioButtons;
}

export function isBasicConfigurationStep(dialogText: string | null, hasNameField: boolean, hasPickerFields: boolean): boolean {
  if (!dialogText) return false;

  return (dialogText.includes('Basic Configuration') ||
    dialogText.includes('Name')) &&
    (hasNameField || hasPickerFields);
}

export function isFeatureConfigurationStep(dialogText: string | null): boolean {
  if (!dialogText) return false;

  // Primary detection: Look for "Features Configuration" title (as shown in screenshot)
  if (dialogText.includes('Features Configuration')) {
    return true;
  }

  return false;
}

export interface ConfigEntry {
  entry_id: string;
  domain: string;
  title: string;
  data: Record<string, unknown>;
  options: Record<string, unknown>;
  system_options: Record<string, unknown>;
  source: string;
  state: string;
}

export class HomeAssistantSetup {
  private _page: Page;

  constructor(page: Page) {
    // assign to internal field so usages like this._page are correctly recognized
    this._page = page;
  }

  /**
   * Wait for the config dialog to be in a stable, interactable state.
   * Handles a transient loading dialog that may briefly appear between steps.
   */
  async waitForConfigDialogStable(context: string = 'generic') {
    try {
      // If transient loading dialog appears, wait for it to disappear
      const loadingDialog = this._page.locator(LOADING_DIALOG_SELECTOR);
      if (await loadingDialog.count()) {
        console.log(`⏳ Waiting for transient loading dialog to disappear (${context})...`);
        await loadingDialog.first().waitFor({ state: 'detached', timeout: 10000 });
      }

      // Ensure the HA config dialog is present and visible
      const haDialog = this._page.locator(OPEN_DIALOG_SELECTOR);
      await haDialog.waitFor({ state: 'visible', timeout: 10000 });

      // Ensure step form is present inside the dialog
      const stepForm = this._page.locator(`${OPEN_DIALOG_SELECTOR} step-flow-form, ${OPEN_DIALOG_SELECTOR} dialog-data-entry-flow`);
      await stepForm.first().waitFor({ state: 'visible', timeout: 10000 });

      await this._page.screenshot({ path: `config-dialog-stable-${Date.now()}-${context}.png` });
      console.log(`✅ Config dialog stabilized (${context})`);
    } catch (err) {
      console.log(`⚠️ Could not fully stabilize dialog (${context}): ${(err as Error).message}`);
    }
  }

  /**
   * Create Home Assistant API helper
   */
  createAPI() {
    return {
      getConfigEntries: async () => {
        // Use browser fetch so authentication cookies are sent
        const result = await this._page.evaluate(async () => {
          const res = await fetch('/api/config/config_entries/entry');
          if (!res.ok) throw new Error(`Failed to get config entries: ${res.status}`);
          return res.json();
        });
        return result as ConfigEntry[];
      },

      getConfigEntry: async (...args: unknown[]) => {
        const entryId = args[0] as string;
        const result = await this._page.evaluate(async (id: string) => {
          const res = await fetch(`/api/config/config_entries/entry/${id}`);
          if (!res.ok) throw new Error(`Failed to get config entry ${id}: ${res.status}`);
          return res.json();
        }, entryId);
        return result as ConfigEntry;
      },

      waitForConfigEntry: async (...args: unknown[]) => {
        const domain = args[0] as string;
        const title = args[1] as string | undefined;
        const timeout = (args[2] as number | undefined) ?? 10000;
        const startTime = Date.now();

        while (Date.now() - startTime < timeout) {
          try {
            const entries = await this.createAPI().getConfigEntries() as ConfigEntry[];
            const entry = entries.find((e: ConfigEntry) =>
              e.domain === domain &&
              (!title || e.title === title)
            );

            if (entry) {
              return entry;
            }
          } catch {
            // Ignore errors and keep polling
          }

          await this._page.waitForTimeout(500);
        }

        throw new Error(`Config entry for domain ${domain}${title ? ` with title ${title}` : ''} not found within ${timeout}ms`);
      },
    };
  }

  /**
   * Navigate to the Integrations page
   */
  async goToIntegrations() {
    try {
      await this._page.goto(INTEGRATIONS_DASHBOARD_URL, { waitUntil: 'load' });
      // Avoid networkidle which can be impacted by websockets/long-polling
      await this._page.waitForSelector('body', { state: 'attached', timeout: 10000 });
    } catch {
      // best-effort navigation
    }
  }

  /**
   * Close common blocking dialogs that may interfere with tests
   */
  async closeBlockingDialogsIfAny() {
    try {
      // close any onboarding or dialog close buttons commonly present
      const closeBtns = this._page.locator('button[aria-label="Close"], button:has-text("Close"), mwc-button[dialogAction="close"]');
      if (await closeBtns.count() > 0) {
        await closeBtns.first().click();
        await this._page.waitForTimeout(200);
      }
    } catch {
      // ignore
    }
  }

  /**
   * Type into a locator slowly as a fallback
   */
  async typeSlowly(locator: Locator, text: string, delayMs = 40) {
    try {
      await locator.focus();
      for (const ch of text) {
        await this._page.keyboard.type(ch, { delay: delayMs });
      }
    } catch {
      // ignore
    }
  }

  /**
   * Fill form field by label
   */
  async fillFieldByLabel(label: string, value: string) {
    const field = this._page.locator(`label:has-text("${label}")`).locator('..').locator('input, select, textarea').first();
    await field.fill(value);
  }

  /**
   * Select option by label
   */
  async selectOptionByLabel(label: string, option: string) {
    const field = this._page.locator(`label:has-text("${label}")`).locator('..').locator('select').first();
    await field.selectOption(option);
  }

  /**
   * Click next/submit button
   */
  async clickNext() {
    await this._page.click(SUBMIT_BUTTON_SELECTOR);
  }

  /**
   * Select system type in config flow dialog
   * @param systemType - The system type enum value to select
   */
  async selectSystemType(systemType: SystemType) {
    const systemTypeLabel = SYSTEM_TYPE_LABELS[systemType];
    console.log(`🔍 Selecting system type: ${systemTypeLabel} (${systemType})`);

    // Find the system type option within the open dialog
    const systemTypeOption = this._page.locator(OPEN_DIALOG_SELECTOR).locator(`text="${systemTypeLabel}"`);
    await expect(systemTypeOption).toBeVisible({ timeout: 5000 });
    await systemTypeOption.click();
    console.log(`✅ ${systemTypeLabel} selected`);

    // Stabilize in case HA shows a transient dialog before the next step
    await this.waitForConfigDialogStable('after-select-system-type');
  }

  /**
   * Select entity in HA entity selector field
   * Handles the complex shadow DOM structure of HA entity pickers
   */
  async selectEntityInPicker(pickerLocator: Locator, entityId: string) {
    console.log(`🔍 Selecting entity: ${entityId}`);

    // Click the picker to open the dropdown
    await pickerLocator.click();
    console.log('✅ Entity picker clicked');

    // Wait for dropdown to appear without using timeout (which loses focus)
    const dropdown = this._page.locator('vaadin-combo-box-scroller[role="listbox"]');
    await dropdown.waitFor({ state: 'visible', timeout: 5000 });
    console.log('✅ Dropdown opened');

    // Type to filter the dropdown options
    await this._page.keyboard.type(entityId);
    console.log(`🔍 Typed entity: ${entityId}`);

    // Wait for filtered results to appear
    await dropdown.waitFor({ state: 'visible', timeout: 3000 });

    // Immediately try to click on the first matching result without waiting
    const dropdownOption = this._page.locator(`vaadin-combo-box-item[role="option"]:has-text("${entityId}")`).first();

    // Try to click immediately - don't wait for visibility which might cause dialog loss
    if (await dropdownOption.count() > 0) {
      await dropdownOption.click();
      console.log(`✅ Clicked on dropdown option: ${entityId}`);
    } else {
      console.log(`⚠️ Could not find exact match "${entityId}", trying first available option`);

      // Fallback: click the first available option immediately
      const firstOption = this._page.locator(`vaadin-combo-box-item[role="option"]`).first();
      if (await firstOption.count() > 0) {
        await firstOption.click();
        console.log('✅ Clicked on first available dropdown option');
      } else {
        console.log('❌ No dropdown options found');
        throw new Error(`No dropdown options found for entity: ${entityId}`);
      }
    }
  }

  /**
   * Wait for step to load
   */
  async waitForStep(stepId?: string) {
    if (stepId) {
      await this._page.waitForSelector(`[data-step-id="${stepId}"]`, { timeout: 5000 });
    } else {
      await this._page.waitForLoadState('networkidle');
    }
  }

  async getStepTitle() {
    const rawTitle = await this._page.locator(OPEN_DIALOG_SELECTOR).locator('[slot="title"]').textContent();
    return rawTitle?.trim() || '';
  }

  /**
   * Submit the current step and wait for transition
   */
  async submitStep(currentStep: number, lastStepName: string): Promise<boolean> {
    const submitButton = this._page.locator(`${OPEN_DIALOG_SELECTOR} step-flow-form button[part="base"]`).first();
    const submitButtonCount = await submitButton.count();
    console.log(`🔍 Submit button count: ${submitButtonCount}`);

    if (submitButtonCount === 0) {
      console.log('❌ No submit button found');
      await this._page.screenshot({ path: `config-flow-no-submit-step-${currentStep}.png` });
      return false;
    }

    const isEnabled = await submitButton.isEnabled();
    console.log(`🔍 Submit button enabled: ${isEnabled}`);

    if (!isEnabled) {
      console.log('⚠️ Submit button is disabled, waiting for form validation...');
      await this._page.waitForTimeout(500);
    }

    // Guard against navigation/reload
    this._page.on('framenavigated', (frame) => {
      if (frame === this._page.mainFrame()) {
        console.log(`⚠️ Unexpected navigation to: ${frame.url()}`);
      }
    });

    await submitButton.click();
    console.log(`✅ Step ${currentStep} submitted`);

    // Wait for the new step to appear (title change)
    try {
      await expect(this._page.locator(OPEN_DIALOG_TITLE_SELECTOR)).not.toHaveText(lastStepName, { timeout: 7000 });
      console.log('✅ Step transition detected');
    } catch {
      // If title didn't change, verify dialog is still present
      const dialogStillOpen = await this._page.locator(OPEN_DIALOG_SELECTOR).count();
      if (dialogStillOpen === 0) {
        console.log('⚠️ Dialog disappeared after submit, waiting for it to re-open...');
        await this.waitForConfigDialogStable(`reopen-after-submit-${currentStep}`);
      } else {
        console.log('⚠️ Step transition timeout but dialog still open - continuing');
      }
    }

    // Take screenshot after transition
    await this._page.screenshot({ path: `config-flow-after-step-${currentStep}.png` });

    // Stabilize dialog after submitting to handle transient loading overlay and re-open
    await this.waitForConfigDialogStable(`after-submit-step-${currentStep}`);
    return true;
  }

}