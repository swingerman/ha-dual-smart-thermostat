import { chromium, type FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Navigate to Home Assistant
  await page.goto(config.projects[0].use.baseURL || 'http://localhost:8123');
  
  // Check if we need to do initial setup
  const isOnboarding = await page.locator('[data-test-id="onboarding"]').isVisible().catch(() => false);
  
  if (isOnboarding) {
    // Handle onboarding flow
    await page.fill('[name="name"]', 'Test User');
    await page.fill('[name="username"]', 'testuser');
    await page.fill('[name="password"]', 'testpass123');
    await page.fill('[name="password_confirm"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Wait for completion
    await page.waitForURL('**/onboarding/analytics', { timeout: 30000 });
    await page.click('button:has-text("Next")');
    
    // Skip location setup
    await page.waitForURL('**/onboarding/area_registry', { timeout: 30000 });  
    await page.click('button:has-text("Finish")');
    
    // Wait for dashboard
    await page.waitForURL('**/lovelace/**', { timeout: 30000 });
  } else {
    // Try to login if login page is shown
    const isLoginPage = await page.locator('[data-test-id="login-form"]').isVisible().catch(() => false);
    
    if (isLoginPage) {
      await page.fill('[name="username"]', 'testuser');
      await page.fill('[name="password"]', 'testpass123');
      await page.click('button[type="submit"]');
      await page.waitForURL('**/lovelace/**', { timeout: 30000 });
    }
  }
  
  // Save authenticated state
  await page.context().storageState({ path: 'tests/auth/storageState.json' });
  
  await browser.close();
}

export default globalSetup;