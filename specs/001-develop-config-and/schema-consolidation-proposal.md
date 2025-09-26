# Schema Consolidation Proposal

Status: Draft

Summary
-------
This document evaluates options to consolidate duplicated schema-like metadata that currently lives in `custom_components/dual_smart_thermostat/const.py` and `custom_components/dual_smart_thermostat/schemas.py`.

Scope
-----
- Identify duplicated definitions such as `SYSTEM_TYPES`, `CONF_PRESETS`/`CONF_PRESETS_OLD`, default values, and feature availability maps.
- Propose consolidation approaches, estimate effort and risk, and recommend a migration plan.

Options evaluated
-----------------
1. Option A — Single metadata module (recommended)
   - Description: Introduce `custom_components/dual_smart_thermostat/metadata.py` (or extend `const.py`) containing structured metadata: system type descriptors, preset definitions, default values, and feature availability maps. `schemas.py` will generate voluptuous selectors from this metadata.
   - Effort: small → medium
   - Risk: low
   - Migration steps: add metadata module; update `schemas.py` to reference metadata; run tests; remove duplicates.

2. Option B — Typed models + generator
   - Description: Define dataclasses/TypedDicts in `models.py` representing metadata and generate selectors from the dataclasses using helper functions.
   - Effort: medium
   - Risk: medium
   - Migration steps: implement models; create generators; refactor `schemas.py`.

3. Option C — Keep constants minimal + docs-driven metadata
   - Description: Keep `const.py` for runtime constants, move preset/feature metadata into `data-model.md` and `models.py`. `schemas.py` will read metadata at runtime or import models.
   - Effort: medium → large
   - Risk: medium → high
   - Migration steps: move definitions to `models.py`/`data-model.md`, update `schemas.py` and translations.

Recommendation
--------------
Pursue Option A: introduce a small `metadata.py` that centralizes labels, keys, and default values. Update `schemas.py` to consume that metadata via lightweight generator helpers. This minimizes risk and preserves the current runtime layout.

Next steps
----------
- Implement a small proof-of-concept: create `metadata.py` with `SYSTEM_TYPES` and `CONF_PRESETS` moved; update `schemas.py::get_system_type_schema()` to import labels from `metadata.py` and run unit tests.
- If PoC passes, proceed with the full migration in small commits per module.

Acceptance criteria
-------------------
- Add the metadata module and update tests to reference the new API.
- No change in persisted config keys or UI labels after first migration step.
- Contract tests continue to pass during and after migration.

Notes
-----
Keep translation keys unchanged; use existing `translations/` files for UI labels and ensure `metadata.py` exposes keys compatible with them.
