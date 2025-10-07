# Housekeeping Instructions for All Tasks

This document explains how to mark tasks as complete in the specification files.

## Quick Reference

All GitHub issues (#415, #416, #418-422, #436) now include housekeeping instructions in their description.

## Standard Housekeeping Workflow

When you complete a task, follow these steps:

### 1. Mark task as complete in tasks.md

Edit `specs/001-develop-config-and/tasks.md` and update the task header:

**Example:**
```diff
- T005 — Complete `heater_cooler` implementation (Phase 1C) 🔥 [TDD APPROACH] — [GitHub Issue #415]
+ T005 — Complete `heater_cooler` implementation ✅ [COMPLETED] — [GitHub Issue #415]
```

### 2. Update task ordering section

In the "Task Ordering and dependency notes" section:
- Move the completed task to the ✅ completed list
- Update the "Recommended Sequential Path" diagram if needed

### 3. Commit changes

```bash
git add specs/001-develop-config-and/tasks.md
git commit -m "docs: Mark T{XXX} ({task_name}) as complete in tasks.md"
```

### 4. Close the GitHub issue

```bash
gh issue close {ISSUE_NUMBER} --comment "Task completed. tasks.md updated to reflect completion."
```

Or close via GitHub web UI with a completion comment.

## Tasks with Housekeeping Instructions

All open issues now have housekeeping sections:

| Task | Issue | Priority | Lines in tasks.md |
|------|-------|----------|-------------------|
| T005 - heater_cooler | [#415](https://github.com/swingerman/ha-dual-smart-thermostat/issues/415) | 🔥 High | 196-336 |
| T006 - heat_pump | [#416](https://github.com/swingerman/ha-dual-smart-thermostat/issues/416) | 🔥 High | 338-410 |
| T007A - Feature interactions | [#436](https://github.com/swingerman/ha-dual-smart-thermostat/issues/436) | 🔥 Critical | 422-539 |
| T008 - Normalize keys | [#418](https://github.com/swingerman/ha-dual-smart-thermostat/issues/418) | ✅ Medium | 541-550 |
| T009 - models.py | [#419](https://github.com/swingerman/ha-dual-smart-thermostat/issues/419) | ✅ Medium | 552-563 |
| T010 - Test reorg | [#420](https://github.com/swingerman/ha-dual-smart-thermostat/issues/420) | ⚪ Optional | 565-579 |
| T011 - Schema consolidation | [#421](https://github.com/swingerman/ha-dual-smart-thermostat/issues/421) | ⚪ Optional | 581-596 |
| T012 - Documentation | [#422](https://github.com/swingerman/ha-dual-smart-thermostat/issues/422) | ✅ Medium | 598-611 |

## Current Release Path

```
T004 → {T005, T006} → T007A → T008 → {T009, T012} → RELEASE
✅      (parallel)      ↑               (parallel)
                    [Critical
                     for features]
```

**Legend:**
- ✅ Completed
- 🔥 High Priority / Critical
- ✅ Medium Priority
- ⚪ Optional

## Already Completed Tasks

These tasks are already marked as complete:

| Task | Issue | Status |
|------|-------|--------|
| T001 - E2E Playwright scaffold | [#411](https://github.com/swingerman/ha-dual-smart-thermostat/issues/411) | ✅ Closed |
| T002 - Playwright tests | [#412](https://github.com/swingerman/ha-dual-smart-thermostat/issues/412) | ✅ Closed |
| T003 - Complete E2E implementation | [#413](https://github.com/swingerman/ha-dual-smart-thermostat/issues/413) | ✅ Closed |
| T004 - Remove Advanced option | [#414](https://github.com/swingerman/ha-dual-smart-thermostat/issues/414) | ✅ Closed |
| T007 - Python unit tests | [#417](https://github.com/swingerman/ha-dual-smart-thermostat/issues/417) | ❌ Removed (duplicate) |

## Verification

After marking a task complete, verify:

1. ✅ Task header updated in tasks.md with ✅ [COMPLETED] marker
2. ✅ Task moved to completed list in "Task Ordering" section
3. ✅ Changes committed to git
4. ✅ GitHub issue closed with comment
5. ✅ No references to the task remain in "CURRENT PRIORITIES" section

## Tips

- **Use grep to find task references:**
  ```bash
  grep -n "T005" specs/001-develop-config-and/tasks.md
  ```

- **Check issue status:**
  ```bash
  gh issue list --state all | grep "T005"
  ```

- **View task in context:**
  ```bash
  sed -n '196,336p' specs/001-develop-config-and/tasks.md
  ```

## Questions?

If you're unsure about any step, check the housekeeping instructions in the GitHub issue itself - each issue has specific line numbers and commands tailored to that task.
