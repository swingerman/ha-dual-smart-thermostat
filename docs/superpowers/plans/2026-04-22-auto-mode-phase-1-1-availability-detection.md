# Auto Mode — Phase 1.1: Availability Detection — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a derived `FeatureManager.is_configured_for_auto_mode` property that returns `True` iff the thermostat has a temperature sensor and at least two distinct climate capabilities (heat / cool / dry / fan).

**Architecture:** A single `@property` on `FeatureManager` that inspects the manager's own state plus the existing `is_configured_for_*` properties. No new modules, no user-visible change; Phase 1.2 will consume the property when wiring the priority engine.

**Tech Stack:** Python 3.13, Home Assistant 2025.1.0+, existing `FeatureManager` / `EnvironmentManager`, pytest.

**Spec:** `docs/superpowers/specs/2026-04-22-auto-mode-phase-1-1-availability-detection-design.md`

---

## Testing Environment

This repo runs tests and lint only inside Docker. Use:

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly.

---

## Prerequisite Fact

During brainstorming we discovered that `FeatureManager` does **not** currently store the temperature sensor entity — only `_humidity_sensor_entity_id`, `_heater_entity_id`, etc. The spec calls for a defensive `temperature sensor is set` guard inside the property, so Task 1 adds a one-line `self._sensor_entity_id = config.get(CONF_SENSOR)` assignment in `__init__` and imports `CONF_SENSOR` from `..const`. This keeps the predicate local to the manager without coupling to `EnvironmentManager` internals.

---

## Task 1: Store the temperature sensor entity on `FeatureManager`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/feature_manager.py`
- Test: `tests/test_auto_mode_availability.py` (new; bootstrap here with one scaffolding test)

- [ ] **Step 1: Create the new test file with a smoke test that exercises the new attribute**

Create `tests/test_auto_mode_availability.py`:

```python
"""Tests for FeatureManager.is_configured_for_auto_mode (Phase 1.1)."""

from unittest.mock import MagicMock

from custom_components.dual_smart_thermostat.const import CONF_HEATER, CONF_SENSOR
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)


def _make_feature_manager(config: dict) -> FeatureManager:
    """Build a FeatureManager from a raw config dict without hass dependencies."""
    hass = MagicMock()
    environment = MagicMock()
    return FeatureManager(hass, config, environment)


def test_feature_manager_stores_sensor_entity_id() -> None:
    """FeatureManager captures the temperature sensor entity from config."""
    config = {
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.indoor_temp",
    }

    fm = _make_feature_manager(config)

    assert fm._sensor_entity_id == "sensor.indoor_temp"


def test_feature_manager_sensor_entity_id_none_when_missing() -> None:
    """With no temperature sensor configured, the attribute is None."""
    config = {CONF_HEATER: "switch.heater"}

    fm = _make_feature_manager(config)

    assert fm._sensor_entity_id is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_availability.py -v
```

Expected: both tests FAIL with `AttributeError: 'FeatureManager' object has no attribute '_sensor_entity_id'`.

- [ ] **Step 3: Add `CONF_SENSOR` to the imports and store the entity in `__init__`**

Open `custom_components/dual_smart_thermostat/managers/feature_manager.py`.

(a) Update the `from ..const import (...)` block (starts around line 18). Insert `CONF_SENSOR` alphabetically so the sorted block reads:

```python
from ..const import (
    ATTR_FAN_MODE,
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_AUX_HEATING_DUAL_MODE,
    CONF_AUX_HEATING_TIMEOUT,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_AIR_OUTSIDE,
    CONF_FAN_HOT_TOLERANCE,
    CONF_FAN_HOT_TOLERANCE_TOGGLE,
    CONF_FAN_MODE,
    CONF_FAN_ON_WITH_AC,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_HVAC_POWER_LEVELS,
    CONF_HVAC_POWER_TOLERANCE,
    CONF_SENSOR,
)
```

(b) In `FeatureManager.__init__`, add a line storing the temperature sensor entity. Place it immediately **after** the existing `self._humidity_sensor_entity_id = config.get(CONF_HUMIDITY_SENSOR)` line (around line 67):

```python
        self._humidity_sensor_entity_id = config.get(CONF_HUMIDITY_SENSOR)
        self._sensor_entity_id = config.get(CONF_SENSOR)
        self._heat_pump_cooling_entity_id = config.get(CONF_HEAT_PUMP_COOLING)
```

(Only the single new line `self._sensor_entity_id = config.get(CONF_SENSOR)` is added; the adjacent lines are shown for context so you find the correct spot.)

- [ ] **Step 4: Run the tests to verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_availability.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Run the broader manager test suite to catch regressions**

```bash
./scripts/docker-test tests/test_heater_mode.py -q
```

Expected: PASS (no behavioural change — the new attribute is added but unused).

- [ ] **Step 6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/feature_manager.py \
        tests/test_auto_mode_availability.py
git commit -m "feat(auto-mode): store temperature sensor entity on FeatureManager

Phase 1.1 (#563) groundwork: capture CONF_SENSOR in FeatureManager so
the forthcoming is_configured_for_auto_mode property can do its
defensive temperature-sensor guard without coupling to EnvironmentManager
internals."
```

---

## Task 2: Implement `is_configured_for_auto_mode`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/feature_manager.py`
- Test: `tests/test_auto_mode_availability.py` (extend)

- [ ] **Step 1: Append the positive-case tests to `tests/test_auto_mode_availability.py`**

Add after the existing tests in the file:

```python
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_AC_MODE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_HEAT_PUMP_COOLING,
    CONF_HUMIDITY_SENSOR,
)


_BASE_SENSOR = {CONF_SENSOR: "sensor.indoor_temp"}


@pytest.mark.parametrize(
    "config",
    [
        # Heater + separate cooler (dual mode) → can_heat + can_cool
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            **_BASE_SENSOR,
        },
        # Heater as AC + dryer + humidity sensor → can_cool + can_dry
        {
            CONF_HEATER: "switch.hvac",
            CONF_AC_MODE: True,
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Heater + fan entity → can_heat + can_fan
        {
            CONF_HEATER: "switch.heater",
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # Heater + dryer + humidity sensor → can_heat + can_dry
        {
            CONF_HEATER: "switch.heater",
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Heat-pump only → can_heat + can_cool (heat pump provides both)
        {
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "sensor.heat_pump_mode",
            **_BASE_SENSOR,
        },
        # Heat pump + fan → can_heat + can_cool + can_fan
        {
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "sensor.heat_pump_mode",
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # All four capabilities → can_heat + can_cool + can_dry + can_fan
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_DRYER: "switch.dryer",
            CONF_FAN: "switch.fan",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
    ],
    ids=[
        "heater+cooler_dual",
        "ac+dryer",
        "heater+fan",
        "heater+dryer",
        "heat_pump_only",
        "heat_pump+fan",
        "all_four",
    ],
)
def test_is_configured_for_auto_mode_true(config: dict) -> None:
    """Configurations with two or more capabilities plus a sensor qualify."""
    fm = _make_feature_manager(config)

    assert fm.is_configured_for_auto_mode is True


@pytest.mark.parametrize(
    "config",
    [
        # Heater-only → can_heat only.
        {
            CONF_HEATER: "switch.heater",
            **_BASE_SENSOR,
        },
        # AC-mode only (heater entity operating as a cooler) → can_cool only.
        {
            CONF_HEATER: "switch.hvac",
            CONF_AC_MODE: True,
            **_BASE_SENSOR,
        },
        # Fan-only → can_fan only (no heater/cooler/dryer).
        {
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # Dryer-only + humidity sensor → can_dry only.
        {
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Otherwise qualifying multi-capability config, but no temperature sensor.
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        },
    ],
    ids=[
        "heater_only",
        "ac_only",
        "fan_only",
        "dryer_only",
        "no_temperature_sensor",
    ],
)
def test_is_configured_for_auto_mode_false(config: dict) -> None:
    """Configurations with zero or one capability, or no sensor, do not qualify."""
    fm = _make_feature_manager(config)

    assert fm.is_configured_for_auto_mode is False
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_availability.py -v
```

Expected: both parametric tests FAIL with `AttributeError: 'FeatureManager' object has no attribute 'is_configured_for_auto_mode'` (all 12 parametrized cases).

- [ ] **Step 3: Add the `is_configured_for_auto_mode` property**

In `custom_components/dual_smart_thermostat/managers/feature_manager.py`, add the new property immediately **after** `is_configured_for_hvac_power_levels` (around line 211) and **before** `set_support_flags`:

```python
    @property
    def is_configured_for_auto_mode(self) -> bool:
        """Determine if the configuration supports Auto Mode.

        Auto Mode requires a temperature sensor and at least two distinct
        climate capabilities (heat / cool / dry / fan). Reserved for
        Phase 1.2 of the Auto Mode roadmap (#563); Phase 1.1 only surfaces
        availability and does not expose HVACMode.AUTO.
        """
        if self._sensor_entity_id is None:
            return False

        can_heat = self.is_configured_for_heat_pump_mode or (
            self._heater_entity_id is not None and not self._ac_mode
        )
        can_cool = (
            self.is_configured_for_heat_pump_mode
            or self.is_configured_for_cooler_mode
            or self.is_configured_for_dual_mode
        )
        can_dry = self.is_configured_for_dryer_mode
        can_fan = self.is_configured_for_fan_mode

        return sum((can_heat, can_cool, can_dry, can_fan)) >= 2
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_availability.py -v
```

Expected: all tests PASS (2 from Task 1 + 7 positive + 5 negative = 14 total).

- [ ] **Step 5: Run the full test suite to verify no regression**

```bash
./scripts/docker-test --tb=short -q
```

Expected: 1386 passed, 2 skipped (same as master baseline), no new failures.

- [ ] **Step 6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/feature_manager.py \
        tests/test_auto_mode_availability.py
git commit -m "feat(auto-mode): add is_configured_for_auto_mode property

Phase 1.1 (#563): FeatureManager now exposes a derived property that
returns True when the configuration supports Auto Mode — temperature
sensor plus >=2 of heat/cool/dry/fan capabilities. Detection only;
HVACMode.AUTO is not yet surfaced in hvac_modes — Phase 1.2 will wire
the priority engine and consume this property."
```

---

## Task 3: Final lint + full test run

**Files:** none (verification only).

- [ ] **Step 1: Run the lint suite**

```bash
./scripts/docker-lint
```

Expected: isort, black, flake8, and ruff are clean on the two touched files. Any codespell findings should be in pre-existing files only (e.g., `htmlcov/`, `config/deps/`, `schemas.py`, `config_flow.py` — confirmed pre-existing noise on master). If `./scripts/docker-lint --fix` modifies files, commit the fixes:

```bash
git add -u
git commit -m "chore: apply linter auto-fixes"
```

- [ ] **Step 2: Run the full test suite one more time**

```bash
./scripts/docker-test
```

Expected: all tests PASS (1386 passed + 14 new = 1400 passed; 2 skipped).

---

## Self-Review Coverage Check

Spec requirements → task coverage:

- Spec §1 Goal & Scope — "single derived property", "not user-visible" → Task 2 (property added; no `hvac_modes` change).
- Spec §2 Decisions Q1 (detection only) → Task 2 (property exists but no consumer).
- Spec §2 Decisions Q2 (lives on FeatureManager) → Task 2.
- Spec §2 Decisions Q3 (mode-capability booleans, heat-pump counts for both) → Task 2 (predicate implementation) + Task 2 Step 1 positive tests (`heat_pump_only`, `heat_pump+fan`).
- Spec §3 Predicate table → Task 2 Step 3 (matches verbatim).
- Spec §4.1 File structure → Task 1 (sensor entity storage), Task 2 (property).
- Spec §4.2 Implementation sketch → Task 2 Step 3 (matches verbatim).
- Spec §5 Error handling & edge cases → each row covered by a parameterised test case (`no_temperature_sensor`, `heat_pump_only`, `dryer_only` → dryer without humidity would fail `is_configured_for_dryer_mode` and yield `can_dry=False`; `ac_only`).
- Spec §6.1 parametric test cases → Task 2 Step 1.
- Spec §6.2 regression surface → Task 2 Step 5 (full suite) + Task 3.
- Spec §7 files touched → Task 1 and Task 2 match.
- Spec §8 risks → mitigations are embedded in the plan (docstring references Phase 1.2, tests pin predicate, conventions followed).
- Spec §9 acceptance criteria → Task 2 Step 4 (tests pass) + Task 3 (lint + full suite).

No gaps.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-22-auto-mode-phase-1-1-availability-detection.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
