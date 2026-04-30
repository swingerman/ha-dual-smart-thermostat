# Auto Mode Phase 1.3 — Outside-Temperature Bias

**Date:** 2026-04-29
**Roadmap issue:** #563
**Depends on:** Phase 1.2 (priority engine, PR #577, merged)

## 1. Goal

Augment the AUTO priority engine with **outside-temperature-aware bias** so AUTO

1. reacts faster on extreme days (outside fighting us hard → escalate to urgent), and
2. prefers fan over compressor when the outdoor air can do the work for us (free cooling).

No new HVAC modes, no PID, no apparent-temp. Strictly extends the Phase 1.2 evaluator.

Backward compatible: when no `outside_sensor` is configured, behavior is identical to Phase 1.2.

## 2. Behavior

### 2.1 Outside-delta urgency promotion

If `|cur_temp − outside_temp| ≥ outside_delta_boost` AND the temperature priority (HEAT or COOL) would already fire on the **normal** tier (priority 7 or 8), promote it to the **urgent** tier (priority 4 or 5).

Direction guard:

- HEAT promotes only when `outside_temp < cur_temp` (cold outside is fighting our heat).
- COOL promotes only when `outside_temp > cur_temp` (hot outside is fighting our cool).

The `HVACActionReason` emitted is the same `AUTO_PRIORITY_TEMPERATURE` value Phase 1.2 already uses — the diagnostic sensor narrative does not change.

### 2.2 Free cooling

When the **normal-tier** COOL branch would fire (priority 8) AND the urgency promotion did NOT apply AND fan is configured AND `outside_temp ≤ cur_temp − FREE_COOLING_MARGIN`, the evaluator emits

```
AutoDecision(next_mode=FAN_ONLY, reason=AUTO_PRIORITY_COMFORT)
```

instead of COOL. `FREE_COOLING_MARGIN` is hardcoded at 2.0 °C.

Free cooling is **suppressed** in the urgent tier — once the room is hot enough to merit urgent cooling, fan won't bring it down quickly enough to be the right choice.

### 2.3 Decision-rule pseudocode

```python
def _outside_promotes_to_urgent(self, mode: HVACMode) -> bool:
    if outside_temp is None or outside_sensor_stalled:
        return False
    inside = env.cur_temp
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


def _free_cooling_applies(self) -> bool:
    if not features.is_configured_for_fan_mode:
        return False
    if outside_temp is None or outside_sensor_stalled:
        return False
    if env.cur_temp is None:
        return False
    return outside_temp <= env.cur_temp - FREE_COOLING_MARGIN_C
```

## 3. Configuration

One new option exposed only in the **options flow** (it is a tuning knob, not a setup-time decision).

| Key | Default | Range (°C) | Range (°F) | Notes |
|---|---|---|---|---|
| `CONF_AUTO_OUTSIDE_DELTA_BOOST` | 8.0 °C / 14.0 °F | 1.0 – 30.0 | 2.0 – 54.0 | Stored in user's unit; converted to °C internally |

Defaults presented in the user's currently-configured unit, identical to how `cold_tolerance` / `hot_tolerance` already work.

The step appears only when AUTO is available (FeatureManager.is_configured_for_auto_mode) AND `outside_sensor` is configured. Translation key `options.step.auto_mode_outside_bias`.

No new dependency tracker entry: the threshold is silently ignored when `outside_sensor` is absent (documented fallback behavior).

## 4. Unit handling

Internal storage and comparison: **°C**. Single conversion at config-read time using `homeassistant.util.unit_conversion.TemperatureConverter` against `hass.config.units.temperature_unit`. No per-tick conversion.

The `FREE_COOLING_MARGIN` (2.0 °C) is also stored as a Celsius constant; it is compared against `cur_temp − outside_temp`, both of which the evaluator receives in their original sensor units. EnvironmentManager normalises all sensor reads to the configured unit before exposing them, so the comparison is always unit-consistent — but to avoid mistakes, the evaluator uses the **delta** (which has the same numeric magnitude in either unit-system if both operands are in the same unit). To be safe across `°C`/`°F` configurations, the margin is converted once at construction time alongside the boost threshold.

## 5. Sensor availability

| Outside-sensor state | Evaluator behaviour |
|---|---|
| Not configured | No bias. No free cooling. Identical to Phase 1.2. |
| `unknown` / `unavailable` | Same as not configured. |
| Stale (no update within stall window) | Same as not configured. AUTO continues running. |

Stall detection follows the existing temp/humidity sensor stall pattern. The flag lives on `DualSmartThermostat` (climate entity) as `_outside_sensor_stalled`, mirroring `_sensor_stalled` and `_humidity_sensor_stalled`. The same `async_track_state_change` mechanism that already detects temp/humidity stalls is extended to the outside sensor (one additional tracker, gated on `outside_sensor` being configured). `climate.py::_async_evaluate_auto_and_dispatch` threads `outside_sensor_stalled` to the evaluator the same way it threads `temp_sensor_stalled`. EnvironmentManager is unchanged — it already exposes `cur_outside_temp` via `update_outside_temp_from_state`.

Outside data is **advisory**, never safety. Unlike `OPENING` or `OVERHEAT`, an outside-sensor problem does not preempt the priority engine — it just removes the bias.

## 6. Code structure

| File | Change |
|---|---|
| `managers/auto_mode_evaluator.py` | Add `_outside_promotes_to_urgent`, `_free_cooling_applies`. Thread `outside_temp` and `outside_sensor_stalled` through `evaluate()`. Cache the boost threshold and free-cooling margin in °C at construction. |
| `climate.py` | Add `_outside_sensor_stalled` flag, extend the existing `async_track_state_change` stall-detection block to the outside sensor (gated on `outside_sensor` being set), and pass `outside_temp` + `outside_sensor_stalled` through `_async_evaluate_auto_and_dispatch` to the evaluator. |
| `const.py` | Add `CONF_AUTO_OUTSIDE_DELTA_BOOST`. |
| `schemas.py` | Add the schema fragment with unit-aware defaults. |
| `feature_steps/auto_mode_steps.py` (new) | Options-flow step exposing the threshold. |
| `options_flow.py` | Wire the new step into the step ordering (after fan/humidity, before openings/presets). |
| `translations/en.json` | New translation block. |
| `tests/test_auto_mode_evaluator.py` | Outside-bias unit tests. |
| `tests/test_auto_mode_integration.py` | 2–3 GWT integration scenarios. |
| `tests/config_flow/test_options_flow.py` | Round-trip persistence test for the new option. |

No changes to `hvac_action_reason/` (reuses existing reasons).

## 7. Testing

### 7.1 Unit tests (evaluator)

- `outside_delta_boost_promotes_normal_heat_to_urgent`
- `outside_delta_below_threshold_does_not_promote`
- `outside_warm_does_not_promote_heat` (wrong direction guard)
- `outside_delta_boost_promotes_normal_cool_to_urgent`
- `outside_cold_does_not_promote_cool` (wrong direction guard)
- `urgent_tier_already_active_unaffected_by_outside_delta`
- `free_cooling_picks_fan_when_outside_cool_and_normal_tier_cool`
- `free_cooling_skipped_when_no_fan_configured`
- `free_cooling_skipped_when_urgent_cool` (suppression in urgent tier)
- `free_cooling_skipped_when_margin_not_met`
- `outside_sensor_unavailable_disables_bias`
- `outside_sensor_stalled_disables_bias`
- `outside_sensor_unconfigured_yields_phase_1_2_behaviour` (regression guard)

### 7.2 GWT integration

- *Helsinki winter:* outside −5 °C, room 18 °C, target 21 °C, heater+cooler — AUTO emits HEAT on first tick with urgent reason despite cur_temp being only 1× tolerance below target.
- *Free cooling:* outside 18 °C, room 24 °C, target 22 °C, heater+cooler+fan — AUTO picks FAN_ONLY (not COOL).
- *Sensor missing:* `outside_sensor` unconfigured — AUTO behaves identically to Phase 1.2 (regression guard).

### 7.3 Config flow

- Round-trip persistence for `CONF_AUTO_OUTSIDE_DELTA_BOOST` in options flow.
- Step is hidden when `outside_sensor` is not configured.
- Default value reflects the user's unit (8.0 in °C, 14.0 in °F).

## 8. Out of scope

- Phase 1.4 (apparent / "feels-like" temperature) — separate PR.
- Phase 2 (PID).
- Symmetric "free heating" via fan from a warm exterior — most fan installations are recirculating, not intake; would mislead users.
- A second knob for the free-cooling margin — hardcoded 2 °C is sufficient flap-prevention for v1; can be added later if real users complain.
