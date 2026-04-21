# Auto Mode — Phase 0: `hvac_action_reason` as Sensor Entity

- **Status:** Approved (design)
- **Date:** 2026-04-21
- **Branch:** `feat/auto-mode-phase-0-action-reason-sensor`
- **Roadmap:** GitHub issue [#563](https://github.com/swingerman/ha-dual-smart-thermostat/issues/563) — Phase 0 (P0.1)

## 1. Goal & Scope

Expose each climate entity's `hvac_action_reason` as a standalone `SensorEntity` (enum device class). This establishes the communication channel that Phase 1 auto mode will use to surface *why* it picked a particular mode. Phase 0 does **not** implement the priority engine itself — it only prepares the sensor-based surface and declares the new auto-reason enum values so the sensor's `options` list is stable across phases.

### In scope
- New `sensor` platform that publishes one action-reason sensor per climate entity.
- Declaration (not emission) of three new auto-mode enum values.
- Dual exposure: new sensor + existing deprecated state attribute on the climate entity.
- README, translations, and TDD coverage.

### Out of scope (Phase 1+)
- Any priority evaluation logic.
- Emitting the new auto reason values from controllers or devices.
- Outside-temperature bias / apparent-temperature features.
- Any config or options flow changes.

## 2. Design Decisions (answers captured during brainstorming)

| # | Decision |
|---|---|
| Q1 | Keep the existing `hvac_action_reason` state attribute on the climate entity as a **deprecated** surface. Document the deprecation; plan removal in a future major release. |
| Q2 | Sensor is **always created** automatically per climate entity, linked to the same HA device as the climate (shared `config_entry.entry_id`), and marked `EntityCategory.DIAGNOSTIC`. |
| Q3 | Sensor `state` is the **raw enum string** (matches the existing attribute value exactly). No extra attributes in Phase 0. |
| Q4 | Sensor uses `SensorDeviceClass.ENUM` with a **static `options` list** containing every value from `HVACActionReasonInternal` + `HVACActionReasonExternal` + `HVACActionReasonAuto` + `"none"`. |
| Q5 | Create a new `HVACActionReasonAuto` enum (new file) in Phase 0, aggregated into the top-level `HVACActionReason`. Values are **declared but not emitted** until Phase 1. |

## 3. Architecture

### 3.1 New platform: `sensor.py`
- Added to `PLATFORMS` in `custom_components/dual_smart_thermostat/__init__.py`.
- `async_setup_entry` creates exactly one `HvacActionReasonSensor` per config entry.
- The sensor shares `DeviceInfo` with the climate entity (linked via `config_entry.entry_id`) so it groups under the same HA device.

### 3.2 New entity class: `HvacActionReasonSensor`
- Base: `SensorEntity` + `RestoreEntity`.
- `_attr_entity_category = EntityCategory.DIAGNOSTIC`.
- `_attr_device_class = SensorDeviceClass.ENUM`.
- `_attr_options = [<all enum values>, "none"]` — constructed from `HVACActionReason` membership.
- `_attr_unique_id = f"{config_entry.entry_id}_hvac_action_reason"`.
- Suggested object ID: `{climate_name}_hvac_action_reason`.
- `_attr_translation_key = "hvac_action_reason"` — combined with the `sensor` platform, this resolves translation lookups to `entity.sensor.hvac_action_reason.state.<value>` in the locale files (see section 8).
- `native_value` holds the current enum string (defaults to `"none"`).

### 3.3 Signals
- Existing: `SET_HVAC_ACTION_REASON_SIGNAL = "set_hvac_action_reason_signal_{}"` — formatted with the climate entity ID, used by the external `set_hvac_action_reason` service. **Unchanged.**
- New: `SET_HVAC_ACTION_REASON_SENSOR_SIGNAL = "set_hvac_action_reason_sensor_signal_{}"` — formatted with the **config entry ID**, fired by the climate whenever `self._hvac_action_reason` changes (covers both internal-controller updates and external-service updates). Subscribed by `HvacActionReasonSensor`.

The climate entity re-broadcasts on this companion signal in every code path that currently assigns `self._hvac_action_reason`. This keeps the sensor authoritative without adding polling.

## 4. Data Flow

```
Controller / device decides reason
      │
      ▼
climate._hvac_action_reason = <value>
      │
      ├──► extra_state_attributes[ATTR_HVAC_ACTION_REASON]    (deprecated path, kept)
      │
      └──► async_dispatcher_send(
              SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format(entry_id),
              value
           )
                        │
                        ▼
         HvacActionReasonSensor._handle_reason_update(value)
                        │
                        ▼
         self._attr_native_value = value
         self.async_write_ha_state()
```

The external service path is unchanged end-to-end: the service still dispatches `SET_HVAC_ACTION_REASON_SIGNAL` to the climate, the climate handler assigns `self._hvac_action_reason`, and the assignment path above then fans out to both the deprecated attribute and the new sensor signal.

## 5. New module: `hvac_action_reason_auto.py`

```python
import enum


class HVACActionReasonAuto(enum.StrEnum):
    """Auto-mode-selected HVAC Action Reason."""

    AUTO_PRIORITY_HUMIDITY = "auto_priority_humidity"
    AUTO_PRIORITY_TEMPERATURE = "auto_priority_temperature"
    AUTO_PRIORITY_COMFORT = "auto_priority_comfort"
```

Merged into the aggregate `HVACActionReason` (`hvac_action_reason.py`):

```python
from .hvac_action_reason_auto import HVACActionReasonAuto

...

for member in chain(
    list(HVACActionReasonInternal),
    list(HVACActionReasonExternal),
    list(HVACActionReasonAuto),
):
    cls[member.name] = member.value
```

Phase 0 leaves these values unreferenced by any controller; Phase 1 will emit them from the priority engine.

## 6. State Persistence & Restore

- `HvacActionReasonSensor` extends `RestoreEntity` (or `RestoreSensor`).
- On `async_added_to_hass`:
  1. Call `async_get_last_state()`.
  2. If the restored state is present and its value is in `_attr_options`, adopt it as `native_value`.
  3. Otherwise default to `"none"`.
- Climate continues to restore `ATTR_HVAC_ACTION_REASON` from its own prior state (deprecated attribute path stays intact).
- When the climate restores its reason value on startup, it re-broadcasts on `SET_HVAC_ACTION_REASON_SENSOR_SIGNAL`, so both surfaces converge regardless of entity startup order.

## 7. Error Handling

- Invalid enum value received on the sensor signal → log a warning, ignore the update, keep current state.
- Restored state value not present in `_attr_options` (e.g., after a downgrade or a bad migration) → default to `"none"` and log debug.
- Config entry unload → the sensor unsubscribes from the dispatcher signal in its `async_will_remove_from_hass`.

## 8. Translations

- Add `translations/en.json` entries under `entity.sensor.hvac_action_reason.state.<value>` for every option (Internal + External + Auto + `none`). This gives UI-friendly labels without changing the stored state value.
- Update `translations/sk.json` with English fallbacks as placeholders; full localization is left to translators.

## 9. Testing Strategy (TDD)

The existing tests in `tests/test_hvac_action_reason_service.py` exercise the legacy state-attribute path. They **stay in place unchanged** so they continue to guard the deprecated surface. Sensor coverage is added **in parallel**, not as a replacement.

### 9.1 New file: `tests/test_hvac_action_reason_sensor.py`

1. Sensor is created per climate with correct `unique_id`, `device_class=SensorDeviceClass.ENUM`, `options` list contents, and `entity_category=EntityCategory.DIAGNOSTIC`.
2. Sensor default state is `"none"` at startup.
3. Internal reason assigned by a controller (e.g., `TARGET_TEMP_REACHED`) propagates to the sensor state.
4. External service call (`dual_smart_thermostat.set_hvac_action_reason` with `PRESENCE`) updates the sensor state — mirror test of the existing legacy-attribute service test, asserted against the sensor.
5. State restoration: after restart, the sensor restores its last persisted enum value.
6. Invalid value received on the sensor signal is ignored; prior state preserved; warning logged.
7. All three `HVACActionReasonAuto` values are present in the sensor's `options` list and are accepted as valid `native_value`s (Phase 0 doesn't emit them but they must be declared).

### 9.2 Extension to existing legacy tests

`tests/test_hvac_action_reason_service.py` — for each of the four existing external-service scenarios (PRESENCE, SCHEDULE, EMERGENCY, MALFUNCTION), add an **adjacent assertion** that the sensor state equals the reason value after the service call. Existing `state.attributes.get(ATTR_HVAC_ACTION_REASON)` assertions are **kept** so we verify the dual exposure in the same scenario.

### 9.3 Helpers

`tests/common.py` — add:
- `get_action_reason_sensor_entity_id(climate_entity_id: str) -> str`
- `get_action_reason_sensor_state(hass, climate_entity_id: str) -> str | None`

No changes to config or options flows (no user-facing configuration introduced in Phase 0).

## 10. README Updates

Under the existing `## HVAC Action Reason` section of `README.md`:

- **Exposure note (near the top of the section):** The action reason is now exposed in two ways:
  - (Preferred) A diagnostic sensor entity per climate: `sensor.<climate_name>_hvac_action_reason`. State is the raw enum value; the entity uses `device_class: enum`.
  - (Deprecated) The `hvac_action_reason` state attribute on the climate entity. Still populated for backward compatibility; slated for removal in a future major release. Users are encouraged to migrate templates and automations to the new sensor.
- **New subsection:** `### HVAC Action Reason Auto values` — table listing `auto_priority_humidity`, `auto_priority_temperature`, `auto_priority_comfort`, with a note that these are **reserved for Auto Mode (Phase 1)** and not yet emitted by the component.
- **Service section update:** `### Set HVAC Action Reason` — clarify that the service now updates both the deprecated attribute and the new sensor state.

## 11. Files Touched Summary

**New files**
- `custom_components/dual_smart_thermostat/sensor.py`
- `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason_auto.py`
- `tests/test_hvac_action_reason_sensor.py`

**Modified files**
- `custom_components/dual_smart_thermostat/__init__.py` — add `Platform.SENSOR` to `PLATFORMS`.
- `custom_components/dual_smart_thermostat/const.py` — add `SET_HVAC_ACTION_REASON_SENSOR_SIGNAL`.
- `custom_components/dual_smart_thermostat/hvac_action_reason/hvac_action_reason.py` — merge `HVACActionReasonAuto` into the aggregate enum.
- `custom_components/dual_smart_thermostat/climate.py` — dispatch on the sensor signal whenever `_hvac_action_reason` changes; add a deprecation docstring/comment on the attribute.
- `custom_components/dual_smart_thermostat/translations/en.json` — sensor state translations.
- `custom_components/dual_smart_thermostat/translations/sk.json` — fallback sensor state translations.
- `README.md` — exposure note, new Auto values subsection, service section update.
- `tests/test_hvac_action_reason_service.py` — add parallel sensor-state assertions (legacy attribute assertions kept).
- `tests/common.py` — sensor helper functions.

## 12. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| User templates/automations break when the attribute is eventually removed | Keep the deprecated attribute working now; document migration path; flag removal only in a future major release. |
| Sensor and attribute drift out of sync | Route every mutation through the same `self._hvac_action_reason` assignment site in `climate.py` and always dispatch on the sensor signal from there. |
| `HVACActionReasonAuto` values appear in the UI before Phase 1 emits them | They are just `options` entries; they will never be the active state in Phase 0. Document the "reserved" status in README. |
| Entity startup order causes a missed initial update | On climate startup, explicitly dispatch the sensor signal with the restored/initial reason value. |
| Existing test suite regression from platform addition | Keep existing tests untouched; add parallel coverage; run full test suite before merge. |

## 13. Acceptance Criteria

1. A `sensor.<climate_name>_hvac_action_reason` entity exists for each configured climate, marked as diagnostic with `device_class: enum`.
2. Sensor state matches the climate's `hvac_action_reason` attribute at all times in all tested scenarios (internal + external reason sources).
3. All existing tests in `tests/test_hvac_action_reason_service.py` still pass unmodified in their legacy assertions.
4. New tests in `tests/test_hvac_action_reason_sensor.py` pass, covering creation, default state, internal-path update, external-path update, restore, invalid-value handling, and Auto values declaration.
5. `HVACActionReasonAuto` enum values are present in the sensor's `options` list and in the aggregate `HVACActionReason` enum, but are not emitted by any controller in Phase 0.
6. README documents the new sensor, deprecates the attribute, and lists the reserved Auto values.
7. `./scripts/docker-lint` and `./scripts/docker-test` both pass.
