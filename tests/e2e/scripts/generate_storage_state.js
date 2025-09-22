#!/usr/bin/env node
/*
Generates a Playwright `storageState.json` for Home Assistant E2E tests.

Usage:
  HA_URL=http://localhost:8123 HA_TOKEN=<long-lived-token> node generate_storage_state.js

This script launches a headless Chromium, sets the `Authorization: Bearer <token>` header
so the frontend requests are authenticated, navigates to the frontend root, then saves
the context storage state to `tests/e2e/tests/auth/storageState.json`.

Note: You must provide a Home Assistant long-lived access token in the `HA_TOKEN` env var.
*/

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const HA_URL = process.env.HA_URL || 'http://localhost:8123';
  const HA_TOKEN = process.env.HA_TOKEN;
  if (!HA_TOKEN) {
    console.error('Missing HA_TOKEN environment variable. Create a long-lived access token in Home Assistant and set HA_TOKEN.');
    process.exit(2);
  }

  const outPath = path.resolve(__dirname, '..', 'tests', 'auth', 'storageState.json');
  const outDir = path.dirname(outPath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

  console.log(`Launching browser to ${HA_URL} and saving storage state to ${outPath}`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    baseURL: HA_URL,
    extraHTTPHeaders: {
      Authorization: `Bearer ${HA_TOKEN}`,
    },
  });

  try {
    const page = await context.newPage();
    // Visit the frontend root to let it populate any localStorage/cookies
    await page.goto('/', { waitUntil: 'networkidle', timeout: 30000 }).catch((e) => {
      console.warn('Warning: visiting frontend root failed or timed out:', e.message);
    });

    // Save storage state
    await context.storageState({ path: outPath });
    console.log('Saved storage state.');
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error('Error generating storageState:', err);
  process.exit(1);
});
