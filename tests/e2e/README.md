# E2E Testing Guide

This directory contains end-to-end (E2E) tests for the Dual Smart Thermostat integration using Playwright and a dockerized Home Assistant instance.

## Overview

E2E tests validate the complete user flow from integration installation to configuration, ensuring that:
- Config flows work correctly for all system types
- Options flows properly update existing configurations
- UI elements are accessible and functional
- Feature combinations work as expected

## Project Status

**Current Status**: E2E infrastructure planning complete. Implementation pending.

The E2E test framework will use:
- **Playwright** for browser automation and UI testing
- **Dockerized Home Assistant** for a clean, reproducible test environment
- **Baseline screenshots** for visual regression testing

## Planned Structure

```
tests/e2e/
├── README.md                           # This file
├── E2E_FEATURE_TESTING_GUIDE.md       # Detailed implementation guide
├── docker-compose.yml                  # Docker setup for HA instance
├── playwright.config.ts                # Playwright configuration
├── ha_config/                          # Home Assistant configuration
│   ├── configuration.yaml
│   └── automations.yaml
├── ha_init/                            # Setup scripts
│   ├── storageState.json               # Auth state (ephemeral for CI)
│   └── setup_entities.py              # Create test entities
├── playwright/                         # Test utilities and specs
│   ├── setup.ts                        # Helper utilities
│   ├── feature-helpers.ts              # Feature configuration helpers
│   ├── config_flow.spec.ts             # Config flow tests
│   ├── options_flow.spec.ts            # Options flow tests
│   └── specs/                          # Feature combination tests
│       ├── simple_heater_feature_combinations.spec.ts
│       ├── ac_only_feature_combinations.spec.ts
│       ├── heater_cooler_feature_combinations.spec.ts
│       ├── heat_pump_feature_combinations.spec.ts
│       └── feature_interactions.spec.ts
├── baselines/                          # Baseline screenshots
└── artifacts/                          # Test output (gitignored)
```

## Running E2E Tests Locally (When Implemented)

### Prerequisites

1. **Docker and Docker Compose** installed
2. **Node.js** (version 18+) for Playwright
3. **npm** or **yarn** for dependency management

### Setup

```bash
# Install Playwright and dependencies
npm install
npx playwright install chromium

# Start the dockerized Home Assistant instance
docker-compose -f tests/e2e/docker-compose.yml up -d

# Wait for Home Assistant to be ready (may take 30-60 seconds)
# Check: curl -f http://localhost:8123 should return 200
```

### Running Tests

```bash
# Run all E2E tests
npx playwright test --config=tests/e2e/playwright.config.ts

# Run specific test file
npx playwright test --config=tests/e2e/playwright.config.ts tests/e2e/playwright/config_flow.spec.ts

# Run in headed mode (see browser)
npx playwright test --config=tests/e2e/playwright.config.ts --headed

# Run in debug mode
npx playwright test --config=tests/e2e/playwright.config.ts --debug

# Run tests for specific system type
npx playwright test --config=tests/e2e/playwright.config.ts -g "simple_heater"
```

### Cleanup

```bash
# Stop and remove containers
docker-compose -f tests/e2e/docker-compose.yml down -v
```

## Running in CI (GitHub Actions)

The E2E tests will be integrated into the CI pipeline with the following workflow:

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Install Playwright browsers
        run: npx playwright install chromium
      
      - name: Start Home Assistant
        run: |
          docker-compose -f tests/e2e/docker-compose.yml up -d
          # Wait for HA readiness
          timeout 120 bash -c 'until curl -f http://localhost:8123; do sleep 2; done'
      
      - name: Run E2E tests
        run: npx playwright test --config=tests/e2e/playwright.config.ts --project=chromium
      
      - name: Upload artifacts on failure
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/e2e/artifacts/
```

## Regenerating Baseline Screenshots

Baseline screenshots are used for visual regression testing. When the UI changes intentionally:

```bash
# Update all baselines
npx playwright test --config=tests/e2e/playwright.config.ts --update-snapshots

# Update specific test baselines
npx playwright test --config=tests/e2e/playwright.config.ts config_flow.spec.ts --update-snapshots

# Review changes before committing
git diff tests/e2e/baselines/
```

**Important**: Only commit baseline updates when UI changes are intentional and reviewed.

## Test Coverage Goals

### System Types
- ✅ `simple_heater` - Basic heating-only configuration
- ✅ `ac_only` - Air conditioning without heating
- ⏳ `heater_cooler` - Separate heating and cooling entities
- ⏳ `heat_pump` - Single entity with mode switching

### Features to Test
- **Fan Control**: Independent fan entity with various modes
- **Humidity Control**: Humidity sensor and dryer configuration
- **Openings Integration**: Door/window sensors with timeouts
- **Floor Heating**: Floor sensor with min/max temperature limits
- **Presets**: Temperature profiles (home, away, eco, etc.)
- **Advanced Settings**: Precision, tolerances, and cycle durations

### Test Scenarios
1. **Happy Path**: Complete configuration without errors
2. **Feature Combinations**: Multiple features enabled together
3. **Options Flow**: Modify existing configurations
4. **Validation**: Invalid inputs are rejected with helpful messages
5. **State Persistence**: Configuration survives restarts

## Security Considerations

### Authentication State

The `storageState.json` file contains authentication tokens for automatic login in tests:

- **Local development**: Generated once and reused
- **CI environment**: Generated per-run with ephemeral tokens
- **Security**: Never commit tokens to long-lived branches
- **Rotation**: Document regeneration steps in this README

### Regenerating storageState.json

```bash
# Start HA instance
docker-compose -f tests/e2e/docker-compose.yml up -d

# Run authentication setup
npx playwright codegen http://localhost:8123

# Manually log in through the browser that opens
# Save the auth state to tests/e2e/ha_init/storageState.json

# Test that it works
npx playwright test --config=tests/e2e/playwright.config.ts
```

## Troubleshooting

### Home Assistant won't start
- Check Docker logs: `docker-compose -f tests/e2e/docker-compose.yml logs`
- Ensure ports 8123 and 8300 are available
- Try clearing volumes: `docker-compose -f tests/e2e/docker-compose.yml down -v`

### Tests are flaky
- Increase wait times in `playwright/setup.ts`
- Use explicit waits instead of fixed timeouts
- Check for race conditions in async operations

### Authentication fails
- Regenerate `storageState.json` (see Security Considerations)
- Verify Home Assistant is accessible at http://localhost:8123
- Check for CORS issues or security restrictions

### Screenshots don't match
- Run with `--update-snapshots` if changes are intentional
- Check for timing issues (loading states, animations)
- Verify resolution and viewport settings in `playwright.config.ts`

## Test Writing Guidelines

### 1. Use Deterministic Entities
Always use predictable entity IDs defined in `ha_config/`:
```typescript
const HEATER_ENTITY = 'switch.test_heater';
const TEMP_SENSOR = 'sensor.test_temperature';
```

### 2. Wait for Elements
Never use fixed timeouts. Wait for specific elements:
```typescript
await page.waitForSelector('[data-testid="submit-button"]');
```

### 3. Descriptive Test Names
```typescript
test('simple_heater: configure with floor heating and fan', async ({ page }) => {
  // Test implementation
});
```

### 4. Clean State Between Tests
Each test should be independent:
```typescript
test.beforeEach(async ({ page }) => {
  await setupCleanHomeAssistant();
});
```

### 5. Use Helper Functions
Reuse helper functions from `feature-helpers.ts`:
```typescript
import { enableFeature, configureFan } from './feature-helpers';

await enableFeature(page, 'fan');
await configureFan(page, { fan: 'switch.test_fan', fan_on_with_ac: true });
```

## Contributing

When adding new E2E tests:

1. Follow the test structure in existing specs
2. Use helper functions for common operations
3. Add descriptive comments for complex flows
4. Test both success and error paths
5. Update baselines if UI changes are intentional
6. Ensure tests are deterministic (no random failures)

## References

- [Playwright Documentation](https://playwright.dev/)
- [Home Assistant Test Helpers](https://developers.home-assistant.io/docs/development_testing/)
- [E2E Feature Testing Guide](./E2E_FEATURE_TESTING_GUIDE.md)
- [Project Plan](../../specs/001-develop-config-and/plan.md)

---

**Last Updated**: 2025-10-12
**Status**: Planning complete, awaiting implementation
**Priority**: High - Critical for release confidence
