# GitHub Issues Sync Status (2025-01-06)

## Summary
✅ All GitHub issues are now synced with tasks.md

## Issues Status

### ✅ Completed/Closed Tasks
- **T001** (#411) - E2E Playwright scaffold - ✅ CLOSED (completed)
- **T002** (#412) - Playwright tests for config & options flows - ✅ CLOSED (completed)
- **T003** (#413) - Complete E2E implementation - ✅ CLOSED (completed beyond scope)
- **T004** (#414) - Remove Advanced Custom Setup option - ✅ CLOSED (completed)
- **T007** (#417) - Python Unit Tests - ✅ CLOSED (removed as duplicate of T005/T006)

### 🔥 High Priority - Active Development
- **T005** (#415) - Complete heater_cooler implementation
  - Status: ✅ SYNCED with acceptance criteria (updated 2025-01-06)
  - Includes: TDD approach, comprehensive acceptance criteria, bug fixes documented

- **T006** (#416) - Complete heat_pump implementation
  - Status: ✅ SYNCED with acceptance criteria (updated 2025-01-06)
  - Includes: TDD approach, comprehensive acceptance criteria, heat_pump_cooling specifics

### ✅ Medium Priority - Post Implementation
- **T008** (#418) - Normalize collected_config keys and constants
  - Status: ✅ OPEN (no updates needed - original content still valid)

- **T009** (#419) - Add models.py dataclasses
  - Status: ✅ OPEN (no updates needed - original content still valid)

### ⚪ Optional - Not Blocking Release
- **T010** (#420) - Perform test reorganization
  - Status: ✅ SYNCED with OPTIONAL priority (updated 2025-01-06)
  - Added: "PRIORITY: ⚪ OPTIONAL - Nice-to-have, not blocking release"
  - Added: "Release Impact: None - Can be done post-release"

- **T011** (#421) - Investigate schema duplication
  - Status: ✅ SYNCED with OPTIONAL priority (updated 2025-01-06)
  - Added: "PRIORITY: ⚪ OPTIONAL - Nice-to-have, not blocking release"
  - Added: "Release Impact: None - Only do if duplication becomes painful"

### ✅ Essential - Release Preparation
- **T012** (#422) - Polish documentation & release prep
  - Status: ✅ OPEN (no updates needed - original content still valid)

## Critical Path to Release (Updated)

```
T004 → {T005, T006} → T008 → {T009, T012} → RELEASE
✅      (parallel)      📋      (parallel)
```

**Legend:**
- ✅ Completed
- 🔥 High Priority (T005, T006)
- ✅ Medium Priority (T008, T009, T012)
- ⚪ Optional (T010, T011)

## Key Changes Made (2025-01-06)

1. **T007 Removed**: Duplicate of T005/T006 acceptance criteria
   - All required tests moved into T005/T006
   - GitHub issue #417 closed with explanation

2. **T005/T006 Enhanced**: Added comprehensive acceptance criteria
   - TDD approach documented
   - Config/options flow core requirements
   - Data structure validation
   - Field-specific validation
   - Business logic validation
   - Bug fixes documented (T005)

3. **T010/T011 Marked Optional**: Not blocking release
   - Clear "OPTIONAL" priority added
   - "Release Impact: None" documented
   - Can be done post-release

4. **Task Ordering Revised**: Clear critical path defined
   - T004 first (cleanup)
   - T005/T006 parallel (core implementation with tests)
   - T008 cleanup (normalize keys)
   - T009/T012 parallel (models + docs)
   - T010/T011 optional post-release

## Verification Commands

Check all issues are synced:
```bash
# List open tasks
gh issue list | grep -E "T00[5-9]|T01[0-2]"

# Check T005/T006 have acceptance criteria
gh issue view 415 | grep -i "acceptance criteria"
gh issue view 416 | grep -i "acceptance criteria"

# Check T010/T011 marked optional
gh issue view 420 | grep -i "optional"
gh issue view 421 | grep -i "optional"

# Verify T007 is closed
gh issue view 417 --json state --jq '.state'
```

## Next Steps

1. ✅ Start T004 (Remove Advanced option) - if not already complete
2. 🔥 Implement T005/T006 in parallel with TDD approach
3. ✅ T008 normalization after learning from T005/T006
4. ✅ T009/T012 in parallel for release prep
5. ⚪ T010/T011 optional post-release improvements
