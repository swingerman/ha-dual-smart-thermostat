# E2E Implementation Guide: Home Assistant Config & Options Flows

## Overview

This guide documents the practical implementation patterns discovered during T003 config flow development. These patterns should be applied to all future E2E test development for the dual_smart_thermostat integration.

## Reference Implementation

**✅ Working Examples**: 
- `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts` - **Clean implementation using reusable helpers**
- `tests/e2e/tests/specs/config_flow.spec.ts` - Legacy implementation with detailed debugging
- `tests/e2e/playwright/setup.ts` - **Reusable helper functions and step detection utilities**

**Key Features**:
- Complete 4-step config flow implementation (System Type → Basic Config → Features → Confirmation)
- Reusable `HomeAssistantSetup` class for integration discovery and config flow initiation
- Shared step detection functions (`isSystemTypeStep`, `isBasicConfigurationStep`, etc.)
- Comprehensive form handling and error recovery
- **Status**: Production-ready with clean, maintainable code

## Reusable Helper Functions

### 1. HomeAssistantSetup Class
```typescript
import { HomeAssistantSetup } from '../../playwright/setup';

// Create helper instance
const helper = new HomeAssistantSetup(page);

// Start integration config flow (handles navigation, search, click)
await helper.startIntegrationConfigFlow('Dual Smart Thermostat');

// Continue with existing config flow dialog
await helper.continueConfigFlow();
```

### 2. Step Detection Functions
```typescript
import { isSystemTypeStep, isBasicConfigurationStep, isFeatureConfigurationStep, isConfirmationStep } from '../../playwright/setup';

// Analyze current dialog state
const dialogText = await page.locator('.mdc-dialog.mdc-dialog--open').textContent();
const hasRadioButtons = await page.locator('input[type="radio"]').count() > 0;
const hasNameField = await page.locator('input[name="name"]').count() > 0;
const hasPickerFields = await page.locator('ha-picker-field').count() > 0;
const hasCheckboxes = await page.locator('input[type="checkbox"]').count() > 0;

// Use reusable detection functions
const isSystemType = isSystemTypeStep(dialogText, hasRadioButtons);
const isBasicConfig = isBasicConfigurationStep(dialogText, hasNameField, hasPickerFields);
const isFeatureConfig = isFeatureConfigurationStep(dialogText);
const isConfirmation = isConfirmationStep(dialogText, hasNameField, hasPickerFields, hasCheckboxes);
```

## Home Assistant UI Interaction Patterns

### 1. Config Flow Navigation
```typescript
// Config flows use modal dialogs - URL never changes
// Step detection must use dialog content analysis
const dialogText = await page.locator('.mdc-dialog.mdc-dialog--open').textContent();
const isBasicConfig = isBasicConfigurationStep(dialogText, hasNameField, hasPickerFields);
```

### 2. Form Element Interactions
```typescript
// ha-picker-field (entity selectors)
await element.click();                    // Open picker
await page.keyboard.type(entityId);      // Type entity ID  
await page.keyboard.press('Tab');        // Confirm (NOT Enter - closes dialog)

// Standard inputs
await element.fill(value);               // Direct fill for text inputs

// Visibility checks (essential)
const isVisible = await element.isVisible();
if (!isVisible) continue;                // Skip invisible fields
```

### 3. Reliable Element Selectors
```typescript
// Discovered working selectors:
'ha-dialog[open]'                                    // Config flow dialog
'dialog-data-entry-flow button[part="base"]'        // Submit buttons  
'ha-integration-list-item:has-text("...")'          // Integration cards
'input[name="name"]'                                 // Name fields
'ha-picker-field[aria-label="..."]'                 // Entity pickers with labels
```

## Step Detection Algorithm

Use this pattern for detecting config/options flow steps:

```typescript
// Analyze form elements for step detection
const hasNameField = await page.locator('input[name="name"]').count() > 0;
const hasPickerFields = await page.locator('ha-picker-field').count() > 0;
const hasCheckboxes = await page.locator('input[type="checkbox"]').count() > 0;

// Detect step types
const isBasicConfig = (dialogText?.includes('Basic Configuration') || 
                      dialogText?.includes('Name')) && 
                      (hasNameField || hasPickerFields);

const isFeatureConfig = (dialogText?.includes('Feature') ||
                        dialogText?.includes('Additional')) &&
                        hasCheckboxes && !isBasicConfig;

const isConfirmation = dialogText?.includes('Success') ||
                      dialogText?.includes('Complete') ||
                      (!hasNameField && !hasPickerFields && !hasCheckboxes);
```

## Form Filling Strategy

### Universal Form Filling Pattern
```typescript
// Get all form elements
const formElements = await page.locator('input, ha-picker-field, select').all();

for (const element of formElements) {
  // Check visibility first
  if (!(await element.isVisible())) continue;
  
  // Skip non-data elements
  const type = await element.getAttribute('type');
  if (type === 'radio' || type === 'checkbox') continue;
  
  // Determine field context
  const label = await element.getAttribute('aria-label');
  const placeholder = await element.getAttribute('placeholder');
  const context = (label || placeholder || '').toLowerCase();
  
  // Fill based on element type and context
  const tagName = await element.evaluate(el => el.tagName);
  if (tagName === 'HA-PICKER-FIELD') {
    // Entity picker pattern
    await element.click();
    await page.keyboard.type(getEntityForContext(context));
    await page.keyboard.press('Tab');
  } else {
    // Standard input pattern
    await element.fill(getValueForContext(context, type));
  }
}
```

## Config vs Options Flow Differences

### Key Differences to Handle
```typescript
// Config Flow:
// - System type: Radio buttons ('text="Simple Heater Only"')
// - All fields empty initially
// - Creates new integration

// Options Flow:  
// - System type: Select dropdown (selectOption())
// - Fields pre-filled with existing values
// - Updates existing integration
```

## Testing Best Practices

### 1. Incremental Development
- Build tests step-by-step
- Validate each step before proceeding
- Use comprehensive logging for debugging

### 2. Environment Management
```bash
# Clean environment for consistent testing
docker-compose down && docker-compose up -d
sleep 15  # Wait for HA startup

# Single worker to avoid conflicts
npx playwright test --workers=1
```

### 3. Debugging Techniques
```typescript
// Essential debugging patterns
console.log(`Step ${step}: ${dialogText?.slice(0, 100)}...`);
await page.screenshot({ path: `debug-step-${step}.png` });

// Form element analysis
console.log(`Element: ${tagName} (type: ${type}, label: ${label})`);
console.log(`Visible: ${await element.isVisible()}`);
```

## Implementation Checklist

For any new E2E test implementation:

### ✅ Setup Phase
- [ ] Use working config flow test as template
- [ ] Set up proper environment isolation (fresh Docker container)
- [ ] Configure single worker execution

### ✅ Navigation Phase  
- [ ] Navigate to integrations page
- [ ] Search for integration using `type()` with delay (not `fill()`)
- [ ] Click proper integration card (`ha-integration-list-item`)

### ✅ Flow Detection Phase
- [ ] Implement step detection using dialog content + form elements
- [ ] Handle all 4 steps: system type, basic config, features, confirmation
- [ ] Add comprehensive logging for each step

### ✅ Form Interaction Phase
- [ ] Check element visibility before interaction
- [ ] Use proper interaction method per element type
- [ ] Handle `ha-picker-field` with click → type → Tab pattern
- [ ] Apply context-based value selection

### ✅ Validation Phase
- [ ] Verify flow completion (redirect to integrations page)
- [ ] Add API validation for persisted configuration
- [ ] Include error handling and recovery

## Future Development

### Apply These Patterns To:
1. **T003 Options Flow** - Use select dropdown for system type, handle pre-filling
2. **AC-Only Config Flow** - Apply same patterns with different feature sets
3. **Heater-Cooler Flow** - Extend patterns for dual-mode systems
4. **Error Handling Tests** - Use same interaction patterns for validation testing

### Documentation References
- **Recommended Implementation**: `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts`
- **Reusable Helper Functions**: `tests/e2e/playwright/setup.ts`
- **Legacy Implementation**: `tests/e2e/tests/specs/config_flow.spec.ts`
- **Setup Instructions**: `tests/e2e/README.md`
- **Testing Guide**: `tests/e2e/TESTING.md`

This guide ensures consistency and reliability across all E2E test implementations while leveraging the hard-won insights from the initial config flow development.
