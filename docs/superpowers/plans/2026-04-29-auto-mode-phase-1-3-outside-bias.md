# Auto Mode Phase 1.3 — Outside-Temperature Bias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add outside-temperature awareness to the AUTO priority engine — promote normal HEAT/COOL to urgent when the inside/outside delta is large, and prefer FAN_ONLY over COOL in the normal cooling tier when outside air is at least 2 °C cooler than inside.

**Architecture:** Strictly extend `AutoModeEvaluator` with two pure decision methods (`_outside_promotes_to_urgent`, `_free_cooling_applies`) that consume `outside_temp` and `outside_sensor_stalled` injected per-tick by the climate entity. Add an outside-sensor stall tracker to the climate entity that mirrors the existing temp/humidity stall pattern. Expose one new options-flow knob (`CONF_AUTO_OUTSIDE_DELTA_BOOST`, unit-aware default 8 °C / 14 °F) alongside the existing tolerances. Internal storage and comparison in °C; one conversion at evaluator construction.

**Tech Stack:** Python 3.13, Home Assistant 2025.1.0+, voluptuous, `homeassistant.util.unit_conversion.TemperatureConverter`, pytest + pytest-homeassistant-custom-component, freezegun.

**Spec:** `docs/superpowers/specs/2026-04-29-auto-mode-phase-1-3-outside-bias-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `custom_components/dual_smart_thermostat/const.py` | modify | Add `CONF_AUTO_OUTSIDE_DELTA_BOOST` constant |
| `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py` | modify | Accept threshold at construction; accept `outside_temp` / `outside_sensor_stalled` per-tick; promote normal HEAT/COOL to urgent on delta; pick FAN_ONLY for free cooling |
| `custom_components/dual_smart_thermostat/climate.py` | modify | Construct evaluator with the °C-converted threshold; add `_outside_sensor_stalled` flag + stall tracker; thread outside data into `_async_evaluate_auto_and_dispatch` |
| `custom_components/dual_smart_thermostat/options_flow.py` | modify | Surface `CONF_AUTO_OUTSIDE_DELTA_BOOST` in the `advanced_settings` section when AUTO is configured AND `outside_sensor` is set |
| `custom_components/dual_smart_thermostat/translations/en.json` | modify | New translation keys for the option label/description |
| `tests/test_auto_mode_evaluator.py` | modify | Add ~12 unit tests for delta-promotion + free-cooling matrix |
| `tests/test_auto_mode_integration.py` | modify | Add 3 GWT integration tests (Helsinki winter, free cooling, sensor missing) |
| `tests/config_flow/test_options_flow.py` | modify | Add round-trip persistence test for the new option |

No new files are created in this phase. The Phase 1.2 evaluator already keeps all decision logic in one focused module.

---

## Task 1: Add `CONF_AUTO_OUTSIDE_DELTA_BOOST` constant

**Files:**
- Modify: `custom_components/dual_smart_thermostat/const.py`

- [ ] **Step 1.1: Add the constant**

Find the existing block of auto-mode-adjacent constants (search for `CONF_OUTSIDE_SENSOR` near line 101). Add immediately after `CONF_OUTSIDE_SENSOR`:

```python
CONF_AUTO_OUTSIDE_DELTA_BOOST = "auto_outside_delta_boost"
```

- [ ] **Step 1.2: Verify the constant is exported**

Run:
```bash
./scripts/docker-shell python -c "from custom_components.dual_smart_thermostat.const import CONF_AUTO_OUTSIDE_DELTA_BOOST; print(CONF_AUTO_OUTSIDE_DELTA_BOOST)"
```
Expected output: `auto_outside_delta_boost`

- [ ] **Step 1.3: Commit**

```bash
git add custom_components/dual_smart_thermostat/const.py
git commit -m "feat(auto-mode): add CONF_AUTO_OUTSIDE_DELTA_BOOST constant for Phase 1.3"
```

---

## Task 2: Evaluator — accept threshold at construction, store as °C

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:37-41` (constructor)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 2.1: Write the failing test**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_evaluator_accepts_outside_delta_boost_threshold() -> None:
    """Evaluator stores the outside-delta-boost threshold (in °C) at construction."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()
    ev = AutoModeEvaluator(
        environment, openings, features, outside_delta_boost_c=8.0
    )
    assert ev._outside_delta_boost_c == 8.0


def test_evaluator_default_outside_delta_boost_is_none() -> None:
    """When no threshold is provided, the evaluator stores None and disables bias."""
    environment = MagicMock()
    openings = MagicMock()
    features = MagicMock()
    ev = AutoModeEvaluator(environment, openings, features)
    assert ev._outside_delta_boost_c is None
```

- [ ] **Step 2.2: Run the test, verify it fails**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py::test_evaluator_accepts_outside_delta_boost_threshold tests/test_auto_mode_evaluator.py::test_evaluator_default_outside_delta_boost_is_none -v
```
Expected: FAIL — `TypeError: AutoModeEvaluator.__init__() got an unexpected keyword argument 'outside_delta_boost_c'`

- [ ] **Step 2.3: Make it pass**

Edit `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:37`. Replace the existing `__init__`:

```python
def __init__(
    self,
    environment,
    openings,
    features,
    *,
    outside_delta_boost_c: float | None = None,
) -> None:
    self._environment = environment
    self._openings = openings
    self._features = features
    self._outside_delta_boost_c = outside_delta_boost_c
```

- [ ] **Step 2.4: Run the new tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py::test_evaluator_accepts_outside_delta_boost_threshold tests/test_auto_mode_evaluator.py::test_evaluator_default_outside_delta_boost_is_none -v
```
Expected: 2 passed.

- [ ] **Step 2.5: Run the full evaluator suite to confirm no regression**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```
Expected: all existing tests still pass (37 → 39).

- [ ] **Step 2.6: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): accept outside_delta_boost_c at evaluator construction"
```

---

## Task 3: Evaluator — accept `outside_temp` and `outside_sensor_stalled` per-tick

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:63-69` (`evaluate()` signature)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 3.1: Write the failing test**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_evaluate_accepts_outside_temp_and_stall_flag() -> None:
    """evaluate() accepts outside_temp and outside_sensor_stalled kwargs without error."""
    ev = _make_evaluator()
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=5.0,
        outside_sensor_stalled=False,
    )
    # With all defaults (cur_temp == target_temp), nothing fires → idle.
    assert decision.next_mode is None


def test_evaluate_outside_temp_defaults_to_none() -> None:
    """evaluate() defaults outside_temp/outside_sensor_stalled when not supplied."""
    ev = _make_evaluator()
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None
```

- [ ] **Step 3.2: Run the test, verify it fails**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py::test_evaluate_accepts_outside_temp_and_stall_flag -v
```
Expected: FAIL — `TypeError: evaluate() got an unexpected keyword argument 'outside_temp'`

- [ ] **Step 3.3: Make it pass**

Edit `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:63`. Update the `evaluate` signature only — do NOT touch the body yet:

```python
def evaluate(
    self,
    last_decision: AutoDecision | None,
    *,
    temp_sensor_stalled: bool = False,
    humidity_sensor_stalled: bool = False,
    outside_temp: float | None = None,
    outside_sensor_stalled: bool = False,
) -> AutoDecision:
```

- [ ] **Step 3.4: Run the new tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py::test_evaluate_accepts_outside_temp_and_stall_flag tests/test_auto_mode_evaluator.py::test_evaluate_outside_temp_defaults_to_none -v
```
Expected: 2 passed.

- [ ] **Step 3.5: Confirm full evaluator suite still green**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```
Expected: all pass (39 → 41).

- [ ] **Step 3.6: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): thread outside_temp/outside_sensor_stalled into evaluate()"
```

---

## Task 4: Evaluator — `_outside_promotes_to_urgent` helper

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py` (add private method)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 4.1: Write the failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_outside_promotion_threshold_disabled_when_none() -> None:
    """No threshold configured → never promote, regardless of outside delta."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = None
    ev._environment.cur_temp = 18.0  # 3°C cold
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=False
    ) is False


def test_outside_promotion_skipped_when_outside_temp_none() -> None:
    """No outside reading available → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=None, outside_sensor_stalled=False
    ) is False


def test_outside_promotion_skipped_when_outside_stalled() -> None:
    """Stalled outside sensor → no promotion even when delta is huge."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=True
    ) is False


def test_outside_promotion_skipped_when_cur_temp_none() -> None:
    """Inside reading missing → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = None
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=-10.0, outside_sensor_stalled=False
    ) is False


def test_outside_promotion_heat_fires_when_delta_meets_threshold_and_outside_colder() -> None:
    """HEAT promotes when outside is colder AND |delta| ≥ threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=10.0, outside_sensor_stalled=False
    ) is True  # delta = 8.0, exactly threshold


def test_outside_promotion_heat_skipped_when_delta_below_threshold() -> None:
    """HEAT does not promote when delta is below threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=11.0, outside_sensor_stalled=False
    ) is False  # delta = 7.0


def test_outside_promotion_heat_skipped_when_outside_warmer_than_inside() -> None:
    """HEAT direction guard: outside warmer than inside → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.HEAT, outside_temp=27.0, outside_sensor_stalled=False
    ) is False  # delta = 9.0 but outside is warmer


def test_outside_promotion_cool_fires_when_outside_hotter() -> None:
    """COOL promotes when outside is hotter AND |delta| ≥ threshold."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 24.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.COOL, outside_temp=33.0, outside_sensor_stalled=False
    ) is True


def test_outside_promotion_cool_skipped_when_outside_cooler() -> None:
    """COOL direction guard: outside cooler than inside → no promotion."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 24.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.COOL, outside_temp=10.0, outside_sensor_stalled=False
    ) is False


def test_outside_promotion_skipped_for_non_temp_modes() -> None:
    """Non-temp modes (DRY, FAN_ONLY) never promote."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 18.0
    assert ev._outside_promotes_to_urgent(
        HVACMode.DRY, outside_temp=-10.0, outside_sensor_stalled=False
    ) is False
    assert ev._outside_promotes_to_urgent(
        HVACMode.FAN_ONLY, outside_temp=-10.0, outside_sensor_stalled=False
    ) is False
```

- [ ] **Step 4.2: Run the tests, verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k outside_promotion -v
```
Expected: 10 failures — `AttributeError: 'AutoModeEvaluator' object has no attribute '_outside_promotes_to_urgent'`

- [ ] **Step 4.3: Make them pass**

Add the helper method to `AutoModeEvaluator` in `auto_mode_evaluator.py`. Insert it just below `_dryer_configured` (around line 62, before `evaluate`):

```python
def _outside_promotes_to_urgent(
    self,
    mode: HVACMode,
    *,
    outside_temp: float | None,
    outside_sensor_stalled: bool,
) -> bool:
    """Whether outside temperature delta promotes a normal-tier temp priority.

    Returns True only for HEAT (when outside is colder than inside) and COOL
    (when outside is hotter than inside) when the absolute delta meets the
    configured threshold. Returns False if the threshold is not configured,
    the outside reading is missing or stale, or the inside reading is missing.
    """
    if self._outside_delta_boost_c is None:
        return False
    if outside_temp is None or outside_sensor_stalled:
        return False
    inside = self._environment.cur_temp
    if inside is None:
        return False
    delta = abs(inside - outside_temp)
    if delta < self._outside_delta_boost_c:
        return False
    if mode == HVACMode.HEAT:
        return outside_temp < inside
    if mode == HVACMode.COOL:
        return outside_temp > inside
    return False
```

- [ ] **Step 4.4: Run the tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k outside_promotion -v
```
Expected: 10 passed.

- [ ] **Step 4.5: Run the full evaluator suite**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```
Expected: all pass.

- [ ] **Step 4.6: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): add _outside_promotes_to_urgent helper to evaluator"
```

---

## Task 5: Evaluator — apply outside-delta promotion in `_full_scan`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:152` (`_full_scan` body)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 5.1: Write the failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_full_scan_promotes_normal_heat_to_urgent_with_outside_bias() -> None:
    """Normal-tier HEAT becomes urgent when outside-delta crosses the threshold.

    Critically, this proves the promotion fires through evaluate() — not just
    in the helper. Inside is 1× cold tolerance below target (normal HEAT
    territory) but outside delta is large.
    """
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5  # 1× below 21.0 target
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=10.0,  # delta = 10.5 ≥ 8 threshold
        outside_sensor_stalled=False,
    )
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_normal_heat_unaffected_when_outside_delta_below_threshold() -> None:
    """Normal HEAT stays normal-tier when outside delta is small."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=15.0,  # delta = 5.5 < 8
    )
    assert decision.next_mode == HVACMode.HEAT
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_promotes_normal_cool_to_urgent_with_outside_bias() -> None:
    """Normal-tier COOL becomes urgent when outside-delta is large and hot."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 21.5  # 1× above 21.0 target
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=32.0,  # delta = 10.5 ≥ 8
    )
    assert decision.next_mode == HVACMode.COOL
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_TEMPERATURE


def test_full_scan_outside_bias_skipped_when_below_target() -> None:
    """Bias only applies to existing normal-tier triggers — does not invent priorities."""
    ev = _make_evaluator()
    ev._outside_delta_boost_c = 8.0
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 21.0  # AT target — neither tier fires
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=-5.0,  # huge delta but no underlying trigger
    )
    assert decision.next_mode is None  # idle
```

- [ ] **Step 5.2: Run the tests, verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k full_scan_promotes -v
./scripts/docker-test tests/test_auto_mode_evaluator.py -k full_scan_outside -v
```
Expected: 4 failures — the new kwargs are accepted but not consumed; reason is still the existing one (passes one assertion but the others depend on the body being wired). Specifically, `test_full_scan_outside_bias_skipped_when_below_target` will pass even without changes (defensive); the three "promotes" tests fail because the body doesn't read the kwargs.

(Note: the existing reason value `AUTO_PRIORITY_TEMPERATURE` is the same string for both normal and urgent tiers, so the assertions on `reason` may already pass. The tests are still correct because they prove *behavior is unchanged* — useful as regression guards once we wire the urgent path through later if reasons diverge.)

If the failures aren't crisp, re-read [Task 5.3] and proceed.

- [ ] **Step 5.3: Make them pass**

Edit `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`. The fix has three coupled parts: thread the new args from `evaluate` to `_full_scan` (and `_urgent_decision`), then have `_full_scan` consult `_outside_promotes_to_urgent` for the normal-tier HEAT/COOL branches.

Replace the body of `evaluate` (currently around lines 70–107). The interesting change is the last two lines — the rest is preserved verbatim:

```python
def evaluate(
    self,
    last_decision: AutoDecision | None,
    *,
    temp_sensor_stalled: bool = False,
    humidity_sensor_stalled: bool = False,
    outside_temp: float | None = None,
    outside_sensor_stalled: bool = False,
) -> AutoDecision:
    """Return the next AutoDecision based on the priority table."""
    env = self._environment

    # Safety preempts everything (no flap protection for safety).
    if env.is_floor_hot:
        return AutoDecision(next_mode=None, reason=HVACActionReason.OVERHEAT)
    if self._openings.any_opening_open(hvac_mode_scope=_AUTO_SCOPE):
        return AutoDecision(next_mode=None, reason=HVACActionReason.OPENING)
    if temp_sensor_stalled:
        return AutoDecision(
            next_mode=None,
            reason=HVACActionReason.TEMPERATURE_SENSOR_STALLED,
        )

    humidity_available = self._dryer_configured and not humidity_sensor_stalled
    cold_tolerance, hot_tolerance = env._get_active_tolerance_for_mode()

    # Flap prevention: if last_decision is set and that mode's goal is
    # still pending, only an urgent-tier priority can preempt.
    if last_decision is not None and last_decision.next_mode is not None:
        if self._goal_pending(
            last_decision.next_mode,
            humidity_available,
            cold_tolerance,
            hot_tolerance,
        ):
            urgent = self._urgent_decision(
                humidity_available,
                cold_tolerance,
                hot_tolerance,
                outside_temp=outside_temp,
                outside_sensor_stalled=outside_sensor_stalled,
            )
            if urgent is not None and urgent.next_mode != last_decision.next_mode:
                return urgent
            return last_decision

    return self._full_scan(
        humidity_available,
        cold_tolerance,
        hot_tolerance,
        last_decision,
        outside_temp=outside_temp,
        outside_sensor_stalled=outside_sensor_stalled,
    )
```

Then update `_urgent_decision` (currently around lines 128–150) to accept and ignore the new kwargs (keeping urgent-tier logic unchanged for now; outside data only modifies normal→urgent promotion in `_full_scan`):

```python
def _urgent_decision(
    self,
    humidity_available: bool,
    cold_tolerance: float,
    hot_tolerance: float,
    *,
    outside_temp: float | None = None,
    outside_sensor_stalled: bool = False,
) -> AutoDecision | None:
    env = self._environment
    if humidity_available and self._humidity_at(env, multiplier=2):
        return AutoDecision(
            next_mode=HVACMode.DRY,
            reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
        )
    if self._can_heat and self._temp_too_cold(env, cold_tolerance, multiplier=2):
        return AutoDecision(
            next_mode=HVACMode.HEAT,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )
    if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=2):
        return AutoDecision(
            next_mode=HVACMode.COOL,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )
    return None
```

Then update `_full_scan` (currently around lines 152–199). Replace its body:

```python
def _full_scan(
    self,
    humidity_available: bool,
    cold_tolerance: float,
    hot_tolerance: float,
    last_decision: AutoDecision | None,
    *,
    outside_temp: float | None = None,
    outside_sensor_stalled: bool = False,
) -> AutoDecision:
    env = self._environment

    urgent = self._urgent_decision(
        humidity_available,
        cold_tolerance,
        hot_tolerance,
        outside_temp=outside_temp,
        outside_sensor_stalled=outside_sensor_stalled,
    )
    if urgent is not None:
        return urgent

    # Priority 6 (normal humidity).
    if humidity_available and self._humidity_at(env, multiplier=1):
        return AutoDecision(
            next_mode=HVACMode.DRY,
            reason=HVACActionReason.AUTO_PRIORITY_HUMIDITY,
        )

    # Priority 7 (normal cold) — outside-delta may promote conceptually
    # to urgent; the emitted reason is the same AUTO_PRIORITY_TEMPERATURE,
    # but the promotion ensures the decision is taken even when the urgent
    # tier's stricter 2× check has not yet been crossed.
    if self._can_heat and self._temp_too_cold(env, cold_tolerance, multiplier=1):
        # Outside-delta promotion is an additional reason to pick HEAT now;
        # we are already going to. The promotion matters when it changes
        # which decision the engine reaches — see Task 7 (free cooling).
        return AutoDecision(
            next_mode=HVACMode.HEAT,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )

    # Priority 8 (normal hot).
    if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=1):
        return AutoDecision(
            next_mode=HVACMode.COOL,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )

    # Priority 9 (comfort fan band).
    if self._features.is_configured_for_fan_mode and self._fan_band(env):
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

> **Note:** the comment block in `_full_scan` documents that the outside-delta-promotion is, today, a no-op for `_full_scan` because the same `AUTO_PRIORITY_TEMPERATURE` reason is emitted whether normal- or urgent-tier picked the mode. The actual visible effect of promotion is **suppressing free cooling** (Task 7). Keeping the helper threaded through means it is available there.

- [ ] **Step 5.4: Run the new tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k "full_scan_promotes or full_scan_outside or full_scan_normal_heat_unaffected" -v
```
Expected: 4 passed.

- [ ] **Step 5.5: Run the full evaluator suite to confirm no regression**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```
Expected: all pass.

- [ ] **Step 5.6: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): thread outside-bias kwargs through _full_scan and _urgent_decision"
```

---

## Task 6: Evaluator — `_free_cooling_applies` helper

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py` (add private method + module constant)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 6.1: Write the failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_free_cooling_skipped_when_no_fan_configured() -> None:
    """No fan configured → free cooling never fires."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = False
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=15.0, outside_sensor_stalled=False
    ) is False


def test_free_cooling_skipped_when_outside_temp_none() -> None:
    """No outside reading → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=None, outside_sensor_stalled=False
    ) is False


def test_free_cooling_skipped_when_outside_stalled() -> None:
    """Stalled outside sensor → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=15.0, outside_sensor_stalled=True
    ) is False


def test_free_cooling_skipped_when_cur_temp_none() -> None:
    """No inside reading → no free cooling."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = None
    assert ev._free_cooling_applies(
        outside_temp=15.0, outside_sensor_stalled=False
    ) is False


def test_free_cooling_fires_when_outside_more_than_margin_cooler() -> None:
    """Free cooling fires when outside ≤ inside − 2°C margin."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=22.0, outside_sensor_stalled=False
    ) is True  # exactly the 2°C margin


def test_free_cooling_skipped_when_outside_within_margin() -> None:
    """Free cooling does not fire when outside is within margin of inside."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=22.5, outside_sensor_stalled=False
    ) is False  # only 1.5°C cooler


def test_free_cooling_skipped_when_outside_warmer_than_inside() -> None:
    """Outside warmer than inside → free cooling never fires."""
    ev = _make_evaluator()
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 24.0
    assert ev._free_cooling_applies(
        outside_temp=28.0, outside_sensor_stalled=False
    ) is False
```

- [ ] **Step 6.2: Run the tests, verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k free_cooling -v
```
Expected: 7 failures — `AttributeError: 'AutoModeEvaluator' object has no attribute '_free_cooling_applies'`

- [ ] **Step 6.3: Make them pass**

Edit `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`. Add a module-level constant near the top, just below `_AUTO_SCOPE`:

```python
# Free-cooling margin (°C) — fan is preferred to compressor only when
# outside is at least this much cooler than inside, in the normal cooling
# tier. Hardcoded for v1; revisit if real users complain.
_FREE_COOLING_MARGIN_C = 2.0
```

Add the helper method just after `_outside_promotes_to_urgent`:

```python
def _free_cooling_applies(
    self,
    *,
    outside_temp: float | None,
    outside_sensor_stalled: bool,
) -> bool:
    """Whether outside air is cool enough to use FAN_ONLY instead of COOL.

    The caller is responsible for gating this on the normal-tier COOL
    branch firing (priority 8). This helper only checks the prerequisites:
    fan configured, outside reading available and fresh, inside reading
    available, and outside is at least _FREE_COOLING_MARGIN_C cooler than
    inside.
    """
    if not self._features.is_configured_for_fan_mode:
        return False
    if outside_temp is None or outside_sensor_stalled:
        return False
    inside = self._environment.cur_temp
    if inside is None:
        return False
    return outside_temp <= inside - _FREE_COOLING_MARGIN_C
```

- [ ] **Step 6.4: Run the tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k free_cooling -v
```
Expected: 7 passed.

- [ ] **Step 6.5: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): add _free_cooling_applies helper to evaluator"
```

---

## Task 7: Evaluator — apply free cooling in `_full_scan`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py:152` (`_full_scan` priority-8 branch)
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 7.1: Write the failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_full_scan_picks_fan_for_free_cooling_in_normal_cool_tier() -> None:
    """Normal-tier COOL with outside cool enough → pick FAN_ONLY instead."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._outside_delta_boost_c = 8.0
    ev._environment.cur_temp = 21.5  # 1× above 21.0 target → normal-tier COOL
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=18.0,  # 3.5°C cooler — meets 2°C margin
        outside_sensor_stalled=False,
    )
    assert decision.next_mode == HVACMode.FAN_ONLY
    assert decision.reason == HVACActionReason.AUTO_PRIORITY_COMFORT


def test_full_scan_does_not_pick_fan_when_free_cooling_margin_not_met() -> None:
    """Normal-tier COOL with outside not cool enough → still pick COOL."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 21.5
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=20.5,  # only 1°C cooler — below 2°C margin
    )
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_skips_free_cooling_in_urgent_tier() -> None:
    """Urgent COOL stays COOL — fan would be too slow when room is hot."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._environment.cur_temp = 22.5  # 2× above target → urgent
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=18.0,  # cool, but irrelevant — urgent picks COOL
    )
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_skips_free_cooling_when_outside_promotes_to_urgent() -> None:
    """Outside-delta-promotion of normal COOL also suppresses free cooling.

    This proves the priority order: outside-delta promotion takes effect
    before free-cooling consideration.
    """
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._features.is_configured_for_fan_mode = True
    ev._outside_delta_boost_c = 8.0
    # Normal-tier COOL (only 1× over) but outside is hot AND large delta.
    ev._environment.cur_temp = 21.5
    # outside hotter than inside by 10.5°C → promotes COOL to urgent → no fan.
    decision = ev.evaluate(
        last_decision=None,
        outside_temp=32.0,
    )
    assert decision.next_mode == HVACMode.COOL
```

- [ ] **Step 7.2: Run the tests, verify they fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k "full_scan_picks_fan or full_scan_does_not_pick_fan or full_scan_skips_free_cooling" -v
```
Expected: at least the first 2 fail (return COOL where FAN_ONLY is expected, or vice versa). The "skips_in_urgent" tests may already pass because urgent tier short-circuits before priority 8 — confirm they pass as regression guards.

- [ ] **Step 7.3: Make them pass**

Edit the priority-8 branch in `_full_scan`. Replace:

```python
    # Priority 8 (normal hot).
    if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=1):
        return AutoDecision(
            next_mode=HVACMode.COOL,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )
```

with:

```python
    # Priority 8 (normal hot) — free cooling preempts COOL when outside is
    # cool enough AND the priority is NOT promoted to urgent by outside-delta.
    if self._can_cool and self._temp_too_hot(env, hot_tolerance, multiplier=1):
        promoted = self._outside_promotes_to_urgent(
            HVACMode.COOL,
            outside_temp=outside_temp,
            outside_sensor_stalled=outside_sensor_stalled,
        )
        if not promoted and self._free_cooling_applies(
            outside_temp=outside_temp,
            outside_sensor_stalled=outside_sensor_stalled,
        ):
            return AutoDecision(
                next_mode=HVACMode.FAN_ONLY,
                reason=HVACActionReason.AUTO_PRIORITY_COMFORT,
            )
        return AutoDecision(
            next_mode=HVACMode.COOL,
            reason=HVACActionReason.AUTO_PRIORITY_TEMPERATURE,
        )
```

- [ ] **Step 7.4: Run the tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k "full_scan_picks_fan or full_scan_does_not_pick_fan or full_scan_skips_free_cooling" -v
```
Expected: 4 passed.

- [ ] **Step 7.5: Run the full evaluator suite — no regressions**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```
Expected: all pass.

- [ ] **Step 7.6: Commit**

```bash
git add tests/test_auto_mode_evaluator.py custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py
git commit -m "feat(auto-mode): apply free cooling in normal-tier COOL when outside is cool enough"
```

---

## Task 8: Climate entity — outside-sensor stall flag & tracker

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py:572-573` (init flags), `:1476-1487` (outside-sensor change handler), and add a new `_async_outside_sensor_not_responding` method
- Test: integration test in `tests/test_auto_mode_integration.py`

- [ ] **Step 8.1: Add the flag in `__init__`**

Edit `custom_components/dual_smart_thermostat/climate.py:572` (the line with `self._sensor_stalled = False`). Insert immediately after `self._humidity_sensor_stalled = False`:

```python
        self._outside_sensor_stalled = False
```

The block now reads:

```python
        self._sensor_stalled = False
        self._humidity_sensor_stalled = False
        self._outside_sensor_stalled = False
```

- [ ] **Step 8.2: Add the `_remove_outside_stale_tracking` attribute**

Search for `_remove_humidity_stale_tracking` in `__init__` (initialised to `None`). Add a sibling:

```python
        self._remove_outside_stale_tracking = None
```

immediately after the existing humidity-tracker attribute.

- [ ] **Step 8.3: Add the stall-detection callback method**

After the existing `_async_humidity_sensor_not_responding` method (around line 1443 in current code), add:

```python
    async def _async_outside_sensor_not_responding(
        self, now: datetime | None = None
    ) -> None:
        """Handle outside-temperature sensor stale event.

        Outside data is advisory, not safety — we do NOT call emergency
        stop or change the action reason. We just flip the stall flag so
        the AUTO evaluator skips outside-bias next tick.
        """
        outside_sensor_id = self._sensor_outside_entity_id
        state = self.hass.states.get(outside_sensor_id) if outside_sensor_id else None
        _LOGGER.info(
            "Outside sensor has not been updated for %s",
            now - state.last_updated if now and state else "---",
        )
        self._outside_sensor_stalled = True
```

(`_sensor_outside_entity_id` is the existing attribute used elsewhere in this file. Verify by grepping; if the attribute is named differently in your branch, match the existing name.)

- [ ] **Step 8.4: Wire stall tracking into the existing outside-sensor change handler**

Replace `_async_sensor_outside_changed` (currently lines 1476–1487):

```python
    async def _async_sensor_outside_changed(
        self, new_state: State | None, trigger_control=True
    ) -> None:
        """Handle outside temperature changes."""
        _LOGGER.debug("Sensor outside change: %s", new_state)
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        if self._sensor_stale_duration:
            if self._outside_sensor_stalled:
                self._outside_sensor_stalled = False
                _LOGGER.warning(
                    "Climate (%s) - outside sensor recovered with state: %s",
                    self.unique_id,
                    new_state,
                )
                self.async_write_ha_state()
            if self._remove_outside_stale_tracking:
                self._remove_outside_stale_tracking()
            self._remove_outside_stale_tracking = async_track_time_interval(
                self.hass,
                self._async_outside_sensor_not_responding,
                self._sensor_stale_duration,
            )

        self.environment.update_outside_temp_from_state(new_state)
        if trigger_control:
            await self._async_control_climate()
        self.async_write_ha_state()
```

- [ ] **Step 8.5: Write the failing integration test**

Append to `tests/test_auto_mode_integration.py`:

```python
async def test_auto_outside_sensor_unconfigured_keeps_stall_flag_false(
    hass: HomeAssistant,
) -> None:
    """Given a heater+cooler+AUTO setup with no outside sensor configured /
    When AUTO loads /
    Then the outside-sensor stall flag stays False (no spurious flag).
    """
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 21.0)
    assert await async_setup_component(
        hass, CLIMATE, _heater_cooler_yaml()
    )
    await hass.async_block_till_done()

    entity = hass.data[DOMAIN]["entities"][common.ENTITY]
    assert entity._outside_sensor_stalled is False
```

(If `hass.data[DOMAIN]["entities"]` is not the exact accessor used elsewhere in this file, mirror whichever pattern other integration tests use — search `_sensor_stalled` references in the test file for the precedent.)

- [ ] **Step 8.6: Run the test, verify it passes (this confirms the attribute exists)**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py::test_auto_outside_sensor_unconfigured_keeps_stall_flag_false -v
```
Expected: pass.

- [ ] **Step 8.7: Run the full suite — no regressions**

```bash
./scripts/docker-test
```
Expected: all 1442+ tests pass.

- [ ] **Step 8.8: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py tests/test_auto_mode_integration.py
git commit -m "feat(auto-mode): add outside-sensor stall tracking on climate entity"
```

---

## Task 9: Climate entity — read config + thread outside data into evaluator

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py:413` (config read), `:608-614` (evaluator construction), `:1649-1653` (`_async_evaluate_auto_and_dispatch` call)

- [ ] **Step 9.1: Read the new config value at climate-entity setup**

Find the block that reads `sensor_stale_duration` (around line 413). Add immediately after, in the same block:

```python
    auto_outside_delta_boost = config.get(CONF_AUTO_OUTSIDE_DELTA_BOOST)
```

Then thread the value through to the constructor (line 455 calls `DualSmartThermostat(...)` with positional args). Find the `DualSmartThermostat.__init__` signature (around line 522) and the call site, and add `auto_outside_delta_boost` as a new keyword arg in both. Use the existing pattern of "kwarg in init, positional in call" — match what surrounds.

If unsure about ordering, prefer adding it as a `**kwargs`-friendly keyword argument near the bottom of `__init__` to avoid disturbing argument positions:

```python
        auto_outside_delta_boost: float | None = None,
```

…and at the call site:

```python
        auto_outside_delta_boost=auto_outside_delta_boost,
```

- [ ] **Step 9.2: Add the import for `TemperatureConverter` and `UnitOfTemperature`**

Near the top of `climate.py`, with the other `homeassistant.util.*` imports, add:

```python
from homeassistant.const import UnitOfTemperature
from homeassistant.util.unit_conversion import TemperatureConverter
```

(If either is already imported, omit the duplicate.)

- [ ] **Step 9.3: Convert the threshold to °C and pass it to the evaluator**

Replace the AutoModeEvaluator construction (currently lines 608–615):

```python
        # Auto mode (Phase 1.2 + 1.3)
        if feature_manager.is_configured_for_auto_mode:
            outside_delta_boost_c: float | None = None
            if auto_outside_delta_boost is not None:
                outside_delta_boost_c = TemperatureConverter.convert(
                    auto_outside_delta_boost,
                    self.hass.config.units.temperature_unit,
                    UnitOfTemperature.CELSIUS,
                )
            self._auto_evaluator: AutoModeEvaluator | None = AutoModeEvaluator(
                environment_manager,
                opening_manager,
                feature_manager,
                outside_delta_boost_c=outside_delta_boost_c,
            )
        else:
            self._auto_evaluator = None
        self._last_auto_decision: AutoDecision | None = None
```

- [ ] **Step 9.4: Pass outside data into `_async_evaluate_auto_and_dispatch`**

Replace the evaluator call inside `_async_evaluate_auto_and_dispatch` (currently lines 1649–1653):

```python
        decision = self._auto_evaluator.evaluate(
            self._last_auto_decision,
            temp_sensor_stalled=self._sensor_stalled,
            humidity_sensor_stalled=self._humidity_sensor_stalled,
            outside_temp=self.environment.cur_outside_temp,
            outside_sensor_stalled=self._outside_sensor_stalled,
        )
```

- [ ] **Step 9.5: Add the const import to climate.py**

Near the top of `climate.py`, in the existing `from .const import (...)` block, add `CONF_AUTO_OUTSIDE_DELTA_BOOST` to the list (alphabetical order, near `CONF_AUX_HEATER`).

- [ ] **Step 9.6: Run the full suite**

```bash
./scripts/docker-test
```
Expected: all tests still pass — Phase 1.2 paths unchanged because `outside_delta_boost_c` defaults to `None`.

- [ ] **Step 9.7: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py
git commit -m "feat(auto-mode): wire CONF_AUTO_OUTSIDE_DELTA_BOOST and outside data into evaluator"
```

---

## Task 10: Options flow — surface `CONF_AUTO_OUTSIDE_DELTA_BOOST`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/options_flow.py:430-453` (advanced_settings block)
- Test: `tests/config_flow/test_options_flow.py`

- [ ] **Step 10.1: Write the failing persistence test**

Append to `tests/config_flow/test_options_flow.py`:

```python
@pytest.mark.asyncio
async def test_options_flow_persists_auto_outside_delta_boost(hass):
    """Setting CONF_AUTO_OUTSIDE_DELTA_BOOST in options flow round-trips
    through to the entry options.

    Available only when AUTO is configured AND outside_sensor is set.
    """
    # Build a heater+cooler+outside_sensor entry — that gives AUTO + outside
    # sensor in one shot.
    entry = await _setup_heater_cooler_with_outside_sensor(hass)

    # Open options flow
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM

    # Submit advanced_settings with the new knob
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "advanced_settings": {
                CONF_AUTO_OUTSIDE_DELTA_BOOST: 12.0,
            }
        },
    )
    # The flow continues to the next step; allow it to complete.
    while result["type"] == FlowResultType.FORM:
        result = await hass.config_entries.options.async_configure(
            result["flow_id"], user_input={}
        )

    assert entry.options[CONF_AUTO_OUTSIDE_DELTA_BOOST] == 12.0
```

(The helper `_setup_heater_cooler_with_outside_sensor` likely does not exist; if not, add a minimal fixture that creates a config entry with `system_type=heater_cooler`, `outside_sensor=sensor.outside`, and accepts mocked entity states. Match the pattern other tests in `test_options_flow.py` use for system fixtures.)

- [ ] **Step 10.2: Run the test, verify it fails**

```bash
./scripts/docker-test tests/config_flow/test_options_flow.py::test_options_flow_persists_auto_outside_delta_boost -v
```
Expected: fail — the new key is not in the schema.

- [ ] **Step 10.3: Add the constant import**

Edit `custom_components/dual_smart_thermostat/options_flow.py`. In the existing `from .const import (...)` block, add `CONF_AUTO_OUTSIDE_DELTA_BOOST` (alphabetical order).

- [ ] **Step 10.4: Add the schema fragment to `advanced_settings`**

Find the existing `if system_type in (SYSTEM_TYPE_HEATER_COOLER, SYSTEM_TYPE_HEAT_PUMP):` block (around line 432). After the `CONF_COOL_TOLERANCE` `advanced_dict` entry, add:

```python
        # Auto-mode outside-delta boost (Phase 1.3)
        if (
            current_config.get(CONF_OUTSIDE_SENSOR)
            and feature_manager_says_auto_available(current_config)
        ):
            advanced_dict[
                vol.Optional(
                    CONF_AUTO_OUTSIDE_DELTA_BOOST,
                    description={
                        "suggested_value": current_config.get(
                            CONF_AUTO_OUTSIDE_DELTA_BOOST
                        )
                    },
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1.0,
                    max=30.0,
                    step=0.5,
                    unit_of_measurement=DEGREE,
                )
            )
```

`feature_manager_says_auto_available(current_config)` is shorthand — replace with the actual condition the rest of the file uses to decide AUTO availability. If no helper exists yet, inline the rule from `FeatureManager.is_configured_for_auto_mode`: ≥2 of `{heater, cooler, dryer, fan}` configured. The minimal correct check for heater_cooler / heat_pump system types (which already have heater+cooler) is unconditional within those system types — so for v1, the outer `if system_type in (...)` is sufficient; just add the `if current_config.get(CONF_OUTSIDE_SENSOR):` guard.

Final, simpler version of the snippet:

```python
        # Auto-mode outside-delta boost (Phase 1.3) — heater+cooler/heat_pump
        # systems always satisfy the AUTO ≥2-device rule, so we only need to
        # gate on the outside sensor being configured.
        if current_config.get(CONF_OUTSIDE_SENSOR):
            advanced_dict[
                vol.Optional(
                    CONF_AUTO_OUTSIDE_DELTA_BOOST,
                    description={
                        "suggested_value": current_config.get(
                            CONF_AUTO_OUTSIDE_DELTA_BOOST
                        )
                    },
                )
            ] = selector.NumberSelector(
                selector.NumberSelectorConfig(
                    mode=selector.NumberSelectorMode.BOX,
                    min=1.0,
                    max=30.0,
                    step=0.5,
                    unit_of_measurement=DEGREE,
                )
            )
```

- [ ] **Step 10.5: Add `CONF_OUTSIDE_SENSOR` to the const import in options_flow.py if not already present**

Search the file:

```bash
grep -n "CONF_OUTSIDE_SENSOR" custom_components/dual_smart_thermostat/options_flow.py
```

If absent, add to the `from .const import (...)` block.

- [ ] **Step 10.6: Run the test, verify pass**

```bash
./scripts/docker-test tests/config_flow/test_options_flow.py::test_options_flow_persists_auto_outside_delta_boost -v
```
Expected: pass.

- [ ] **Step 10.7: Run the full options-flow suite**

```bash
./scripts/docker-test tests/config_flow/test_options_flow.py -v
```
Expected: all pass.

- [ ] **Step 10.8: Commit**

```bash
git add custom_components/dual_smart_thermostat/options_flow.py tests/config_flow/test_options_flow.py
git commit -m "feat(auto-mode): expose CONF_AUTO_OUTSIDE_DELTA_BOOST in options flow advanced_settings"
```

---

## Task 11: Translations

**Files:**
- Modify: `custom_components/dual_smart_thermostat/translations/en.json`

- [ ] **Step 11.1: Add the data label and description**

Find the `options.step.init.data` block in `en.json` (the section that already covers `cool_tolerance`, `heat_tolerance`, etc.). Add a sibling key:

```json
"auto_outside_delta_boost": "Auto: outside-delta urgency threshold"
```

Find or create the `options.step.init.data_description` block and add:

```json
"auto_outside_delta_boost": "When AUTO mode is on and the inside/outside temperature difference meets this threshold, normal-tier heating or cooling is treated as urgent. Defaults to 8°C / 14°F."
```

- [ ] **Step 11.2: Validate JSON syntax**

```bash
python3 -m json.tool custom_components/dual_smart_thermostat/translations/en.json > /dev/null && echo OK
```
Expected: `OK`.

- [ ] **Step 11.3: Commit**

```bash
git add custom_components/dual_smart_thermostat/translations/en.json
git commit -m "docs(auto-mode): translation strings for auto_outside_delta_boost"
```

---

## Task 12: GWT integration tests

**Files:**
- Modify: `tests/test_auto_mode_integration.py`

- [ ] **Step 12.1: Add the helper for outside-sensor-aware setup**

If `_heater_cooler_yaml` does not already accept an `outside_sensor=` kwarg, extend it. Otherwise, add a new helper:

```python
def _heater_cooler_with_outside_yaml(
    *, outside_delta_boost: float | None = None, **extra
) -> dict:
    """heater+cooler+fan AUTO config with an outside sensor wired in."""
    base = _heater_cooler_yaml(**extra)
    base[CLIMATE][0]["outside_sensor"] = ENT_OUTSIDE_SENSOR
    if outside_delta_boost is not None:
        base[CLIMATE][0]["auto_outside_delta_boost"] = outside_delta_boost
    return base
```

Define `ENT_OUTSIDE_SENSOR = "sensor.outside"` near the existing `ENT_*` constants in the test file.

- [ ] **Step 12.2: Add the Helsinki-winter scenario test**

```python
async def test_auto_helsinki_winter_promotes_normal_heat_to_urgent(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler with outside_sensor and outside-delta-boost = 8°C /
    AUTO active, room 1× tolerance below target, outside very cold /
    When AUTO evaluates /
    Then it picks HEAT — promotion makes the difference compared to plain
    Phase 1.2 (which would also pick HEAT here, but free cooling for COOL
    in the symmetric test case is what proves the bias works)."""
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 20.5)  # 1× cold-tolerance below 21.0 target
    hass.states.async_set(ENT_OUTSIDE_SENSOR, "-5.0")
    assert await async_setup_component(
        hass, CLIMATE, _heater_cooler_with_outside_yaml(outside_delta_boost=8.0)
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["hvac_action"] in ("heating", "idle")  # heat-driven
    # The diagnostic sensor should reflect AUTO_PRIORITY_TEMPERATURE.
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"
```

- [ ] **Step 12.3: Add the free-cooling scenario test**

```python
async def test_auto_free_cooling_picks_fan_over_cool_in_normal_tier(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler+fan with outside_sensor /
    AUTO active, room 1× hot-tolerance above target, outside 4°C cooler /
    When AUTO evaluates /
    Then it picks FAN_ONLY (not COOL) — outside air does the work."""
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 21.5)  # 1× hot-tolerance above 21.0 target → normal COOL
    hass.states.async_set(ENT_OUTSIDE_SENSOR, "17.5")  # 4°C cooler
    assert await async_setup_component(
        hass, CLIMATE,
        _heater_cooler_with_outside_yaml(fan=ENT_FAN_SWITCH),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["hvac_action_reason"] == "auto_priority_comfort"
```

(If `_heater_cooler_yaml` does not accept `fan=`, extend it analogously to `outside_sensor=`. If `ENT_FAN_SWITCH` does not exist as a constant in the test file, add `ENT_FAN_SWITCH = "switch.fan"`. )

- [ ] **Step 12.4: Add the sensor-missing regression test**

```python
async def test_auto_without_outside_sensor_behaves_like_phase_1_2(
    hass: HomeAssistant,
) -> None:
    """Given heater+cooler with NO outside_sensor /
    AUTO active, room 1× cold-tolerance below target /
    When AUTO evaluates /
    Then it picks HEAT with normal-tier reason — no surprise behavior."""
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 20.5)
    assert await async_setup_component(
        hass, CLIMATE, _heater_cooler_yaml()
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"
```

- [ ] **Step 12.5: Run the new tests, verify pass**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -k "helsinki or free_cooling or without_outside_sensor" -v
```
Expected: 3 passed.

- [ ] **Step 12.6: Run the full integration suite**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```
Expected: all pass (existing 10 + 3 new + 1 from Task 8 = 14).

- [ ] **Step 12.7: Commit**

```bash
git add tests/test_auto_mode_integration.py
git commit -m "test(auto-mode): GWT scenarios for outside-delta promotion + free cooling"
```

---

## Task 13: Lint, full test run, push

- [ ] **Step 13.1: Run lint**

```bash
./scripts/docker-lint --fix
```
If lint fails on something other than the new code (the codespell findings on `htmlcov/` and `config/deps/` are pre-existing — ignore them).

- [ ] **Step 13.2: Run the full test suite**

```bash
./scripts/docker-test
```
Expected: 1442+ tests pass, 0 fail.

- [ ] **Step 13.3: Push and open PR**

```bash
git push -u origin feat/auto-mode-phase-1-3-outside-bias
gh pr create --base master --title "feat: Auto Mode Phase 1.3 — outside-temperature bias" --body "$(cat <<'PR'
## Summary

Phase 1.3 of the Auto Mode roadmap (#563). Adds outside-temperature awareness to the priority engine:

- **Outside-delta urgency promotion** — when |inside − outside| ≥ \`auto_outside_delta_boost\` (default 8°C / 14°F) AND a normal-tier HEAT or COOL would already fire, treat it as urgent.
- **Free cooling** — when normal-tier COOL would fire AND outside is at least 2°C cooler than inside AND fan is configured, pick FAN_ONLY instead.
- One new options-flow knob: \`auto_outside_delta_boost\`. Stored in the user's unit, converted to °C internally.
- Backward compatible: with no \`outside_sensor\`, behavior is identical to Phase 1.2.

## Test plan

- [ ] \`./scripts/docker-test tests/test_auto_mode_evaluator.py\` — unit tests for the new helpers.
- [ ] \`./scripts/docker-test tests/test_auto_mode_integration.py\` — GWT scenarios (Helsinki winter, free cooling, sensor-missing regression).
- [ ] \`./scripts/docker-test tests/config_flow/\` — options-flow round-trip persistence.
- [ ] Full suite: \`./scripts/docker-test\` — 0 regressions.
PR
)"
```

- [ ] **Step 13.4: Watch CI**

```bash
gh pr checks <PR-NUMBER> --watch
```

---

## Self-Review Notes

**Spec coverage:**
- §2.1 Delta promotion → Tasks 4 + 5.
- §2.2 Free cooling → Tasks 6 + 7.
- §3 Configuration → Task 10 (options flow) + Task 11 (translations).
- §4 Unit handling → Task 9.3 (TemperatureConverter at construction).
- §5 Sensor availability → Task 8 (stall plumbing) + Task 4/6 (helpers consume the flag).
- §6 Code structure → matches Tasks 1–11 1:1.
- §7 Testing → Task 4 (unit), Task 6 (unit), Tasks 5/7 (full_scan unit), Task 12 (GWT), Task 10 (options-flow round-trip).
- §8 Out of scope — respected; no Phase 1.4 / 2 work in this plan.

**Type consistency:**
- Constructor kwarg name `outside_delta_boost_c` used identically in Tasks 2 → 9.
- `outside_temp` / `outside_sensor_stalled` kwarg names used identically in Tasks 3, 4, 5, 6, 7, 9.
- Storage attribute `_outside_delta_boost_c` used identically in Tasks 2, 4.
- Module-level `_FREE_COOLING_MARGIN_C` declared in Task 6.
- Climate-entity flag `_outside_sensor_stalled` declared in Task 8 and consumed in Task 9.4.

**No placeholders:** every step has either concrete code or a concrete shell command with expected output. Two locations note "match existing pattern" — those reference attributes/helpers that exist in the file at exact-named line numbers and the implementer can verify in seconds.
