# E2E Tests for Dual Smart Thermostat

This directory contains Playwright-based End-to-End tests for the Dual Smart Thermostat Home Assistant integration.

## Overview

The E2E tests validate:
- Configuration flow for different system types (simple_heater, ac_only)
- Options flow for modifying existing configurations
- REST API validation of persisted configuration data
- Visual regression testing with baseline images

## Prerequisites

1. **Home Assistant Instance**: Tests require a running Home Assistant instance
   - Default URL: `http://localhost:8123`
   - Override with `HA_URL` environment variable

2. **Authentication**: Tests use stored authentication state
   - Username/password can be set via `HA_USERNAME`/`HA_PASSWORD` environment variables
   - Default: `admin`/`admin`

3. **Test Entities**: The following test entities should exist in HA:
   - `switch.test_heater` - A switch entity to use as heater
   - `sensor.test_temperature` - A temperature sensor
   - `switch.test_cooler` - A switch entity to use as cooler (for AC tests)

## Running Tests

### All Tests
```bash
cd tests/e2e
npx playwright test
```

### Specific Test Suite
```bash
npx playwright test config_flow.spec.ts
npx playwright test options_flow.spec.ts
```

### With Browser UI (for debugging)
```bash
npx playwright test --headed
```

### Debug Mode
```bash
npx playwright test --debug
```

## Test Structure

### Config Flow Tests (`config_flow.spec.ts`)
- Tests the initial setup flow for new integrations
- Validates system type selection (simple_heater focus)
- Verifies form validation and error handling
- Checks REST API config entry data structure

### Options Flow Tests (`options_flow.spec.ts`)
- Tests modification of existing configurations
- Validates temperature, tolerance, and HVAC behavior settings
- Checks options persistence via REST API

## Data Model Validation

Tests validate that config entries match the expected data model:

### Simple Heater Required Keys
- `name`: string - Integration name
- `heater`: string - Heater entity ID
- `target_sensor`: string - Temperature sensor entity ID
- `system_type`: 'simple_heater' - System type identifier
- `cold_tolerance`: number - Cold tolerance in degrees
- `hot_tolerance`: number - Hot tolerance in degrees

### Optional Keys with Defaults
- `ac_mode`: boolean - AC mode enable/disable
- `initial_hvac_mode`: string - Initial HVAC mode
- `min_temp`: number - Minimum temperature
- `max_temp`: number - Maximum temperature
- `target_temp`: number - Default target temperature
- `precision`: number - Temperature precision
- `target_temp_step`: number - Temperature step size

## Visual Regression Testing

Baseline images are stored in `baselines/` subdirectories:
- `baselines/simple_heater/` - Simple heater system type baselines
- `baselines/ac_only/` - AC only system type baselines

### Pixel Difference Tolerances
- Form screenshots: 2% tolerance
- Dialog screenshots: 1% tolerance
- Integration list screenshots: 3% tolerance

### Updating Baselines
```bash
npx playwright test --update-snapshots
```

## Environment Variables

- `HA_URL`: Home Assistant URL (default: `http://localhost:8123`)
- `HA_USERNAME`: HA username (default: `admin`)
- `HA_PASSWORD`: HA password (default: `admin`)
- `CI`: Set to enable CI-specific behaviors (retries, etc.)

## Troubleshooting

### Authentication Issues
1. Check Home Assistant is running and accessible
2. Verify username/password are correct
3. Delete `playwright/storageState.json` to force re-authentication

### Test Entity Issues
1. Ensure test entities exist in Home Assistant
2. Check entity IDs match those used in tests
3. Verify entities are in expected states

### Visual Regression Issues
1. Check if legitimate UI changes occurred
2. Update baselines if changes are expected
3. Adjust pixel tolerances if needed for different environments