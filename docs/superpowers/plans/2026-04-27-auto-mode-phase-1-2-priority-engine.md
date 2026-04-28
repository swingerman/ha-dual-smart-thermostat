# Auto Mode — Phase 1.2: Priority Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire `HVACMode.AUTO` into the dual_smart_thermostat climate entity. A pure `AutoModeEvaluator` decides which concrete sub-mode (HEAT / COOL / DRY / FAN_ONLY / IDLE-keep) runs based on the priority table from issue #563. The climate entity intercepts AUTO at `async_set_hvac_mode` and `_async_control_climate` and dispatches via the evaluator. Mode-flap prevention prevents thrashing.

**Architecture:** New pure decision class `managers/auto_mode_evaluator.py` (no HA deps beyond `HVACMode` and the existing `HVACActionReason` enums). `climate.py` constructs the evaluator when `features.is_configured_for_auto_mode`, extends `_attr_hvac_modes` with AUTO, and routes AUTO selections through a new `_async_evaluate_auto_and_dispatch` helper. Sensor stalls are passed in as kwargs because they live on the climate entity, not on `EnvironmentManager`.

**Tech Stack:** Python 3.13, Home Assistant 2025.1.0+, existing `EnvironmentManager` / `OpeningManager` / `FeatureManager`, pytest.

**Spec:** `docs/superpowers/specs/2026-04-27-auto-mode-phase-1-2-priority-engine-design.md`

---

## Testing Environment

This repo runs tests and lint only inside Docker:

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
```

Do NOT call `pytest`, `black`, `isort`, `flake8`, or `ruff` directly.

---

## Shared Context

### Evaluator surface

```python
# managers/auto_mode_evaluator.py

@dataclass(frozen=True)
class AutoDecision:
    next_mode: HVACMode | None  # None = idle-keep (stay in last picked sub-mode)
    reason: HVACActionReason


class AutoModeEvaluator:
    def __init__(self, environment, openings, features): ...
    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision: ...
```

### Existing `EnvironmentManager` primitives the evaluator uses

| Primitive | Returns |
|---|---|
| `is_floor_hot` | bool — `cur_floor_temp >= max_floor_temp` |
| `is_too_cold(target_attr)` | bool — `cur_temp <= target − cold_tolerance` |
| `is_too_hot(target_attr)` | bool — `cur_temp >= target + hot_tolerance` |
| `is_too_moist` | bool — `cur_humidity >= target_humidity + moist_tolerance` |
| `is_within_fan_tolerance(target_attr)` | bool — `target+hot_tol < cur_temp <= target+hot_tol+fan_hot_tol` |
| `cur_temp`, `cur_humidity`, `cur_floor_temp` | floats / `None` |
| `target_temp`, `target_temp_high`, `target_temp_low`, `target_humidity` | floats / `None` |
| `_cold_tolerance`, `_hot_tolerance`, `_moist_tolerance`, `_dry_tolerance` | floats |
| `_get_active_tolerance_for_mode()` | `(cold_tol, hot_tol)` tuple — mode-aware |

For "urgent" 2× tolerance checks the evaluator computes its own thresholds inline rather than adding new methods on `EnvironmentManager`. This keeps the change footprint inside the new module.

### `OpeningManager`

`any_opening_open(hvac_mode_scope=OpeningHvacModeScope.AUTO)` — already exists; returns `True` if any opening is currently open and the scope matches.

### `FeatureManager` capability flags (existing)

- `is_configured_for_auto_mode` (Phase 1.1)
- `is_configured_for_dryer_mode`
- `is_configured_for_fan_mode`
- `is_range_mode`

### Sensor stall

Lives on the climate entity (`self._sensor_stalled`, `self._humidity_sensor_stalled`). Climate passes them into `evaluate(...)` as kwargs.

---

## Task 1: Scaffold `AutoModeEvaluator` module

**Files:**
- Create: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (new)

- [ ] **Step 1: Write the failing test**

Create `tests/test_auto_mode_evaluator.py`:

```python
"""Tests for AutoModeEvaluator (Phase 1.2)."""

from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.managers.auto_mode_evaluator import (
    AutoDecision,
    AutoModeEvaluator,
)


def _make_evaluator(**overrides) -> AutoModeEvaluator:
    """Build an evaluator with stub managers; overrides set attribute values on stubs."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()

    # Sensible defaults — every test overrides what it cares about.
    environment.cur_temp = 20.0
    environment.cur_humidity = 50.0
    environment.cur_floor_temp = None
    environment.target_temp = 21.0
    environment.target_temp_low = None
    environment.target_temp_high = None
    environment.target_humidity = 50.0
    environment._cold_tolerance = 0.5
    environment._hot_tolerance = 0.5
    environment._moist_tolerance = 5.0
    environment._dry_tolerance = 5.0
    environment._fan_hot_tolerance = 0.0
    environment.is_floor_hot = False
    environment.is_too_cold.return_value = False
    environment.is_too_hot.return_value = False
    environment.is_too_moist = False
    environment.is_within_fan_tolerance.return_value = False

    openings.any_opening_open.return_value = False

    features.is_configured_for_dryer_mode = False
    features.is_configured_for_fan_mode = False
    features.is_range_mode = False

    for key, value in overrides.items():
        if "." in key:
            obj_name, attr = key.split(".", 1)
            setattr(locals()[obj_name], attr, value)
        else:
            raise AssertionError(f"Override key must be 'object.attr', got {key!r}")

    return AutoModeEvaluator(environment, openings, features)


def test_evaluator_constructs_with_managers() -> None:
    """AutoModeEvaluator is importable and constructible."""
    ev = _make_evaluator()
    assert ev is not None


def test_auto_decision_is_frozen_dataclass() -> None:
    """AutoDecision exposes next_mode and reason and is hashable/frozen."""
    decision = AutoDecision(next_mode=HVACMode.HEAT, reason=HVACActionReason.TARGET_TEMP_NOT_REACHED)
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.TARGET_TEMP_NOT_REACHED
    # frozen → cannot reassign
    try:
        decision.next_mode = HVACMode.COOL
    except Exception as exc:  # FrozenInstanceError
        assert "frozen" in str(exc).lower() or "cannot" in str(exc).lower()
    else:
        raise AssertionError("AutoDecision should be frozen")
```

- [ ] **Step 2: Run test to verify it fails**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'custom_components.dual_smart_thermostat.managers.auto_mode_evaluator'`.

- [ ] **Step 3: Create the new module**

Create `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`:

```python
"""Auto Mode priority evaluator (Phase 1.2).

Pure decision class. Reads from injected EnvironmentManager / OpeningManager /
FeatureManager and returns an AutoDecision. Holds no mutable state beyond
construction-time references; the previous decision is passed in by the caller
so the evaluator itself is reentrant.

Reserved for the climate entity's AUTO mode intercept; never wired in unless
the user has selected ``HVACMode.AUTO`` and ``features.is_configured_for_auto_mode``
is True.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.climate import HVACMode

from ..hvac_action_reason.hvac_action_reason import HVACActionReason


@dataclass(frozen=True)
class AutoDecision:
    """Result of one priority evaluation.

    ``next_mode`` is ``None`` when the engine wants to keep the last picked
    sub-mode running (e.g., all targets met — actuators idle naturally via
    the existing bang-bang controller).
    """

    next_mode: HVACMode | None
    reason: HVACActionReason


class AutoModeEvaluator:
    """Decides which concrete sub-mode AUTO runs each tick."""

    def __init__(self, environment, openings, features) -> None:
        self._environment = environment
        self._openings = openings
        self._features = features

    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        """Return the next AutoDecision. Subsequent tasks fill this in."""
        # Placeholder — overridden in Task 2.
        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): scaffold AutoModeEvaluator + AutoDecision

Phase 1.2 (#563) groundwork: pure decision class with the evaluate()
method as a placeholder; subsequent tasks fill in the priority table.
AutoDecision is a frozen dataclass exposing next_mode and reason."
```

---

## Task 2: Safety priorities (overheat, opening) + sensor stall handling

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append the failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_floor_hot_returns_overheat() -> None:
    """Priority 1: floor temp at limit forces idle / OVERHEAT."""
    ev = _make_evaluator(**{"environment.is_floor_hot": True})
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.OVERHEAT


def test_opening_open_returns_opening_idle() -> None:
    """Priority 2: opening detected forces idle / OPENING."""
    ev = _make_evaluator()
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.OPENING


def test_temperature_stall_returns_temperature_stall() -> None:
    """Temperature sensor stall → idle / TEMPERATURE_SENSOR_STALLED."""
    ev = _make_evaluator()
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TEMPERATURE_SENSOR_STALLED


def test_floor_hot_preempts_opening_and_stall() -> None:
    """Safety priority 1 wins over priority 2 and over stall."""
    ev = _make_evaluator(**{"environment.is_floor_hot": True})
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.reason == HVACActionReason.OVERHEAT


def test_opening_preempts_stall() -> None:
    """Opening (safety 2) wins over a stall."""
    ev = _make_evaluator()
    ev._openings.any_opening_open.return_value = True
    decision = ev.evaluate(last_decision=None, temp_sensor_stalled=True)
    assert decision.reason == HVACActionReason.OPENING
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: the 5 new tests FAIL.

- [ ] **Step 3: Implement safety priorities + stall**

Replace the `evaluate` body in `auto_mode_evaluator.py`:

```python
    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        """Return the next AutoDecision based on the priority table."""

        # Priority 1: floor overheat — preempts everything.
        if self._environment.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)

        # Priority 2: opening — preempts everything except floor overheat.
        from homeassistant.components.climate import HVACMode  # local: avoid circular

        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)

        # Sensor stall: if the temperature sensor stalled, pause completely.
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        # Subsequent priorities filled in by later tasks.
        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)
```

Add this helper near the top of the module (right under the `AutoDecision` dataclass):

```python
def _auto_scope():
    """Return the OpeningHvacModeScope value used for AUTO opening checks."""
    # Local import to avoid pulling the enum at module load time and to keep
    # the evaluator's external surface minimal.
    from ..managers.opening_manager import OpeningHvacModeScope

    return OpeningHvacModeScope.ALL
```

We use `OpeningHvacModeScope.ALL` because at AUTO time we want any configured opening (regardless of its declared scope) to pause the engine. If a user wants opening-pause to apply only when AUTO ends up running a specific concrete sub-mode, that nuance lives in the existing scope filter — but at the AUTO entry level we treat any open opening as a global pause.

- [ ] **Step 4: Run tests to verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 7 tests PASS (2 from Task 1 + 5 new).

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): add safety + stall priorities to evaluator

Phase 1.2 (#563): floor overheat (priority 1), opening detection
(priority 2), and temperature sensor stall handling. Floor overheat
preempts everything; opening preempts stall; humidity priorities are
suppressed when the humidity sensor stalls (covered in Task 3)."
```

---

## Task 3: Urgent + normal humidity priorities (3, 6) + humidity stall

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append failing tests**

```python
def test_humidity_urgent_2x_returns_dry() -> None:
    """Priority 3: humidity at 2x moist tolerance triggers DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0   # target 50, moist_tol 5 → 2x = 60
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_HUMIDITY


def test_humidity_normal_returns_dry() -> None:
    """Priority 6: humidity at 1x moist tolerance triggers DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # target 50, moist_tol 5 → 1x = 55
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY


def test_humidity_priority_skipped_when_no_dryer() -> None:
    """When dryer not configured, humidity priorities are silent."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = False
    ev._environment.cur_humidity = 65.0  # would otherwise be urgent
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None  # no other priority fires here
    assert decision.reason != HVACActionReason.AUTO_PRIORITY_HUMIDITY


def test_humidity_stall_suppresses_humidity_priorities() -> None:
    """A stalled humidity sensor → humidity priorities skipped."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0  # would be urgent
    decision = ev.evaluate(last_decision=None, humidity_sensor_stalled=True)
    assert decision.next_mode != HVACMode.DRY


def test_humidity_below_target_does_not_trigger() -> None:
    """Humidity below target does not pick DRY (Phase 1.2 doesn't humidify)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 30.0
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.DRY
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 5 new tests FAIL (each returns `next_mode=None` from the placeholder logic).

- [ ] **Step 3: Implement humidity priorities**

Replace the `evaluate` body in `auto_mode_evaluator.py` with:

```python
    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        env = self._environment
        feats = self._features

        # Priority 1: floor overheat.
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)

        # Priority 2: opening detected.
        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)

        # Sensor stalls.
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = (
            feats.is_configured_for_dryer_mode and not humidity_sensor_stalled
        )

        # Priority 3 (urgent): humidity at 2x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priorities 4-5 fill in next task (urgent temp).

        # Priority 6 (normal): humidity at 1x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priorities 7-10 fill in next tasks.

        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)

    @staticmethod
    def _humidity_at(env, *, multiplier: int) -> bool:
        """Check if cur_humidity is at or above target_humidity + multiplier×moist_tolerance."""
        if env.cur_humidity is None or env.target_humidity is None:
            return False
        threshold = env.target_humidity + multiplier * env._moist_tolerance
        return env.cur_humidity >= threshold
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 12 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): add urgent + normal humidity priorities

Phase 1.2 (#563): priorities 3 (humidity 2x moist tolerance) and 6
(humidity 1x moist tolerance) both pick DRY mode and emit
AUTO_PRIORITY_HUMIDITY. Capability filter: no dryer configured =>
humidity priorities are silent. Humidity sensor stall => humidity
priorities skipped (temp/fan still run)."
```

---

## Task 4: Urgent + normal temperature priorities (4, 5, 7, 8) — single target mode

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append failing tests**

```python
def test_temp_urgent_cold_2x_returns_heat() -> None:
    """Priority 4: temp at 2x cold tolerance triggers HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.0   # target 21, cold_tol 0.5, 2x = 1.0 below
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_temp_urgent_hot_2x_returns_cool() -> None:
    """Priority 5: temp at 2x hot tolerance triggers COOL."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 22.0   # target 21, hot_tol 0.5, 2x = 1.0 above
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_temp_normal_cold_returns_heat() -> None:
    """Priority 7: temp at 1x cold tolerance triggers HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.5  # target 21, cold_tol 0.5, 1x below
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT


def test_temp_normal_hot_returns_cool() -> None:
    """Priority 8: temp at 1x hot tolerance triggers COOL."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 21.5  # target 21, hot_tol 0.5, 1x above
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_humidity_urgent_preempts_temp_normal() -> None:
    """Urgent humidity (priority 3) wins over normal temp (priority 7)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 60.0  # urgent
    ev._environment.cur_temp = 20.5      # normal cold
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.DRY


def test_temp_urgent_preempts_humidity_normal() -> None:
    """Urgent temp (priority 4) wins over normal humidity (priority 6)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # normal moist
    ev._environment.cur_temp = 20.0      # urgent cold
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 6 new tests FAIL.

- [ ] **Step 3: Implement temperature priorities**

Replace the `evaluate` body in `auto_mode_evaluator.py`:

```python
    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        env = self._environment
        feats = self._features

        # Priority 1: floor overheat.
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)

        # Priority 2: opening detected.
        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)

        # Temperature sensor stall pauses everything (DRY also reads cur_temp/floor sensor).
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = (
            feats.is_configured_for_dryer_mode and not humidity_sensor_stalled
        )

        # Priority 3 (urgent): humidity at 2x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priority 4 (urgent): temp at 2x cold tolerance below cold_target.
        if self._temp_too_cold(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 5 (urgent): temp at 2x hot tolerance above hot_target.
        if self._temp_too_hot(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 6 (normal): humidity at 1x moist tolerance.
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priority 7 (normal): temp at 1x cold tolerance.
        if self._temp_too_cold(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 8 (normal): temp at 1x hot tolerance.
        if self._temp_too_hot(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priorities 9-10 fill in next tasks.

        return AutoDecision(next_mode=None, reason=HVACActionReason.NONE)

    def _cold_target(self, env) -> float | None:
        """Single-target mode: target_temp. Range mode (Task 6): target_temp_low."""
        if self._features.is_range_mode and env.target_temp_low is not None:
            return env.target_temp_low
        return env.target_temp

    def _hot_target(self, env) -> float | None:
        """Single-target mode: target_temp. Range mode (Task 6): target_temp_high."""
        if self._features.is_range_mode and env.target_temp_high is not None:
            return env.target_temp_high
        return env.target_temp

    def _temp_too_cold(self, env, *, multiplier: int) -> bool:
        cold_target = self._cold_target(env)
        if env.cur_temp is None or cold_target is None:
            return False
        return env.cur_temp <= cold_target - multiplier * env._cold_tolerance

    def _temp_too_hot(self, env, *, multiplier: int) -> bool:
        hot_target = self._hot_target(env)
        if env.cur_temp is None or hot_target is None:
            return False
        return env.cur_temp >= hot_target + multiplier * env._hot_tolerance
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 18 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): add urgent + normal temperature priorities

Phase 1.2 (#563): priorities 4, 5 (2x cold/hot tolerance => HEAT/COOL,
urgent) and 7, 8 (1x cold/hot tolerance => HEAT/COOL, normal). Helpers
_cold_target / _hot_target encapsulate the single-vs-range-mode target
selection; range-mode default to target_temp until Task 6 wires
features.is_range_mode."
```

---

## Task 5: Comfort priority (9) and idle (10)

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append failing tests**

```python
def test_fan_band_returns_fan_only() -> None:
    """Priority 9: temp in fan band → FAN_ONLY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.FAN_ONLY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_COMFORT


def test_fan_skipped_when_no_fan_configured() -> None:
    """No fan configured → priority 9 silent."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = False
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode != HVACMode.FAN_ONLY


def test_temp_normal_hot_preempts_fan_band() -> None:
    """Priority 8 (normal hot) beats priority 9 (fan band)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 21.5  # 1x hot tolerance
    ev._environment.is_within_fan_tolerance.return_value = True
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_idle_when_all_targets_met() -> None:
    """Priority 10: nothing fires → idle-keep with TARGET_TEMP_REACHED."""
    ev = _make_evaluator()  # all defaults: nothing fires
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_idle_after_dry_uses_humidity_reached_reason() -> None:
    """Priority 10 idle after DRY → reason TARGET_HUMIDITY_REACHED."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    last = AutoDecision(next_mode=HVACMode.DRY, reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_HUMIDITY_REACHED
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 5 new tests FAIL.

- [ ] **Step 3: Implement priorities 9 and 10**

In `auto_mode_evaluator.py`, replace the comment block `# Priorities 9-10 fill in next tasks.` and the bare default `return` with:

```python
        # Priority 9 (comfort): temp in fan-tolerance band, fan available.
        if (
            feats.is_configured_for_fan_mode
            and self._fan_band(env)
        ):
            return AutoDecision(
                next_mode=HVACMode.FAN_ONLY,
                reason=HVACActionReason.AUTO_PRIORITY_COMFORT,
            )

        # Priority 10 (idle): all targets met. Reason depends on prior decision.
        idle_reason = HVACActionReason.TARGET_TEMP_REACHED
        if last_decision is not None and last_decision.next_mode == HVACMode.DRY:
            idle_reason = HVACActionReason.TARGET_HUMIDITY_REACHED
        return AutoDecision(next_mode=None, reason=idle_reason)
```

Also add this helper at the end of the class (next to `_temp_too_hot`):

```python
    def _fan_band(self, env) -> bool:
        """Whether cur_temp is within the fan-tolerance comfort band."""
        target_attr = "_target_temp_high" if (
            self._features.is_range_mode and env.target_temp_high is not None
        ) else "_target_temp"
        return env.is_within_fan_tolerance(target_attr)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 23 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): add comfort fan band and idle-keep priorities

Phase 1.2 (#563): priority 9 (fan-tolerance band => FAN_ONLY,
AUTO_PRIORITY_COMFORT) and priority 10 (idle-keep with reason derived
from the previous decision: TARGET_HUMIDITY_REACHED if previously DRY,
otherwise TARGET_TEMP_REACHED)."
```

---

## Task 6: Range-mode target selection

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py` (no logic change — `_cold_target` / `_hot_target` / `_fan_band` already branch on `is_range_mode`; this task pins behaviour with tests).
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append failing tests**

```python
def test_range_mode_uses_target_temp_low_for_heat() -> None:
    """Range mode: HEAT priority uses target_temp_low."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.target_temp = 21.0  # ignored in range mode
    ev._environment.cur_temp = 18.4  # below low - 1x cold_tol (0.5) = below 18.5
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT


def test_range_mode_uses_target_temp_high_for_cool() -> None:
    """Range mode: COOL priority uses target_temp_high."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.target_temp = 21.0  # ignored in range mode
    ev._environment.cur_temp = 24.6  # above high + 1x hot_tol (0.5) = above 24.5
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_range_mode_idle_between_targets() -> None:
    """Range mode: temp between low and high → idle."""
    ev = _make_evaluator()
    ev._features.is_range_mode = True
    ev._environment.target_temp_low = 19.0
    ev._environment.target_temp_high = 24.0
    ev._environment.cur_temp = 21.5  # comfortably between
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED
```

- [ ] **Step 2: Run tests — verify they pass on first run**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: all 26 tests PASS. The implementation already supports range-mode via `_cold_target` / `_hot_target` from Task 4; this task pins the contract with tests.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auto_mode_evaluator.py
git commit -m "test(auto-mode): pin range-mode target selection behaviour

Phase 1.2 (#563): explicit tests for the range-mode branch of
_cold_target / _hot_target — HEAT uses target_temp_low, COOL uses
target_temp_high, idle between."
```

---

## Task 7: Mode-flap prevention

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py` (extend)

- [ ] **Step 1: Append failing tests**

```python
def test_flap_prevention_stays_heat_while_goal_pending() -> None:
    """In HEAT, still cold (goal pending) and no urgent → stay HEAT."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 20.5  # 1x below — goal still pending
    last = AutoDecision(next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.HEAT


def test_flap_prevention_switches_to_dry_on_urgent_humidity() -> None:
    """In HEAT, urgent humidity emerges → switch to DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_temp = 20.5  # still cold (goal pending)
    ev._environment.cur_humidity = 60.0  # urgent humidity
    last = AutoDecision(next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.DRY


def test_flap_prevention_normal_humidity_does_not_preempt_heat() -> None:
    """Normal-tier humidity does NOT preempt active urgent-tier HEAT."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_temp = 20.5  # 1x below (goal pending)
    ev._environment.cur_humidity = 55.0  # normal moist
    last = AutoDecision(next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.HEAT


def test_flap_prevention_rescans_when_goal_reached() -> None:
    """In HEAT, temp recovered → full top-down scan picks fresh."""
    ev = _make_evaluator()
    ev._environment.cur_temp = 21.0  # at target — goal reached
    last = AutoDecision(next_mode=HVACMode.HEAT, reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode is None  # idle
    assert decision.reason == HVACActionReason.TARGET_TEMP_REACHED


def test_flap_prevention_dry_stays_until_dry_goal_reached() -> None:
    """In DRY, humidity still high (goal pending) → stay DRY."""
    ev = _make_evaluator()
    ev._features.is_configured_for_dryer_mode = True
    ev._environment.cur_humidity = 55.0  # still 1x — goal pending
    last = AutoDecision(next_mode=HVACMode.DRY, reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY)
    decision = ev.evaluate(last_decision=last)
    assert decision.next_mode == HVACMode.DRY
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: 5 new tests FAIL — the current evaluator always re-runs the full scan, so flap prevention isn't doing anything yet (some pass coincidentally, others fail).

- [ ] **Step 3: Implement flap prevention**

Wrap the priority cascade in a goal-pending / urgent-preempt check. Update `evaluate` in `auto_mode_evaluator.py`:

```python
    def evaluate(
        self,
        last_decision: AutoDecision | None,
        *,
        temp_sensor_stalled: bool = False,
        humidity_sensor_stalled: bool = False,
    ) -> AutoDecision:
        env = self._environment
        feats = self._features

        # Safety preempts everything (no flap protection for safety).
        if env.is_floor_hot:
            return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)
        if self._openings.any_opening_open(hvac_mode_scope=_auto_scope()):
            return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)
        if temp_sensor_stalled:
            return AutoDecision(
                next_mode=None,
                reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
            )

        humidity_available = (
            feats.is_configured_for_dryer_mode and not humidity_sensor_stalled
        )

        # Flap prevention: if last_decision is set and that mode's goal is
        # still pending, only an urgent-tier priority can preempt.
        if last_decision is not None and last_decision.next_mode is not None:
            if self._goal_pending(last_decision.next_mode, humidity_available):
                # Allow urgent priorities (3, 4, 5) to preempt.
                urgent = self._urgent_decision(humidity_available)
                if urgent is not None and urgent.next_mode != last_decision.next_mode:
                    return urgent
                # Otherwise stay.
                return last_decision

        # Goal reached or no last_decision: full top-down scan.
        return self._full_scan(humidity_available, last_decision)

    def _goal_pending(self, mode, humidity_available: bool) -> bool:
        env = self._environment
        if mode == HVACMode.HEAT:
            return self._temp_too_cold(env, multiplier=1)
        if mode == HVACMode.COOL:
            return self._temp_too_hot(env, multiplier=1)
        if mode == HVACMode.DRY:
            return humidity_available and self._humidity_at(env, multiplier=1)
        if mode == HVACMode.FAN_ONLY:
            return self._fan_band(env)
        return False

    def _urgent_decision(self, humidity_available: bool) -> AutoDecision | None:
        env = self._environment
        if humidity_available and self._humidity_at(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )
        if self._temp_too_cold(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        if self._temp_too_hot(env, multiplier=2):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )
        return None

    def _full_scan(
        self,
        humidity_available: bool,
        last_decision: AutoDecision | None,
    ) -> AutoDecision:
        env = self._environment
        feats = self._features

        urgent = self._urgent_decision(humidity_available)
        if urgent is not None:
            return urgent

        # Priority 6 (normal humidity).
        if humidity_available and self._humidity_at(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.DRY,
                reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
            )

        # Priority 7 (normal cold).
        if self._temp_too_cold(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.HEAT,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 8 (normal hot).
        if self._temp_too_hot(env, multiplier=1):
            return AutoDecision(
                next_mode=HVACMode.COOL,
                reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
            )

        # Priority 9 (fan band).
        if feats.is_configured_for_fan_mode and self._fan_band(env):
            return AutoDecision(
                next_mode=HVACMode.FAN_ONLY,
                reason=HVACActionReason.AUTO_PRIORITY_COMFORT,
            )

        # Priority 10 (idle).
        idle_reason = HVACActionReason.TARGET_TEMP_REACHED
        if last_decision is not None and last_decision.next_mode == HVACMode.DRY:
            idle_reason = HVACActionReason.TARGET_HUMIDITY_REACHED
        return AutoDecision(next_mode=None, reason=idle_reason)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: all 31 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py \
        tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): add mode-flap prevention to evaluator

Phase 1.2 (#563): when last_decision is set and that mode's goal is
still pending, only an urgent-tier priority can preempt the current
mode. Otherwise the evaluator stays in the same sub-mode, preventing
thrashing on the normal-tier boundary."
```

---

## Task 8: Climate.py — extend hvac_modes + construct evaluator

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py`
- Test: `tests/test_auto_mode_integration.py` (new)

- [ ] **Step 1: Write the failing integration tests**

Create `tests/test_auto_mode_integration.py`:

```python
"""Integration tests for AUTO mode end-to-end through the climate entity."""

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common


@pytest.mark.asyncio
async def test_auto_in_hvac_modes_when_two_capabilities(hass: HomeAssistant) -> None:
    """AUTO appears in hvac_modes when heater + cooler are both configured."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO in state.attributes["hvac_modes"]


@pytest.mark.asyncio
async def test_auto_absent_from_hvac_modes_for_heater_only(hass: HomeAssistant) -> None:
    """AUTO is NOT in hvac_modes for a heater-only setup (1 capability)."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO not in state.attributes["hvac_modes"]
```

- [ ] **Step 2: Run tests — verify they fail (or pass for the second one)**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```

Expected: `test_auto_in_hvac_modes_when_two_capabilities` FAILS (AUTO not exposed); `test_auto_absent_from_hvac_modes_for_heater_only` PASSES (no AUTO yet, single-capability config).

- [ ] **Step 3: Construct the evaluator + extend hvac_modes in climate.py**

Open `custom_components/dual_smart_thermostat/climate.py`.

(a) Add the import alongside other manager imports near the top of the file:

```python
from .managers.auto_mode_evaluator import AutoDecision, AutoModeEvaluator
```

(b) In `DualSmartThermostat.__init__`, immediately after the existing `# hvac action reason` block (around line 600), add:

```python
        # Auto mode (Phase 1.2)
        if feature_manager.is_configured_for_auto_mode:
            self._auto_evaluator: AutoModeEvaluator | None = AutoModeEvaluator(
                environment_manager, opening_manager, feature_manager
            )
        else:
            self._auto_evaluator = None
        self._last_auto_decision: AutoDecision | None = None
```

(c) In `__init__`, find the existing `self._attr_hvac_modes = self.hvac_device.hvac_modes` line (around line 587) and append:

```python
        self._attr_hvac_modes = self.hvac_device.hvac_modes
        if self.features.is_configured_for_auto_mode and HVACMode.AUTO not in self._attr_hvac_modes:
            self._attr_hvac_modes = [*self._attr_hvac_modes, HVACMode.AUTO]
```

- [ ] **Step 4: Run integration tests — verify Task 8 ones pass**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```

Expected: both PASS.

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```bash
./scripts/docker-test --tb=short -q
```

Expected: previous baseline + 2 new tests; no failures.

- [ ] **Step 6: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py \
        tests/test_auto_mode_integration.py
git commit -m "feat(auto-mode): expose HVACMode.AUTO and construct evaluator

Phase 1.2 (#563): when features.is_configured_for_auto_mode, the
climate entity appends HVACMode.AUTO to _attr_hvac_modes and constructs
an AutoModeEvaluator. The evaluator is dormant until Task 9 wires it
into the control loop. Single-capability configurations are unaffected."
```

---

## Task 9: Climate.py — intercept AUTO in async_set_hvac_mode and _async_control_climate

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py`
- Test: `tests/test_auto_mode_integration.py` (extend)

- [ ] **Step 1: Append failing integration tests**

```python
@pytest.mark.asyncio
async def test_auto_picks_heat_when_too_cold(hass: HomeAssistant) -> None:
    """Selecting AUTO with cur_temp << target → heater turns on."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 21.0,
            }
        },
    )
    await hass.async_block_till_done()

    common.setup_sensor(hass, 18.0)  # well below target − tolerance
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, common.ENTITY, HVACMode.AUTO)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO
    # Heater switch should be ON.
    heater_state = hass.states.get(common.ENT_SWITCH)
    assert heater_state.state == "on"


@pytest.mark.asyncio
async def test_auto_picks_cool_when_too_hot(hass: HomeAssistant) -> None:
    """Selecting AUTO with cur_temp >> target → cooler turns on."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 21.0,
            }
        },
    )
    await hass.async_block_till_done()

    # Cooler switch must exist as an on/off entity.
    hass.states.async_set("switch.cooler_test", "off")
    await hass.async_block_till_done()

    common.setup_sensor(hass, 25.0)  # well above target + tolerance
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, common.ENTITY, HVACMode.AUTO)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO
    cooler_state = hass.states.get("switch.cooler_test")
    assert cooler_state.state == "on"


@pytest.mark.asyncio
async def test_auto_idle_when_at_target(hass: HomeAssistant) -> None:
    """At target → AUTO reports idle, heater off."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                "target_temp": 21.0,
            }
        },
    )
    await hass.async_block_till_done()

    common.setup_sensor(hass, 21.0)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, common.ENTITY, HVACMode.AUTO)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO
    heater_state = hass.states.get(common.ENT_SWITCH)
    assert heater_state.state == "off"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```

Expected: the 3 new tests FAIL — climate enters AUTO mode but doesn't dispatch to a sub-device because the intercept isn't wired yet.

- [ ] **Step 3: Add the AUTO intercept in `async_set_hvac_mode` and `_async_control_climate`**

In `custom_components/dual_smart_thermostat/climate.py`:

(a) Modify `async_set_hvac_mode` (around line 1173). Insert the intercept at the very start of the method body (immediately after the docstring):

```python
    async def async_set_hvac_mode(
        self, hvac_mode: HVACMode, is_restore: bool = False
    ) -> None:
        """Call climate mode based on current mode."""
        _LOGGER.info("%s: Setting hvac mode: %s", self.entity_id, hvac_mode)

        if hvac_mode == HVACMode.AUTO and self._auto_evaluator is not None:
            self._hvac_mode = HVACMode.AUTO
            self._set_support_flags()
            self._last_auto_decision = None  # fresh top-down scan on entry
            await self._async_evaluate_auto_and_dispatch(force=True)
            self.async_write_ha_state()
            return

        if hvac_mode not in self.hvac_modes:
            _LOGGER.debug("%s: Unrecognized hvac mode: %s", self.entity_id, hvac_mode)
            return

        # ...rest of existing method unchanged...
```

(b) Modify `_async_control_climate` (around line 1566). Insert the intercept inside the `async with self._temp_lock:` block, before the existing OFF check:

```python
    async def _async_control_climate(self, time=None, force=False) -> None:
        """Control the climate device based on config."""
        _LOGGER.debug("Attempting to control climate, time %s, force %s", time, force)

        async with self._temp_lock:
            if self._hvac_mode == HVACMode.AUTO and self._auto_evaluator is not None:
                await self._async_evaluate_auto_and_dispatch(force=force)
                return

            if self.hvac_device.hvac_mode == HVACMode.OFF and time is None:
                _LOGGER.debug("Climate is off, skipping control")
                return

            await self.hvac_device.async_control_hvac(time, force)
            # ...rest unchanged...
```

(c) Add the helper method anywhere reasonable inside `DualSmartThermostat` — recommended placement is right after `_async_control_climate_no_time` (around line 1593):

```python
    async def _async_evaluate_auto_and_dispatch(self, force: bool) -> None:
        """Run the AutoModeEvaluator and dispatch to the chosen sub-mode."""
        decision = self._auto_evaluator.evaluate(
            self._last_auto_decision,
            temp_sensor_stalled=self._sensor_stalled,
            humidity_sensor_stalled=self._humidity_sensor_stalled,
        )
        self._last_auto_decision = decision

        if decision.next_mode is not None and decision.next_mode != self.hvac_device.hvac_mode:
            await self.hvac_device.async_set_hvac_mode(decision.next_mode)

        await self.hvac_device.async_control_hvac(force=force)

        self._hvac_action_reason = decision.reason
        self._publish_hvac_action_reason(decision.reason)
```

- [ ] **Step 4: Run integration tests — verify they pass**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```

Expected: all 5 PASS.

- [ ] **Step 5: Run full test suite to confirm no regression**

```bash
./scripts/docker-test --tb=short -q
```

Expected: previous baseline + 5 new auto tests; no other failures.

- [ ] **Step 6: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py \
        tests/test_auto_mode_integration.py
git commit -m "feat(auto-mode): wire AUTO mode through the control loop

Phase 1.2 (#563): async_set_hvac_mode and _async_control_climate now
intercept HVACMode.AUTO and dispatch through the evaluator. The new
helper _async_evaluate_auto_and_dispatch evaluates with current sensor
stall state, sets the device's concrete sub-mode if it changed,
exercises the existing controller, and publishes the picked
hvac_action_reason."
```

---

## Task 10: Restoration of AUTO across restart

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py` (no functional change expected — restoration goes through the existing `async_set_hvac_mode(AUTO, is_restore=True)` path which now hits the intercept added in Task 9; this task pins the behaviour with a test).
- Test: `tests/test_auto_mode_integration.py` (extend)

- [ ] **Step 1: Append failing test**

```python
from homeassistant.core import State
from pytest_homeassistant_custom_component.common import mock_restore_cache


@pytest.mark.asyncio
async def test_auto_mode_restored_after_restart(hass: HomeAssistant) -> None:
    """A persisted hvac_mode=auto state is restored and AUTO immediately re-evaluates."""
    mock_restore_cache(
        hass,
        (State(common.ENTITY, HVACMode.AUTO),),
    )

    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 21.0,
            }
        },
    )
    await hass.async_block_till_done()

    common.setup_sensor(hass, 18.0)  # cold
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO
```

- [ ] **Step 2: Run test — verify it passes (likely on first run)**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py::test_auto_mode_restored_after_restart -v
```

Expected: PASS. Restoration goes through `async_set_hvac_mode(AUTO, is_restore=True)`, which Task 9's intercept handles. If it FAILS, the most likely cause is that the restore path calls `async_set_hvac_mode` with `HVACMode.AUTO` while `_attr_hvac_modes` still includes AUTO and the intercept correctly fires — investigate by adding `_LOGGER.debug` calls.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auto_mode_integration.py
git commit -m "test(auto-mode): pin AUTO restoration behaviour across restart

Phase 1.2 (#563): mock_restore_cache + async_setup_component reproduces
the restart scenario; verifies the existing restore path correctly
re-enters the AUTO intercept and re-evaluates immediately."
```

---

## Task 11: Capability-filtered integration scenarios

**Files:**
- Test: `tests/test_auto_mode_integration.py` (extend)

These are end-to-end checks of behaviours already covered by the evaluator unit tests, but observed through the climate entity to catch any wiring regression.

- [ ] **Step 1: Append failing tests**

```python
@pytest.mark.asyncio
async def test_auto_with_heater_fan_only_no_cool(hass: HomeAssistant) -> None:
    """Heater + fan (no cooler) → AUTO available; warm temp picks FAN_ONLY."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "fan_hot_tolerance": 1.0,
                "heater": common.ENT_SWITCH,
                "fan": "switch.fan_test",
                "target_sensor": common.ENT_SENSOR,
                "target_temp": 21.0,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    hass.states.async_set("switch.fan_test", "off")

    common.setup_sensor(hass, 22.0)  # in fan band: 21 + 0.5 < 22.0 <= 21 + 0.5 + 1.0
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, common.ENTITY, HVACMode.AUTO)
    await hass.async_block_till_done()

    fan_state = hass.states.get("switch.fan_test")
    assert fan_state.state == "on"
```

- [ ] **Step 2: Run test — verify it passes**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py::test_auto_with_heater_fan_only_no_cool -v
```

Expected: PASS. Implementation is already complete; this is a pin-test for the heater+fan capability slice.

- [ ] **Step 3: Commit**

```bash
git add tests/test_auto_mode_integration.py
git commit -m "test(auto-mode): pin heater+fan capability behaviour in AUTO

Phase 1.2 (#563): with heater + fan but no cooler, AUTO picks FAN_ONLY
when temp is in the fan-tolerance comfort band — exercising priority
9 end-to-end through the climate entity."
```

---

## Task 12: README — Auto Mode section

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Locate the existing "## Examples" or feature-table area**

Find the existing feature table near the top of `README.md` (around lines 30-40) that lists capabilities like "Window/Door Sensor Integration (Openings)" and "Preset Modes Support". Insert a new row for Auto Mode.

Find a sensible location for the detailed section — adjacent to or below the existing "## HVAC Action Reason" section (around line 613). The Auto Mode section references that section anyway via the action-reason sensor.

- [ ] **Step 2: Add the feature-table row**

Insert before the row that ends the table:

```markdown
| **Auto Mode (Priority Engine)** | | [docs](#auto-mode) |
```

- [ ] **Step 3: Add the detailed section**

Insert below the "## HVAC Action Reason" section (or wherever feels right by reading the surrounding flow):

```markdown
## Auto Mode

When the thermostat is configured with at least two distinct climate capabilities (any of heating, cooling, drying, fan), the integration exposes `auto` as one of its HVAC modes. In Auto Mode the integration picks between HEAT, COOL, DRY, and FAN_ONLY automatically based on the current environment, configured tolerances, and a fixed priority table:

1. **Safety** — floor-temperature limit and window/door openings preempt all other decisions.
2. **Urgent** (2× tolerance) — temperature or humidity beyond 2× the configured tolerance switches the mode immediately, even if a different mode is currently active.
3. **Normal** (1× tolerance) — temperature or humidity beyond the configured tolerance picks the matching mode.
4. **Comfort** — when the room is mildly above target and a fan is configured, run the fan instead of cooling.
5. **Idle** — when all targets are met, stop actuators.

The thermostat continues to report `auto` as its `hvac_mode`; the underlying actuator (heater / cooler / dryer / fan) reflects the chosen sub-mode in `hvac_action`. Mode-flap prevention keeps the chosen sub-mode running until its goal is reached or a higher-priority concern arises.

The active priority is exposed via the `hvac_action_reason` sensor as `auto_priority_temperature`, `auto_priority_humidity`, or `auto_priority_comfort`. See [HVAC Action Reason Auto values](#hvac-action-reason-auto-values).

Auto Mode requires a temperature sensor; the humidity-priority paths additionally require a humidity sensor. Phase 1.3 will add outside-temperature bias; Phase 1.4 will add apparent-temperature support; Phase 2 will add a PID controller option.
```

- [ ] **Step 4: Run targeted tests + lint to confirm no regression**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py tests/test_auto_mode_integration.py -v
./scripts/docker-lint
```

Expected: all evaluator + integration tests PASS; lint shows no net-new findings on README.md (codespell may emit pre-existing noise on unrelated files — ignore those).

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document Auto Mode in README

Phase 1.2 (#563): user-facing section explaining the priority table,
mode-flap prevention semantics, dual-state hvac_mode/hvac_action
display, and the action-reason sensor's auto_priority_* values."
```

---

## Task 13: Final lint + full test run

**Files:** none (verification only).

- [ ] **Step 1: Run the lint suite**

```bash
./scripts/docker-lint
```

Expected: isort, black, flake8, ruff clean on the changed files. Codespell findings should match the pre-existing master baseline (htmlcov/*, config/deps/*, schemas.py, config_flow.py, options_flow.py — pre-existing, not introduced by this branch).

If lint surfaces any net-new issue:

```bash
./scripts/docker-lint --fix
git add -u
git commit -m "chore: apply linter auto-fixes"
```

- [ ] **Step 2: Run the full test suite**

```bash
./scripts/docker-test
```

Expected: all tests PASS. Counts: master baseline (1398) + ~30 new evaluator unit tests + ~7 new integration tests ≈ ~1435 passed, 2 skipped. Zero failures.

If the count is lower than expected by a small margin (e.g., -2), check whether any test was inadvertently deleted in the diff against master.

- [ ] **Step 3: No commit needed**

If steps 1 and 2 succeed without changes, this task produces no commit. Move on to the final code review.

---

## Self-Review Coverage Check

Spec requirements → task coverage:

- Spec §1 Goal & Scope — Task 1 (scaffold), 8–9 (climate integration), 12 (README).
- Spec §2 Decisions — embedded in:
  - Q1 single PR → all tasks land on one branch.
  - Q2 evaluator + climate hook (no new device) → Task 1, 8, 9.
  - Q3 range mode → Task 4 helpers, Task 6 pin tests.
  - Tolerances reuse → Task 3 / 4 (compute thresholds inline using existing tolerance attributes).
  - Reason mapping → Task 3 (humidity), 4 (temp), 5 (comfort + idle).
  - Persistence → Task 10.
  - Capability filtering → Task 3 (humidity skip), 5 (fan skip), 11 (heater+fan integration).
- Spec §3 Priority Table — Task 2 (rows 1, 2, stall), 3 (3, 6), 4 (4, 5, 7, 8), 5 (9, 10), 6 (range-mode pins).
- Spec §4 Flap Prevention → Task 7.
- Spec §5 Architecture →
  - 5.1 New module → Task 1.
  - 5.2 Climate changes → Task 8 (hvac_modes, evaluator construction), Task 9 (intercepts + helper).
  - 5.3 Restoration → Task 10.
- Spec §6 Data flow → Task 9 (helper composition).
- Spec §7 Error handling table → Task 2 (stall), Task 7 (preset switch via fresh tick), Task 11 (heater+fan).
- Spec §8 Testing → Task 1–7 (evaluator unit tests), Task 8–11 (integration), Task 13 (full suite).
- Spec §9 README → Task 12.
- Spec §10 Files Touched → Task 1 (auto_mode_evaluator.py), 8/9 (climate.py), 12 (README.md).
- Spec §11 Risks → all addressed by tests across Tasks 7 (flap), 9 (sensor stall), 10 (restore), 11 (capability).
- Spec §12 Acceptance Criteria — Task 13 verifies (1, 9, 10); Tasks 8–11 cover (2, 3, 4, 5, 6, 7, 8).

No gaps.

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-27-auto-mode-phase-1-2-priority-engine.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach?**
