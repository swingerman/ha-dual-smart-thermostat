# GitHub Issues Update Plan

**Date**: 2025-01-17
**Context**: Update GitHub issues to reflect refined testing strategy (minimal E2E, comprehensive Python unit tests)

## 🎯 **Issues Requiring Updates**

### **ISSUE #413 - T003: Complete E2E Implementation** ✅ **CLOSE AS COMPLETE**
**Current Status**: Open
**Required Action**: **CLOSE** with completion comment

**Completion Comment Template:**
```markdown
## ✅ T003 COMPLETED BEYOND ORIGINAL SCOPE

**Achievement Summary:**
- ✅ Config flow tests for both `simple_heater` and `ac_only`
- ✅ Options flow tests for both system types with pre-fill validation
- ✅ Integration creation/deletion verification
- ✅ CI workflow running E2E tests automatically
- ✅ Robust `HomeAssistantSetup` helper class with comprehensive methods

**Files Created:**
- ✅ `tests/e2e/tests/specs/basic_heater_config_flow.spec.ts`
- ✅ `tests/e2e/tests/specs/ac_only_config_flow.spec.ts`
- ✅ `tests/e2e/tests/specs/basic_heater_options_flow.spec.ts`
- ✅ `tests/e2e/tests/specs/ac_only_options_flow.spec.ts`
- ✅ `tests/e2e/tests/specs/integration_creation_verification.spec.ts`

**Status**: **COMPLETE** - exceeded original requirements and provides sufficient E2E coverage.

**Next Steps**: Focus shifts to Python unit tests for business logic validation (see issue #417).
```

---

### **ISSUE #414 - T004: Remove Advanced Option** 🔥 **UPDATE TO HIGH PRIORITY**
**Current Status**: Open
**Required Action**: Update priority and add urgency

**Priority Update Comment:**
```markdown
## 🔥 PRIORITY ELEVATED TO HIGH

**Rationale**: With E2E tests complete (T003), removing the Advanced (Custom Setup) option is now the highest priority to clean up the codebase before implementing remaining system types.

**Updated Priority**: **HIGH PRIORITY** (was medium)
**Dependencies**: Should be completed before T005/T006 system type implementations
**Parallel Work**: Can be done in parallel with T007 (Python unit tests) as they touch different files
```

---

### **ISSUE #417 - T007: Contract & Options-Parity Tests** 🔥 **MAJOR SCOPE EXPANSION**
**Current Status**: Open
**Required Action**: **MAJOR UPDATE** - expand scope and elevate priority

**Scope Expansion Comment:**
```markdown
## 🔥 SCOPE EXPANDED & PRIORITY ELEVATED

**New Focus**: Comprehensive Python unit tests for business logic and data structure validation

**Priority Change**: **ELEVATED TO HIGH PRIORITY** (was medium)

**Expanded Scope - New Files to Create:**
- `tests/unit/test_climate_entity_generation.py` — **NEW HIGH PRIORITY**: Test actual HA climate entity creation and configuration
- `tests/unit/test_config_entry_data_structure.py` — **NEW HIGH PRIORITY**: Test saved config entry data matches canonical `data-model.md`
- `tests/unit/test_system_type_configs.py` — **NEW HIGH PRIORITY**: Test system-specific configurations
- `tests/integration/test_integration_behavior.py` — **NEW HIGH PRIORITY**: Test HA integration behavior
- `tests/contracts/test_schemas.py` — Original contract tests
- `tests/options/test_options_parity.py` — Original options parity tests

**Rationale**: E2E tests handle UI journeys; Python tests should handle business logic, data structures, and HA integration behavior.

**Updated Acceptance Criteria:**
- ✅ Climate entity structure tests validate actual HA entity attributes per system type
- ✅ Config entry data structure tests ensure saved data matches `data-model.md`
- ✅ System type configuration tests validate system-specific behavior
- ✅ Integration behavior tests validate HA core integration
- ✅ Original contract tests for schema validation

**Parallel Work**: Can be done in parallel with T004 (different files)
```

---

### **ISSUE #415 - T005: Complete heater_cooler** 📉 **REDUCE SCOPE**
**Current Status**: Open
**Required Action**: Update to remove E2E requirements

**Scope Reduction Comment:**
```markdown
## 📉 SCOPE REDUCED - PYTHON IMPLEMENTATION ONLY

**Scope Change**: Focus on Python implementation and unit tests only; E2E tests removed from scope

**Rationale**: E2E tests are expensive to maintain and should focus on critical user journeys only. Python unit tests are sufficient for validating business logic.

**REMOVED FROM SCOPE:**
- ❌ E2E Playwright tests for `heater_cooler`
- ❌ Screenshot baseline management
- ❌ UI interaction testing

**ADDED TO SCOPE:**
- ✅ `tests/unit/test_heater_cooler_climate_entity.py` — Test climate entity generation

**Updated Acceptance Criteria:**
- ✅ Unit and contract tests for `heater_cooler` pass
- ✅ Python tests validate climate entity structure and behavior
- ✅ E2E tests for `simple_heater`/`ac_only` remain green
- ❌ **REMOVED**: E2E test coverage requirement

**Dependencies**: Should be done after T004 (Advanced option removal) and T007 (Python unit test framework)
```

---

### **ISSUE #416 - T006: Complete heat_pump** 📉 **REDUCE SCOPE**
**Current Status**: Open
**Required Action**: Update to remove E2E requirements (same as T005)

**Scope Reduction Comment:**
```markdown
## 📉 SCOPE REDUCED - PYTHON IMPLEMENTATION ONLY

**Scope Change**: Focus on Python implementation and unit tests only; E2E tests removed from scope

**Rationale**: E2E tests are expensive to maintain and should focus on critical user journeys only. Python unit tests are sufficient for validating business logic.

**REMOVED FROM SCOPE:**
- ❌ E2E Playwright tests for `heat_pump`
- ❌ Screenshot baseline management
- ❌ UI interaction testing

**ADDED TO SCOPE:**
- ✅ `tests/unit/test_heat_pump_climate_entity.py` — Test climate entity generation

**Updated Acceptance Criteria:**
- ✅ Contract tests for `heat_pump` pass
- ✅ Python tests validate climate entity structure and behavior
- ✅ `heat_pump_cooling` entity selector functionality works correctly
- ❌ **REMOVED**: E2E test coverage requirement

**Dependencies**: Should be done after T004 (Advanced option removal) and T007 (Python unit test framework)
```

---

## 📊 **Updated Priority Matrix**

| Issue | Task | Current Priority | New Priority | Action Required |
|-------|------|-----------------|--------------|-----------------|
| #413 | T003 E2E Implementation | Open | ✅ **CLOSE** | Close as complete |
| #414 | T004 Remove Advanced | Medium | 🔥 **HIGH** | Update priority |
| #417 | T007 Python Unit Tests | Medium | 🔥 **HIGH** | Expand scope + elevate |
| #415 | T005 heater_cooler | Medium | 📉 **MEDIUM** | Reduce E2E scope |
| #416 | T006 heat_pump | Medium | 📉 **MEDIUM** | Reduce E2E scope |
| #418 | T008 Normalize keys | Medium | 📊 **MEDIUM** | No change needed |
| #419 | T009 Models.py | Medium | 📊 **MEDIUM** | No change needed |
| #420 | T010 Test reorg | Medium | 📉 **LOW** | Reduce priority |
| #421 | T011 Schema consolidation | Medium | 📉 **LOW** | Reduce priority |
| #422 | T012 Documentation | Medium | 📊 **MEDIUM** | No change needed |

## 🚀 **Implementation Plan**

1. **Close #413** - T003 complete beyond scope
2. **Update #414** - Mark as high priority 
3. **Major update #417** - Expand scope and elevate priority
4. **Update #415 & #416** - Remove E2E scope requirements
5. **Optional**: Update lower priority issues (#420, #421) to reflect reduced priority

**Total Issues Requiring Updates**: 5 critical updates needed
