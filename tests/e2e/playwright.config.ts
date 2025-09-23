import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests/specs',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 1,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : 1,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8123',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Increase default timeout for actions */
    actionTimeout: 10000,

    /* Increase default timeout for navigation */
    navigationTimeout: 15000,
  },

  /* Global test timeout */
  timeout: 60000,

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        /* Use prepared auth state for Home Assistant - disabled for now */
        // storageState: 'tests/auth/storageState.json'
      },
    },

    /* Uncomment for cross-browser testing */
    // {
    //   name: 'firefox',
    //   use: { 
    //     ...devices['Desktop Firefox'],
    //     storageState: 'tests/auth/storageState.json'
    //   },
    // },

    // {
    //   name: 'webkit',
    //   use: { 
    //     ...devices['Desktop Safari'],
    //     storageState: 'tests/auth/storageState.json'
    //   },
    // },
  ],

  /* Global setup for authentication - disabled for now */
  // globalSetup: require.resolve('./tests/auth/global-setup.ts'),

  /* Test output directories */
  outputDir: 'test-results/',

  /* Artifacts and expect configuration */
  expect: {
    /* Global expect timeout */
    timeout: 10000,

    /* Update snapshots with --update-snapshots flag */
    toHaveScreenshot: {
      threshold: 0.2,
      maxDiffPixelRatio: 0.1,
    },

    /* Visual comparison baseline directory */
    toMatchSnapshot: {
      threshold: 0.2,
    }
  },

  /* Run your local dev server before starting the tests */
  // webServer: {
  //   command: 'docker compose up homeassistant',
  //   url: 'http://localhost:8123',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120 * 1000, // 2 minutes for HA to start
  // },
});