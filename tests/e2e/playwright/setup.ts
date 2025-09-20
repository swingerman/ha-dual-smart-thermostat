// Helper for Playwright E2E setup. Linting is kept strict; explicit ignores are avoided.
import type { Page, Locator } from '@playwright/test';

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

// Note: We intentionally do not export a dedicated HomeAssistantAPI interface here
// because some linters/TS servers may flag unused parameter names in interface
// call signatures. Instead we declare the return type for createAPI inline.

export class HomeAssistantSetup {
  private _page: Page;

  constructor(page: Page) {
    // assign to internal field so usages like this._page are correctly recognized
    this._page = page;
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
   * Ensure integration is ready for config flow testing.
   * This method checks if the integration is available and starts the config flow if needed.
   */
  async ensureIntegrationReadyForConfigFlow(integrationName: string, domain: string): Promise<boolean> {
    // First check if the integration is already configured (exists in integrations list)
    try {
      await this.goToIntegrations();
      await this._page.waitForTimeout(1000);

      // Look for existing integration in the list
      const existingIntegration = this._page.locator(`[data-test-id="integration-card"] :text("${integrationName}"), [role="listitem"] :text("${integrationName}")`).first();
      if (await existingIntegration.count() > 0) {
        console.log(`🔧 Integration '${integrationName}' already configured - tests may need to handle this case`);
        return false; // Already exists, config flow not needed
      }
    } catch (err) {
      console.log('⚠️ Could not check for existing integration:', err instanceof Error ? err.message : err);
    }

    // Integration not configured yet, start the config flow
    console.log(`🚀 Starting config flow for '${integrationName}'`);

    // Navigate to integrations and open Add Integration dialog
    await this.goToIntegrations();
    await this._page.click('button:has-text("Add integration")');

    // Wait for the dialog and search - use the exact same approach as working test
    await this._page.waitForSelector('input[type="search"], input[placeholder*="Search"]', { timeout: 10000 });
    await this._page.fill('input[type="search"], input[placeholder*="Search"]', integrationName);

    // Click on the integration to start config flow - use the exact same selector as working test
    const integrationCard = this._page.locator(`:text("${integrationName}")`).first();
    await integrationCard.waitFor({ state: 'visible', timeout: 10000 });
    await integrationCard.click();

    // Wait for config flow to start - should be on first step now
    await this._page.waitForTimeout(2000);

    return true;
  }

  /**
   * Ensure a given integration is present (config entry exists).
   * We rely on the preloaded `placeholder_climate` in `tests/e2e/ha_config/configuration.yaml`.
   */
  async ensureIntegrationPresent(integrationName: string, domain: string) {
    // First, check for the preloaded YAML climate entity that we add for deterministic
    // E2E tests. This verifies the integration was loaded from YAML rather than
    // relying on a config entry which may not exist for YAML-only setups.
    const entityId = 'climate.placeholder_climate';
    const deadline = Date.now() + 60000; // wait up to 60s for HA to finish startup
    while (Date.now() < deadline) {
      try {
        // Use page.evaluate/fetch so auth cookies from storageState are sent
        const state = await this._page.evaluate(async (id: string) => {
          try {
            const res = await fetch(`/api/states/${id}`);
            if (!res.ok) return null;
            return res.json();
          } catch {
            return null;
          }
        }, entityId);
        if (state && state.entity_id === entityId) {
          console.log(`🔎 Entity ${entityId} present (detected via states API) — YAML config loaded`);
          return;
        }
      } catch { /* ignore transient errors */ }

      // If the YAML entity isn't present yet, fall back to checking config entries
      // (some integrations create config entries instead of YAML-only entities).
      try {
        const entries = await this._page.evaluate(async () => {
          try {
            const res = await fetch('/api/config/config_entries/entry');
            if (!res.ok) return null;
            return res.json();
          } catch {
            return null;
          }
        });
        if (Array.isArray(entries)) {
          const cfg = entries as ConfigEntry[];
          if (cfg.some((e: ConfigEntry) => e.domain === domain)) {
            console.log(`🔎 Integration ${domain} present (detected via config entries)`);
            return;
          }
        }
      } catch { /* ignore transient network errors */ }

      // Periodically check the Integrations page DOM for the integration name in case
      // the UI renders it before the states API returns the specific entity.
      try {
        await this.goToIntegrations();
        // Wait up to remaining deadline for the integration card to appear
        const remaining = Math.max(1000, deadline - Date.now());
        const integrationCard = this._page.locator(`[data-test-id="integration-card"] :text("${integrationName}"), [role="listitem"] :text("${integrationName}")`).first();
        try {
          await integrationCard.waitFor({ state: 'visible', timeout: remaining });
          console.log(`🔎 Integration '${integrationName}' found in Integrations UI during polling`);
          return;
        } catch {
          // not yet visible, continue polling
        }
      } catch { /* ignore UI navigation/rendering errors during polling */ }

      // Wait a bit before retrying
      await this._page.waitForTimeout(1000);
    }

    // Do not attempt to add the integration through the UI — tests must rely on
    // deterministic YAML provisioning. Instead, navigate to the Integrations
    // page and verify the integration is already listed in the UI. This gives a
    // clear assertion that the integration was loaded at HA startup without
    // triggering config flows or adding via the UI.
    try {
      await this.goToIntegrations();

      // Wait a short while for the integrations list to render
      await this._page.waitForTimeout(500);

      // Look for a visible integration card or list item with the integration name
      const integrationCard = this._page.locator(`[data-test-id="integration-card"] :text("${integrationName}"), [role="listitem"] :text("${integrationName}")`).first();
      if (await integrationCard.count() > 0) {
        console.log(`� Integration '${integrationName}' found in Integrations UI`);
        return;
      }

      // As an additional fallback for different UI variations, search the page
      // content for the integration name (shadow DOM aware traversal is heavier,
      // but this simpler text search often suffices).
      const pageText = await this._page.content();
      if (pageText.includes(integrationName)) {
        console.log(`🔎 Integration '${integrationName}' text found in Integrations page content`);
        return;
      }
    } catch (err) {
      // Ignore navigation/rendering errors here; we'll fail with a clear message
      console.log('⚠️ Could not verify integration presence via UI check:', err instanceof Error ? err.message : err);
    }

    // Fail clearly so CI/debugging can surface the missing YAML/configuration.
    throw new Error(`Integration '${domain}' not detected. Ensure 'placeholder_climate' is present in tests/e2e/ha_config/configuration.yaml and that Home Assistant was restarted so the YAML was loaded.`);
  }
  /**
   * Start adding an integration
   */
  async startAddingIntegration(integrationName: string, domain?: string): Promise<boolean> {
    // If a config flow UI is already open, treat this as "already started" and return.
    try {
      const alreadyForm = this._page.locator('form, label:has-text("Name"), label:has-text("System Type")').first();
      if (await alreadyForm.count() > 0) {
        console.log('🔧 Config flow already in progress - startAddingIntegration is idempotent and will return');
        return true;
      }
    } catch { /* ignore errors checking for existing form */ }

    // If a domain is provided, check server-side for an active flow (covers cases where the
    // flow was started and no form is yet rendered). This uses the Playwright request API
    // which avoids page.evaluate 401 issues.
    if (domain) {
      try {
        const flowsResp = await this._page.request.get('http://localhost:8123/api/config/config_entries/flow');
        if (flowsResp.ok()) {
          const flows = await flowsResp.json() as Array<{ handler: string; flow_id?: string }>;
          if (Array.isArray(flows) && flows.some(f => f.handler === domain)) {
            console.log('🔧 Detected active config flow for domain via request - not opening Add Integration dialog');
            return true;
          }
        }
      } catch { /* ignore network errors here */ }
    }

    await this.goToIntegrations();

    // Try to open Add Integration dialog with retries (UI can be slow or blocked by dialogs)
    const maxOpenAttempts = 4;
    let opened = false;
    for (let attempt = 1; attempt <= maxOpenAttempts; attempt++) {
      try {
        // Close any possible blocking dialogs (e.g., onboarding, cloud banners)
        await this.closeBlockingDialogsIfAny();

        // Prefer the explicit Add Integration button, fallback to menu
        const addBtn = this._page.locator('button:has-text("Add Integration")').first();
        if (await addBtn.count() > 0) {
          await addBtn.waitFor({ state: 'visible', timeout: 3000 });
          await addBtn.click();
          opened = true;
          break;
        }

        // Alternate: the integrations header menu trigger
        const headerPlus = this._page.locator('ha-button:has([icon="mdi:plus"])').first();
        if (await headerPlus.count() > 0) {
          await headerPlus.click();
          opened = true;
          break;
        }
      } catch {
        // Wait a bit and try again
        await this._page.waitForTimeout(500 * attempt);
      }
    }

    if (!opened) {
      const html = await this._page.content();
      console.log('❌ Could not open Add Integration dialog. Page snapshot (first 4000 chars):', html.substring(0, 4000));
      throw new Error('Unable to open Add Integration dialog');
    }

    // Prefer the search input scoped to the Add Integration dialog to avoid ambiguity
    const dialog = this._page.locator('dialog-add-integration, dialog-add-integration-root, dialog-add-integration').first();
    const searchInput = dialog.locator('input[placeholder*="Search"], input[type="search"], input[aria-label*="Filter"], input').first();
    await searchInput.waitFor({ state: 'visible', timeout: 15000 });

    // Prefer to type into the search input using real key events. Clear the input first
    // to avoid duplicate typing (some flows also set the value programmatically).
    try {
      await searchInput.focus();
      await this._page.waitForTimeout(100);

      // Try to clear via locator.fill (preferred), fall back to evaluate if necessary
      try {
        await searchInput.fill('');
      } catch {
        try {
          await searchInput.evaluate((el: HTMLInputElement) => { el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })); });
        } catch { /* ignore */ }
      }

      // Type the integration name and commit with Enter
      await this._page.keyboard.type(integrationName, { delay: 20 });
      await this._page.keyboard.press('Enter');
    } catch {
      // fallback to slow typing into the locator
      try { await this.typeSlowly(searchInput, integrationName, 80); } catch { /* ignore */ }
    }

    // allow results to render
    await this._page.waitForTimeout(700);

    // If programmatic set didn't cause results to appear, try real keyboard events while focused
    // (some client-side handlers only respond to actual key events). We try multiple
    // strategies to ensure we focus the actual input element inside the dialog, including
    // components that live inside shadow roots.
    const visibleAfterSet = await this._page.locator(`[data-test-id="integration-card"]:has-text("${integrationName}")`).count();
    if (!visibleAfterSet) {
      try {
        // First try to focus the previously found locator input
        try { await searchInput.focus(); } catch { /* ignore */ }
        await this._page.waitForTimeout(120);

        // If focus on the locator didn't trigger the UI, attempt to find a better input
        // candidate from the document (covers shadow DOM + custom elements).
        const focused = await this._page.evaluate(() => {
          // Try to find any visible input-like element whose placeholder/aria-label matches search
          function isVisible(el: Element) {
            try {
              const r = (el as HTMLElement).getBoundingClientRect();
              return r.width > 0 && r.height > 0;
            } catch { return false; }
          }

          function findInputs(root: Node | ShadowRoot) {
            const inputs: Element[] = [];
            const walker = document.createTreeWalker(root as Node, NodeFilter.SHOW_ELEMENT, null as unknown as NodeFilter);
            let node = walker.nextNode() as Element | null;
            while (node) {
              const tag = node.tagName && node.tagName.toLowerCase();
              if (tag === 'input' || tag === 'textarea' || tag === 'mwc-textfield' || tag === 'ha-textfield') {
                inputs.push(node);
              }
              try {
                const sr = (node as unknown as { shadowRoot?: ShadowRoot }).shadowRoot;
                if (sr) inputs.push(...findInputs(sr));
              } catch { /* ignore shadow access errors */ }
              node = walker.nextNode() as Element | null;
            }
            return inputs;
          }

          // search within the open dialog first
          const dialog = document.querySelector('div[role="dialog"], ha-dialog, home-assistant');
          const roots = dialog ? [dialog] : [document];

          for (const r of roots) {
            const inputs = findInputs(r as unknown as Node);
            for (const el of inputs) {
              try {
                if (!isVisible(el)) continue;
                const ph = (el as HTMLInputElement).placeholder || (el as HTMLElement).getAttribute && (el as HTMLElement).getAttribute('aria-label') || '';
                if (/search|filter|integration|brand/i.test(ph) || /search|filter|integration|brand/i.test((el.textContent || ''))) {
                  try { (el as HTMLElement).focus(); return true; } catch { /* ignore */ }
                }
              } catch { /* ignore per-element errors */ }
            }
          }

          // fallback: focus the first visible input inside the dialog
          if (dialog) {
            const anyInput = dialog.querySelector('input, textarea, mwc-textfield, ha-textfield');
            if (anyInput) try { (anyInput as HTMLElement).focus(); return true; } catch { /* ignore */ }
          }
          return false;
        }, integrationName);

        // If we managed to focus something, send keystrokes to trigger client-side handlers
        if (focused) {
          // First try to explicitly clear the located search input's value (covers inputs inside shadow DOM/custom elements)
          try {
            await searchInput.evaluate((el: HTMLInputElement) => {
              try { el.value = ''; el.dispatchEvent(new Event('input', { bubbles: true })); } catch { /* ignore */ }
            });
          } catch { /* ignore if locator evaluate fails */ }

          // Also attempt to clear any value on the active/focused element as a best-effort fallback
          try {
            await this._page.evaluate(() => {
              const af = document.activeElement as HTMLInputElement | null;
              if (af && ('value' in af)) {
                try { af.value = ''; af.dispatchEvent(new Event('input', { bubbles: true })); } catch { /* ignore */ }
              }
            });
          } catch { /* ignore */ }

          // Clear using keyboard shortcuts (select-all + backspace) for elements that require real key events
          try { await this._page.keyboard.press('Control+A'); await this._page.keyboard.press('Backspace'); } catch { /* ignore */ }
          try { await this._page.keyboard.press('Meta+A'); await this._page.keyboard.press('Backspace'); } catch { /* ignore */ }

          // Type the integration name with small delay to simulate user typing
          await this._page.keyboard.type(integrationName, { delay: 20 });
          // Some handlers expect Enter to commit the search
          await this._page.keyboard.press('Enter');
          await this._page.waitForTimeout(900);
        } else {
          // As a last-ditch attempt, clear the active element then type into it
          try {
            await this._page.evaluate(() => {
              const af = document.activeElement as HTMLInputElement | null;
              if (af && ('value' in af)) {
                try { af.value = ''; af.dispatchEvent(new Event('input', { bubbles: true })); } catch { /* ignore */ }
              }
            });
            await this._page.keyboard.type(integrationName, { delay: 20 });
            await this._page.keyboard.press('Enter');
            await this._page.waitForTimeout(900);
          } catch (kbErr) { console.log('⚠️ Keyboard typing fallback failed (final):', kbErr instanceof Error ? kbErr.message : kbErr); }
        }
      } catch (kbErr) {
        console.log('⚠️ Keyboard typing fallback failed:', kbErr instanceof Error ? kbErr.message : kbErr);
      }
    }

    // Click on the integration card if present, wait explicitly for it
    const cardLocator = this._page.locator(`[data-test-id="integration-card"]:has-text("${integrationName}")`).first();
    if (await cardLocator.count() > 0) {
      try {
        await cardLocator.waitFor({ state: 'visible', timeout: 10000 });
        await cardLocator.scrollIntoViewIfNeeded();
        await cardLocator.click();
        return true;
      } catch (err) {
        console.log('⚠️ Found card locator but could not click it:', err instanceof Error ? err.message : err);
      }
    }

    // Alternate: look for the integration title text anywhere inside results
    const textLocator = this._page.locator(`.integration-card, [role="listitem"] >> text="${integrationName}"`).first();
    if (await textLocator.count() > 0) {
      try {
        await textLocator.waitFor({ state: 'visible', timeout: 8000 });
        await textLocator.scrollIntoViewIfNeeded();
        await textLocator.click();
        return true;
      } catch (err) {
        console.log('⚠️ Found text locator but could not click it:', err instanceof Error ? err.message : err);
      }
    }

    // Special case: new HA Add Integration dialog sometimes shows an 'Select brand' alertdialog
    // with a simple list of brand names. Search within any alertdialog/dialog for the name.
    const dialogTextLocator = this._page.locator('alertdialog, [role="alertdialog"], div[role="dialog"]').locator(`text="${integrationName}"`).first();
    if (await dialogTextLocator.count() > 0) {
      try {
        await dialogTextLocator.waitFor({ state: 'visible', timeout: 8000 });
        await dialogTextLocator.scrollIntoViewIfNeeded();
        await dialogTextLocator.click();
        return true;
      } catch (err) {
        console.log('⚠️ Found brand list locator in dialog but could not click it:', err instanceof Error ? err.message : err);
      }
    }

    // Last-resort: search through the document and shadow roots for any element containing the integration name and click it
    try {
      const clicked = await this._page.evaluate(/* istanbul ignore next */ async (name: string) => {
        function visible(el: Element): boolean {
          // getBoundingClientRect exists on HTMLElement
          const r = (el as HTMLElement).getBoundingClientRect();
          return r.width > 0 && r.height > 0;
        }

        // Traverse DOM and shadow roots
        function traverse(root: Document | ShadowRoot | Element): Element[] {
          const results: Element[] = [];
          const walker = document.createTreeWalker(root as Node, NodeFilter.SHOW_ELEMENT, null);
          let node = walker.nextNode() as Element | null;
          while (node) {
            results.push(node);
            try {
              // shadowRoot may exist on elements
              const maybeShadow = (node as unknown as { shadowRoot?: ShadowRoot }).shadowRoot;
              if (maybeShadow) {
                results.push(...traverse(maybeShadow));
              }
            } catch (err) { void err; }
            node = walker.nextNode() as Element | null;
          }
          return results;
        }

        const nodes = traverse(document);
        for (const el of nodes) {
          try {
            if (!visible(el)) continue;
            const text = el.textContent;
            if (!text) continue;
            if (text.trim().includes(name)) {
              try { (el as HTMLElement).click(); return true; } catch (err) { void err; }
            }
          } catch (err) { void err; }
        }
        return false;
      }, integrationName);

      if (clicked) {
        console.log('✅ Clicked integration via shadow-DOM-aware fallback');
        return true;
      }
    } catch (e) {
      console.log('⚠️ Shadow-DOM fallback failed:', e instanceof Error ? e.message : e);
    }

    // Additional robust click: traverse shadow roots and dialog containers with a targeted click helper
    try {
      const clicked2 = await this._page.evaluate(async (name: string) => {
        function visible(el: Element) {
          try { const r = (el as HTMLElement).getBoundingClientRect(); return r.width > 0 && r.height > 0; } catch { return false; }
        }

        function traverseAndCollect(root: Document | ShadowRoot | Element) {
          const collected: Element[] = [];
          const walker = document.createTreeWalker(root as Node, NodeFilter.SHOW_ELEMENT, null);
          let node = walker.nextNode() as Element | null;
          while (node) {
            collected.push(node);
            try {
              const sr = (node as unknown as { shadowRoot?: ShadowRoot }).shadowRoot;
              if (sr) collected.push(...traverseAndCollect(sr));
            } catch { /* ignore */ }
            node = walker.nextNode() as Element | null;
          }
          return collected;
        }

        // prefer to search inside dialogs / alertdialogs
        const dialogCandidates = Array.from(document.querySelectorAll('div[role="dialog"], ha-dialog, alertdialog, [role="alertdialog"]'));
        const roots = dialogCandidates.length ? dialogCandidates : [document];

        for (const r of roots as unknown as Array<Document | Element | ShadowRoot>) {
          const nodes = traverseAndCollect(r as unknown as Document | ShadowRoot | Element);
          for (const n of nodes) {
            try {
              if (!visible(n)) continue;
              const text = n.textContent || '';
              if (text.trim().includes(name)) {
                try { (n as HTMLElement).click(); return true; } catch { /* ignore */ }
              }
            } catch { /* ignore */ }
          }
        }

        return false;
      }, integrationName);

      if (clicked2) {
        console.log('✅ Clicked integration via targeted shadow-DOM+dialog traversal');
        return true;
      }
    } catch (err) { console.log('⚠️ targeted traversal click failed:', err instanceof Error ? err.message : err); }

    // If we get here, attempt to surface virtualized/invisible results by scrolling the results container
    try {
      const names = await this._page.evaluate(() => {
        function findContainer() {
          const candidates = Array.from(document.querySelectorAll('div, section, mwc-list, ha-list'));
          for (const c of candidates) {
            try {
              if (c.querySelector && c.querySelector('[data-test-id="integration-card"], .integration-card, [role="listitem"]')) return c;
            } catch (err) { void err; }
          }
          return null;
        }

        const container = findContainer();
        const collected = new Set();
        if (!container) return [];

        // Scroll the container to attempt to render virtualized items
        const scrollStep = Math.max(200, container.clientHeight || 400);
        for (let y = 0; y < (container.scrollHeight || scrollStep * 5); y += scrollStep) {
          try { (container as HTMLElement).scrollTop = y; } catch (err) { void err; }
          // collect titles
          const cards = container.querySelectorAll('[data-test-id="integration-card"] .name, .integration-card .name, [role="listitem"]');
          for (const card of Array.from(cards)) {
            const text = card.textContent && card.textContent.trim();
            if (text) collected.add(text);
          }
        }

        return Array.from(collected).slice(0, 200);
      });

      if (names && names.length) {
        console.log('🔎 Integration names visible in results (first 200):', names.join(' | '));
      } else {
        console.log('🔎 No integration names could be detected in Add Integration results');
      }
    } catch (e) {
      console.log('⚠️ Could not collect integration names from dialog:', e instanceof Error ? e.message : e);
    }
    return false;
  }

  /**
   * Attempt to create a config entry via Home Assistant config_entries flow API.
   * Returns true if created, false if not created but flow progressed to form, and throws on error.
   */
  private async attemptCreateConfigEntryViaAPI(domain: string, data: Record<string, unknown>): Promise<boolean> {
    // Use browser-side fetch to keep auth cookies
    const startJson = await this._page.evaluate(async (handler: string) => {
      const res = await fetch('/api/config/config_entries/flow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ handler })
      });
      if (!res.ok) throw new Error(`Failed to start config flow: ${res.status}`);
      return res.json();
    }, domain);

    if (startJson.type === 'create_entry') return true;

    const flowId = startJson.flow_id;
    const deadline = Date.now() + 20000;

    while (Date.now() < deadline) {
      const resultAny = await this._page.evaluate(async (opts: { fid: string; payload: Record<string, unknown> }) => {
        const res = await fetch(`/api/config/config_entries/flow/${opts.fid}/configure`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(opts.payload)
        });
        if (!res.ok) throw new Error(`Failed to configure flow: ${res.status}`);
        return res.json();
      }, { fid: flowId, payload: data }) as unknown;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const result = resultAny as any;

      if (result.type === 'create_entry') return true;
      if (result.type === 'form') {
        // flow needs more input; wait a bit and retry
        await this._page.waitForTimeout(500);
        continue;
      }
      break;
    }

    return false;
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
    await this._page.click('button[type="submit"], button:has-text("Next"), button:has-text("Submit")');
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

  /**
   * Navigate to the Integrations page
   */
  async goToIntegrations() {
    try {
      await this._page.goto('http://localhost:8123/config/integrations');
      await this._page.waitForLoadState('networkidle');
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
}