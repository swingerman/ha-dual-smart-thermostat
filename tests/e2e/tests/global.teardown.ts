import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Running global teardown...');
  
  // Add any cleanup logic here if needed
  // For example: clear temporary files, reset test data, etc.
  
  console.log('✅ Global teardown completed');
}

export default globalTeardown;