# E2E Tests for Dual Smart Thermostat

This directory contains End-to-End (E2E) tests using Playwright to test the Home Assistant integration config flows and options flows for the Dual Smart Thermostat custom component.

## Prerequisites

- Docker and Docker Compose
- Node.js (v18 or higher)
- Playwright (will be installed via npm)

## Quick Start

### 1. Start Home Assistant Test Environment

```bash
cd tests/e2e
docker compose up -d
```

Wait for Home Assistant to fully start (60-120 seconds). You can monitor the startup:

```bash
docker compose logs -f homeassistant
```

Home Assistant is ready when you see logs like:
```
INFO (MainThread) [homeassistant.core] Starting Home Assistant
INFO (MainThread) [homeassistant.components.http] Now listening on port 8123
```

### 2. Install Playwright Dependencies (First time only)

```bash
npm init -y  # Creates package.json if needed
npm install -D @playwright/test
npx playwright install
```

### 3. Run Tests

```bash
# Run all E2E tests
npx playwright test

# Run specific test file  
npx playwright test config-flow.spec.ts

# Run tests with UI mode for debugging
npx playwright test --ui

# Run tests in headed mode (visible browser)
npx playwright test --headed
```

## Test Environment Details

### Home Assistant Configuration

The test environment (`ha_config/configuration.yaml`) provides:

- **Test Entities**: Pre-configured input helpers for switches and sensors
- **Template Entities**: Ready-to-use temperature, humidity, and binary sensors
- **Minimal Logging**: Reduced log noise for cleaner test output
- **API Access**: Enabled for Playwright automation

Available test entities:
- `sensor.test_temperature` - Temperature sensor for target_sensor
- `sensor.test_humidity` - Humidity sensor 
- `sensor.test_floor_temp` - Floor temperature sensor
- `switch.test_heater` - Heater switch
- `switch.test_cooler` - Cooler switch 
- `switch.test_fan` - Fan switch
- `input_boolean.test_opening` - Opening/window sensor

### Authentication

Playwright uses stored authentication state to avoid repeated logins:

1. **First Run**: The global setup will create an owner account
2. **Storage State**: Authentication tokens saved to `tests/auth/storageState.json`
3. **Reuse**: Subsequent test runs use the stored authentication

To regenerate authentication (if tests fail with auth errors):

```bash
rm tests/auth/storageState.json
npx playwright test --headed  # Will recreate auth
```

## Test Structure

```
tests/e2e/
├── docker-compose.yml           # Home Assistant container setup
├── ha_config/                   # Home Assistant configuration
│   └── configuration.yaml      # Minimal test configuration
├── playwright.config.ts         # Playwright test configuration
├── tests/                       # Test files (to be created)
│   ├── auth/                   # Authentication setup
│   │   ├── global-setup.ts     # Initial auth setup
│   │   └── storageState.json   # Stored auth tokens
│   ├── config-flow.spec.ts     # Config flow tests
│   └── options-flow.spec.ts    # Options flow tests
├── test-results/               # Test output and artifacts
└── scripts/
    └── regenerate_baselines.sh # Baseline regeneration script
```

## Baseline Management

Visual regression tests use screenshot baselines stored in the test directories. 

### Regenerating Baselines

When the UI changes legitimately, update baselines:

```bash
# Update all baselines
./scripts/regenerate_baselines.sh

# Or use Playwright's update flag
npx playwright test --update-snapshots
```

The regeneration script will:
1. Ensure Home Assistant is running
2. Run tests with `--update-snapshots` 
3. Commit new baselines (optional)

### Baseline Locations

- `tests/config-flow.spec.ts-snapshots/` - Config flow screenshots
- `tests/options-flow.spec.ts-snapshots/` - Options flow screenshots

## Development Workflow

### Creating New Tests

1. **Start Environment**: `docker compose up -d`
2. **Create Test File**: Add `.spec.ts` files in `tests/`
3. **Run Interactively**: `npx playwright test --ui` to develop/debug
4. **Generate Baselines**: Run tests with `--update-snapshots`
5. **Commit Results**: Include test files and baselines

### Debugging Tests

```bash
# Run with browser visible
npx playwright test --headed

# Run in debug mode with inspector
npx playwright test --debug

# Run specific test with trace
npx playwright test config-flow.spec.ts --trace on
```

### Accessing Home Assistant

During development, you can access the test Home Assistant instance at:
- **URL**: http://localhost:8123
- **Username**: Set during first test run
- **Password**: Set during first test run

## Configuration Testing Scenarios

The E2E tests should cover:

### Config Flow Tests
- [ ] System type selection (heating, cooling, dual, etc.)
- [ ] Basic entity selection (heater, cooler, target_sensor)
- [ ] Advanced options toggling
- [ ] Feature-specific steps (fan, humidity, presets)
- [ ] Validation and error handling
- [ ] Multi-step wizard navigation

### Options Flow Tests  
- [ ] Reconfiguring existing thermostats
- [ ] Adding/removing features
- [ ] Updating entity selections
- [ ] Preset management
- [ ] Advanced settings modification

## Troubleshooting

### Home Assistant Won't Start
```bash
# Check container status
docker compose ps

# View logs
docker compose logs homeassistant

# Restart services
docker compose down && docker compose up -d
```

### Authentication Issues
```bash
# Clear stored auth and retry
rm tests/auth/storageState.json
npx playwright test --headed
```

### Port Conflicts
If port 8123 is in use, edit `docker-compose.yml`:
```yaml
ports:
  - "8124:8123"  # Use different port
```
And update `playwright.config.ts` baseURL accordingly.

### Test Failures
1. **Check Home Assistant Status**: Ensure container is healthy
2. **Review Screenshots**: Check `test-results/` for failure screenshots
3. **Update Baselines**: If UI changed, regenerate with `--update-snapshots`
4. **Check Logs**: Review both HA logs and Playwright output

## CI/CD Integration

For continuous integration:

```yaml
# Example GitHub Actions setup
- name: Start Home Assistant
  run: |
    cd tests/e2e
    docker compose up -d
    # Wait for healthy status
    timeout 120 bash -c 'until docker compose exec homeassistant curl -f http://localhost:8123/; do sleep 5; done'

- name: Run E2E Tests  
  run: |
    cd tests/e2e
    npx playwright test --reporter=github
```

## Token Handling Notes

- **Development**: Tokens stored locally in `storageState.json`
- **CI/CD**: Tokens regenerated on each run via global setup
- **Security**: Never commit real production tokens
- **Cleanup**: Test tokens are ephemeral and container-specific

For production-like testing with real tokens, use environment variables:
```bash
export HA_TOKEN="your_long_lived_token"
npx playwright test
```