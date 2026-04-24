# Auto Mode — Phase 1.1: Availability Detection

- **Status:** Approved (design)
- **Date:** 2026-04-22
- **Branch:** `feat/auto-mode-phase-1-1-availability-detection`
- **Roadmap:** GitHub issue [#563](https://github.com/swingerman/ha-dual-smart-thermostat/issues/563) — Phase 1 (P1.1)

## 1. Goal & Scope

Add a single derived property `FeatureManager.is_configured_for_auto_mode` that reports whether the current configuration can support Auto Mode. Auto Mode is available when the thermostat has a temperature sensor **and** at least two distinct climate capabilities (heat / cool / dry / fan) that it could choose between.

Phase 1.1 only **surfaces availability**. The property is not consumed by any other code path yet — `hvac_modes` stays unchanged, `HVACMode.AUTO` is not exposed in the UI, and no config/options flow is altered. Phase 1.2 will wire the priority evaluation engine that reads this property and exposes `HVACMode.AUTO` when it returns `True`.

### In scope
- New `is_configured_for_auto_mode` property on `FeatureManager`.
- Parameterised unit tests covering the predicate across representative configurations.

### Out of scope (Phase 1.2+)
- `hvac_modes` changes / `HVACMode.AUTO` exposure.
- Priority evaluation engine.
- Mode-selection behaviour when `AUTO` is chosen by the user.
- Outside-temperature influence (P1.3) and apparent-temperature support (P1.4).
- Any config or options flow integration.
- README changes — nothing user-facing ships in this slice.

## 2. Design Decisions (from brainstorming)

| # | Decision |
|---|---|
| Q1 | **Detection only** — property exists, but nothing downstream consumes it. Matches the Phase 0 precedent (declare capability now, wire in later phase). |
| Q2 | Property lives on `FeatureManager` alongside the existing `is_configured_for_*` properties. No new module or manager class. |
| Q3 | Capability counting uses derived mode-capability booleans, not raw entity presence. Heat-pump-only setups satisfy both `can_heat` and `can_cool` and therefore qualify. |
| Threshold | **≥ 2** capabilities required (matches the roadmap). Single-capability setups — heater-only, fan-only, dryer-only — would make Auto Mode equivalent to that one mode and are excluded by design. |

## 3. The Predicate

Four capability booleans derived from existing `FeatureManager` state:

| Capability | True when |
|---|---|
| `can_heat` | `is_configured_for_heat_pump_mode` **OR** (`_heater_entity_id is not None` AND NOT `_ac_mode`) |
| `can_cool` | `is_configured_for_heat_pump_mode` **OR** `is_configured_for_cooler_mode` **OR** `is_configured_for_dual_mode` |
| `can_dry` | `is_configured_for_dryer_mode` |
| `can_fan` | `is_configured_for_fan_mode` |

Plus a defensive guard: `_sensor_entity_id is not None`. The integration already requires a temperature sensor, but the explicit check makes the predicate self-documenting and robust to future refactors.

**Result:** `is_configured_for_auto_mode` returns `True` iff `temperature_sensor_set AND sum(capabilities) >= 2`.

## 4. Architecture

### 4.1 File structure

- **Modified:** `custom_components/dual_smart_thermostat/managers/feature_manager.py`
  - Append one `@property` (~15 lines) near the other `is_configured_for_*` properties.
  - No new imports; all referenced properties already exist on the class.
- **New:** `tests/test_auto_mode_availability.py`
  - Focused unit test file. Uses minimal `FeatureManager` fixtures constructed from raw config dicts.

### 4.2 Implementation sketch

```python
@property
def is_configured_for_auto_mode(self) -> bool:
    """Determine if the configuration supports Auto Mode.

    Auto Mode requires a temperature sensor and at least two distinct
    climate capabilities (heat / cool / dry / fan). Reserved for Phase 1.2
    of the Auto Mode roadmap (#563); Phase 1.1 only surfaces availability.
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

## 5. Error Handling & Edge Cases

| Scenario | Result | Rationale |
|---|---|---|
| Missing temperature sensor | `False` | Defensive guard; matches the roadmap's stated prerequisite. |
| Heat-pump-only (no fan / dryer / separate cooler) | `True` | Heat pump provides both heating and cooling, so two capability slots are satisfied by a single entity. |
| `CONF_DRYER` set but no humidity sensor | `False` for `can_dry` | Already enforced by `is_configured_for_dryer_mode`; no duplicate check needed. |
| Heater entity + `ac_mode=True` | `can_heat = False`, `can_cool = True` | The heater entity is operating as an AC unit, so it contributes a cooling slot only. |
| All four capabilities (heater + cooler + dryer + fan) | `True` | Obvious positive case; exercised by a regression test. |
| Heater-only, fan-only, dryer-only, ac-mode-only | `False` | Single capability — Auto Mode has no decision to make. |

## 6. Testing Strategy

### 6.1 New file: `tests/test_auto_mode_availability.py`

Parameterised tests over `(config_dict, expected_available)` pairs. Each test constructs a `FeatureManager` from the config and asserts `is_configured_for_auto_mode`. Covered permutations:

**Expected `True`:**
- Heater + separate cooler (dual mode)
- Heater + `ac_mode=True` + dryer + humidity sensor → 1 cool + 1 dry = 2
- Heater + fan entity
- Heater + dryer + humidity sensor
- Heat-pump-only (heat-pump cooling sensor present, heater entity present)
- Heat-pump + fan
- All four capabilities (heater + cooler + dryer + fan + humidity sensor)

**Expected `False`:**
- Heater-only (no cooler, no fan, no dryer)
- `ac_mode=True` only (heater entity operates as AC — just `can_cool`)
- Fan-only (no heater, no cooler, no dryer)
- Dryer-only + humidity sensor (no heater, no cooler, no fan)
- Qualifying multi-capability config but `CONF_SENSOR` absent → `False`

### 6.2 Regression surface
- Full test suite run to confirm no existing `hvac_modes` / feature assertions are affected (the property is additive).

## 7. Files Touched Summary

**New files**
- `custom_components/dual_smart_thermostat/` — none
- `tests/test_auto_mode_availability.py`

**Modified files**
- `custom_components/dual_smart_thermostat/managers/feature_manager.py` — add property.

No changes to: `climate.py`, `sensor.py`, translations, README, config_flow, options_flow, manifest.

## 8. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Property becomes dead code if Phase 1.2 takes a different shape | Docstring explicitly references the Phase 1.2 follow-up; property name mirrors existing `is_configured_for_*` convention so it's discoverable and removable if needed. |
| Heat-pump-only setups unintentionally qualify | Documented in the edge-cases table. Phase 1.2 will verify behaviour end-to-end before exposing `HVACMode.AUTO`. |
| Future `FeatureManager` refactors break the predicate silently | Parameterised tests pin the predicate behaviour across every representative configuration. |

## 9. Acceptance Criteria

1. `FeatureManager.is_configured_for_auto_mode` exists and returns `bool`.
2. All parameterised test cases in section 6.1 pass.
3. The existing test suite still passes unmodified (no hvac_modes / feature assertions affected).
4. `./scripts/docker-lint` is clean on the modified files.
5. No user-visible change: the same config that showed no `HVACMode.AUTO` in the selector before this change still shows no `HVACMode.AUTO` after.
