# Climate Entities as Device Roles

- **Status:** Proposed (design)
- **Date:** 2026-10-20
- **Branch:** `feat/climate-entity-devices`
- **Roadmap:** GitHub issue [#281](https://github.com/swingerman/ha-dual-smart-thermostat/issues/281) (agreed design in the owner's comment). Related: [#322](https://github.com/swingerman/ha-dual-smart-thermostat/issues/322) (number/switch-backed devices, out of scope, see section 12).

## 0. Open questions for the owner

Everything else in this document is decided. These are the few calls that are the owner's.

| # | Question | Default taken in this design |
|---|---|---|
| OQ1 | `setpoint_offset` is one thermostat-wide signed value added as-is (the agreed text). A single AC filling heater **and** cooler wants opposite signs (the "+3 heat / -5 cool" trick from the issue thread), which one value cannot express. Keep one value for v1, or add per-role override keys now? | One value, added as-is, applies to every climate-backed role. Per-role keys are an additive follow-up (no migration needed). |
| OQ2 | `control_style: setpoint` combined with a **heat pump** role (climate heater + `heat_pump_cooling`) is rejected in v1. The heat pump device swaps strategies at runtime and the self-regulating strategy would need to follow. Acceptable? | Rejected with a validation error. A single AC is still fully covered by heater + cooler (+ fan, dryer) pointing at one climate. |
| OQ3 | When DST is switched OFF it stops only the mode its own roles command. A child left in a mode none of the roles owns (say the user set `auto` on the AC remote) is not touched. The alternative is "OFF always sends `climate.turn_off`", which would also override a manual mode. | Do not touch foreign modes. Safer for shared devices, matches "DST owns the modes it has roles for". |
| OQ4 | In `setpoint` style the child decides when it actually runs, so DST's `hvac_action` can only say "engaged" (HEATING/COOLING), not "idle between cycles". Reading the child's own `hvac_action` is possible but is a follow-up. | Report engaged, document it. |

## 1. Goal and scope

Let a device role (`heater`, `cooler`, `fan`, `dryer`, heat pump) be backed by a `climate.*` entity instead of a switch-like entity, so users stop writing template switches that call `climate.set_hvac_mode` / `climate.set_temperature` / `climate.turn_off`. The role type is detected from the entity domain, so mixed setups (IR AC as cooler, smart plug as heater) work.

### In scope
- Climate domain accepted for the five roles (YAML, config, reconfigure, options flows).
- `control_style`: `on_off` (default) and `setpoint`.
- `setpoint_offset` (default `0`).
- `target_sensor` optional when a climate role exists (falls back to the child's `current_temperature`).
- One climate entity filling several roles without the roles fighting.
- Device safety: min cycle duration, availability, `assumed_state` (IR) devices.
- Dependency tracking, translations, README and example.

### Out of scope
- Fan speed control through the climate's `fan_mode` (a climate fan role has no speed control, like a `switch` fan today).
- Humidity from the child's `current_humidity` (a dryer still needs `humidity_sensor`).
- Mirroring the child's `hvac_action` into DST (OQ4).
- Climate as `secondary_heater` (aux). Stays switch-like only.
- Number/switch-pair devices from #322 (section 12).
- Any change to existing YAML semantics.

## 2. Design decisions

| # | Decision |
|---|---|
| D1 | **The seam is one object per role: `EntityPort`.** Today the stack touches its entity in exactly three ways, all inside `GenericHVACDevice` / `GenericHvacController`: read "is it on" (`hass.states.is_state(id, "on")`), read "how long in this state" (`condition.state(..., min_cycle)`), command it (`homeassistant.turn_on/off`, valve open/close). All three move behind `EntityPort` (`is_active`, `ran_long_enough`, `async_turn_on`, `async_turn_off`). Two implementations: `SwitchPort` (today's code, valve included, moved not changed) and `ClimatePort`. Controllers, managers, `climate.py`, `MultiHvacDevice` keep calling `async_turn_on/off` / `is_active` and do not change. |
| D2 | **No default port.** `GenericHVACDevice` builds its port from the entity domain via `make_port`; a device class without a role mode mapping cannot be built on a climate entity (raises at setup). No code path can silently drive a `climate.*` entity with `homeassistant.turn_on` and then wait for the state `on` (it never comes, the failure class a naive "just allow the domain" change would create). |
| D3 | **Role conflicts are structurally impossible.** One `ClimateChild` per real climate entity (per `hass`, keyed by entity id) owns the only record of that device's mode. A role's "active" is a derived predicate `child.mode == my_mode`, never stored per role. Two roles on one climate therefore cannot both be active, and `turn_off` of a role is a no-op unless the child is currently in that role's mode, so a keep-alive `turn_off` from the idle cooler cannot stop the heater. The existing `in_use` guard in `MultiHvacDevice` (#637) keeps working because shared entity ids already compare equal. |
| D4 | **`control_style` is a property of the port, not a new device class.** `on_off`: DST's strategy decides (existing code path). `setpoint`: the port reports `self_regulating = True`; `GenericHVACDevice` then swaps in a strategy whose goal is never reached and skips the min-cycle gate. The unchanged controller therefore keeps the child engaged, pauses it for openings and floor limits, and restores it afterwards. No second control loop. |
| D5 | **Target mirroring is one idempotent method**, `port.async_sync()`, called at the top of `async_control_hvac`. Every trigger that already reaches control (target change, preset, mode change, sensor tick, keep-alive) mirrors the target; it only calls the child when the desired value differs from what the child reports. Pushed value = `target + setpoint_offset`, clamped to the child's `min_temp`/`max_temp`, rounded to `target_temp_step`. |
| D6 | **Temperature source is an entity id plus a reader.** When `target_sensor` is missing, config normalisation sets it to the first climate role entity (heater, cooler, fan, dryer order). `EnvironmentManager.update_temp_from_state` reads `attributes["current_temperature"]` when `state.domain == "climate"`, else `state.state`. Listeners, stale detection and startup read all keep using `sensor_entity_id` unchanged. An explicit `target_sensor: climate.x` works by the same rule. |
| D7 | **State truth.** Non-assumed child: its reported `state` is the mode and `last_changed` is the mode age. `assumed_state` child (IR): DST's own last commanded mode and timestamp are authoritative, initialised from the restored state. One property (`ClimateChild.mode`) hides the difference. Commands are serialised by one lock per child. |
| D8 | **Availability.** Unavailable/unknown child: commands are skipped (same rule `SwitchPort` has today, #499) and `mode` is `None`. A mode the child does not list in `hvac_modes` is logged once and not sent. |
| D9 | **Config surface.** Two new keys, `control_style` (`on_off`/`setpoint`) and `setpoint_offset` (float, default 0), both thermostat-wide. One new flow step `climate_control`, shown only when a role is a climate entity, placed right after the entity step (before `features`), so it respects the openings/presets-last rule. A single helper (`climate_roles.py`) answers "which roles are climate" for YAML validation, the flows and runtime, so the three cannot drift. |
| D10 | **Same entity in several roles is allowed for climate only.** The factory guard "cooler equals heater, ignore cooler" and the flow errors `same_heater_cooler` stay for switch-like entities. |
| D11 | **Role to child mode:** heater `heat`, cooler `cool`, fan `fan_only`, dryer `dry`, heat pump `heat` or `cool` following `heat_pump_cooling` (evaluated lazily). Only heater, cooler and heat pump push a temperature. |

## 3. Architecture

### 3.1 New module `hvac_device/entity_port.py`

```python
class EntityPort(ABC):
    entity_id: str
    self_regulating: bool = False          # True only for ClimatePort(setpoint)

    @property
    @abstractmethod
    def is_active(self) -> bool: ...
    @abstractmethod
    def ran_long_enough(self, min_cycle: timedelta) -> bool: ...
    @abstractmethod
    async def async_turn_on(self, context) -> None: ...
    @abstractmethod
    async def async_turn_off(self, context) -> None: ...
    async def async_sync(self, context) -> None:    # default: nothing to mirror
        return


class SwitchPort(EntityPort): ...     # today's logic from GenericHVACDevice/GenericHvacController, valve included


class ClimateChild:                   # one per real climate entity, shared by roles
    mode -> str | None
    since -> datetime | None
    async def async_set_mode(mode, context) -> bool
    async def async_turn_off(context) -> None
    async def async_push_target(value, context) -> None


class ClimatePort(EntityPort):        # one per role, thin: derives everything from the child
    def __init__(self, child, role_mode: Callable[[], HVACMode], target: Callable[[], float | None],
                 offset: float, style: str) -> None: ...


def make_port(hass, entity_id, *, role_mode, target, style, offset) -> EntityPort: ...
```

`climate_child(hass, entity_id)` is a get-or-create over `hass.data["dual_smart_thermostat_climate_children"]`. The child holds no thermostat config (no min cycle, offset, style); those live in the per-role port, so a reload cannot leave stale config behind. The only retained state is the last commanded mode/time, which stays true across reloads.

### 3.2 `ClimatePort` behaviour

| Port call | on_off | setpoint |
|---|---|---|
| `is_active` | `child.mode == role_mode()` | same |
| `async_turn_on` | child unavailable: skip. Else `climate.set_hvac_mode(role_mode)`, then push target (+offset) for heater/cooler/heat pump | same |
| `async_turn_off` | only if `child.mode == role_mode()`: `climate.turn_off` | same |
| `async_sync` | if `child.mode == role_mode()` and desired target differs from the child's reported `temperature` (assumed: last pushed): push | same |
| `ran_long_enough(d)` | `now - child.since >= d` | always `True` (no DST cycling) |
| `self_regulating` | `False` | `True` |

`climate.set_hvac_mode` and `climate.set_temperature` are two calls on purpose: some devices drop the setpoint on a mode change, so the order is mode, then target. A mode change clears the "last pushed" memory so the target is re-sent.

### 3.3 Changes to existing classes

- `GenericHVACDevice.__init__`: build `self.port = make_port(...)` first, pass `self.port` to the controller. Replace `_entity_state`, `_is_valve`, `_entity_features`, `_supports_*_valve`, `is_on`, `_async_turn_on_entity`, `_async_turn_off_entity` and the valve helpers with calls to the port (`SwitchPort` owns them). Add `role_mode()` (default `None`) overridden by Heater/Cooler/Fan/Dryer/HeatPump devices. Add one line in `async_control_hvac`: `await self.port.async_sync(self._context)` after the OFF branch.
- `GenericHvacController`: constructor takes `port` instead of `hass, entity_id`; `is_active` and `ran_long_enough` delegate to it. `entity_id` stays as a property of the port for logging. `HeaterHvacConroller` and `CoolerHvacController` pass it through.
- `HvacEnvStrategy`: one classmethod `self_regulating(goal, reached_reason, not_reached_reason)` returning a strategy with `hvac_goal_reached == False` and `hvac_goal_not_reached == True`.
- `HVACDeviceFactory`: relax the cooler-equals-heater guard for climate entities.
- `MultiHvacDevice.get_device_ids`: de-duplicate (a shared child would otherwise register the state listener twice).
- `EnvironmentManager.update_temp_from_state`: the domain-aware reader (D6).
- `climate.py`: normalise `target_sensor` (D6). `PLATFORM_SCHEMA`: `target_sensor` optional plus the cross-field validator.
- `schemas.py`, `config_flow.py`, `options_flow.py`, `flow_utils.py`, translations: section 6.

Device constructors keep their `entity_id: str` parameter (no signature churn for the 17 direct constructions in `tests/test_fan_speed_control.py`); the port is built inside the base class from that id. `HeatPumpDevice` keeps its two controllers; both receive the same port. `FanDevice._detect_fan_capabilities` already treats non-`fan` domains as "no speed control", so a climate fan needs no change.

### 3.4 Data flow (on_off, climate cooler, switch heater)

```
sensor/target change
   -> climate.py _async_control_climate
   -> MultiHvacDevice.async_control_hvac -> CoolerDevice.async_control_hvac
        -> port.async_sync()                       # mirrors changed target
        -> CoolerHvacController.async_control_device_when_off(strategy,...)
             goal not reached -> async_turn_on_callback -> CoolerDevice.async_turn_on
                 -> ClimatePort.async_turn_on
                      -> ClimateChild.async_set_mode(cool)   # serialised, optimistic record
                      -> climate.set_temperature(target + offset)
child state_changed -> existing listener (_async_switch_changed) -> write state / resume
```

HeaterDevice with a `SwitchPort` is the same code as before, reached through the same port calls.

## 4. Role conflicts (one climate, several roles)

Heater, cooler, fan and dryer pointing at the same `climate.x` are four `ClimatePort`s over one `ClimateChild`.

- **Exclusion by derivation (D3).** `is_active` is `child.mode == role_mode`; there is no per-role flag to get out of sync.
- **Switching modes.** `MultiHvacDevice` already stops the devices that do not handle the new mode before running the one that does, sparing entities the running device also owns. Heat to cool: the heater port turns the child off (it is in `heat`), the cooler port sets `cool`. Even if the stop is skipped, `set_hvac_mode(cool)` replaces `heat` because the child holds one mode.
- **No cross-kill.** An idle role's keep-alive or OFF-mode `turn_off` is a no-op unless the child is in that role's mode.
- **Min cycle** is measured on the child (`since`), which is also what protects the compressor when heat and cool alternate.
- **Config guard.** The factory and flow "same entity" checks apply only to non-climate entities.
- **Self reference.** A role pointing at the DST entity itself would loop; rejected when the entity is added.

## 5. Device safety

| Concern | Rule |
|---|---|
| Min cycle | `ran_long_enough` on the child's `since`; bypassed in `setpoint` (child self-regulates, DST adds no cycling). Keep-alive still bypasses the gate as today. |
| Availability | Skip commands when unavailable/unknown (as `SwitchPort`); `mode is None` so the role reads inactive; the existing "unavailable to available" resume re-runs control. |
| `assumed_state` | DST's own record is the truth; initialised from the restored child state; no reliance on state feedback. Idempotent re-sends happen only on keep-alive. |
| Unsupported mode | `hvac_modes` of the child checked at command time; logged once, not sent. |
| Failure | Service error is logged and the optimistic record is rolled back (same error policy as switches). |
| Range | Pushed target clamped to child `min_temp`/`max_temp`. |
| Floor and openings | Unchanged. They act through the same controller, so a climate heater obeys floor limits and an opening pauses a setpoint-style child. |

## 6. Configuration

### 6.1 Keys

| Key | Type | Default | Notes |
|---|---|---|---|
| `heater`, `cooler`, `fan`, `dryer` | entity id | existing | `climate` accepted (YAML already uses `cv.entity_id`) |
| `control_style` | `on_off` / `setpoint` | `on_off` | requires a climate role; not with climate heat pump (OQ2) |
| `setpoint_offset` | float | `0` | requires a climate role |
| `target_sensor` | entity id | required | optional when a climate role exists |
| `secondary_heater` | entity id | existing | climate rejected |

### 6.2 Flows

- Entity selectors for heater/cooler/dryer add the `climate` domain. The fan selector already allows `fan`; it adds `climate`.
- Sensor selector becomes optional in every schema that has it. `EntityValidator` returns `sensor_required` when there is neither a sensor nor a climate role.
- New step `climate_control` (`control_style` select, `setpoint_offset` number) in the config flow, reachable from reconfigure, and a `climate_control_options` step in the options flow. Both guarded by `has_climate_role(config)`.
- Ordering (`docs/config_flow/step_ordering.md`): entity step, **climate_control**, features, ..., openings, presets. Climate control is part of "basic entity configuration".
- Dependency tracking: `control_style` and `setpoint_offset` require a climate role; `target_sensor` is conditionally required. Recorded in `tools/focused_config_dependencies.json`, `tools/config_validator.py`, `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`.
- Translations: `en.json` (step, field labels, `sensor_required` error, `control_style` option labels); other locales follow the existing fallback practice.

### 6.3 YAML

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Room
    heater: switch.room_heater_plug       # switch-like
    cooler: climate.room_ac               # climate
    control_style: on_off                 # default
    setpoint_offset: 0                    # default
    target_sensor: sensor.room_temperature
```

## 7. Backward compatibility

- No existing key changes meaning. `target_sensor` stays accepted everywhere; it only stops being mandatory when a climate role exists.
- `SwitchPort` is a move, not a rewrite: the first plan task is a behaviour-preserving extraction verified by the complete existing suite.
- Config entries without the new keys read as `on_off` / `0`.
- The `homeassistant.turn_on/off` service path for switches, valves and input_booleans is untouched.

## 8. Testing strategy

Per `docs/TESTING.md`: no standalone bug-fix files; flow tests go in the existing consolidated flow files.

- **Behaviour (new feature home):** `tests/features/test_climate_backed_devices.py`, one new file because no existing file covers a cross-role feature. It uses one fake child fixture (`setup_climate_child` in `tests/__init__.py`) that registers `climate.set_hvac_mode`, `climate.set_temperature`, `climate.turn_off` and updates its own state like a real entity (optionally `assumed_state`).
- **Seam regression:** the entire existing suite. Phase 1 task 1 changes no behaviour.
- **Config validation:** `tests/unit/test_config_validation_integration.py`.
- **Flows:** `tests/config_flow/test_heater_cooler_flow.py`, `test_options_flow.py`, `test_reconfigure_flow.py`, `test_e2e_heater_cooler_persistence.py`, `test_translations.py`.
- **Real device:** phase 5 checklist.

## 9. Phases

| Phase | Plan | Delivers |
|---|---|---|
| 1 | `2026-10-20-climate-entity-devices-phase-1-port-seam.md` | `EntityPort`/`SwitchPort` extraction, `ClimatePort` on_off, YAML, single role, mixed setup |
| 2 | `2026-10-20-climate-entity-devices-phase-2-setpoint-style.md` | `control_style: setpoint`, `setpoint_offset`, target mirroring, clamp |
| 3 | `2026-10-20-climate-entity-devices-phase-3-shared-climate-and-sensor-fallback.md` | one climate in several roles, heat pump role, `target_sensor` fallback, self-reference guard |
| 4 | `2026-10-20-climate-entity-devices-phase-4-config-flows.md` | config, reconfigure, options flows, dependency tracking, translations, README and example |
| 5 | `2026-10-20-climate-entity-devices-phase-5-real-device-verification.md` | HAOS checklist for the two rigs |

## 10. Files touched summary

**New**
- `custom_components/dual_smart_thermostat/hvac_device/entity_port.py`
- `custom_components/dual_smart_thermostat/climate_roles.py`
- `tests/features/test_climate_backed_devices.py`
- `examples/basic_configurations/climate_entity_roles.yaml`

**Modified**
- `hvac_device/generic_hvac_device.py`, `heater_device.py`, `cooler_device.py`, `fan_device.py`, `dryer_device.py`, `heat_pump_device.py`, `multi_hvac_device.py`, `hvac_device_factory.py`
- `hvac_controller/hvac_controller.py`, `generic_controller.py`, `heater_controller.py`, `cooler_controller.py`
- `managers/environment_manager.py`, `managers/feature_manager.py`
- `climate.py`, `const.py`, `config_validation.py`, `schemas.py`, `config_flow.py`, `options_flow.py`, `flow_utils.py`, `translations/*.json`
- `tools/focused_config_dependencies.json`, `tools/config_validator.py`, `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`, `docs/config_flow/step_ordering.md`, `README.md`
- `tests/__init__.py` plus the existing flow test files listed in section 8

(all paths under `custom_components/dual_smart_thermostat/` unless they start with `tests/`, `tools/`, `docs/`, `examples/` or are `README.md`)

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Extraction changes switch behaviour | Phase 1 task 1 is move-only; the whole suite must stay green before any climate code lands. |
| Child state event storm (every attribute change fires `state_changed`) | Listeners already tolerate it; `async_sync` and `async_set_mode` are idempotent so our own pushes do not re-trigger commands. |
| Two roles re-send the same mode concurrently | One lock per child; `async_set_mode` is a no-op when the child already reports that mode (keep-alive excepted). |
| IR device drifts from DST's record | Documented; keep-alive re-sends; a mode change re-sends too. |
| Pushed target rejected by the child | Clamped and stepped; failure is logged, not raised. |
| Late-starting child integration | Same resume path as switches (unavailable to available triggers control). |

## 12. Relation to #322

#322 asks for devices driven by a power `switch` plus a `number` setpoint. `EntityPort` is where such a port would plug in later. It is not built here (nothing consumes it yet); the interface is deliberately the same four calls plus `async_sync`, so it would be additive.

## 13. Acceptance criteria

1. Each role accepts a `climate.*` entity in YAML and in the config, reconfigure and options flows.
2. Mixed setup (climate cooler, switch heater) cycles both correctly in one thermostat.
3. `on_off`: DST's loop turns the child on (mode plus target plus offset) and off (`climate.turn_off`) with tolerances and min cycle respected.
4. `setpoint`: child stays engaged; target, mode and presets mirrored; openings pause and restore it; no DST cycling.
5. `target_sensor` omitted: current temperature, stale detection and startup use the child's `current_temperature`.
6. One climate in heater+cooler+fan+dryer never has two active roles; an idle role cannot stop an active one.
7. Unavailable child: no service calls; recovery resumes control. `assumed_state` child: control works with no state feedback.
8. Existing suite passes unchanged; `./scripts/docker-lint` passes.
9. Dependency validator (`python tools/config_validator.py`) knows the new keys.
10. Phase 5 checklist passes on both rigs.
