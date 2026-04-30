# Auto Mode Phase 1.4 — Apparent ("Feels-Like") Temperature

**Date:** 2026-04-30
**Roadmap issue:** #563
**Depends on:** Phase 1.3 (outside-temperature bias, PR #580, merged)

## 1. Goal

Add `CONF_USE_APPARENT_TEMP`. When the flag is on AND humidity is available, the COOL decision path — both the priority-picking layer (`AutoModeEvaluator`) and the cooler bang-bang controller — operates on the **NWS Rothfusz heat index** instead of raw dry-bulb temperature.

AUTO picks COOL based on how the room *feels*. Once COOL is running, the cooler cycles ON and OFF against the same metric (no asymmetric hysteresis). HEAT, DRY, FAN_ONLY are unaffected — heat index is not a meaningful signal for them and the formula is undefined below 27 °C anyway.

Backward compatible: flag defaults to false; behavior identical to Phase 1.3 when off.

## 2. Behavior

### 2.1 Apparent-temp formula

`EnvironmentManager.apparent_temp` returns:

- `cur_temp` if `cur_temp` is None, `cur_humidity` is None, the humidity sensor is stalled, or `cur_temp_in_C < 27.0` (the Rothfusz formula's validity threshold).
- Otherwise, the Rothfusz polynomial in °F (8 standard NWS coefficients), then converted back to the user's configured unit.

Internally, the calculation is performed in °F because the published coefficients are in °F. Inputs are converted via `homeassistant.util.unit_conversion.TemperatureConverter`.

### 2.2 Mode-aware selector

`EnvironmentManager.effective_temp_for_mode(mode: HVACMode) -> float | None`:

- If `_use_apparent_temp` is False → returns `cur_temp` regardless of mode.
- If `mode == HVACMode.COOL` AND apparent-temp prerequisites are met → returns `apparent_temp`.
- Otherwise → returns `cur_temp`.

This is the only public new method on `EnvironmentManager`. Existing methods (`is_too_hot`, `is_too_cold`, `cur_temp`, etc.) are NOT modified — callers that should consult apparent temp will switch to the new method explicitly.

### 2.3 Both-sides substitution

The cooler controller AND `AutoModeEvaluator`'s COOL branch compare against the same effective-temp value when deciding to start AND stop cooling. No asymmetry → no extra cycling. The user effectively gets "cool until it FEELS like target".

### 2.4 Concrete examples

| `cur_temp` | RH | Flag on | `effective_temp_for_mode(COOL)` |
|---|---|---|---|
| 18 °C | 80% | Yes | 18 °C (below threshold) |
| 26.9 °C | 80% | Yes | 26.9 °C (still below) |
| 27 °C | 40% | Yes | ~27 °C (formula barely active) |
| 27 °C | 80% | Yes | ~30 °C |
| 32 °C | 80% | Yes | ~41 °C |
| 32 °C | 80% | No | 32 °C (flag off — raw) |
| 32 °C | None | Yes | 32 °C (humidity unavailable) |

## 3. Configuration

One new option:

| Key | Default | Type | Where |
|---|---|---|---|
| `CONF_USE_APPARENT_TEMP` | `False` | `bool` | options flow only — not initial config |

Lives in the `advanced_settings` section alongside `auto_outside_delta_boost`. Step entry appears **only when** `humidity_sensor` is configured (otherwise the flag has no effect).

No new dependency tracker entry: the flag is silently ignored when the humidity sensor is absent, mirroring the Phase 1.3 outside-sensor pattern.

## 4. Unit handling

The Rothfusz polynomial is published with °F coefficients. The implementation converts inside the property:

```python
def apparent_temp(self) -> float | None:
    if not self._use_apparent_temp:
        return self.cur_temp
    if self.cur_temp is None or self.cur_humidity is None or self._humidity_sensor_stalled:
        return self.cur_temp
    cur_c = TemperatureConverter.convert(
        self.cur_temp, self._unit, UnitOfTemperature.CELSIUS
    )
    if cur_c < 27.0:
        return self.cur_temp
    cur_f = TemperatureConverter.convert(
        self.cur_temp, self._unit, UnitOfTemperature.FAHRENHEIT
    )
    rh = self.cur_humidity
    hi_f = _ROTHFUSZ_HEAT_INDEX(cur_f, rh)
    return TemperatureConverter.convert(
        hi_f, UnitOfTemperature.FAHRENHEIT, self._unit
    )
```

The 8-term polynomial lives as a private module-level helper `_ROTHFUSZ_HEAT_INDEX(t_f: float, rh: float) -> float` in `environment_manager.py`. Coefficients are the NWS standard.

## 5. Sensor availability

| State | Behavior |
|---|---|
| `humidity_sensor` not configured | Flag has no effect. Identical to Phase 1.3. |
| Humidity reading `unknown`/`unavailable` | `apparent_temp` falls back to `cur_temp`. |
| Humidity stalled (existing stall flag from Phase 1.2) | Same — raw `cur_temp`. |
| `cur_temp` below 27 °C | Formula not valid; raw `cur_temp`. |

Outside-temperature data is unrelated to this phase.

## 6. Diagnostic exposure

When `CONF_USE_APPARENT_TEMP` is on AND humidity is available, `climate.py` exposes a new state attribute:

```yaml
apparent_temperature: 30.5
```

Visible in HA dev tools / Lovelace card YAML / template sensors. Hidden when the flag is off (no clutter for users not using the feature).

`current_temperature` (the canonical attribute) ALWAYS reflects the raw sensor reading — UI shows actual room temp, even when control logic uses apparent.

## 7. Code structure

| File | Change |
|---|---|
| `const.py` | Add `CONF_USE_APPARENT_TEMP`. |
| `managers/environment_manager.py` | Add `_use_apparent_temp` flag from config. Add `apparent_temp` property. Add `effective_temp_for_mode(mode)` selector. Add private `_ROTHFUSZ_HEAT_INDEX(t_f, rh)` helper. |
| `managers/auto_mode_evaluator.py` | In the helpers `_temp_too_hot` / `_hot_target` (used by both normal and urgent-tier COOL checks), replace `env.cur_temp` with `env.effective_temp_for_mode(HVACMode.COOL)`. The free-cooling check (`_free_cooling_applies`) keeps raw `cur_temp` (inside/outside delta is meaningful only for actual temps). |
| `hvac_controller/cooler_controller.py` (verify exact location during implementation) | Substitute `env.cur_temp` with `env.effective_temp_for_mode(HVACMode.COOL)` in cooling on/off comparisons. |
| `climate.py` | Pass through (no constructor change — `EnvironmentManager` already receives the full config dict). Expose `apparent_temperature` extra-state-attribute when flag on AND humidity available. |
| `schemas.py` | Add `vol.Optional(CONF_USE_APPARENT_TEMP): cv.boolean` to `PLATFORM_SCHEMA`. |
| `options_flow.py` | Add boolean toggle in `advanced_settings`, gated on `humidity_sensor` configured. |
| `translations/en.json` | Translation keys for the toggle label + description. |
| `tests/test_environment_manager.py` (or new test file) | Unit tests for `apparent_temp` math + `effective_temp_for_mode`. |
| `tests/test_auto_mode_evaluator.py` | Tests that COOL priority decisions consult apparent temp when flag is on. |
| `tests/test_auto_mode_integration.py` | Per-system-type GWT scenarios (see §8). |
| `tests/config_flow/test_options_flow.py` | Round-trip persistence test. |

No changes to `hvac_action_reason/` (reuses existing reasons — diagnostic sensor still reports `auto_priority_temperature`).

## 8. Testing — per system type

### 8.1 Unit tests

- **`test_environment_manager.py`** — ~12 tests covering the formula at boundary points (26.9 / 27.0 / 27.1 °C), Fahrenheit input, all fallback paths, and the `effective_temp_for_mode(...)` selector matrix (COOL vs every other mode, flag on/off).
- **`test_auto_mode_evaluator.py`** — 3 tests covering COOL priority decisions when the flag is on (positive case, flag-off regression, free-cooling still uses raw delta).

### 8.2 Integration / GWT — per system type

The feature affects every system type that exposes COOL. Coverage matrix:

| System type | AUTO + apparent_temp | Standalone COOL + apparent_temp | Flag-off regression |
|---|---|---|---|
| **ac_only** | n/a (AUTO not exposed) | ✅ humid 26 °C → cooler runs above raw target | ✅ identical to today |
| **heater_cooler** | ✅ humid 26 °C → AUTO picks COOL | ✅ standalone COOL respects apparent in ON/OFF | ✅ flag-off matches Phase 1.3 |
| **heat_pump** | ✅ humid 26 °C → AUTO picks COOL via heat-pump dispatch | (covered transitively — heat_pump uses the same cooler controller logic) | ✅ flag-off matches Phase 1.3 |

Total: **8 integration tests**.

| File | New tests |
|---|---|
| `tests/test_ac_only_mode.py` (or equivalent — confirm during implementation) | 2 — apparent-temp ON cools above raw target; flag-off regression |
| `tests/test_auto_mode_integration.py` | 4 — heater_cooler AUTO+apparent, heater_cooler standalone COOL+apparent, heater_cooler flag-off regression, heat_pump AUTO+apparent |
| `tests/test_heat_pump_mode.py` (or equivalent) | 1 — heat_pump flag-off regression |
| (test from existing GWT-style file) | 1 — heat_pump COOL via dispatch with apparent on (smoke) |

### 8.3 Config flow

Round-trip persistence test in `test_options_flow.py`. The toggle appears only when `humidity_sensor` is configured AND the system type has COOL capability (`ac_only`, `heater_cooler`, `heat_pump`).

### 8.4 Edge cases — covered by unit tests

- Humidity sensor unavailable / stalled / below threshold — exercised by mocking in `test_environment_manager.py`. Phase 1.2 already has integration coverage for the humidity-stall plumbing itself; Phase 1.4 doesn't need to re-test that path.
- Below 27 °C threshold — boundary tests at 26.9 / 27.0 / 27.1 °C in `test_environment_manager.py`.

## 9. Out of scope

- "Feels-like" for HEATING (wind chill, etc.). The Rothfusz formula doesn't apply below 27 °C; substituting at all would require a different model and a wind sensor we don't have.
- Apparent-temp influence on **DRY** mode (DRY operates on humidity directly, not temp).
- Apparent-temp influence on **FAN_ONLY**'s comfort band (already a humidity-related knob via fan-tolerance config; layering apparent-temp would muddy the existing user-visible setting).
- Phase 2 (PID controller, autotune, feedforward) — separate roadmap step.
