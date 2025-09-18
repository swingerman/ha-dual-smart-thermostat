# E2E Testing Guide for Dual Smart Thermostat

This document describes the End-to-End testing approach for the Dual Smart Thermostat integration.

## Test Design Philosophy

### TDD Approach (Test-Driven Development)

Following the TDD approach mentioned in the issue:

1. **Write Contract Tests First**: Tests validate the final config entry structure
2. **API Validation**: REST API calls verify persisted configuration matches data model
3. **Red-Green-Refactor**: Tests are written to fail first, then implementation makes them pass

### Test Coverage

Our E2E tests cover the following scenarios:

#### Config Flow Tests
- ✅ **Happy Path**: Complete setup of simple_heater system type
- ✅ **Minimal Setup**: Basic configuration without optional features  
- ✅ **AC-Only System**: Full feature configuration for AC-only systems
- ✅ **Validation**: Error handling for invalid inputs

#### Options Flow Tests
- ✅ **Modify Settings**: Update existing configuration options
- ✅ **Feature Toggle**: Enable/disable optional features in existing configs
- ✅ **Validation**: Error handling in options modification flow
- ✅ **Cancellation**: Cancel options flow without saving changes
- ✅ **System Type Preservation**: Ensure system type cannot be changed

### Key Test Pattern: API Contract Validation

Each test follows this pattern:
1. **Navigate UI**: Use Playwright to interact with Home Assistant UI
2. **Fill Forms**: Set deterministic values for reproducible tests
3. **Complete Flow**: Submit forms and wait for integration creation
4. **API Validation**: Poll Home Assistant REST API to verify config entry
5. **Assert Structure**: Validate config entry matches expected data model

Example:
```typescript
// Complete the UI flow
await haSetup.startAddingIntegration('Dual Smart Thermostat');
// ... UI interactions ...

// Validate via REST API
const api = haSetup.createAPI();
const configEntry = await api.waitForConfigEntry('dual_smart_thermostat', 'Test Name');

// Assert data model compliance
expect(configEntry.data).toMatchObject({
  name: 'Test Name',
  sensor: 'sensor.test_temperature',
  heater: 'switch.test_heater',
  system_type: 'simple_heater'
});
```

## Test Organization

### File Structure
```
tests/specs/
├── config_flow.spec.ts          # Core config flow tests
├── options_flow.spec.ts          # Options modification tests
└── ac_only_config_flow.spec.ts   # AC-only system specific tests
```

### Shared Utilities
```
playwright/setup.ts               # HomeAssistantSetup class with helpers
tests/auth/global-setup.ts        # Authentication management
```

### Visual Baselines
```
baselines/
├── simple_heater/               # Screenshots for simple heater flow
└── ac_only/                     # Screenshots for AC-only flow
```

## Data Model Validation

Tests validate that persisted configuration entries match the canonical data model:

### Simple Heater System
```typescript
expect(configEntry.data).toMatchObject({
  name: string,
  sensor: string,
  heater: string,
  cold_tolerance: number,
  hot_tolerance: number,
  min_cycle_duration: number,
  system_type: 'simple_heater'
});
```

### AC-Only System
```typescript
expect(configEntry.data).toMatchObject({
  name: string,
  sensor: string,
  ac_mode: string,
  system_type: 'ac_only'
});

// Additional options validation
expect(configEntry.options).toMatchObject({
  fan_entity?: string,
  humidity_sensor?: string,
  openings?: string,
  away_temp?: number,
  sleep_temp?: number
});
```

## Running Tests

### Prerequisites
1. Home Assistant running on localhost:8123
2. Node.js and npm installed
3. Playwright browsers installed

### Commands
```bash
# Run all tests
npm test

# Run specific test suite
npx playwright test config_flow.spec.ts

# Debug mode (step through tests)
npm run test:debug

# Update visual baselines
npm run test:update-snapshots

# Type checking
npm run type-check
```

### CI/CD Integration
Tests are designed to run in continuous integration:
- Home Assistant started via Docker Compose
- Tests run headlessly with Chromium
- Screenshots and videos saved on failure
- HTML report generated for review

## Quality Gates

Before merging, all tests must:
- ✅ Pass TypeScript type checking
- ✅ Complete without assertion failures  
- ✅ Validate REST API responses correctly
- ✅ Maintain consistent visual baselines
- ✅ Cover both happy path and error scenarios

This ensures the config flow implementation is robust and maintains data integrity throughout the user experience.