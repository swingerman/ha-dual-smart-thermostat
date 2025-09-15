# E2E Testing for Dual Smart Thermostat

This directory contains end-to-end (E2E) tests for the Dual Smart Thermostat Home Assistant custom component using Playwright.

## Overview

The E2E testing setup provides:
- A reproducible Docker Compose environment with Home Assistant
- Playwright configuration for UI testing
- Minimal Home Assistant configuration with required entities
- Test utilities for config flow testing

## Prerequisites

- Docker and Docker Compose
- Node.js (v18 or later)
- Playwright (will be installed via npm)

## Quick Start

1. **Start Home Assistant container:**
   ```bash
   cd tests/e2e
   docker compose up -d
   ```

2. **Wait for Home Assistant to be ready (60-120 seconds):**
   ```bash
   # Monitor logs to see when HA is ready
   docker compose logs -f homeassistant
   
   # Or check health status
   docker compose ps
   ```

3. **Install Playwright dependencies:**
   ```bash
   npm install
   npx playwright install
   ```

4. **Run E2E tests:**
   ```bash
   npx playwright test
   ```

## Container Health Check

The Home Assistant container includes a health check that verifies the API is accessible. You can monitor the container status:

```bash
# Check container status
docker compose ps

# View container logs
docker compose logs homeassistant

# Check if API is responding
curl http://localhost:8123/api/
```

The container should show as "healthy" when Home Assistant is fully loaded and the API is responding.

## Home Assistant Configuration

The test environment uses a minimal Home Assistant configuration (`ha_config/configuration.yaml`) that includes:

- **Input Helpers**: For simulating temperature sensors and device states
- **Template Sensors**: Room temperature sensor for thermostat testing
- **Template Switches**: Heater and cooler switches for device control
- **Binary Sensors**: Window sensor for opening detection
- **Climate Entity**: Pre-configured dual smart thermostat for testing

### Available Test Entities

- `sensor.room_temp` - Temperature sensor (controlled by `input_number.room_temp`)
- `switch.heater` - Heater switch (controlled by `input_boolean.heater_on`)
- `switch.cooler` - Cooler switch (controlled by `input_boolean.cooler_on`)
- `binary_sensor.window` - Window sensor (controlled by `input_boolean.window_open`)
- `climate.e2e_test_thermostat` - Pre-configured dual smart thermostat

## Playwright Configuration

The Playwright setup includes:

- **Base URL**: `http://localhost:8123` (Home Assistant frontend)
- **Multiple Browsers**: Chrome, Firefox, and Safari testing
- **Authentication State**: Stored in `.auth/user.json` for session persistence
- **Artifacts**: Screenshots, videos, and traces on test failures
- **Baseline Snapshots**: Stored in `test-results/baselines/`

### Test Structure

```
tests/e2e/
├── tests/                     # Test files
│   ├── global.setup.ts       # Global test setup
│   ├── global.teardown.ts    # Global test cleanup
│   ├── config-flow.spec.ts   # Config flow tests
│   └── options-flow.spec.ts  # Options flow tests
├── test-results/             # Test outputs
│   ├── baselines/           # Visual test baselines
│   ├── artifacts/           # Test artifacts
│   └── html-report/         # HTML test report
└── .auth/                   # Authentication state
    └── user.json           # Stored login session
```

## Token Handling and Authentication

Home Assistant requires authentication for API access. The test setup handles this automatically:

1. **Initial Setup**: The global setup script will handle first-time authentication
2. **Session Storage**: Authentication state is stored in `.auth/user.json`
3. **Token Management**: Long-lived access tokens are preferred for E2E testing

### Manual Token Setup (if needed)

If automatic authentication fails, you can manually create a long-lived access token:

1. Access Home Assistant at `http://localhost:8123`
2. Go to Profile → Security → Long-lived access tokens
3. Create a new token and store it securely
4. Update the test configuration as needed

## Baseline Management

Visual regression testing uses baseline screenshots for comparison.

### Regenerating Baselines

When UI changes are intentional, regenerate baselines using the provided script:

```bash
# Regenerate all baselines
./scripts/regenerate_baselines.sh

# Or update specific test baselines
npx playwright test --update-snapshots
```

### Baseline Storage

- Baselines are stored in `test-results/baselines/`
- Each test browser/device combination has separate baselines
- Baselines should be committed to version control for consistency

## Test Development

### Writing Config Flow Tests

```typescript
import { test, expect } from '@playwright/test';

test('dual smart thermostat config flow', async ({ page }) => {
  // Navigate to integrations page
  await page.goto('/config/integrations');
  
  // Add new integration
  await page.click('[data-testid="add-integration"]');
  
  // Search for dual smart thermostat
  await page.fill('input[type="search"]', 'dual smart thermostat');
  
  // Continue with config flow testing...
});
```

### Test Utilities

Common test utilities should be placed in `tests/utils/` for reusability across test files.

## Troubleshooting

### Container Issues

```bash
# Stop and remove containers
docker compose down

# Rebuild and start fresh
docker compose up -d --build

# Check container logs
docker compose logs homeassistant
```

### Port Conflicts

If port 8123 is already in use, modify the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "8124:8123"  # Use different host port
```

And update the `baseURL` in `playwright.config.ts` accordingly.

### Test Failures

1. Check if Home Assistant is running and healthy
2. Verify all required entities are available
3. Check test artifacts in `test-results/` for failure details
4. Review container logs for any errors

## Development Workflow

1. **Make changes** to the custom component
2. **Restart container** to load changes:
   ```bash
   docker compose restart homeassistant
   ```
3. **Run tests** to verify functionality:
   ```bash
   npx playwright test
   ```
4. **Update baselines** if UI changes are intentional:
   ```bash
   ./scripts/regenerate_baselines.sh
   ```

## Cleanup

To clean up the test environment:

```bash
# Stop containers
docker compose down

# Remove test artifacts
rm -rf test-results/
rm -rf .auth/

# Remove node modules (if needed)
rm -rf node_modules/
```

## Integration with CI/CD

The E2E tests are designed to run in CI/CD pipelines. Key considerations:

- Container startup time (~60-120 seconds)
- Resource requirements (Docker, Node.js)
- Artifact storage and baseline management
- Parallel test execution settings