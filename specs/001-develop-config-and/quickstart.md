# Quickstart: Implementing Config & Options Flow (iteration per system type)

## Getting Started

1. Checkout the feature branch:

```bash
git checkout 001-develop-config-and
```

2. Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

3. Verify the current state:

```bash
# Run all tests
pytest -q

# Run linting
isort . && black . && flake8 . && codespell
```

## System Type Implementation Status

Work iteratively per system type (one iteration = implement one system type and its tests):

- ✅ `simple_heater` — **COMPLETE** (production-ready with tests and translations)
- ✅ `ac_only` — **COMPLETE** (production-ready with tests and translations)
- ✅ `heater_with_cooler` — **COMPLETE** (production-ready with tests and translations)
- ✅ `heat_pump` — **COMPLETE** (production-ready with tests and translations)

## Implementation Workflow

### For Each System Type

1. **Schema Definition** (`custom_components/dual_smart_thermostat/schemas.py`)
   - Add or verify schema factory function (e.g., `get_simple_heater_schema()`)
   - Define selectors for all required and optional fields
   - Set appropriate defaults and validation rules

2. **Config Flow Integration** (`custom_components/dual_smart_thermostat/config_flow.py`)
   - Add routing logic in `_determine_next_step()` for the system type
   - Connect to the unified `features` step
   - Handle validation and error cases

3. **Feature Steps** (`custom_components/dual_smart_thermostat/feature_steps/`)
   - Implement or verify per-feature step modules
   - Ensure feature availability matches system type capabilities
   - Handle conditional feature dependencies

4. **Testing** (`tests/config_flow/` and `tests/features/`)
   - Write config flow tests for happy path and error cases
   - Add feature interaction tests
   - Verify options flow parity

5. **Translations** (`translations/en.json`)
   - Add user-facing strings for the system type
   - Translate feature labels and descriptions
   - Include helpful error messages

## Quick Reference: System Type Examples

### Simple Heater Configuration

The `simple_heater` system type is the most basic configuration, suitable for heating-only systems.

**Example Configuration:**
```yaml
# Minimal simple_heater config
system_type: simple_heater
heater: switch.living_room_heater
target_sensor: sensor.living_room_temp
cold_tolerance: 0.3
hot_tolerance: 0.3
min_cycle_duration: 300  # 5 minutes
```

**With Features:**
```yaml
# simple_heater with floor heating and presets
system_type: simple_heater
heater: switch.living_room_heater
target_sensor: sensor.living_room_temp

# Floor heating feature
configure_floor_heating: true
floor_sensor: sensor.floor_temp
min_floor_temp: 5
max_floor_temp: 28

# Presets feature
configure_presets: true
presets: [home, away, eco]
home_temp: 21
away_temp: 16
eco_temp: 18
```

**Config Flow Steps:**
1. Select `simple_heater` system type
2. Configure core settings (heater, sensor, tolerances)
3. Select features (floor_heating, presets, openings)
4. Configure floor heating (if enabled)
5. Configure presets (if enabled)
6. Configure openings (if enabled)

### AC-Only Configuration

The `ac_only` system type is for air conditioning units without heating capability.

**Example Configuration:**
```yaml
# Minimal ac_only config
system_type: ac_only
heater: switch.living_room_ac  # AC switch stored under heater key
target_sensor: sensor.living_room_temp
ac_mode: true  # Automatically set for ac_only
cold_tolerance: 0.3
hot_tolerance: 0.3
min_cycle_duration: 300
```

**With Features:**
```yaml
# ac_only with fan, humidity, and openings
system_type: ac_only
heater: switch.living_room_ac
target_sensor: sensor.living_room_temp
ac_mode: true

# Fan feature
configure_fan: true
fan: fan.living_room_fan
fan_on_with_ac: true
fan_air_outside: false

# Humidity feature
configure_humidity: true
humidity_sensor: sensor.living_room_humidity
dryer: switch.dehumidifier
target_humidity: 50
dry_tolerance: 3

# Openings feature
configure_openings: true
openings:
  - entity_id: binary_sensor.front_door
    timeout_open: 30
    timeout_close: 30
openings_scope: cool  # Only pause when cooling
```

**Config Flow Steps:**
1. Select `ac_only` system type
2. Configure core settings (AC switch as heater, sensor)
3. Select features (fan, humidity, openings)
4. Configure fan settings (if enabled)
5. Configure humidity control (if enabled)
6. Configure openings (if enabled)

**Key Differences from Simple Heater:**
- AC switch is stored under the `heater` key for backwards compatibility
- `ac_mode` is automatically set to `true` and hidden in UI
- Available HVAC modes are limited to cooling modes
- Fan and humidity features are commonly used with AC systems

## Implementation Quick Links

**Core Files** (open these first):

- `custom_components/dual_smart_thermostat/config_flow.py::ConfigFlowHandler` — main routing logic and `_determine_next_step`
- `custom_components/dual_smart_thermostat/options_flow.py::OptionsFlowHandler` — options merging and `_determine_options_next_step`
- `custom_components/dual_smart_thermostat/schemas.py` — all schema factories used by flows (get_core_schema, get_features_schema, per-feature schemas)
- `custom_components/dual_smart_thermostat/feature_steps/` — per-feature step helpers (HumiditySteps, FanSteps, OpeningsSteps, PresetsSteps)

**Test Files:**

- `tests/config_flow/test_step_ordering.py` — step ordering validation
- `tests/features/test_ac_features_ux.py` — AC-specific feature tests
- `tests/config_flow/test_simple_heater_config_flow.py` — simple_heater tests
- `tests/config_flow/test_ac_only_config_flow.py` — ac_only tests

When iterating on a system type, run the focused tests referenced above and inspect the listed files to understand current behavior before editing.

## Running Tests

### Focused Test Runs

```bash
# Test specific system type
pytest tests/config_flow/test_simple_heater_config_flow.py -v
pytest tests/config_flow/test_ac_only_config_flow.py -v

# Test step ordering
pytest tests/config_flow/test_step_ordering.py -q

# Test feature interactions
pytest tests/features/test_ac_features_ux.py -q

# Run all config flow tests
pytest tests/config_flow/ -v

# Run with debug logging
pytest tests/config_flow/ --log-cli-level=DEBUG
```

### Full Test Suite

```bash
# Run all tests
pytest -q

# Run with coverage
pytest --cov=custom_components.dual_smart_thermostat --cov-report=html
```

## Code Quality Checks

**All code must pass these checks before commit:**

```bash
# Fix imports
isort .

# Fix formatting
black .

# Check style
flake8 .

# Check spelling
codespell

# Run all pre-commit hooks
pre-commit run --all-files
```

## Debugging Tips

### Enable Debug Logging

In your Home Assistant `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.dual_smart_thermostat: debug
```

### Test-Driven Development

Always follow the RED-GREEN-Refactor cycle:

1. **RED**: Write a failing test first
2. **GREEN**: Make minimal changes to pass the test
3. **Refactor**: Clean up while keeping tests green

### Common Issues

**Issue**: Test fails with "Schema validation error"
- Check that schema factory returns correct voluptuous schema
- Verify defaults are set for optional fields
- Ensure entity selectors use correct domain

**Issue**: Options flow doesn't pre-fill values
- Check that options flow reads from `config_entry.data`
- Verify schema uses same keys as persisted data
- Ensure defaults match config flow

**Issue**: Feature not available for system type
- Check feature availability in `feature_manager.py`
- Verify system type capabilities in `const.py`
- Update feature step logic to handle system type

## Next Steps

When all system types are implemented and tests pass:

1. **Run full test suite**: `pytest -q`
2. **Run linting**: `isort . && black . && flake8 . && codespell`
3. **Update documentation**: Review and update README, CHANGELOG
4. **Open PR**: From `001-develop-config-and` to appropriate target branch
5. **E2E Testing**: Verify Python e2e persistence tests pass (see files with `_e2e_` in `tests/config_flow/`)

## Release Checklist

When preparing for a release, follow this comprehensive checklist to ensure quality and completeness.

### Pre-Release Quality Gates

#### 1. Code Quality
- [ ] All linting passes: `isort . && black . && flake8 . && codespell`
- [ ] No TODO/FIXME comments in production code (move to issues)
- [ ] Code follows project conventions (see `CLAUDE.md`)
- [ ] Pre-commit hooks run successfully: `pre-commit run --all-files`

#### 2. Testing
- [ ] All unit tests pass: `pytest -q`
- [ ] All integration tests pass: `pytest tests/integration/ -v`
- [ ] All config flow tests pass: `pytest tests/config_flow/ -v`
- [ ] All feature tests pass: `pytest tests/features/ -v`
- [ ] Python e2e persistence tests pass: `pytest tests/config_flow/test_e2e_* -v`
- [ ] Contract tests pass: `pytest tests/contracts/ -v`
- [ ] Test coverage meets minimum threshold (check `pytest --cov`)

#### 3. Documentation
- [ ] README.md is up-to-date with new features
- [ ] CHANGELOG.md includes all changes since last release
- [ ] Quickstart guide reflects current implementation
- [ ] Data model documentation is accurate
- [ ] Config flow examples are correct
- [ ] Translation keys are complete (`translations/en.json`)

#### 4. Version Management
- [ ] Update version in `custom_components/dual_smart_thermostat/manifest.json`
- [ ] Version follows semantic versioning (MAJOR.MINOR.PATCH)
- [ ] CHANGELOG.md includes version number and date
- [ ] Git tag matches version: `git tag v0.X.X`

#### 5. HACS Compatibility
- [ ] `hacs.json` metadata is accurate and complete
- [ ] `homeassistant` minimum version is correct in `hacs.json`
- [ ] Integration name matches HACS repository
- [ ] `render_readme` is set appropriately

#### 6. Home Assistant Compatibility
- [ ] Tested against target Home Assistant version (2025.1.0+)
- [ ] All dependencies listed in `manifest.json`
- [ ] `integration_type` and `iot_class` are correct
- [ ] Config flow enabled: `"config_flow": true`
- [ ] Documentation URL is valid

### Version Update Commands

```bash
# Update version in manifest.json
# Edit: custom_components/dual_smart_thermostat/manifest.json
# Change "version": "v0.9.13" to "version": "v0.X.X"

# Verify version
grep '"version"' custom_components/dual_smart_thermostat/manifest.json

# Create git tag
git tag v0.X.X
git push origin v0.X.X
```

### Changelog Update

Update `CHANGELOG.md` with the following structure:

```markdown
## [0.X.X] - YYYY-MM-DD

### Added
- New features and functionality

### Changed
- Changes to existing features
- Breaking changes (with migration guide)

### Fixed
- Bug fixes

### Deprecated
- Features marked for removal

### Removed
- Removed features
```

### HACS Metadata Verification

Verify `hacs.json` contains:

```json
{
  "name": "Dual Smart Thermostat",
  "render_readme": true,
  "hide_default_branch": true,
  "country": [],
  "homeassistant": "2025.1.0",
  "filename": "ha-dual-smart-thermostat.zip"
}
```

### Manifest Verification

Verify `custom_components/dual_smart_thermostat/manifest.json`:

```json
{
  "domain": "dual_smart_thermostat",
  "name": "Dual Smart Thermostat",
  "codeowners": ["@swingerman"],
  "config_flow": true,
  "dependencies": [...],
  "documentation": "https://github.com/swingerman/ha-dual-smart-thermostat.git",
  "integration_type": "device",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/swingerman/ha-dual-smart-thermostat/issues",
  "requirements": [],
  "version": "v0.X.X"
}
```

### Release Process

1. **Create Release Branch**
   ```bash
   git checkout -b release/v0.X.X
   ```

2. **Update Version and Documentation**
   - Update `manifest.json` version
   - Update `CHANGELOG.md`
   - Review and update `README.md`

3. **Run Full Test Suite**
   ```bash
   pytest -q
   isort . && black . && flake8 . && codespell
   pre-commit run --all-files
   ```

4. **Commit and Tag**
   ```bash
   git add .
   git commit -m "chore: Prepare release v0.X.X"
   git tag v0.X.X
   ```

5. **Push to GitHub**
   ```bash
   git push origin release/v0.X.X
   git push origin v0.X.X
   ```

6. **Create GitHub Release**
   - Go to GitHub repository → Releases → Draft new release
   - Select the tag (v0.X.X)
   - Title: "Release v0.X.X"
   - Description: Copy from CHANGELOG.md
   - Attach zip file if required by HACS

7. **Merge to Main**
   ```bash
   git checkout master  # or main
   git merge release/v0.X.X
   git push origin master
   ```

8. **Post-Release**
   - Verify HACS can discover the release
   - Test installation via HACS in a fresh Home Assistant instance
   - Monitor issue tracker for bug reports
   - Update documentation site if applicable

### Rollback Procedure

If critical issues are found after release:

1. **Immediate**
   - Document the issue in GitHub Issues
   - Add warning to README if needed

2. **Create Hotfix**
   ```bash
   git checkout -b hotfix/v0.X.X+1 v0.X.X
   # Fix the issue
   # Update version to v0.X.X+1
   git commit -m "fix: Critical issue description"
   git tag v0.X.X+1
   git push origin hotfix/v0.X.X+1
   git push origin v0.X.X+1
   ```

3. **Release Hotfix**
   - Follow release process for hotfix version
   - Clearly document in CHANGELOG

### Release Notes Template

```markdown
# Release v0.X.X

## 🎉 Highlights

[Brief summary of major features/changes]

## ✨ New Features

- Feature 1: Description
- Feature 2: Description

## 🔧 Improvements

- Improvement 1: Description
- Improvement 2: Description

## 🐛 Bug Fixes

- Fix 1: Description
- Fix 2: Description

## ⚠️ Breaking Changes

- Breaking change 1: Description and migration guide
- Breaking change 2: Description and migration guide

## 📝 Documentation

- Documentation updates
- New guides

## 🙏 Contributors

Thanks to @contributor1, @contributor2 for their contributions!

## 📦 Installation

Install via HACS or manually by downloading the latest release.
```

## Additional Resources

- **Data Model**: See `specs/001-develop-config-and/data-model.md` for canonical data structures
- **Architecture**: See `docs/config_flow/architecture.md` for design decisions
- **E2E Testing**: Python-based e2e persistence tests in `tests/config_flow/test_e2e_*.py` validate complete config/options flows
- **Project Plan**: See `specs/001-develop-config-and/plan.md` for full implementation plan
- **Task List**: See `specs/001-develop-config-and/tasks.md` for implementation tasks
