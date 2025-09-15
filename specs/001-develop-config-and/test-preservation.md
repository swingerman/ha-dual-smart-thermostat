# Test Preservation Guide

Purpose
-------
Ensure currently passing unit tests remain passing while implementing the feature-complete config/options flow and while performing schema consolidation.

Local workflow
--------------
1. Install developer requirements (if needed):

```bash
python -m pip install -r requirements-dev.txt
```

2. Run focused tests while developing (fast feedback):

```bash
# Run a single test file
pytest tests/test_ac_ux.py -q

# Run a single test function
pytest tests/test_ac_ux.py::test_my_feature -q
```

3. Run the full test-suite before opening a PR:

```bash
pytest -q
```

CI guidance
-----------
- All PRs that touch `custom_components/dual_smart_thermostat/*` or `specs/001-develop-config-and/*` must run `pytest -q` in CI.
- For large refactors that touch schema contracts, add a contract test that asserts the expected set of keys/types produced by `schemas.py` for a representative `system_type`.
- Do not merge PRs that reduce the number of passing tests unless a migration plan is present and the PR includes the corresponding test updates and documentation.

Failure handling
----------------
- If tests fail after a refactor, revert the refactor or add targeted fixes and tests that explain the change.
- For intentionally deprecated behavior, add a dedicated migration test and document the user impact in `specs/001-develop-config-and/migration.md`.

Notes
-----
- Keep tests deterministic: avoid relying on external network calls or slow timing-sensitive assertions.
- Mark flaky tests as a separate task to stabilize; do not use skips as a long-term solution.
