# GitHub Issues Update - Acceptance Criteria (2025-01-06)

This document contains the updated acceptance criteria for GitHub issues #415 and #416.

---

## Issue #415: Complete `heater_cooler` implementation

**URL**: https://github.com/swingerman/ha-dual-smart-thermostat/issues/415

### Proposed Update

Add the following section after "## Special Notes" (or replace existing "## Acceptance Criteria"):

```markdown
## Acceptance Criteria (UPDATED 2025-01-06 - TDD + DATA VALIDATION)

### Test-Driven Development (TDD)
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in existing simple_heater/ac_only tests

### Config Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully to completion
2. ✅ **Valid configuration is created** - Config entry data matches `data-model.md` structure
3. ✅ **Climate entity is created** - Verify entity appears in HA with correct entity_id

### Config Flow - Data Structure Validation
- ✅ All required fields from schema are present in saved config
- ✅ Field types match expected types (entity_id strings, numeric values, booleans)
- ✅ System-specific fields: `heater`, `cooler`, `target_sensor` are entity_ids
- ✅ `heat_cool_mode` field exists with correct boolean default
- ✅ Advanced settings are flattened to top level (tolerances, min_cycle_duration)
- ✅ `name` field is collected (bug fix 2025-01-06 verified)

### Options Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully
2. ✅ **Configuration is updated correctly** - Modified fields are persisted
3. ✅ **Unmodified fields are preserved** - Fields not changed remain intact

### Options Flow - Data Structure Validation
- ✅ `name` field is omitted in options flow
- ✅ Options flow pre-fills all heater_cooler fields from existing config
- ✅ System type is displayed but non-editable
- ✅ Updated config matches `data-model.md` structure after changes

### Field-Specific Validation (Unit Tests)
- ✅ Optional entity fields accept empty values (vol.UNDEFINED pattern)
- ✅ Numeric fields have correct defaults when not provided
- ✅ Required fields (heater, cooler, sensor) raise validation errors when missing
- ✅ Validation: same heater/cooler entity produces error
- ✅ Validation: same heater/sensor entity produces error

### Feature Integration
- ✅ Features step allows toggling features on/off
- ✅ Enabled features show their configuration steps
- ✅ Feature settings are saved under correct keys
- ✅ Feature settings match schema definitions

### Business Logic Validation
- ✅ HeaterCoolerDevice class works correctly with schema
- ✅ Config flow creates working climate entity
- ✅ Climate entity has correct HVAC modes for heater_cooler system

### Quality Gates
- ✅ All code must pass linting checks
- ✅ All unit tests must pass
- ✅ Pull requests must target branch `copilot/fix-157`

### Scope Notes
- ❌ **REMOVED**: E2E test coverage (covered by simple_heater/ac_only E2E tests)
- ✅ **FOCUS**: Python unit/integration tests for data validation and business logic

### Bug Fixes Applied (2025-01-06)
- ✅ Missing name field in get_heater_cooler_schema() - config_flow.py:248
- ✅ Missing fan_hot_tolerance numeric field - schemas.py:690
- ✅ fan_hot_tolerance_toggle validation error (vol.UNDEFINED) - schemas.py:695
- ✅ Unified fan/humidity schemas to remove duplication
- ✅ Added translations for fan_hot_tolerance fields
- ✅ Updated README.md documentation
```

---

## Issue #416: Complete `heat_pump` implementation

**URL**: https://github.com/swingerman/ha-dual-smart-thermostat/issues/416

### Proposed Update

Add the following section after "## Special Notes" (or replace existing "## Acceptance Criteria"):

```markdown
## Acceptance Criteria (UPDATED 2025-01-06 - TDD + DATA VALIDATION)

### Test-Driven Development (TDD)
- ✅ All tests written BEFORE implementation (RED phase)
- ✅ Tests fail initially with clear error messages
- ✅ Implementation makes tests pass (GREEN phase)
- ✅ No regressions in existing system type tests

### Config Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully to completion
2. ✅ **Valid configuration is created** - Config entry data matches `data-model.md` structure
3. ✅ **Climate entity is created** - Verify entity appears in HA with correct entity_id

### Config Flow - Data Structure Validation
- ✅ All required fields from schema are present in saved config
- ✅ Field types match expected types (entity_id strings, numeric values, booleans)
- ✅ System-specific fields: `heater` (entity_id), `heat_pump_cooling` (entity_id or boolean)
- ✅ `target_sensor` is entity_id
- ✅ Advanced settings are flattened to top level (tolerances, min_cycle_duration)
- ✅ `name` field is collected in config flow

### Options Flow - Core Requirements
1. ✅ **Flow completes without error** - All steps navigate successfully
2. ✅ **Configuration is updated correctly** - Modified fields are persisted
3. ✅ **Unmodified fields are preserved** - Fields not changed remain intact

### Options Flow - Data Structure Validation
- ✅ `name` field is omitted in options flow
- ✅ Options flow pre-fills all heat_pump fields from existing config
- ✅ System type is displayed but non-editable
- ✅ Updated config matches `data-model.md` structure after changes

### Field-Specific Validation (Unit Tests)
- ✅ `heat_pump_cooling` accepts entity_id (preferred) or boolean
- ✅ `heat_pump_cooling` entity selector functionality works correctly
- ✅ Optional entity fields accept empty values (vol.UNDEFINED pattern)
- ✅ Numeric fields have correct defaults when not provided
- ✅ Required fields (heater, sensor) raise validation errors when missing

### Feature Integration
- ✅ Features step allows toggling features on/off
- ✅ Enabled features show their configuration steps
- ✅ Feature settings are saved under correct keys
- ✅ Feature settings match schema definitions

### Business Logic Validation
- ✅ HeatPumpDevice class works correctly with schema
- ✅ Config flow creates working climate entity
- ✅ Climate entity has correct HVAC modes based on heat_pump_cooling state
- ✅ Dynamic heat_pump_cooling entity state changes update available HVAC modes

### Quality Gates
- ✅ All code must pass linting checks
- ✅ All unit tests must pass
- ✅ Pull requests must target branch `copilot/fix-157`

### Scope Notes
- ❌ **REMOVED**: E2E test coverage (covered by simple_heater/ac_only E2E tests)
- ✅ **FOCUS**: Python unit/integration tests for data validation and business logic
```

---

## How to Apply These Updates

### Option 1: Via GitHub Web UI
1. Navigate to each issue URL
2. Click "Edit" on the issue description
3. Replace the "## Acceptance Criteria" section with the new content above
4. Save changes

### Option 2: Via GitHub CLI (when available)
```bash
# Install GitHub CLI if needed
# Then update issues programmatically

# Issue #415
gh issue edit 415 --body-file /path/to/new-body.md

# Issue #416
gh issue edit 416 --body-file /path/to/new-body.md
```

### Option 3: Bulk Update Script
Create individual body files and use the script in this directory if GitHub CLI becomes available.

---

## Summary of Changes

Both issues now have:
- ✅ Comprehensive acceptance criteria matching tasks.md
- ✅ TDD approach clearly documented
- ✅ Core requirements (flow works + valid config)
- ✅ Data structure validation requirements
- ✅ Business logic validation requirements
- ✅ Clear scope notes (Python tests, not E2E)
- ✅ Quality gates unchanged
- ✅ Issue #415 includes bug fixes from 2025-01-06

These updates align GitHub issues with the refined strategy documented in `tasks.md`.
