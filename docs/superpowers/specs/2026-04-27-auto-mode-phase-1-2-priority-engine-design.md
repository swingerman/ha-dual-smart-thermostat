# Auto Mode — Phase 1.2: Priority Evaluation Engine

- **Status:** Approved (design)
- **Date:** 2026-04-27
- **Branch:** `feat/auto-mode-phase-1-2-priority-engine`
- **Roadmap:** GitHub issue [#563](https://github.com/swingerman/ha-dual-smart-thermostat/issues/563) — Phase 1 (P1.2)

## 1. Goal & Scope

Wire `HVACMode.AUTO` into the climate entity. When the user selects AUTO, a priority evaluation engine runs on each control tick and decides which concrete sub-mode (HEAT / COOL / DRY / FAN_ONLY) to execute, based on the current environment, configured capabilities, and the priority table from issue #563. The climate entity continues to report `hvac_mode == AUTO` to Home Assistant; the underlying HVAC device runs the chosen concrete mode. Mode-flap prevention prevents thrashing across ticks.

### In scope
- A pure `AutoModeEvaluator` class that, given environment + opening + feature managers, returns a decision for the next sub-mode.
- Climate entity exposes `HVACMode.AUTO` in `_attr_hvac_modes` when `features.is_configured_for_auto_mode`.
- Climate entity intercepts AUTO at `async_set_hvac_mode` and `_async_control_climate` and dispatches via the evaluator.
- Mode-flap prevention via 2× tolerance "urgent" thresholds and goal-reached checks.
- Restoration: persisted AUTO state survives a restart.
- Reuses existing `HVACActionReasonAuto` enum values declared in Phase 0.
- Parametric unit tests for the evaluator + integration tests through the climate entity.
- README section documenting AUTO mode behaviour.

### Out of scope (later phases)
- Outside-temperature bias (Phase 1.3).
- Apparent / "feels-like" temperature (Phase 1.4).
- PID controller (Phase 2).
- Any new config keys, options-flow integration, or UI changes beyond the new HVACMode.AUTO option.

## 2. Design Decisions (from brainstorming)

| # | Decision |
|---|---|
| Q1 | **Single PR** — full priority table + flap prevention + AUTO exposure all ship together. Sub-slicing within the table is unsafe (no safety) or thrashy (no flap prevention). |
| Q2 | **Priority evaluator as a pure class + climate.py hook**. No new device class, no controller class. The evaluator is decision logic; the climate entity dispatches it. Devices are unchanged. |
| Q3 (presets / range mode) | **Follow the existing target mode**: when `features.is_range_mode`, evaluator uses `target_temp_low` for HEAT priorities (4, 7) and `target_temp_high` for COOL priorities (5, 8). Otherwise uses the single `target_temp`. Preset writes flow through `EnvironmentManager` unchanged. |
| Tolerances | Reuse `cold_tolerance` / `hot_tolerance` (or active mode-aware tolerance) and `moist_tolerance` / `dry_tolerance`. "Urgent" = 2× the matching tolerance. No new config. |
| Reasons | DRY → `AUTO_PRIORITY_HUMIDITY`; HEAT or COOL → `AUTO_PRIORITY_TEMPERATURE`; FAN_ONLY → `AUTO_PRIORITY_COMFORT`. Safety + idle reuse existing reasons (`OPENING`, `OVERHEAT`, `LIMIT`, `TARGET_TEMP_REACHED`, `TARGET_HUMIDITY_REACHED`, `TEMPERATURE_SENSOR_STALLED`, `HUMIDITY_SENSOR_STALLED`). |
| Persistence | No bespoke persistence. The `_hvac_mode == AUTO` is restored from HA's state machine just like every other mode; the engine re-evaluates on first tick. |
| Capability filtering | Priorities for absent capabilities (no humidity sensor → no DRY priorities; no fan entity → no FAN_ONLY priority) are skipped at evaluator construction time. |

## 3. Priority Table

| Priority | Condition | Outcome | Reason |
|---|---|---|---|
| 1 (safety) | `is_floor_hot` (`floor_temp >= max_floor_temp`) | Idle, force heater off | `OVERHEAT` |
| 2 (safety) | Any opening open with `hvac_mode_scope=AUTO` | Idle | `OPENING` |
| — | Temperature sensor stalled | Idle, suppress all temp priorities | `TEMPERATURE_SENSOR_STALLED` |
| — | Humidity sensor stalled | Suppress humidity priorities only | `HUMIDITY_SENSOR_STALLED` if it would have been the active concern |
| 3 (urgent) | `cur_humidity >= target_humidity + 2 × moist_tolerance` | DRY | `AUTO_PRIORITY_HUMIDITY` |
| 4 (urgent) | `cur_temp <= cold_target − 2 × cold_tolerance` | HEAT | `AUTO_PRIORITY_TEMPERATURE` |
| 5 (urgent) | `cur_temp >= hot_target + 2 × hot_tolerance` | COOL | `AUTO_PRIORITY_TEMPERATURE` |
| 6 (normal) | `cur_humidity >= target_humidity + moist_tolerance` | DRY | `AUTO_PRIORITY_HUMIDITY` |
| 7 (normal) | `cur_temp <= cold_target − cold_tolerance` | HEAT | `AUTO_PRIORITY_TEMPERATURE` |
| 8 (normal) | `cur_temp >= hot_target + hot_tolerance` | COOL | `AUTO_PRIORITY_TEMPERATURE` |
| 9 (comfort) | `hot_target + hot_tolerance < cur_temp <= hot_target + hot_tolerance + fan_hot_tolerance` | FAN_ONLY | `AUTO_PRIORITY_COMFORT` |
| 10 (idle) | All targets met | IDLE-keep (`next_mode = None`, sub-mode unchanged) | `TARGET_HUMIDITY_REACHED` if `last_decision.next_mode == DRY`, else `TARGET_TEMP_REACHED` |

Where `cold_target`/`hot_target` follow Q3:
- Range mode: `cold_target = target_temp_low`, `hot_target = target_temp_high`.
- Single mode: `cold_target = hot_target = target_temp`.

## 4. Mode-Flap Prevention

The evaluator's `evaluate(last_decision)` method follows this state machine:

```
1. If safety priorities (1, 2) fire → return safety decision unconditionally.
2. If a sensor stall affects temp → return IDLE-stall.
3. If last_decision is None → full top-down scan; return first match.
4. Else (we're already in an auto-picked sub-mode):
   a. If any URGENT priority (3, 4, 5) above last_decision fires
      AND that priority's mode != last_decision.next_mode
      → switch to the urgent winner.
   b. Else if last_decision's goal is "still pending" (the original
      condition that picked this mode is still true)
      → stay (return last_decision unchanged but refreshed reason).
   c. Else (goal reached) → full top-down scan; return first match.
```

"Goal pending" predicates:
- `last_decision.next_mode == DRY` → `is_too_moist` still true.
- `last_decision.next_mode == HEAT` → `is_too_cold(target_attr)` still true (where `target_attr` is `_target_temp_low` in range mode or `_target_temp` otherwise).
- `last_decision.next_mode == COOL` → `is_too_hot(target_attr)` still true (range: `_target_temp_high`; single: `_target_temp`).
- `last_decision.next_mode == FAN_ONLY` → temp still in fan band.

This guarantees a stable environment across multiple ticks does not switch modes, while a sudden urgent concern still wins immediately.

## 5. Architecture

### 5.1 New module

**File:** `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.climate import HVACMode

from ..hvac_action_reason.hvac_action_reason import HVACActionReason


@dataclass(frozen=True)
class AutoDecision:
    """Result of one priority evaluation."""

    next_mode: HVACMode | None  # None means "stay in last picked sub-mode" (idle-keep).
    reason: HVACActionReason


class AutoModeEvaluator:
    """Pure decision class for Auto Mode priority evaluation.

    Reads from injected environment / opening / feature managers; never writes.
    Holds no mutable state beyond construction-time capability flags. Callers
    pass the previous AutoDecision so flap prevention can apply.
    """

    def __init__(self, environment, openings, features):
        self._environment = environment
        self._openings = openings
        self._features = features

    def evaluate(self, last_decision: AutoDecision | None) -> AutoDecision:
        ...
```

The implementation maps the priority table from Section 3 directly. Capability gating happens inline (e.g., humidity priorities only run when `features.is_configured_for_dryer_mode`).

### 5.2 Climate entity changes

**File:** `custom_components/dual_smart_thermostat/climate.py`

Three changes:

1. **Construct the evaluator** in `__init__`:

   ```python
   self._auto_evaluator = (
       AutoModeEvaluator(environment_manager, opening_manager, feature_manager)
       if feature_manager.is_configured_for_auto_mode
       else None
   )
   self._last_auto_decision: AutoDecision | None = None
   ```

2. **Extend `_attr_hvac_modes`** when AUTO is available. This is set after the device is constructed (existing code already initialises `self._attr_hvac_modes = self.hvac_device.hvac_modes`):

   ```python
   if self.features.is_configured_for_auto_mode:
       modes = list(self._attr_hvac_modes)
       if HVACMode.AUTO not in modes:
           modes.append(HVACMode.AUTO)
       self._attr_hvac_modes = modes
   ```

3. **Intercept AUTO** in `async_set_hvac_mode` and `_async_control_climate`:

   ```python
   async def async_set_hvac_mode(self, hvac_mode, is_restore=False):
       if hvac_mode == HVACMode.AUTO and self._auto_evaluator is not None:
           self._hvac_mode = HVACMode.AUTO
           self._last_auto_decision = None  # fresh scan on entry
           await self._async_evaluate_auto_and_dispatch(force=True)
           return
       # ...existing path unchanged...

   async def _async_control_climate(self, time=None, force=False):
       async with self._temp_lock:
           if self._hvac_mode == HVACMode.AUTO and self._auto_evaluator is not None:
               await self._async_evaluate_auto_and_dispatch(force=force)
               return
           # ...existing path unchanged...

   async def _async_evaluate_auto_and_dispatch(self, force: bool):
       decision = self._auto_evaluator.evaluate(self._last_auto_decision)
       self._last_auto_decision = decision

       if decision.next_mode is not None and decision.next_mode != self.hvac_device.hvac_mode:
           await self.hvac_device.async_set_hvac_mode(decision.next_mode)

       await self.hvac_device.async_control_hvac(force=force)

       self._hvac_action_reason = decision.reason
       self._publish_hvac_action_reason(decision.reason)
   ```

The `hvac_mode` getter on the climate entity continues to return `self._hvac_mode` (which is `AUTO`); `hvac_action` continues to delegate to `self.hvac_device.hvac_action` (which reflects the concrete sub-mode's runtime state).

### 5.3 Restoration

In the existing `async_added_to_hass` restore path:

```python
if (old_state := await self.async_get_last_state()) is not None:
    hvac_mode = self._hvac_mode or old_state.state or HVACMode.OFF
    if hvac_mode not in self.hvac_modes:
        hvac_mode = HVACMode.OFF
    # ...existing restore path...
    await self.async_set_hvac_mode(hvac_mode, is_restore=True)
```

Once the existing branch in step 2 above appends `HVACMode.AUTO` to `self.hvac_modes`, this code path naturally handles AUTO restoration: `async_set_hvac_mode(AUTO, is_restore=True)` enters the new intercept branch, which seeds `_last_auto_decision = None` and runs an immediate evaluation. `is_restore=True` is honoured by skipping `set_temepratures_from_hvac_mode_and_presets` (existing behaviour) so preset-restored targets are not overwritten.

## 6. Data Flow

```
Sensor change / keep_alive tick
        │
        ▼
_async_control_climate(time=…, force=False)
        │
        ▼
[hvac_mode == AUTO?]── no ──► existing path
        │ yes
        ▼
AutoModeEvaluator.evaluate(last_decision)
   reads: environment.cur_temp/cur_humidity/cur_floor_temp,
          environment.target_temp/target_temp_high/_low/target_humidity,
          environment.cold_tolerance/hot_tolerance/moist_tolerance/dry_tolerance,
          environment.fan_hot_tolerance, environment.is_floor_hot,
          environment.is_too_cold/_too_hot/_too_moist/_too_dry,
          openings.any_opening_open(scope=AUTO),
          features.is_configured_for_dryer_mode/_fan_mode/_range_mode,
          self.last_decision (passed in)
   returns: AutoDecision(next_mode, reason)
        │
        ▼
[next_mode != device.hvac_mode?]── no ──► skip set_hvac_mode
        │ yes
        ▼
device.async_set_hvac_mode(next_mode)
        │
        ▼
device.async_control_hvac(force=force)   ── existing controller logic runs
        │
        ▼
self._hvac_action_reason = decision.reason
self._publish_hvac_action_reason(reason)  ── fans out to Phase 0 sensor
```

## 7. Error Handling & Edge Cases

| Scenario | Outcome |
|---|---|
| Temperature sensor stalled | Evaluator returns `AutoDecision(None, TEMPERATURE_SENSOR_STALLED)`. Climate stays in last picked sub-mode but actuators are off (existing stall behaviour). |
| Humidity sensor stalled | Evaluator suppresses humidity priorities (3, 6). Temp/fan priorities still run. If humidity *would* have been the active concern, reason becomes `HUMIDITY_SENSOR_STALLED`; otherwise temp priorities decide. |
| `target_temp` is None on entry | Skip temp priorities. Evaluator falls through to humidity / fan / idle. |
| User has heater + fan only (no humidity sensor / dryer) | Humidity priorities are absent at construction time; only temp + fan + idle priorities run. |
| Heat-pump-only setup | Both HEAT and COOL priorities are in play; engine picks one and `device.async_set_hvac_mode` triggers HeatPumpDevice's existing mode swap. |
| Preset switch while in AUTO | Preset writes new targets to `EnvironmentManager`; next tick the evaluator reads them. Goal-pending check runs against the new targets, so flap prevention adapts naturally. |
| User selects HEAT manually while in AUTO | Existing path runs; `_hvac_mode = HEAT`, evaluator stops being consulted. `_last_auto_decision` is left as-is and reset on next AUTO entry. |
| Restart with persisted AUTO state | `async_set_hvac_mode(AUTO, is_restore=True)` runs the intercept branch; evaluator runs immediately with `last_decision = None` (top-down scan). |
| AUTO in `_attr_hvac_modes` but no auto evaluator (defensive) | Climate falls back to existing path; treats AUTO like an unknown mode (existing code logs and returns). Cannot happen in practice because the same flag drives both. |

## 8. Testing Strategy

### 8.1 New file: `tests/test_auto_mode_evaluator.py`

Pure-Python tests over the evaluator using `MagicMock` for the three injected managers. Covered scenarios:

**Per-priority firing** (one test per row of the priority table):
- Floor temp ≥ max_floor_temp → IDLE / OVERHEAT.
- Opening open → IDLE / OPENING.
- Humidity at 2× tolerance → DRY / AUTO_PRIORITY_HUMIDITY.
- Temp at 2× cold tolerance → HEAT / AUTO_PRIORITY_TEMPERATURE.
- Temp at 2× hot tolerance → COOL / AUTO_PRIORITY_TEMPERATURE.
- Humidity at normal tolerance → DRY / AUTO_PRIORITY_HUMIDITY.
- Temp at normal cold tolerance → HEAT.
- Temp at normal hot tolerance → COOL.
- Temp in fan band → FAN_ONLY / AUTO_PRIORITY_COMFORT.
- All targets met → IDLE-keep.

**Preemption**:
- Floor hot + temp cold → IDLE/OVERHEAT (safety beats normal).
- Opening + humidity high → IDLE/OPENING.
- Humidity 2× + temp normal → DRY (urgent humidity beats normal temp).
- Temp 2× + humidity normal → HEAT/COOL (urgent temp beats normal humidity).

**Flap prevention**:
- HEAT picked, temp still cold (goal pending), no urgent → stay HEAT.
- HEAT picked, temp reached target → next scan picks new mode.
- HEAT picked, humidity goes 2× → switch to DRY.
- COOL picked, temp briefly drops 0.1°C below threshold → stay COOL (goal pending interpretation: still hotter than target — depends on tolerance hysteresis; tests pin the chosen semantic).

**Range vs single target**:
- Range mode: temp below `target_temp_low − cold_tol` → HEAT; above `target_temp_high + hot_tol` → COOL; between → IDLE.
- Single mode: temp ± tolerance from `target_temp`.

**Capability filtering**:
- No humidity sensor → priorities 3, 6 skipped (DRY never picked).
- No fan entity → priority 9 skipped.
- Heater only + fan only (no cooler / dryer) → only HEAT, FAN_ONLY, IDLE picked.

**Sensor stall**:
- Temp stall → IDLE / TEMPERATURE_SENSOR_STALLED.
- Humidity stall, temp normal → temp priorities decide.
- Humidity stall, would have been DRY → IDLE / HUMIDITY_SENSOR_STALLED.

### 8.2 New file: `tests/test_auto_mode_integration.py`

End-to-end tests via the YAML fixture pattern (matching `tests/test_heater_mode.py`):

1. AUTO available in `hvac_modes` only when ≥2 capabilities + sensor.
2. Set AUTO → evaluator picks HEAT → heater switch turns on.
3. Temp drops further → stays HEAT (flap prevention).
4. Temp reaches target → heater off, climate idle, hvac_mode still AUTO.
5. Humidity rises past 2× moist → switches to DRY.
6. Floor temp limit triggers → heater off, reason OVERHEAT.
7. Opening open → idle, reason OPENING; opening closes → re-evaluates.
8. AUTO survives a restart (`mock_restore_cache` with state `auto`).
9. Action-reason sensor (Phase 0 surface) reflects `auto_priority_*` values during AUTO operation.
10. Preset switch in AUTO mode → new target → re-evaluates.

### 8.3 Regression coverage

Run the full test suite to confirm:
- Existing `hvac_modes` assertions on master are unaffected (AUTO is gated behind the auto-mode availability check, which yields False for the vast majority of fixtures).
- Existing legacy state-attribute assertions still pass.
- The Phase 0 `test_hvac_action_reason_sensor.py` and Phase 1.1 `test_auto_mode_availability.py` keep passing.

## 9. README

Add a new `## Auto Mode` section under the existing feature documentation:

> ### Auto Mode (Phase 1)
>
> When the thermostat is configured with at least two distinct climate capabilities (any of heating, cooling, drying, fan), the integration exposes `auto` as one of its HVAC modes. In Auto Mode the integration picks between HEAT, COOL, DRY, and FAN_ONLY automatically based on the current environment, configured tolerances, and a fixed priority table:
>
> 1. Safety: floor-temperature limit and window/door openings preempt all decisions.
> 2. Urgent: temperature or humidity beyond 2× the configured tolerance switches mode immediately.
> 3. Normal: temperature or humidity beyond the configured tolerance picks the matching mode.
> 4. Comfort: when the room is mildly above target and a fan is configured, run the fan instead of cooling.
> 5. Idle: when all targets are met, stop actuators.
>
> The thermostat continues to report `auto` as its `hvac_mode`; the underlying actuator (heater / cooler / dryer / fan) reflects the chosen sub-mode in `hvac_action`. Mode flap prevention keeps the chosen sub-mode running until its goal is reached or a higher-priority concern arises. Active priority is exposed via the `hvac_action_reason` sensor as `auto_priority_temperature`, `auto_priority_humidity`, or `auto_priority_comfort`. Phase 1.3 will add outside-temperature bias; Phase 1.4 will add apparent-temperature support.

(The link from the existing top-of-readme features table also gets a new row pointing at `#auto-mode`.)

## 10. Files Touched Summary

**New files:**
- `custom_components/dual_smart_thermostat/managers/auto_mode_evaluator.py`
- `tests/test_auto_mode_evaluator.py`
- `tests/test_auto_mode_integration.py`

**Modified files:**
- `custom_components/dual_smart_thermostat/climate.py` — evaluator construction, `_attr_hvac_modes` extension, AUTO intercept in `async_set_hvac_mode` and `_async_control_climate`, `_async_evaluate_auto_and_dispatch` helper.
- `README.md` — new Auto Mode section + features-table row.
- `tests/common.py` — small helper if needed for AUTO-capable thermostat fixture.

**Not touched:** `const.py`, `schemas.py`, `config_flow.py`, `options_flow.py`, `manifest.json`, translations, sensor.py, hvac_action_reason/* (the Auto reason values were declared in Phase 0).

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Mode thrashing if flap prevention is buggy | Parametric "stay across ticks" tests; integration tests with stable env confirm no extra mode switches. |
| User confusion: `hvac_mode = AUTO` while device runs HEAT | Matches HA convention (HEAT_COOL → HEATING). README explicitly documents the dual-state. The action-reason sensor (Phase 0) shows the picked priority. |
| AUTO restored to a stale sub-mode | Restore path resets `_last_auto_decision = None` and runs a fresh top-down scan on first tick. |
| Sub-config (heater + dryer) but humidity sensor missing at runtime | Capability filtering excludes humidity priorities; existing `is_configured_for_dryer_mode` already enforces humidity-sensor presence at config time. |
| Preset switch while in AUTO | Targets flow through `EnvironmentManager`; goal-pending check uses fresh values on next tick. |
| Fan band priority (9) overlaps with normal temp tolerance (8) | Priority order disambiguates: priority 8 fires first when its threshold is met, priority 9 only fires in the band immediately above it. Tests pin the boundary. |
| HeatPumpDevice mode swap latency | When evaluator picks COOL on a heat-pump-only setup, `device.async_set_hvac_mode(COOL)` triggers the existing heat-pump cooling-sensor swap; the actual hardware transition is at the heat pump's discretion. Documented; no engine changes. |
| Range-mode default (target_temp_high vs _low) ambiguity | Q3 decision: range mode uses both bounds; single mode uses the one target. Explicit in the priority table footer. |

## 12. Acceptance Criteria

1. `HVACMode.AUTO` appears in `hvac_modes` if and only if `features.is_configured_for_auto_mode` is True.
2. With AUTO selected, the evaluator picks HEAT/COOL/DRY/FAN_ONLY/IDLE-keep per the priority table for every parametric scenario in §8.1.
3. Mode flap prevention: a stable environment across multiple ticks does not switch modes.
4. Safety priorities (floor temp limit, opening) preempt mode selection in both AUTO entry and subsequent ticks.
5. Sensor stall on temperature → climate reports IDLE with `TEMPERATURE_SENSOR_STALLED`; humidity stall → humidity priorities are skipped.
6. Restart with persisted AUTO state restores AUTO and re-evaluates immediately.
7. Climate continues to report `hvac_mode == HVACMode.AUTO` while the underlying device runs the picked sub-mode.
8. The Phase 0 action-reason sensor reflects `auto_priority_*` values during AUTO operation.
9. All existing tests pass; new tests cover the evaluator's full priority table, flap prevention, capability filtering, and the integration scenarios in §8.2.
10. `./scripts/docker-test` and `./scripts/docker-lint` clean.
