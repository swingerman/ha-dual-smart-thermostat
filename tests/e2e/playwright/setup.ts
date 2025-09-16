import { chromium, FullConfig } from '@playwright/test';

/**
 * Global setup for Playwright tests
 * This file handles authentication setup for Home Assistant
 */
async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Get HA URL from environment or use localhost
  const haUrl = process.env.HA_URL || 'http://localhost:8123';
  
  try {
    // Navigate to Home Assistant
    await page.goto(haUrl);
    
    // Wait for login form or check if already authenticated
    try {
      // If already authenticated, we might be redirected to the main page
      await page.waitForSelector('[data-panel="lovelace"]', { timeout: 5000 });
      console.log('Already authenticated, skipping login');
    } catch {
      // Not authenticated, need to login
      console.log('Attempting to authenticate with Home Assistant');
      
      // Check if we have username/password in environment
      const username = process.env.HA_USERNAME || 'admin';
      const password = process.env.HA_PASSWORD || 'admin';
      
      // Look for login form
      await page.waitForSelector('input[type="text"], input[type="email"]', { timeout: 10000 });
      
      // Fill login form
      await page.fill('input[type="text"], input[type="email"]', username);
      await page.fill('input[type="password"]', password);
      
      // Submit form
      await page.click('button[type="submit"]');
      
      // Wait for successful login
      await page.waitForSelector('[data-panel="lovelace"]', { timeout: 15000 });
      console.log('Successfully authenticated');
    }
    
    // Save authentication state
    await page.context().storageState({ path: './tests/e2e/playwright/storageState.json' });
    console.log('Saved authentication state');
    
  } catch (error) {
    console.error('Failed to setup authentication:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;