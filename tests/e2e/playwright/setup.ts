import { APIResponse, Page } from '@playwright/test';

export interface ConfigEntry {
  entry_id: string;
  domain: string;
  title: string;
  data: Record<string, any>;
  options: Record<string, any>;
  system_options: Record<string, any>;
  source: string;
  state: string;
}

export interface HomeAssistantAPI {
  /**
   * Get all config entries
   */
  getConfigEntries(): Promise<ConfigEntry[]>;
  
  /**
   * Get a specific config entry by ID
   */
  getConfigEntry(entryId: string): Promise<ConfigEntry>;
  
  /**
   * Wait for a config entry to exist with polling
   */
  waitForConfigEntry(domain: string, title?: string, timeout?: number): Promise<ConfigEntry>;
}

export class HomeAssistantSetup {
  constructor(private page: Page) {}

  /**
   * Create Home Assistant API helper
   */
  createAPI(): HomeAssistantAPI {
    return {
      getConfigEntries: async () => {
        const response = await this.page.request.get('/api/config/config_entries/entry');
        if (!response.ok()) {
          throw new Error(`Failed to get config entries: ${response.status()}`);
        }
        return response.json();
      },

      getConfigEntry: async (entryId: string) => {
        const response = await this.page.request.get(`/api/config/config_entries/entry/${entryId}`);
        if (!response.ok()) {
          throw new Error(`Failed to get config entry ${entryId}: ${response.status()}`);
        }
        return response.json();
      },

      waitForConfigEntry: async (domain: string, title?: string, timeout = 10000) => {
        const startTime = Date.now();
        
        while (Date.now() - startTime < timeout) {
          try {
            const entries = await this.createAPI().getConfigEntries();
            const entry = entries.find(e => 
              e.domain === domain && 
              (!title || e.title === title)
            );
            
            if (entry) {
              return entry;
            }
          } catch (error) {
            // Ignore errors and keep polling
          }
          
          await this.page.waitForTimeout(500);
        }
        
        throw new Error(`Config entry for domain ${domain}${title ? ` with title ${title}` : ''} not found within ${timeout}ms`);
      }
    };
  }

  /**
   * Navigate to integrations page
   */
  async goToIntegrations() {
    await this.page.goto('/config/integrations');
    await this.page.waitForSelector('[data-domain]', { timeout: 10000 });
  }

  /**
   * Start adding an integration
   */
  async startAddingIntegration(integrationName: string) {
    await this.goToIntegrations();
    
    // Click "Add Integration" button  
    await this.page.click('button:has-text("Add Integration")');
    
    // Search for the integration
    await this.page.fill('input[placeholder*="Search"]', integrationName);
    await this.page.waitForTimeout(1000);
    
    // Click on the integration
    await this.page.click(`[data-test-id="integration-card"]:has-text("${integrationName}")`);
  }

  /**
   * Fill form field by label
   */
  async fillFieldByLabel(label: string, value: string) {
    const field = this.page.locator(`label:has-text("${label}")`).locator('..').locator('input, select, textarea').first();
    await field.fill(value);
  }

  /**
   * Select option by label
   */
  async selectOptionByLabel(label: string, option: string) {
    const field = this.page.locator(`label:has-text("${label}")`).locator('..').locator('select').first();
    await field.selectOption(option);
  }

  /**
   * Click next/submit button
   */
  async clickNext() {
    await this.page.click('button[type="submit"], button:has-text("Next"), button:has-text("Submit")');
  }

  /**
   * Wait for step to load
   */
  async waitForStep(stepId?: string) {
    if (stepId) {
      await this.page.waitForSelector(`[data-step-id="${stepId}"]`, { timeout: 5000 });
    } else {
      await this.page.waitForLoadState('networkidle');
    }
  }
}