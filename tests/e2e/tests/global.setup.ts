import { chromium, FullConfig } from '@playwright/test';
import path from 'path';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Setting up E2E test environment...');
  
  const { baseURL, headless } = config.projects[0]?.use || {};
  const browser = await chromium.launch({ headless });
  const page = await browser.newPage();
  
  try {
    console.log(`📡 Connecting to Home Assistant at ${baseURL}`);
    
    // Wait for Home Assistant to be available
    let retries = 30;
    while (retries > 0) {
      try {
        await page.goto(baseURL || 'http://localhost:8123', { 
          waitUntil: 'networkidle',
          timeout: 10000 
        });
        break;
      } catch (error) {
        retries--;
        if (retries === 0) {
          throw new Error(`Failed to connect to Home Assistant at ${baseURL}. Make sure the container is running and healthy.`);
        }
        console.log(`⏳ Waiting for Home Assistant to be ready... (${retries} retries left)`);
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    }
    
    // Check if we're on the onboarding page
    const isOnboarding = await page.locator('ha-onboarding').isVisible().catch(() => false);
    
    if (isOnboarding) {
      console.log('🏠 Completing Home Assistant onboarding...');
      
      // Complete onboarding flow
      // Step 1: Create user account
      await page.locator('input[name="name"]').fill('E2E Test User');
      await page.locator('input[name="username"]').fill('test');
      await page.locator('input[name="password"]').fill('test123');
      await page.locator('input[name="password_confirm"]').fill('test123');
      await page.locator('button[type="submit"]').click();
      
      // Wait for next step
      await page.waitForTimeout(2000);
      
      // Step 2: Location setup (skip if available)
      const locationNext = page.locator('button:has-text("Next")');
      if (await locationNext.isVisible()) {
        await locationNext.click();
        await page.waitForTimeout(2000);
      }
      
      // Step 3: Analytics (decline)
      const analyticsDecline = page.locator('button:has-text("No thanks")');
      if (await analyticsDecline.isVisible()) {
        await analyticsDecline.click();
        await page.waitForTimeout(2000);
      }
      
      // Step 4: Finish onboarding
      const finishButton = page.locator('button:has-text("Finish")');
      if (await finishButton.isVisible()) {
        await finishButton.click();
      }
      
      // Wait for Home Assistant to load
      await page.waitForSelector('home-assistant-main', { timeout: 30000 });
      console.log('✅ Onboarding completed successfully');
    } else {
      console.log('🔑 Home Assistant already configured, checking authentication...');
      
      // Check if we need to login
      const loginForm = await page.locator('ha-login-form').isVisible().catch(() => false);
      
      if (loginForm) {
        console.log('🔐 Logging in to Home Assistant...');
        await page.locator('input[name="username"]').fill('test');
        await page.locator('input[name="password"]').fill('test123');
        await page.locator('button[type="submit"]').click();
        
        // Wait for successful login
        await page.waitForSelector('home-assistant-main', { timeout: 15000 });
        console.log('✅ Login successful');
      }
    }
    
    // Verify we can access the integrations page
    await page.goto('/config/integrations');
    await page.waitForSelector('ha-config-integrations', { timeout: 10000 });
    
    // Save authentication state
    const authPath = path.join(__dirname, '..', '.auth', 'user.json');
    await page.context().storageState({ path: authPath });
    console.log(`💾 Authentication state saved to ${authPath}`);
    
    console.log('✅ Global setup completed successfully');
    
  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;