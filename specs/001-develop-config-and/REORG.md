# Test Reorganization Plan

Purpose: reorganize existing tests into a clearer folder structure without changing behavior. Do the move in a single commit to preserve history and make review easier.

Proposed target layout:

```
tests/
├── config_flow/
├── features/
├── openings/
├── presets/
├── integration/
└── unit/
```

Steps
1. Create a mapping of source -> destination for all test files. Keep the mapping in this document.
2. Run a dry-run to ensure imports will still resolve. Update test imports only if necessary.
3. Move files in a single commit (git mv ...) and run focused tests.
4. Fix any failing tests and repeat until green.
5. Push branch and open PR with a clear description "Reorganize tests into coherent folders".

Mapping (examples — update after review):
- `tests/config_flow/test_options_flow.py` -> `tests/config_flow/test_options_flow.py` (same)
- `tests/features/test_ac_features_ux.py` -> `tests/features/test_ac_features_ux.py` (same)
- `tests/presets/test_comprehensive_preset_logic.py` -> `tests/presets/test_comprehensive_preset_logic.py`

Notes
- Avoid renaming test functions or changing test fixtures in the same commit.
- Run `pytest -q` after the move and fix any import paths.
