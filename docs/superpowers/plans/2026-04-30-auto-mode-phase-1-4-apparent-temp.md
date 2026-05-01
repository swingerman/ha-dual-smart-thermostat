# Auto Mode Phase 1.4 — Apparent Temperature Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `CONF_USE_APPARENT_TEMP` so AUTO's COOL branch and the cooler bang-bang controller decide based on the NWS Rothfusz heat index ("feels-like" temp) when humidity is available, instead of raw dry-bulb temperature.

**Architecture:** Compute the heat index inside `EnvironmentManager` as a private `apparent_temp` property and a public `effective_temp_for_mode(mode)` selector. Make `EnvironmentManager.is_too_hot` apparent-aware when the env's current mode is COOL — that single change propagates to every cooler controller (heater_cooler, heat_pump dispatched COOL, ac_only) without further surgery. Update `AutoModeEvaluator`'s `_temp_too_hot` helper to substitute too. One new options-flow boolean toggle, gated on `humidity_sensor` configured.

**Tech Stack:** Python 3.13, Home Assistant 2025.1.0+, voluptuous, `homeassistant.util.unit_conversion.TemperatureConverter`, pytest + pytest-homeassistant-custom-component.

**Spec:** `docs/superpowers/specs/2026-04-30-auto-mode-phase-1-4-apparent-temp-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `custom_components/dual_smart_thermostat/const.py` | modify | Add `CONF_USE_APPARENT_TEMP` |
| `custom_components/dual_smart_thermostat/managers/environment_manager.py` | modify | Add `_use_apparent_temp` flag, `_humidity_sensor_stalled` setter, `_rothfusz_heat_index_f()` helper, `apparent_temp` property, `effective_temp_for_mode()` selector, apparent-aware `is_too_hot()` |
| `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py` | modify | Make `_temp_too_hot` consult `env.effective_temp_for_mode(HVACMode.COOL)` |
| `custom_components/dual_smart_thermostat/climate.py` | modify | Sync `_humidity_sensor_stalled` flag into env; expose `apparent_temperature` extra-state-attribute when flag-on AND humidity available |
| `custom_components/dual_smart_thermostat/schemas.py` | modify | Add `vol.Optional(CONF_USE_APPARENT_TEMP): cv.boolean` to `PLATFORM_SCHEMA` |
| `custom_components/dual_smart_thermostat/options_flow.py` | modify | Add boolean toggle in `advanced_settings`, gated on `humidity_sensor` configured |
| `custom_components/dual_smart_thermostat/translations/en.json` | modify | New translation keys |
| `tests/test_environment_manager.py` (or new file if absent) | modify/create | Heat-index math + selector unit tests |
| `tests/test_auto_mode_evaluator.py` | modify | COOL-priority apparent-temp tests |
| `tests/test_auto_mode_integration.py` | modify | Per-system-type GWT — heater_cooler (3), heat_pump (2) |
| `tests/test_ac_only_mode.py` | modify | ac_only standalone-COOL apparent + flag-off (2) |
| `tests/config_flow/test_options_flow.py` | modify | Round-trip persistence test |

---

## Task 1: `CONF_USE_APPARENT_TEMP` constant and schema entry

**Files:**
- Modify: `custom_components/dual_smart_thermostat/const.py`
- Modify: `custom_components/dual_smart_thermostat/schemas.py`

- [ ] **Step 1.1: Add the constant**

In `const.py`, immediately after `CONF_AUTO_OUTSIDE_DELTA_BOOST` (Phase 1.3 added at line 102), insert:

```python
CONF_USE_APPARENT_TEMP = "use_apparent_temp"
```

- [ ] **Step 1.2: Add to PLATFORM_SCHEMA**

In `schemas.py`, find the existing `PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({...})` block. Locate the line `vol.Optional(CONF_AUTO_OUTSIDE_DELTA_BOOST): vol.Coerce(float),` (added in Phase 1.3) and add immediately after:

```python
        vol.Optional(CONF_USE_APPARENT_TEMP): cv.boolean,
```

Add `CONF_USE_APPARENT_TEMP` to the existing `from .const import (...)` block at the top of `schemas.py` (alphabetical order). Verify with:

```bash
grep -n "CONF_USE_APPARENT_TEMP\|CONF_AUTO_OUTSIDE_DELTA_BOOST" custom_components/dual_smart_thermostat/schemas.py
```

- [ ] **Step 1.3: Verify importability and YAML acceptance**

```bash
./scripts/docker-shell python -c "from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP; print(CONF_USE_APPARENT_TEMP)"
```
Expected: `use_apparent_temp`.

- [ ] **Step 1.4: Commit**

```bash
git add custom_components/dual_smart_thermostat/const.py custom_components/dual_smart_thermostat/schemas.py
git commit -m "feat(auto-mode): add CONF_USE_APPARENT_TEMP constant + schema entry for Phase 1.4"
```

---

## Task 2: Rothfusz heat-index helper with TDD

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/environment_manager.py`
- Test: `tests/test_environment_manager.py` (create if absent)

- [ ] **Step 2.1: Determine if `tests/test_environment_manager.py` exists**

```bash
ls tests/test_environment_manager.py 2>/dev/null || echo "MISSING"
```

If `MISSING`, create a new file with this preamble:

```python
"""Tests for EnvironmentManager additions in Phase 1.4 (apparent temperature)."""

from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
import pytest

from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
    _rothfusz_heat_index_f,
)
```

If it already exists, just append the imports if missing.

- [ ] **Step 2.2: Write failing tests for `_rothfusz_heat_index_f`**

Append to `tests/test_environment_manager.py`:

```python
def test_rothfusz_heat_index_at_threshold_minimum_humidity() -> None:
    """At 80°F (≈27°C) and 40% RH, heat index ≈ 80°F (formula barely active)."""
    hi = _rothfusz_heat_index_f(80.0, 40.0)
    assert 79.0 <= hi <= 81.0


def test_rothfusz_heat_index_high_humidity_above_threshold() -> None:
    """At 80°F and 80% RH, heat index ≈ 84°F (mild humidity boost)."""
    hi = _rothfusz_heat_index_f(80.0, 80.0)
    assert 83.0 <= hi <= 85.0


def test_rothfusz_heat_index_hot_humid() -> None:
    """At 90°F and 80% RH, heat index ≈ 113°F (per NWS table)."""
    hi = _rothfusz_heat_index_f(90.0, 80.0)
    assert 110.0 <= hi <= 116.0


def test_rothfusz_heat_index_low_humidity_extreme_temp() -> None:
    """At 100°F and 20% RH, heat index ≈ 99°F."""
    hi = _rothfusz_heat_index_f(100.0, 20.0)
    assert 96.0 <= hi <= 102.0
```

- [ ] **Step 2.3: Run; expect 4 failures**

```bash
./scripts/docker-test tests/test_environment_manager.py -k rothfusz -v
```

Expected: `ImportError: cannot import name '_rothfusz_heat_index_f'`.

- [ ] **Step 2.4: Implement the helper**

Open `custom_components/dual_smart_thermostat/managers/environment_manager.py`. Just before `class EnvironmentManager`, after the existing imports, add:

```python
def _rothfusz_heat_index_f(t_f: float, rh: float) -> float:
    """NWS Rothfusz heat-index polynomial.

    ``t_f`` is dry-bulb temperature in degrees Fahrenheit. ``rh`` is relative
    humidity as a percentage (0-100). Returns heat index in degrees Fahrenheit.

    Standard 8-term polynomial. Caller is responsible for the validity gate
    (formula is meaningful only above ~80 °F / 27 °C).
    """
    return (
        -42.379
        + 2.04901523 * t_f
        + 10.14333127 * rh
        - 0.22475541 * t_f * rh
        - 0.00683783 * t_f * t_f
        - 0.05481717 * rh * rh
        + 0.00122874 * t_f * t_f * rh
        + 0.00085282 * t_f * rh * rh
        - 0.00000199 * t_f * t_f * rh * rh
    )
```

- [ ] **Step 2.5: Run; expect 4 passes**

```bash
./scripts/docker-test tests/test_environment_manager.py -k rothfusz -v
```

Expected: `4 passed`.

- [ ] **Step 2.6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/environment_manager.py tests/test_environment_manager.py
git commit -m "feat(auto-mode): add Rothfusz heat-index helper for Phase 1.4"
```

---

## Task 3: `EnvironmentManager` accepts `_use_apparent_temp` flag and tracks `_humidity_sensor_stalled`

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/environment_manager.py:78-122` (`__init__`)

- [ ] **Step 3.1: Write failing test**

Append to `tests/test_environment_manager.py`:

```python
def _make_env(**config_overrides) -> EnvironmentManager:
    """Build an EnvironmentManager with a mocked hass and a fresh config dict."""
    hass = MagicMock()
    hass.config.units.temperature_unit = UnitOfTemperature.CELSIUS
    config: dict = {}
    config.update(config_overrides)
    return EnvironmentManager(hass, config)


def test_env_manager_default_use_apparent_temp_is_false() -> None:
    """Without CONF_USE_APPARENT_TEMP set, the flag stores False."""
    env = _make_env()
    assert env._use_apparent_temp is False


def test_env_manager_reads_use_apparent_temp_from_config() -> None:
    """When config sets the flag, it is stored on the manager."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    assert env._use_apparent_temp is True


def test_env_manager_humidity_sensor_stalled_default_false() -> None:
    """Default humidity-stalled flag is False."""
    env = _make_env()
    assert env.humidity_sensor_stalled is False


def test_env_manager_humidity_sensor_stalled_setter_updates_flag() -> None:
    """Setter flips the flag."""
    env = _make_env()
    env.humidity_sensor_stalled = True
    assert env.humidity_sensor_stalled is True
```

- [ ] **Step 3.2: Run; expect failures (`AttributeError` on either field)**

```bash
./scripts/docker-test tests/test_environment_manager.py -k "use_apparent_temp or humidity_sensor_stalled" -v
```

- [ ] **Step 3.3: Implement**

In `environment_manager.py`, find the `from ..const import (...)` block at top and add `CONF_USE_APPARENT_TEMP` (alphabetical order).

Then in `__init__` (around line 121, after `self._config_heat_cool_mode = config.get(CONF_HEAT_COOL_MODE) or False`), add:

```python
        self._use_apparent_temp = config.get(CONF_USE_APPARENT_TEMP, False)
        self._humidity_sensor_stalled = False
```

After `__init__` (anywhere reasonable in the class — near other status properties around line 267 next to `cur_humidity` is a good spot), add:

```python
    @property
    def humidity_sensor_stalled(self) -> bool:
        return self._humidity_sensor_stalled

    @humidity_sensor_stalled.setter
    def humidity_sensor_stalled(self, value: bool) -> None:
        self._humidity_sensor_stalled = bool(value)
```

- [ ] **Step 3.4: Run; expect 4 passes**

```bash
./scripts/docker-test tests/test_environment_manager.py -k "use_apparent_temp or humidity_sensor_stalled" -v
```

- [ ] **Step 3.5: Run full suite to confirm no regression**

```bash
./scripts/docker-test
```

Expected: 1479 passed (Phase 1.3 baseline) + 8 new env-manager tests = 1487 passed. Confirm 0 failures.

- [ ] **Step 3.6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/environment_manager.py tests/test_environment_manager.py
git commit -m "feat(auto-mode): EnvironmentManager tracks use_apparent_temp + humidity_sensor_stalled"
```

---

## Task 4: `EnvironmentManager.apparent_temp` property

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/environment_manager.py`

- [ ] **Step 4.1: Write failing tests**

Append to `tests/test_environment_manager.py`:

```python
def test_apparent_temp_falls_back_when_flag_off() -> None:
    """Flag off → apparent_temp returns cur_temp regardless of humidity."""
    env = _make_env()
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_when_cur_temp_none() -> None:
    """No temp → apparent_temp returns None."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = None
    env._cur_humidity = 80.0
    assert env.apparent_temp is None


def test_apparent_temp_falls_back_when_humidity_none() -> None:
    """Humidity unavailable → apparent_temp returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = None
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_when_humidity_stalled() -> None:
    """Humidity stalled → apparent_temp returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    env.humidity_sensor_stalled = True
    assert env.apparent_temp == 32.0


def test_apparent_temp_falls_back_below_27c_threshold() -> None:
    """Below 27°C (Rothfusz validity threshold) → returns cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 26.9  # just below
    env._cur_humidity = 80.0
    assert env.apparent_temp == 26.9


def test_apparent_temp_above_threshold_humid_celsius() -> None:
    """Above threshold + humid → apparent_temp > cur_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0  # ≈90°F
    env._cur_humidity = 80.0
    # Expect ≈41°C (≈ heat index 113°F → 45°C upper bound).
    apparent = env.apparent_temp
    assert apparent is not None
    assert 39.0 < apparent < 47.0
    assert apparent > env._cur_temp


def test_apparent_temp_fahrenheit_input_conversion() -> None:
    """Same physical conditions in °F input → consistent output in °F."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    hass = MagicMock()
    hass.config.units.temperature_unit = UnitOfTemperature.FAHRENHEIT
    env = EnvironmentManager(hass, {CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 90.0  # 90°F = 32.2°C
    env._cur_humidity = 80.0
    apparent = env.apparent_temp
    # 90°F / 80% RH → 113°F per NWS table (window 110-116).
    assert 110.0 < apparent < 116.0
```

- [ ] **Step 4.2: Run; expect failures**

```bash
./scripts/docker-test tests/test_environment_manager.py -k apparent_temp -v
```

Expected: `AttributeError: 'EnvironmentManager' object has no attribute 'apparent_temp'`.

- [ ] **Step 4.3: Implement the property**

Add the import for `UnitOfTemperature` near the top of `environment_manager.py` if absent. Verify:

```bash
grep -n "UnitOfTemperature" custom_components/dual_smart_thermostat/managers/environment_manager.py
```

The class already imports `TemperatureConverter` (used by `max_temp` and `min_temp` properties). Just confirm `UnitOfTemperature` is also imported (it's typically in the same `from homeassistant.const import` line).

Add the property anywhere reasonable in the class — near `cur_humidity` (around line 267) or near `cur_outside_temp` (around line 147) is fine. Recommended location: just below `cur_outside_temp` (line 148) so all "current" properties stay together.

```python
    @property
    def apparent_temp(self) -> float | None:
        """Heat-index ("feels-like") temperature in the user's configured unit.

        Returns ``cur_temp`` (i.e. acts as a no-op) when:
        - ``CONF_USE_APPARENT_TEMP`` is False,
        - ``cur_temp`` or ``cur_humidity`` is missing,
        - the humidity sensor is stalled,
        - or the dry-bulb temperature is below 27 °C (Rothfusz validity).

        Otherwise returns the NWS Rothfusz heat index, computed in °F and
        converted back to the user's unit.
        """
        if not self._use_apparent_temp:
            return self._cur_temp
        if self._cur_temp is None or self._cur_humidity is None:
            return self._cur_temp
        if self._humidity_sensor_stalled:
            return self._cur_temp
        cur_c = TemperatureConverter.convert(
            self._cur_temp, self._temperature_unit, UnitOfTemperature.CELSIUS
        )
        if cur_c < 27.0:
            return self._cur_temp
        cur_f = TemperatureConverter.convert(
            self._cur_temp, self._temperature_unit, UnitOfTemperature.FAHRENHEIT
        )
        hi_f = _rothfusz_heat_index_f(cur_f, self._cur_humidity)
        return TemperatureConverter.convert(
            hi_f, UnitOfTemperature.FAHRENHEIT, self._temperature_unit
        )
```

- [ ] **Step 4.4: Run; expect 7 passes**

```bash
./scripts/docker-test tests/test_environment_manager.py -k apparent_temp -v
```

- [ ] **Step 4.5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/environment_manager.py tests/test_environment_manager.py
git commit -m "feat(auto-mode): EnvironmentManager.apparent_temp property"
```

---

## Task 5: `EnvironmentManager.effective_temp_for_mode` selector

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/environment_manager.py`

- [ ] **Step 5.1: Write failing tests**

Append to `tests/test_environment_manager.py`:

```python
def test_effective_temp_for_mode_returns_cur_when_flag_off() -> None:
    """Flag off → returns cur_temp for every mode."""
    env = _make_env()
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    for mode in (HVACMode.HEAT, HVACMode.COOL, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.AUTO):
        assert env.effective_temp_for_mode(mode) == 32.0


def test_effective_temp_for_mode_cool_returns_apparent_when_eligible() -> None:
    """COOL mode + flag on + humid + above 27°C → returns apparent_temp."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    eff = env.effective_temp_for_mode(HVACMode.COOL)
    assert eff is not None
    assert eff > 32.0  # apparent boosts above raw


def test_effective_temp_for_mode_non_cool_returns_cur() -> None:
    """Non-COOL modes → returns cur_temp even when flag is on."""
    from custom_components.dual_smart_thermostat.const import CONF_USE_APPARENT_TEMP

    env = _make_env(**{CONF_USE_APPARENT_TEMP: True})
    env._cur_temp = 32.0
    env._cur_humidity = 80.0
    for mode in (HVACMode.HEAT, HVACMode.DRY, HVACMode.FAN_ONLY, HVACMode.AUTO):
        assert env.effective_temp_for_mode(mode) == 32.0
```

- [ ] **Step 5.2: Run; expect failures**

```bash
./scripts/docker-test tests/test_environment_manager.py -k effective_temp -v
```

- [ ] **Step 5.3: Implement**

Add the method to `EnvironmentManager` immediately after `apparent_temp`:

```python
    def effective_temp_for_mode(self, mode) -> float | None:
        """Return the temperature to use for control decisions in ``mode``.

        Substitutes ``apparent_temp`` for ``cur_temp`` only when the mode is
        COOL and the apparent-temp prerequisites are met (see ``apparent_temp``).
        All other modes get raw ``cur_temp`` regardless of the flag.
        """
        if mode == HVACMode.COOL:
            return self.apparent_temp
        return self._cur_temp
```

`HVACMode` is already imported in the file — verify:

```bash
grep -n "from homeassistant.components.climate import" custom_components/dual_smart_thermostat/managers/environment_manager.py
```

If not, add `HVACMode` to the existing climate-component imports.

- [ ] **Step 5.4: Run; expect 3 passes**

```bash
./scripts/docker-test tests/test_environment_manager.py -k effective_temp -v
```

- [ ] **Step 5.5: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/environment_manager.py tests/test_environment_manager.py
git commit -m "feat(auto-mode): EnvironmentManager.effective_temp_for_mode selector"
```

---

## Task 6: Make `EnvironmentManager.is_too_hot` apparent-aware

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/environment_manager.py:477-492`

- [ ] **Step 6.1: Write failing test**

Append to `tests/test_environment_manager.py`:

```python
def test_is_too_hot_uses_apparent_when_mode_cool_and_flag_on() -> None:
    """is_too_hot consults apparent_temp when env._hvac_mode == COOL and flag on.

    Setup: target=21.0, hot_tolerance=0.5, cur_temp=21.5 (1× over → normally too_hot=False
    because we're exactly at the hot-tolerance boundary), but humidity=80% pushes
    apparent above the threshold.

    Wait — at cur_temp=21.5 (below 27°C), apparent falls back to raw. So this test
    needs cur_temp ≥ 27°C to trigger apparent.

    Adjust: target=27.0, hot_tolerance=0.5, cur_temp=27.5 (raw too_hot = True
    because cur_temp >= 27.5 == target+tolerance, but the test must verify that
    apparent is what was consulted, not raw, when COOL + flag on).

    A cleaner version: target=27.0, cur_temp=27.4, humidity=80%, flag on, mode=COOL.
    raw cur_temp 27.4 < 27.5 → raw is_too_hot=False. apparent ≈ 30°C → apparent
    is_too_hot=True. Asserts on apparent path.
    """
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
        CONF_USE_APPARENT_TEMP,
    )

    env = _make_env(
        **{
            CONF_USE_APPARENT_TEMP: True,
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4  # raw is just below target+tolerance (27.5)
    env._cur_humidity = 80.0  # apparent boosts above threshold
    env._hvac_mode = HVACMode.COOL
    # Force the active tolerance returned by _get_active_tolerance_for_mode to (0.3, 0.5).
    # The default config doesn't set heat_tolerance/cool_tolerance, so the helper
    # falls back to cold_tolerance / hot_tolerance. cold_tolerance defaults via
    # the const module value (0.3). cur_temp 27.4 with target 27.0, tol 0.5 →
    # raw too_hot=False, apparent (~30) too_hot=True.
    assert env.is_too_hot() is True


def test_is_too_hot_uses_raw_when_mode_not_cool() -> None:
    """is_too_hot uses raw cur_temp when env._hvac_mode != COOL even with flag on."""
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
        CONF_USE_APPARENT_TEMP,
    )

    env = _make_env(
        **{
            CONF_USE_APPARENT_TEMP: True,
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4
    env._cur_humidity = 80.0
    env._hvac_mode = HVACMode.HEAT  # NOT cool
    # Raw cur_temp 27.4 < target+tolerance (27.5) → False.
    assert env.is_too_hot() is False


def test_is_too_hot_uses_raw_when_flag_off() -> None:
    """Flag off → raw cur_temp regardless of mode."""
    from custom_components.dual_smart_thermostat.const import (
        CONF_HOT_TOLERANCE,
        CONF_TARGET_TEMP,
    )

    env = _make_env(
        **{
            CONF_TARGET_TEMP: 27.0,
            CONF_HOT_TOLERANCE: 0.5,
        }
    )
    env._cur_temp = 27.4
    env._cur_humidity = 80.0
    env._hvac_mode = HVACMode.COOL
    assert env.is_too_hot() is False
```

- [ ] **Step 6.2: Run; expect first test to fail**

```bash
./scripts/docker-test tests/test_environment_manager.py -k is_too_hot -v
```

Expected: `test_is_too_hot_uses_apparent_when_mode_cool_and_flag_on` fails (returns False instead of True). The other two should pass already.

- [ ] **Step 6.3: Modify `is_too_hot`**

Find the existing method (currently at line 477). Replace its body to consult `effective_temp_for_mode` when mode is COOL:

```python
    def is_too_hot(self, target_attr="_target_temp") -> bool:
        """Checks if the current temperature is above target.

        Uses ``effective_temp_for_mode(self._hvac_mode)`` so that COOL mode
        with ``CONF_USE_APPARENT_TEMP`` enabled compares against the heat
        index. All other modes compare against raw ``cur_temp`` (the
        selector returns ``cur_temp`` for them).
        """
        target_temp = getattr(self, target_attr)
        active_temp = self.effective_temp_for_mode(self._hvac_mode)
        if active_temp is None or target_temp is None:
            return False

        _, hot_tolerance = self._get_active_tolerance_for_mode()

        _LOGGER.debug(
            "is_too_hot - target temp attr: %s, Target temp: %s, "
            "active temp: %s (cur_temp: %s, mode: %s), tolerance: %s",
            target_attr,
            target_temp,
            active_temp,
            self._cur_temp,
            self._hvac_mode,
            hot_tolerance,
        )
        return active_temp >= target_temp + hot_tolerance
```

- [ ] **Step 6.4: Run; expect 3 passes**

```bash
./scripts/docker-test tests/test_environment_manager.py -k is_too_hot -v
```

- [ ] **Step 6.5: Run full suite**

```bash
./scripts/docker-test
```

Expected: all pass. Cooler-controller behavior is unchanged when the flag is off (default), so no regressions.

If any unrelated tests fail, the most likely cause is a test that mocks `_cur_temp` directly and didn't set `_hvac_mode`. The new code calls `self.effective_temp_for_mode(self._hvac_mode)` which returns `cur_temp` when mode is None or anything other than COOL — so behavior is identical for those tests. If a regression appears, STOP and investigate.

- [ ] **Step 6.6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/environment_manager.py tests/test_environment_manager.py
git commit -m "feat(auto-mode): is_too_hot consults apparent_temp in COOL mode"
```

---

## Task 7: AutoModeEvaluator's `_temp_too_hot` consults apparent

**Files:**
- Modify: `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- Test: `tests/test_auto_mode_evaluator.py`

- [ ] **Step 7.1: Write failing tests**

Append to `tests/test_auto_mode_evaluator.py`:

```python
def test_full_scan_picks_cool_when_apparent_above_target_even_if_raw_below() -> None:
    """When CONF_USE_APPARENT_TEMP is on, AUTO picks COOL using apparent temp.

    Setup: target=27, hot_tolerance=0.5, cur_temp=27.4 (raw → not too_hot),
    humidity=80% (apparent → ~30°C → too_hot). AUTO must pick COOL.
    """
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 27.4
    ev._environment.cur_humidity = 80.0
    ev._environment.target_temp = 27.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
    # Stub the env's effective_temp_for_mode to return apparent only for COOL.
    def _eff(mode):
        if mode == HVACMode.COOL:
            return 30.0  # simulated apparent temp
        return 27.4
    ev._environment.effective_temp_for_mode = _eff
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.COOL


def test_full_scan_does_not_pick_cool_when_raw_below_target_and_no_apparent_substitution() -> None:
    """Without apparent substitution, AUTO does NOT pick COOL when raw < target+tol."""
    ev = _make_evaluator()
    ev._features.is_configured_for_cooler_mode = True
    ev._environment.cur_temp = 27.4
    ev._environment.target_temp = 27.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
    # effective_temp_for_mode returns raw for all modes (flag off behaviour).
    ev._environment.effective_temp_for_mode = lambda mode: 27.4
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode is None  # idle


def test_full_scan_apparent_only_affects_cool_decisions() -> None:
    """HEAT decisions still consult cur_temp directly (regression guard)."""
    ev = _make_evaluator()
    ev._features.is_configured_for_heater_mode = True
    ev._environment.cur_temp = 20.5
    ev._environment.target_temp = 21.0
    ev._environment._get_active_tolerance_for_mode.return_value = (0.5, 0.5)
    # If something accidentally consulted effective_temp_for_mode for HEAT,
    # this stub would lie and say apparent is 22 — which would NOT trigger HEAT.
    # The test passes only if _temp_too_cold uses raw cur_temp (20.5 < 20.5).
    ev._environment.effective_temp_for_mode = lambda mode: 22.0
    decision = ev.evaluate(last_decision=None)
    assert decision.next_mode == HVACMode.HEAT
```

- [ ] **Step 7.2: Run; expect first test to fail**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k "apparent or full_scan_picks_cool_when_apparent" -v
```

- [ ] **Step 7.3: Modify `_temp_too_hot` in `auto_mode_evaluator.py`**

Find the helper (post-Phase-1.3, around line 245):

```python
    def _temp_too_hot(self, env, hot_tolerance: float, *, multiplier: int) -> bool:
        hot_target = self._hot_target(env)
        if env.cur_temp is None or hot_target is None:
            return False
        return env.cur_temp >= hot_target + multiplier * hot_tolerance
```

Replace with:

```python
    def _temp_too_hot(self, env, hot_tolerance: float, *, multiplier: int) -> bool:
        hot_target = self._hot_target(env)
        active_temp = env.effective_temp_for_mode(HVACMode.COOL)
        if active_temp is None or hot_target is None:
            return False
        return active_temp >= hot_target + multiplier * hot_tolerance
```

The change is two lines: replace `env.cur_temp` with `active_temp` (computed via `effective_temp_for_mode(HVACMode.COOL)`).

`_temp_too_cold` is NOT modified — HEAT decisions still consult raw `cur_temp` per the spec.

- [ ] **Step 7.4: Run; expect 3 passes**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -k "apparent or full_scan_picks_cool_when_apparent or apparent_only_affects" -v
```

- [ ] **Step 7.5: Run full evaluator suite**

```bash
./scripts/docker-test tests/test_auto_mode_evaluator.py -v
```

Expected: all pre-Phase-1.4 evaluator tests still pass (66 from Phase 1.3 + 3 new = 69).

If any pre-existing evaluator test fails, the cause is most likely a test that uses MagicMock for env without configuring `effective_temp_for_mode`. MagicMock auto-creates the method but returns a MagicMock object, not a number — so `active_temp >= hot_target + ...` would raise. The fix is in the existing `_make_evaluator` helper (line 18 of test_auto_mode_evaluator.py): the helper sets up sensible defaults; add `effective_temp_for_mode` to the defaults block:

```python
environment.effective_temp_for_mode = lambda mode: environment.cur_temp
```

Add this line in `_make_evaluator` immediately after the existing `environment.is_within_fan_tolerance.return_value = False` line. The lambda makes the mock behave like the real method when the flag is off — returns raw cur_temp.

- [ ] **Step 7.6: Commit**

```bash
git add custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py tests/test_auto_mode_evaluator.py
git commit -m "feat(auto-mode): evaluator _temp_too_hot consults effective_temp_for_mode(COOL)"
```

---

## Task 8: Climate entity syncs humidity-stalled flag + exposes `apparent_temperature` attribute

**Files:**
- Modify: `custom_components/dual_smart_thermostat/climate.py`

- [ ] **Step 8.1: Sync the stall flag into env**

Find every line that writes `self._humidity_sensor_stalled` in `climate.py` (Phase 1.2 added these). Mirror each write into the env manager:

```bash
grep -n "self._humidity_sensor_stalled\b" custom_components/dual_smart_thermostat/climate.py
```

Expect ~3 hits: the init (False), the recovery clear (False in `_async_sensor_humidity_changed`), and the stale callback (True in `_async_humidity_sensor_not_responding`).

For each `True`/`False` assignment, add a sibling line:

```python
        self.environment.humidity_sensor_stalled = <same value>
```

Specifically:

In `__init__` (around line 575 after Phase 1.3):
```python
        self._humidity_sensor_stalled = False
        self._outside_sensor_stalled = False
```
Add:
```python
        # Mirror to env so apparent_temp can fall back when humidity stalls.
        # (env defaults humidity_sensor_stalled to False at construction.)
```
(no actual code line needed in __init__ — the env defaults to False on construction)

In `_async_humidity_sensor_not_responding` (line ~1442 post-Phase-1.3, the line `self._humidity_sensor_stalled = True`):

Add immediately after:
```python
            self.environment.humidity_sensor_stalled = True
```

In `_async_sensor_humidity_changed` (around line 1507, the line `self._humidity_sensor_stalled = False`):

Add immediately after:
```python
                self.environment.humidity_sensor_stalled = False
```

- [ ] **Step 8.2: Expose `apparent_temperature` extra-state-attribute**

Find the existing `extra_state_attributes` property in `climate.py`:

```bash
grep -n "extra_state_attributes" custom_components/dual_smart_thermostat/climate.py | head -5
```

Inside the property, after the existing attribute additions, add:

```python
        # Phase 1.4: expose apparent ("feels-like") temp when the flag is
        # on and humidity is available. Hidden otherwise to avoid clutter.
        if self.environment._use_apparent_temp:
            apparent = self.environment.apparent_temp
            if apparent is not None and apparent != self.environment.cur_temp:
                attributes["apparent_temperature"] = round(apparent, 1)
```

(If the property uses a different attribute-dict name, match it. The codebase uses `attributes` consistently — confirm.)

- [ ] **Step 8.3: Run the full integration suite**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
./scripts/docker-test tests/test_environment_manager.py -v
```

Expected: all pass (no behavior change for default configs because the flag defaults to False).

- [ ] **Step 8.4: Commit**

```bash
git add custom_components/dual_smart_thermostat/climate.py
git commit -m "feat(auto-mode): climate syncs humidity stall to env + exposes apparent_temperature attribute"
```

---

## Task 9: Options flow toggle

**Files:**
- Modify: `custom_components/dual_smart_thermostat/options_flow.py`
- Test: `tests/config_flow/test_options_flow.py`

- [ ] **Step 9.1: Add the constant import**

In `options_flow.py`, add `CONF_USE_APPARENT_TEMP` to the existing `from .const import (...)` block (alphabetical — likely near `CONF_TARGET_TEMP`).

Verify `CONF_HUMIDITY_SENSOR` is also imported — Phase 1.4 needs to gate the toggle on it. If absent:

```bash
grep -n "CONF_HUMIDITY_SENSOR" custom_components/dual_smart_thermostat/options_flow.py
```

Add to imports if missing.

- [ ] **Step 9.2: Add the toggle to advanced_settings**

Find the block where Phase 1.3 added `CONF_AUTO_OUTSIDE_DELTA_BOOST` (gated on `CONF_OUTSIDE_SENSOR`). Immediately after that block, add:

```python
        # Phase 1.4 — apparent temp toggle, gated on humidity sensor configured.
        if current_config.get(CONF_HUMIDITY_SENSOR):
            advanced_dict[
                vol.Optional(
                    CONF_USE_APPARENT_TEMP,
                    default=current_config.get(CONF_USE_APPARENT_TEMP, False),
                )
            ] = selector.BooleanSelector()
```

- [ ] **Step 9.3: Write the persistence test**

Append to `tests/config_flow/test_options_flow.py`:

```python
@pytest.mark.asyncio
async def test_options_flow_persists_use_apparent_temp(mock_hass):
    """CONF_USE_APPARENT_TEMP round-trips through the options flow.

    The toggle lives in the advanced_settings collapsed section and is only
    surfaced when a humidity_sensor is configured.
    """
    config_entry = Mock()
    config_entry.data = {
        CONF_NAME: "Test Thermostat",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.temperature",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
    }
    config_entry.options = {}
    config_entry.entry_id = "test_apparent_temp_entry"

    flow = OptionsFlowHandler(config_entry)
    flow.hass = mock_hass

    result = await flow.async_step_init()
    assert result["type"] == FlowResultType.FORM

    result = await flow.async_step_init(
        {
            "advanced_settings": {
                CONF_USE_APPARENT_TEMP: True,
            }
        }
    )

    max_steps = 10
    while result["type"] == FlowResultType.FORM and max_steps > 0:
        step_id = result.get("step_id", "")
        step_handler = getattr(flow, f"async_step_{step_id}", None)
        if step_handler is None:
            break
        result = await step_handler({})
        max_steps -= 1

    assert flow.collected_config.get(CONF_USE_APPARENT_TEMP) is True
```

Add `CONF_USE_APPARENT_TEMP` and `CONF_HUMIDITY_SENSOR` to the file's `from custom_components.dual_smart_thermostat.const import (...)` block if absent.

- [ ] **Step 9.4: Run the new test + full options-flow suite**

```bash
./scripts/docker-test tests/config_flow/test_options_flow.py::test_options_flow_persists_use_apparent_temp -v
./scripts/docker-test tests/config_flow/test_options_flow.py -v
```

Expected: new test passes; full options-flow suite stays green.

- [ ] **Step 9.5: Commit**

```bash
git add custom_components/dual_smart_thermostat/options_flow.py tests/config_flow/test_options_flow.py
git commit -m "feat(auto-mode): options-flow toggle for CONF_USE_APPARENT_TEMP"
```

---

## Task 10: Translations

**Files:**
- Modify: `custom_components/dual_smart_thermostat/translations/en.json`

- [ ] **Step 10.1: Add labels and descriptions**

In `translations/en.json`, find the `options.step.init.sections.advanced_settings` block (the same one Phase 1.3 modified — line ~690 onwards). In `data`, add:

```json
"use_apparent_temp": "Use apparent (\"feels-like\") temperature for cooling decisions"
```

Sibling immediately after `auto_outside_delta_boost`.

In `data_description`, add:

```json
"use_apparent_temp": "When enabled and a humidity sensor is configured, AUTO and standalone COOL decide based on the heat index instead of raw temperature. Above 27°C / 80°F humidity makes the room feel hotter, so the cooler runs more aggressively. The actual sensor temperature continues to be shown in the UI."
```

- [ ] **Step 10.2: Validate JSON**

```bash
python3 -m json.tool custom_components/dual_smart_thermostat/translations/en.json > /dev/null && echo OK
```

- [ ] **Step 10.3: Commit**

```bash
git add custom_components/dual_smart_thermostat/translations/en.json
git commit -m "docs(auto-mode): translation strings for use_apparent_temp"
```

---

## Task 11: GWT integration tests — heater_cooler

**Files:**
- Modify: `tests/test_auto_mode_integration.py`

- [ ] **Step 11.1: Confirm the existing helper supports the flag**

The Phase-1.3 helper `_heater_cooler_yaml(initial_mode=HVACMode.OFF, **extra)` accepts arbitrary extra config keys via `**extra`. So passing `use_apparent_temp=True` and `humidity_sensor=...` should "just work".

Verify by reading lines 34-56 of `tests/test_auto_mode_integration.py`. If the helper hard-codes the dict without spread, adapt as needed.

- [ ] **Step 11.2: Add three GWT tests for heater_cooler**

Append to `tests/test_auto_mode_integration.py`:

```python
# ---------------------------------------------------------------------------
# Phase 1.4: apparent temperature
# ---------------------------------------------------------------------------

ENT_HUMIDITY_SENSOR = "sensor.humidity_test"


@pytest.mark.asyncio
async def test_heater_cooler_auto_picks_cool_via_apparent_temp(
    hass: HomeAssistant,
) -> None:
    """Given heater_cooler+humidity sensor with use_apparent_temp on,
    AUTO active, target=27 °C, raw cur_temp=27.4 (1× below tolerance),
    humidity=80% (apparent ≈ 30 °C, well above target+tolerance) /
    When AUTO evaluates /
    Then it picks COOL with AUTO_PRIORITY_TEMPERATURE.
    """
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)

    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(
            humidity_sensor=ENT_HUMIDITY_SENSOR,
            target_temp=27.0,
            target_humidity=50,
            moist_tolerance=5,
            dry_tolerance=5,
            use_apparent_temp=True,
        ),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"
    # apparent_temperature attribute exposed when flag on AND humidity available
    # AND apparent != cur_temp.
    assert "apparent_temperature" in state.attributes


@pytest.mark.asyncio
async def test_heater_cooler_standalone_cool_uses_apparent_temp(
    hass: HomeAssistant,
) -> None:
    """Given heater_cooler+humidity with use_apparent_temp on /
    User sets HVAC mode to COOL directly (not AUTO), target=27°C,
    cur_temp=27.4, humidity=80% /
    When the cooler controller evaluates /
    Then is_too_hot returns True via apparent (raw would be False) and the
    cooler service-call fires."""
    hass.config.units = METRIC_SYSTEM
    calls = setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)

    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(
            humidity_sensor=ENT_HUMIDITY_SENSOR,
            target_temp=27.0,
            target_humidity=50,
            moist_tolerance=5,
            dry_tolerance=5,
            use_apparent_temp=True,
        ),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.COOL, common.ENTITY)
    await hass.async_block_till_done()

    cool_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == ENT_COOLER_SWITCH
    ]
    assert cool_calls, "cooler should fire because apparent >= target+tol"


@pytest.mark.asyncio
async def test_heater_cooler_apparent_temp_off_matches_phase_1_3(
    hass: HomeAssistant,
) -> None:
    """Given heater_cooler+humidity but use_apparent_temp left off /
    AUTO active, target=27, cur_temp=27.4, humidity=80% /
    When AUTO evaluates /
    Then it does NOT pick COOL (raw < target+tolerance) — Phase 1.3 behavior
    is preserved (regression guard)."""
    hass.config.units = METRIC_SYSTEM
    setup_switch_dual(hass, ENT_COOLER_SWITCH, False, False)
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)

    assert await async_setup_component(
        hass,
        CLIMATE,
        _heater_cooler_yaml(
            humidity_sensor=ENT_HUMIDITY_SENSOR,
            target_temp=27.0,
            target_humidity=50,
            moist_tolerance=5,
            dry_tolerance=5,
            # use_apparent_temp NOT set → defaults to False
        ),
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    # Without apparent, raw cur_temp 27.4 is below 27.5 (target+0.5) → idle.
    assert state.attributes["hvac_action_reason"] != "auto_priority_temperature"
    assert "apparent_temperature" not in state.attributes
```

- [ ] **Step 11.3: Run; expect 3 passes**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -k "apparent" -v
```

- [ ] **Step 11.4: Run full integration suite**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -v
```

Expected: prior 16 + 3 new = 19 passed.

- [ ] **Step 11.5: Commit**

```bash
git add tests/test_auto_mode_integration.py
git commit -m "test(auto-mode): heater_cooler integration tests for apparent temp"
```

---

## Task 12: GWT integration tests — heat_pump

**Files:**
- Modify: `tests/test_auto_mode_integration.py`

- [ ] **Step 12.1: Append two heat_pump tests**

```python
@pytest.mark.asyncio
async def test_heat_pump_auto_picks_cool_via_apparent_temp(
    hass: HomeAssistant,
) -> None:
    """Given a heat_pump system with humidity sensor + use_apparent_temp on,
    target=27, cur_temp=27.4, humidity=80% /
    When AUTO evaluates /
    Then it routes to COOL via the heat-pump dispatch path (proves the env
    plumbing works through heat_pump too, not just heater_cooler)."""
    hass.config.units = METRIC_SYSTEM
    hass.states.async_set(common.ENT_SWITCH, STATE_OFF)
    hass.states.async_set("binary_sensor.heat_pump_cooling", "off")
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)

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
                "heat_pump_cooling": "binary_sensor.heat_pump_cooling",
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": ENT_HUMIDITY_SENSOR,
                "target_temp": 27.0,
                "target_humidity": 50,
                "moist_tolerance": 5,
                "dry_tolerance": 5,
                "use_apparent_temp": True,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] == "auto_priority_temperature"


@pytest.mark.asyncio
async def test_heat_pump_apparent_temp_off_matches_phase_1_3(
    hass: HomeAssistant,
) -> None:
    """heat_pump with humidity sensor but apparent flag OFF must behave as
    Phase 1.3 did (regression guard)."""
    hass.config.units = METRIC_SYSTEM
    hass.states.async_set(common.ENT_SWITCH, STATE_OFF)
    hass.states.async_set("binary_sensor.heat_pump_cooling", "off")
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)

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
                "heat_pump_cooling": "binary_sensor.heat_pump_cooling",
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": ENT_HUMIDITY_SENSOR,
                "target_temp": 27.0,
                "target_humidity": 50,
                "moist_tolerance": 5,
                "dry_tolerance": 5,
                "initial_hvac_mode": HVACMode.OFF,
                # use_apparent_temp NOT set
            }
        },
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes["hvac_action_reason"] != "auto_priority_temperature"
    assert "apparent_temperature" not in state.attributes
```

- [ ] **Step 12.2: Run; expect 2 passes**

```bash
./scripts/docker-test tests/test_auto_mode_integration.py -k "heat_pump_auto_picks_cool_via_apparent or heat_pump_apparent_temp_off" -v
```

- [ ] **Step 12.3: Commit**

```bash
git add tests/test_auto_mode_integration.py
git commit -m "test(auto-mode): heat_pump integration tests for apparent temp"
```

---

## Task 13: GWT integration tests — ac_only

**Files:**
- Modify: `tests/test_ac_only_mode.py`

- [ ] **Step 13.1: Examine the existing test patterns**

```bash
grep -nE "^async def test_|setup_sensor|setup_humidity_sensor|setup_switch_dual|ac_mode" tests/test_ac_only_mode.py | head -20
```

The ac_only system uses `ac_mode: True` with a `cooler` switch. Confirm the helper conventions in this file. Most ac_only tests likely use `setup_sensor` + `setup_switch` (no dual switch) for the cooler entity. If there's a YAML helper analogous to `_heater_cooler_yaml`, use it. Otherwise, write a minimal self-contained YAML inline.

- [ ] **Step 13.2: Append two tests**

Append at the end of `tests/test_ac_only_mode.py`:

```python
@pytest.mark.asyncio
async def test_ac_only_cool_uses_apparent_temp_when_flag_on(
    hass: HomeAssistant,
) -> None:
    """Given ac_only with humidity sensor + use_apparent_temp on,
    target=27, cur_temp=27.4 (raw not too_hot), humidity=80% /
    When user sets HVAC mode to COOL /
    Then the cooler fires because apparent ≥ target+tolerance."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)
    calls = setup_switch(hass, False)  # cooler switch — ac_only uses single switch

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "ac_mode": True,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,  # ac_mode uses the heater key for the cooler switch
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": ENT_HUMIDITY_SENSOR,
                "target_temp": 27.0,
                "target_humidity": 50,
                "moist_tolerance": 5,
                "dry_tolerance": 5,
                "use_apparent_temp": True,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.COOL, common.ENTITY)
    await hass.async_block_till_done()

    cool_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    assert cool_calls, "ac_only cooler should fire via apparent_temp"


@pytest.mark.asyncio
async def test_ac_only_apparent_temp_off_does_not_cool_when_raw_below(
    hass: HomeAssistant,
) -> None:
    """ac_only with humidity sensor but apparent flag OFF must NOT cool when
    raw cur_temp is below target+tolerance (regression guard)."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 27.4)
    setup_humidity_sensor(hass, 80.0)
    calls = setup_switch(hass, False)

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "ac_mode": True,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": ENT_HUMIDITY_SENSOR,
                "target_temp": 27.0,
                "target_humidity": 50,
                "moist_tolerance": 5,
                "dry_tolerance": 5,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()
    await common.async_set_hvac_mode(hass, HVACMode.COOL, common.ENTITY)
    await hass.async_block_till_done()

    cool_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    assert not cool_calls, "ac_only must not cool when raw < target+tol and apparent off"
```

Add `from . import setup_humidity_sensor, setup_switch, setup_sensor` and `ENT_HUMIDITY_SENSOR = "sensor.humidity_test"` near the top of the file if absent. Confirm import names by reading the existing imports in test_ac_only_mode.py.

- [ ] **Step 13.3: Run**

```bash
./scripts/docker-test tests/test_ac_only_mode.py -k "ac_only_cool_uses_apparent or ac_only_apparent_temp_off" -v
```

Expected: 2 passed.

If the test fails because `setup_switch` (single-switch helper) isn't the right name in this file — read the existing tests in test_ac_only_mode.py for the actual helper. Use whatever the existing tests use to register the cooler switch and capture service calls.

- [ ] **Step 13.4: Commit**

```bash
git add tests/test_ac_only_mode.py
git commit -m "test(auto-mode): ac_only integration tests for apparent temp"
```

---

## Task 14: Lint, full test run, push, open PR

- [ ] **Step 14.1: Run lint**

```bash
./scripts/docker-lint --fix
```

If new findings unrelated to Phase 1.4 appear (`htmlcov/`, `config/deps/`, pre-existing codespell findings), ignore. New findings on this phase's files must be resolved.

- [ ] **Step 14.2: Run the full suite**

```bash
./scripts/docker-test
```

Expected: 1479 (Phase 1.3 baseline) + new Phase 1.4 tests = ~1500 passed. 0 failed.

- [ ] **Step 14.3: Push**

```bash
git push -u origin feat/auto-mode-phase-1-4-apparent-temp
```

- [ ] **Step 14.4: Open the PR**

```bash
gh pr create --base master --head feat/auto-mode-phase-1-4-apparent-temp \
  --title "feat: Auto Mode Phase 1.4 — apparent (\"feels-like\") temperature" \
  --body "$(cat <<'PR'
## Summary

Phase 1.4 of the Auto Mode roadmap (#563). Adds the NWS Rothfusz heat-index ("feels-like" temperature) for cooling decisions:

- **AUTO's COOL branch** now consults apparent temp via `EnvironmentManager.effective_temp_for_mode(HVACMode.COOL)`.
- **The cooler controller** (heater_cooler, heat_pump dispatched COOL, ac_only) — same. \`is_too_hot()\` is now apparent-aware when env's mode is COOL.
- **One new options-flow toggle**: \`use_apparent_temp\`, gated on \`humidity_sensor\` configured. Default off → identical to Phase 1.3.
- **\`apparent_temperature\` state attribute** exposed when flag on AND humidity available AND apparent ≠ cur_temp. UI's \`current_temperature\` continues to show the raw sensor reading.
- HEAT, DRY, FAN_ONLY are unchanged — the formula is undefined below 27 °C and meaningless for them anyway.

## Spec & plan

- Design: \`docs/superpowers/specs/2026-04-30-auto-mode-phase-1-4-apparent-temp-design.md\`
- Plan: \`docs/superpowers/plans/2026-04-30-auto-mode-phase-1-4-apparent-temp.md\`

## Test plan

- [x] Heat-index math + selector + apparent-aware \`is_too_hot\` — \`tests/test_environment_manager.py\`.
- [x] Evaluator COOL-priority apparent — \`tests/test_auto_mode_evaluator.py\`.
- [x] Per-system-type integration tests:
  - heater_cooler — AUTO+apparent picks COOL, standalone COOL uses apparent, flag-off regression.
  - heat_pump — AUTO+apparent via heat-pump dispatch, flag-off regression.
  - ac_only — standalone COOL uses apparent, flag-off regression.
- [x] Options-flow round-trip persistence.
- [x] Full suite green; lint clean.

## Roadmap

- ✅ Phase 0 (#569) — \`hvac_action_reason\` sensor entity
- ✅ Phase 1.1 (#570) — auto-mode availability detection
- ✅ Phase 1.2 (#577) — priority evaluation engine
- ✅ Phase 1.3 (#580) — outside-temperature bias
- ⬅️  **Phase 1.4 (this PR)** — apparent temperature
- ⬜ Phase 2.x — PID controller, autotune, feedforward
PR
)"
```

- [ ] **Step 14.5: Watch CI**

```bash
gh pr checks <PR-NUMBER> --watch
```

---

## Self-Review Notes

**Spec coverage:**
- §2.1 formula → Task 2.
- §2.2 selector → Task 5.
- §2.3 both-sides substitution → Tasks 6 (cooler) + 7 (evaluator).
- §3 config + option → Tasks 1 + 9.
- §4 unit handling → inside Task 4 (apparent_temp uses TemperatureConverter).
- §5 sensor availability → Tasks 4 (apparent_temp guard) + 8 (climate syncs stall).
- §6 diagnostic exposure → Task 8.
- §7 code structure → matches Tasks 1–10 1:1.
- §8 testing — per system type → Tasks 11 (heater_cooler), 12 (heat_pump), 13 (ac_only). Unit tests in Tasks 2-7 + 9.
- §9 out of scope — respected; HEAT/DRY/FAN_ONLY untouched.

**Type consistency:**
- Method name `effective_temp_for_mode` used identically in Tasks 5, 6, 7.
- Property name `apparent_temp` used identically in Tasks 4, 8.
- Helper name `_rothfusz_heat_index_f` used identically in Tasks 2, 4.
- Flag name `_use_apparent_temp` used identically in Tasks 3, 4, 5, 8.
- Climate-side flag name remains `_humidity_sensor_stalled` (Phase 1.2); Task 8 mirrors it into env via the public setter `humidity_sensor_stalled`.

**No placeholders:** every step has either concrete code or a concrete shell command with expected output. Two locations note "match existing pattern" or "verify import name" — those reference attributes that exist in the file at named line numbers and the implementer can verify in seconds.
