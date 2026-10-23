# Climate Entities as Device Roles

- **Status:** Proposed (design)
- **Date:** 2026-10-20
- **Branch:** `feat/climate-entity-devices`
- **Roadmap:** GitHub issue [#281](https://github.com/swingerman/ha-dual-smart-thermostat/issues/281) (agreed design in the owner's comment). Related: [#322](https://github.com/swingerman/ha-dual-smart-thermostat/issues/322) (number/switch-backed devices, out of scope, see section 12).

## 0. Owner decisions (design review)

The four open questions of the first draft are resolved. They are folded into the sections below; this table is the record.

| # | Decision |
|---|---|
| OQ1 | **Offset is per role from the start.** Keys `heater_setpoint_offset` and `cooler_setpoint_offset` (default `0`, signed, added as-is). There is no thermostat-wide offset. Only roles that push a temperature get a key; fan and dryer push none, so they get none. A heat pump uses the heater key while heating and the cooler key while cooling. An `ac_mode` cooler (cooler served by the `heater` entity) uses the cooler key. |
| OQ2 | `control_style: setpoint` with a climate heat pump is **rejected** in v1, with a clear validation error in YAML and in the flows. |
| OQ3 | **Off means off, once.** On the transition to Off DST sends one `climate.turn_off` to every climate child it holds, whatever mode the child is in, including a mode no role owns (for example `auto` set from a remote). While DST stays Off it is hands-off: keep-alive ticks send nothing to a climate (assumed or not), so the AC's own remote keeps working. Switch behaviour is unchanged. |
| OQ4 | In `setpoint` style `hvac_action` shows "engaged" only. Mirroring the child's own action is a follow-up and out of scope. |
| Follow | **Follow device changes (phase 6, after real-device testing).** The physical remote (or the device's own app, or an automation acting on the child) takes priority: latest intent wins. An external change on a climate child is adopted at once as the user's new DST setting, detected by value against per-thermostat expectations (section 3.6). Option `follow_device_changes`, default on; off keeps DST authoritative. This **supersedes** the first-draft rule "DST re-asserts remote changes within seconds", which now holds only with `follow_device_changes: false`. |
| Restart | **Restart, reconnect, first sight: decided (b).** DST re-asserts its restored setting; nothing is adopted from first sight or a reconnect. Reason: safe after power cuts (an AC may power up "off" and must not switch DST Off); the cost is that a remote change made while HA was down is overridden once. |
| Off | "Off means off" as implemented: the transition to Off sends one unscoped `turn_off` to every climate child; keep-alive while Off sends nothing to climate children. |
| New | **Fan speed for a climate child** (section 3.5, phase 3b): the child's `fan_modes` are used verbatim whenever a climate fills any role; one fan-speed target is chosen once at setup. |

## 1. Goal and scope

Let a device role (`heater`, `cooler`, `fan`, `dryer`, heat pump) be backed by a `climate.*` entity instead of a switch-like entity, so users stop writing template switches that call `climate.set_hvac_mode` / `climate.set_temperature` / `climate.turn_off`. The role type is detected from the entity domain, so mixed setups (IR AC as cooler, smart plug as heater) work.

### In scope
- Climate domain accepted for the five roles (YAML, config, reconfigure, options flows).
- `control_style`: `on_off` (default) and `setpoint`.
- `heater_setpoint_offset` and `cooler_setpoint_offset` (default `0`, per role).
- Fan speed (`fan_mode`) for a climate child, from its own `fan_modes` (section 3.5).
- `target_sensor` optional when a climate role exists (falls back to the child's `current_temperature`).
- One climate entity filling several roles without the roles fighting.
- Device safety: min cycle duration, availability, `assumed_state` (IR) devices.
- Dependency tracking, translations, README and example.

### Out of scope
- Humidity from the child's `current_humidity` (a dryer still needs `humidity_sensor`).
- Mirroring the child's `hvac_action` into DST (OQ4, follow-up).
- A fan-speed option or mapping (child `fan_modes` are used verbatim, no config).
- Climate as `secondary_heater` (aux). Stays switch-like only.
- Number/switch-pair devices from #322 (section 12).
- Any change to existing YAML semantics.

## 2. Design decisions

| # | Decision |
|---|---|
| D1 | **The seam is one object per role: `EntityPort`.** Today the stack touches its entity in exactly three ways, all inside `GenericHVACDevice` / `GenericHvacController`: read "is it on" (`hass.states.is_state(id, "on")`), read "how long in this state" (`condition.state(..., min_cycle)`), command it (`homeassistant.turn_on/off`, valve open/close). All three move behind `EntityPort` (`is_active`, `ran_long_enough`, `async_turn_on`, `async_turn_off`). Two implementations: `SwitchPort` (today's code, valve included, moved not changed) and `ClimatePort`. Controllers take a port in their constructor instead of `hass, entity_id`; managers, `climate.py`, `MultiHvacDevice` keep calling `async_turn_on/off` / `is_active` and do not change. |
| D2 | **No default port.** `GenericHVACDevice` builds its port from the entity domain via `make_port`; a device class without a role mode mapping cannot be built on a climate entity (raises at setup). No code path can silently drive a `climate.*` entity with `homeassistant.turn_on` and then wait for the state `on` (it never comes, the failure class a naive "just allow the domain" change would create). |
| D3 | **Role conflicts are structurally impossible.** One `ClimateChild` per real climate entity (per `hass`, keyed by entity id) owns the only record of that device's mode. A role's "active" is a derived predicate `child.mode == my_mode`, never stored per role. Two roles on one climate therefore cannot both be active, and a role's `turn_off` (the controller stopping its own role) is a no-op unless the child is currently in that role's mode, so a keep-alive `turn_off` from the idle cooler cannot stop the heater. "DST is Off" is a different call, `async_stop`, which turns the child off whatever its mode, but only on the transition and only while no role on the child is selected (OQ3); a role stop while Off is a no-op. The `in_use` guard in `MultiHvacDevice` (#637) protects switch-like entities only: a climate's role stop is scoped to the role's own mode, so sharing one needs no protection (and the guard would leave the child in the old mode). |
| D4 | **`control_style` is a property of the port, not a new device class.** `on_off`: DST's strategy decides (existing code path). `setpoint`: the port reports `self_regulating = True`; `GenericHVACDevice` then swaps in a strategy whose goal is never reached and skips the min-cycle gate. The unchanged controller therefore keeps the child engaged, pauses it for openings and floor limits, and restores it afterwards. No second control loop. |
| D5 | **Target mirroring is one idempotent method**, `port.async_sync()`, called at the top of `async_control_hvac`. Every trigger that already reaches control (target change, preset, mode change, sensor tick, keep-alive) mirrors the target; it only calls the child when the desired value differs from what the child reports. Pushed value = `target + the role's setpoint offset`, clamped to the child's `min_temp`/`max_temp`, rounded to `target_temp_step`. |
| D6 | **Temperature source is an entity id plus a reader.** When `target_sensor` is missing, config normalisation sets it to the first climate role entity (heater, cooler, fan, dryer order). `EnvironmentManager.update_temp_from_state` reads `attributes["current_temperature"]` when `state.domain == "climate"`, else `state.state`. Listeners, stale detection and startup read all keep using `sensor_entity_id` unchanged. An explicit `target_sensor: climate.x` works by the same rule. |
| D7 | **State truth.** Non-assumed child: its reported `state` is the mode and `last_changed` is the mode age. `assumed_state` child (IR): DST's own last commanded mode and timestamp are authoritative, initialised from the restored state. One property (`ClimateChild.mode`) hides the difference. Commands are serialised by one lock per child. |
| D8 | **Availability.** Unavailable/unknown child: commands are skipped (same rule `SwitchPort` has today, #499) and `mode` is `None`. A mode the child does not list in `hvac_modes` is logged once and not sent. |
| D9 | **Config surface.** `control_style` (`on_off`/`setpoint`, thermostat-wide) and per-role `heater_setpoint_offset` / `cooler_setpoint_offset` (float, default 0). Each offset key requires the matching role to be a climate entity. One new flow step `climate_control`, shown only when a role is a climate entity, shows only the offset fields that apply, and sits right after the entity step (before `features`), so openings/presets stay last. A single helper (`climate_roles.py`) answers "which roles are climate" and "which offsets apply" for YAML validation, the flows and runtime, so they cannot drift. |
| D10 | **Same entity in several roles is allowed for climate only.** The factory guard "cooler equals heater, ignore cooler" and the flow errors `same_heater_cooler` stay for switch-like entities. |
| D12 | **One fan-speed target, chosen once.** `FeatureManager` holds exactly one `FanSpeedControl`, selected in the factory (section 3.5). Nothing downstream asks which entity owns fan speed. |
| D11 | **Role to child mode:** heater `heat`, cooler `cool`, fan `fan_only`, dryer `dry`, heat pump `heat` or `cool` following `heat_pump_cooling` (evaluated lazily). Only heater, cooler and heat pump push a temperature, each with its own offset (heat pump: heater offset while heating, cooler offset while cooling). |

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
    @abstractmethod
    async def async_stop(self, context) -> None:    # "DST is Off": off means off


class SwitchPort(EntityPort): ...     # today's logic from GenericHVACDevice/GenericHvacController, valve included


class ClimateChild:                   # one per real climate entity, shared by roles
    mode -> str | None
    since -> datetime | None
    async def async_set_mode(mode, context) -> bool
    async def async_turn_off(context) -> None
    async def async_push_target(value, context) -> None


class ClimatePort(EntityPort):        # one per role, thin: derives everything from the child
    def __init__(self, child, role_mode: Callable[[], HVACMode], target: Callable[[], float | None],
                 offset: Callable[[], float], style: str, fan_speed=...) -> None: ...


def make_port(hass, entity_id, *, role_mode, target, style, offset: Callable[[], float],
              fan_speed: Callable[[], FanSpeedControl | None]) -> EntityPort: ...
```

`acquire_climate_child(hass, entity_id)` is a reference-counted get-or-create over `hass.data["dual_smart_thermostat_climate_children"]`: each port holds one reference, released (idempotently) when its thermostat is removed; the last release drops the child, so a reload starts from a fresh record and a shared child is never pulled from under another thermostat. The child holds no thermostat config (no min cycle, offset, style); those live in the per-role port, so a reload cannot leave stale config behind. The only retained state is the last commanded mode/time, which stays true across reloads.

### 3.2 `ClimatePort` behaviour

| Port call | on_off | setpoint |
|---|---|---|
| `is_active` | `child.mode == role_mode()` | same |
| `async_turn_on` | child unavailable: skip. Else `climate.set_hvac_mode(role_mode)`, then push target (+offset) for heater/cooler/heat pump | same |
| `async_turn_off` | only if `child.mode == role_mode()`: `climate.turn_off` | same |
| `async_stop` (DST Off) | `SwitchPort`: turn off if active (today's behaviour). `ClimatePort`: if no role on the child is selected and the child is available and not already off, `climate.turn_off`, whatever its mode; a keep-alive tick sends nothing | same |
| `async_sync` | if `child.mode == role_mode()` and desired target differs from the child's reported `temperature` (assumed: last pushed): push | same |
| `ran_long_enough(d)` | `now - child.since >= d` | always `True` (no DST cycling) |
| `self_regulating` | `False` | `True` |

`climate.set_hvac_mode` and `climate.set_temperature` are two calls on purpose: some devices drop the setpoint on a mode change, so the order is mode, then target. A mode change clears the "last pushed" memory so the target is re-sent.

### 3.3 Changes to existing classes

- `GenericHVACDevice.__init__`: build `self.port = make_port(...)` first, pass `self.port` to the controller. Replace `_entity_state`, `_is_valve`, `_entity_features`, `_supports_*_valve`, `is_on`, `_async_turn_on_entity`, `_async_turn_off_entity` and the valve helpers with calls to the port (`SwitchPort` owns them). Add `role_mode()` (default `None`) overridden by Heater/Cooler/Fan/Dryer/HeatPump devices. Add one line in `async_control_hvac`: `await self.port.async_sync(self._context)` after the OFF branch.
- `GenericHvacController`: constructor takes `port` instead of `hass, entity_id`; `is_active` and `ran_long_enough` delegate to it. `entity_id` stays as a property of the port for logging. `HeaterHvacConroller` and `CoolerHvacController` pass it through.
- `HvacEnvStrategy`: one classmethod `self_regulating(goal, reached_reason, not_reached_reason)` returning a strategy with `hvac_goal_reached == False` and `hvac_goal_not_reached == True`.
- Off paths: `ControlableHVACDevice.async_set_hvac_mode` (OFF), `GenericHVACDevice.async_control_hvac` (OFF branch), `_async_check_device_initial_state` and `MultiHvacDevice.async_turn_off_all` call the new `async_stop()` instead of `if is_active: turn_off`. Keep-alive (`time is not None`) keeps its unconditional `turn_off` for switches; a climate ignores ticks while Off. `GenericHVACDevice.async_stop` delegates to `port.async_stop` and updates hvac power as `async_turn_off` does.
- Offsets: each device class returns its offset via `setpoint_offset()` (Heater: `features.heater_setpoint_offset`, Cooler: `features.cooler_setpoint_offset`, HeatPump: by `_heat_pump_is_cooling`, Fan/Dryer: `0.0`); the port reads it lazily.
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

### 3.5 Fan speed for a climate child (phase 3b)

Today fan speed lives inside `FanDevice` (`_detect_fan_capabilities`, `async_set_fan_mode`, `restore_fan_mode`, `redetect_capabilities`) and `climate.py` reaches it through `features.fan_device`. Speed control is extracted into one small class, `FanSpeedControl(hass, entity_id)`, with the same members and one more detection source:

| Source | Modes | Set with |
|---|---|---|
| `fan` entity with `preset_modes` | the presets (as today) | `fan.set_preset_mode` |
| `fan` entity with `percentage` | `auto/low/medium/high` (as today) | `fan.set_percentage` |
| `switch` / `input_boolean` | none | n/a |
| **`climate` entity with `fan_modes`** | **its `fan_modes` verbatim** (values like `quiet`, `strong` survive; no mapping) | **`climate.set_fan_mode`** |

- **One target, chosen once (D12).** `FanDevice` owns a `FanSpeedControl` for its entity. The factory selects the single control for the thermostat: if a fan device exists (a fan entity is configured for the fan role, or the fan role is the climate itself) its control wins; otherwise, if any role is a climate entity, a `FanSpeedControl` over the first climate role (heater, cooler, fan, dryer order) is created; otherwise none. It is stored with `features.set_fan_speed(control)` (replaces `set_fan_device`). A cooler-only AC therefore gets speed control, and when a separate fan entity is configured the AC's own fan speed is never touched. `climate.py`, `FeatureManager` (`supports_fan_mode`, `fan_modes`, restore) and the state-change redetect use that one object.
- **Re-apply after turn on.** Many ACs, IR ones especially, reset the fan speed when the mode changes. `ClimatePort.async_turn_on` calls `fan_speed.async_reapply(entity_id)` after the mode (and target) are set; it acts only when the control targets that same climate entity, so a separate fan entity or a different climate is never touched. `FanDevice.async_turn_on` skips its own explicit apply when its control is climate-backed (the port already did it).
- **Restore across restarts** and **late discovery** reuse today's mechanism unchanged: `restore_fan_mode` holds the value until detection succeeds; `redetect_capabilities` runs on the child's state changes (the child is always in the thermostat's listened entity ids because it fills a role).
- **No new config option.** Detection is automatic, as today (`hvac_device/CLAUDE.md`).
- Setting the speed on an unavailable child, or to a value outside `fan_modes`, is logged and skipped (same as fans).

### 3.6 Following device changes (phase 6)

The device is also operated from outside DST (remote, vendor app, an automation). The latest intent wins, so an external change on a climate child becomes DST's setting instead of being corrected back. Detection is by **value**, never by context or time (reviewed against HA core: a state write within 5 s of a service call carries the caller's context, and coordinator refreshes are debounced for 10 s, so contexts and timing cannot tell DST's echo from a remote press).

**Expectations (the only memory).** Each thermostat keeps, per child and per attribute (`mode`, `target`, `fan_mode`), a short list (at most 4) of the values *a DST thermostat* commanded and has not yet seen reported. It is kept on the child per observing thermostat (`FeatureManager` instance), and every command, whichever thermostat sent it and whether the user or its own control (a safety stop, a start) caused it, is recorded for **all** thermostats on the child, tagged with the one that sent it. So a thermostat never takes a peer's command for the user acting on the device. Rules:
- A command that will actually be sent appends its value. A command skipped because the child already reports that value appends nothing, and a failed command removes its entry. Assumed-state children record nothing.
- When the child's state changes, each tracked attribute that changed is compared with that thermostat's list: if the new value is in the list it is an echo and only that entry is consumed (so echoes may arrive in any order: a late echo of an older command is still found in the list); otherwise the change is **external**.
- Nothing expires on a timer. Entries die by being matched, by overflow, or by the next adoption, which clears the thermostat's lists.
- Contexts are a hint only: every DST command goes out with a fresh `Context` (logbook attribution), the DST entity's own context is never passed down, and no decision reads a context.

An event is ignored when either state is unavailable/unknown, when the child is `assumed_state` in either state (its reported state is DST's own record), or while this thermostat is mid-command (below). An integration that decodes the remote but is not flagged `assumed_state` just looks like a normal device and is followed.

**Adoption is immediate.** There is no settle window and no hold. On an external change the thermostat takes the report that came from outside (not the child as it is by the time the adoption runs: a peer may have stopped it meanwhile) and applies **only the attributes that changed in it** through its own public setters, in this order: fan mode (only if this child is the fan-speed target), mode, target. A target is taken only if it changed and the role owning the child's current mode pushes a setpoint (a fan or dryer role does not, and an off child has no owning role), so a stale target the user never touched is not imported. Then one normal forced control run follows. Two flags, both owned by the thermostat and both lasting milliseconds, keep this sound:
- `adopting`: while the setters run, this thermostat's commands to the child are dropped (the child already holds the adopted state, and the setters reload targets from presets, which would otherwise be pushed back over the remote's value). The flag is released before the control run, so safety stops and every normal command go out at once. It never affects another thermostat.
- `sending` (around one `turn_on` sequence): events that arrive while DST itself is sending mode, target and fan are the device's own side effects (many ACs reset the fan or setpoint on a mode change) and are not external. This keeps the fan re-apply of phase 3b working. A reset that a polling integration reports later than the sequence looks like a remote change and is followed (device is the truth).

| Child state | DST becomes |
|---|---|
| fan_mode (this child is the fan-speed target and the value is one of its modes) | `fan_mode` |
| mode owned by a role (heat, cool, fan_only, dry, a heat pump's current direction) | `hvac_mode` = that mode |
| `off` | `Off` |
| a mode no role owns (for example `auto`) | `Off`, and hands-off |
| target `T` | target = `T` minus the owning role's setpoint offset, through the same path as a user-set temperature |

Adoptions are serialised per thermostat and always read the snapshot when they run; an event arriving during a running adoption marks it dirty and the adoption runs again. A split remote sequence (mode, then target) is simply two adoptions with nothing commanded in between. A chatty integration therefore cannot defer anything: an open window pauses the child on the control run that follows each adoption.

**One change, one effect; two thermostats.** One external change causes one adoption per thermostat that follows the child, and the adopted state is already on the child, so nothing is commanded and nothing comes back. Two thermostats on one child do **not** follow each other: A's command (user-driven or its own control, such as an opening's stop) is an echo for B, only changes from outside DST are adopted, by both. B re-engages on its own next run, as on master, and neither's safety stop is delayed by the other. An adoption forgets only the expectations its own thermostat sent.

**Safety precedence.** Adoption records the intent and then runs one *forced* control run (like a manual change): an open window pauses the child (restored after closing) and a floor limit applies at once, whatever the minimum cycle, and a stale sensor stops the child once (the intent is kept). The forced run starts a device that wants to run, but it does not stop one for a reached goal before its minimum cycle is over (it must not short-cycle a device the user just started); automatic ticks afterwards wait for the minimum cycle as usual.

**Edge cases decided.**
- Remote then DST, and DST then remote, in any interleaving: the later one wins, because each is judged by value against the thermostat's own pending list. A remote press within 5 s of a DST command is adopted even though HA stamps it with DST's context.
- A remote toggling A to B to A (target or mode) is followed each time: an echo is consumed once, it is not remembered as "DST's value".
- A device that rewrites what it was sent (rounds a target differently than DST pushed) is followed, so DST's target takes the device's resolution.
- A stale value polled back after DST's command (an optimistic write, then an old reading some seconds later) is followed as the device's truth. Documented, checked in the real-device run (P5 step 9), not guarded: guarding would mean timers, and the symptom (DST yields to what the device really reports) matches "the device is the truth".
- A remote press landing inside the few milliseconds of an adoption's setters can be overwritten. Accepted.
- Spontaneous device changes (defrost, protection shut-off, the unit's own timer) look like the remote and are adopted.
- A target outside DST's own min/max is clamped like any user input, then pushed to the child once.
- Option off (`follow_device_changes: false`): expectations are still consumed, nothing is adopted; DST re-asserts on its next control run and does not fight while Off.

**Restart, reconnect, first sight (owner decision (b), section 0).** Nothing is adopted from first sight (startup, a child that appears late) or from a reconnect (unavailable to available). DST keeps its restored setting and re-asserts it on its next control run; a remote change made during downtime is overridden once. This is safe after a power cut, when an AC may power up off. There is no flag for it: events with an unavailable or missing old state are simply ignored.

**Option.** `follow_device_changes` (bool, default `true`), thermostat-wide, only valid with a climate role (`climate_roles` is the single rule source). Flows: shown in the `climate_control` and `climate_control_options` steps. Dependency tracking: requires a climate role.

## 4. Role conflicts (one climate, several roles)

Heater, cooler, fan and dryer pointing at the same `climate.x` are four `ClimatePort`s over one `ClimateChild`.

- **Exclusion by derivation (D3).** `is_active` is `child.mode == role_mode`; there is no per-role flag to get out of sync.
- **Switching modes.** `MultiHvacDevice` already stops the devices that do not handle the new mode before running the one that does, sparing entities the running device also owns. Heat to cool: the heater port turns the child off (it is in `heat`), the cooler port sets `cool`. Even if the stop is skipped, `set_hvac_mode(cool)` replaces `heat` because the child holds one mode.
- **No cross-kill.** An idle role's keep-alive or OFF-mode `turn_off` is a no-op unless the child is in that role's mode.
- **Min cycle** is measured on the child (`since`), which is also what protects the compressor when heat and cool alternate.
- **Off is global, once.** `async_stop` turns the child off in any mode on the transition to Off, so Off cannot be defeated by a mode no role owns; it only applies while no role on the child is selected (a role switched out by another mode just does its mode-scoped stop). While Off, ticks leave the climate alone.
- **Stops inside one control run.** A climate holds one mode, so the role stops of a control run (`MultiHvacDevice.control_pass`, also around `set_temperature` with `hvac_mode`) are held back and sent at the end only if no mode was set meanwhile and the child is still in the stopped role's mode. Otherwise a turn_off could land after the new mode on a slow device.
- **Config guard.** The factory and flow "same entity" checks apply only to non-climate entities.
- **Setpoint style and heat_cool.** With `control_style: setpoint`, a heater and cooler on the *same* climate both stay engaged, so heat_cool would flip the child between modes every tick. Rejected in YAML and the flows (`heat_cool_mode` or both target limits set, one climate as heater and cooler); separate climates for heater and cooler are fine. Mapping to the child's own `heat_cool`/`auto` mode is a follow-up. Only roles that push a setpoint (heater, cooler, heat pump) can be self-regulating; fan and dryer are always `on_off`.
- **Remote changes. SUPERSEDED by section 3.6.** The first draft said a change made on the AC's own remote is re-asserted by DST within seconds. With `follow_device_changes` on (default) the change is adopted instead; the re-assert behaviour remains only with `follow_device_changes: false`.
- **Self reference.** A role pointing at the DST entity itself would loop; rejected when the entity is added.

## 5. Device safety

| Concern | Rule |
|---|---|
| Min cycle | `ran_long_enough` on the child's `since`; bypassed in `setpoint` (child self-regulates, DST adds no cycling). Keep-alive still bypasses the gate as today. |
| Availability | Skip commands when unavailable/unknown (as `SwitchPort`); `mode is None` so the role reads inactive; the existing "unavailable to available" resume re-runs control. |
| `assumed_state` | DST's own record is the truth; initialised from the restored child state; no reliance on state feedback. The mode is not re-sent on keep-alive while Off. |
| Unsupported mode | `hvac_modes` of the child checked at command time; logged once, not sent. |
| Failure | Service error is logged and the optimistic record is rolled back (same error policy as switches). |
| Range | Pushed target clamped to child `min_temp`/`max_temp`. |
| Floor and openings | Unchanged. They act through the same controller, so a climate heater obeys floor limits and an opening pauses a setpoint-style child. |

## 6. Configuration

### 6.1 Keys

| Key | Type | Default | Notes |
|---|---|---|---|
| `heater`, `cooler`, `fan`, `dryer` | entity id | existing | `climate` accepted (YAML already uses `cv.entity_id`) |
| `follow_device_changes` | bool | `true` | requires a climate role (section 3.6) |
| `control_style` | `on_off` / `setpoint` | `on_off` | requires a climate role; rejected with a climate heat pump (OQ2) |
| `heater_setpoint_offset` | float | `0` | requires `heater` to be a climate entity (not when it only serves as an `ac_mode` cooler) |
| `cooler_setpoint_offset` | float | `0` | requires `cooler` to be a climate entity, or an `ac_mode` / heat pump `heater` that is climate |
| `target_sensor` | entity id | required | optional when a climate role exists |
| `secondary_heater` | entity id | existing | climate rejected |

### 6.2 Flows

- Entity selectors for heater/cooler/dryer add the `climate` domain. The fan selector already allows `fan`; it adds `climate`.
- Sensor selector becomes optional in every schema that has it. `EntityValidator` returns `sensor_required` when there is neither a sensor nor a climate role.
- New step `climate_control` (`control_style` select plus the applicable `heater_setpoint_offset` / `cooler_setpoint_offset` numbers) in the config flow, reachable from reconfigure, and a `climate_control_options` step in the options flow. Both guarded by `has_climate_role(config)`.
- Ordering (`docs/config_flow/step_ordering.md`): entity step, **climate_control**, features, ..., openings, presets. Climate control is part of "basic entity configuration".
- Dependency tracking: `control_style` requires a climate role and each offset key requires its own role to be climate; `target_sensor` is conditionally required. Recorded in `tools/focused_config_dependencies.json`, `tools/config_validator.py`, `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`.
- Translations: `en.json` (step, field labels, `sensor_required` error, `control_style` option labels); other locales follow the existing fallback practice.

### 6.3 YAML

```yaml
climate:
  - platform: dual_smart_thermostat
    name: Room
    heater: switch.room_heater_plug       # switch-like
    cooler: climate.room_ac               # climate
    control_style: on_off                 # default
    cooler_setpoint_offset: 0             # default; per role
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
| 2 | `2026-10-20-climate-entity-devices-phase-2-setpoint-style.md` | `control_style: setpoint`, per-role `*_setpoint_offset`, target mirroring, clamp |
| 3 | `2026-10-20-climate-entity-devices-phase-3-shared-climate-and-sensor-fallback.md` | one climate in several roles, heat pump role, `target_sensor` fallback, self-reference guard |
| 3b | `2026-10-20-climate-entity-devices-phase-3b-climate-fan-speed.md` | `FanSpeedControl` extraction, climate `fan_modes` source, single fan-speed target, re-apply after turn on |
| 4 | `2026-10-20-climate-entity-devices-phase-4-config-flows.md` | config, reconfigure, options flows, dependency tracking, translations, README and example |
| 5 | `2026-10-20-climate-entity-devices-phase-5-real-device-verification.md` | HAOS checklist for the two rigs |
| 6 | `2026-10-20-climate-entity-devices-phase-6-follow-device-changes.md` | `follow_device_changes`: external-change detection, adoption, scenario test matrix |

## 10. Files touched summary

**New**
- `custom_components/dual_smart_thermostat/hvac_device/entity_port.py`
- `custom_components/dual_smart_thermostat/hvac_device/fan_speed.py`
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
| IR device drifts from DST's record | Documented; a mode change re-sends; hands-off while Off. |
| Pushed target rejected by the child | Clamped and stepped; failure is logged, not raised. |
| Late-starting child integration | Same resume path as switches (unavailable to available triggers control). |

## 12. Relation to #322

#322 asks for devices driven by a power `switch` plus a `number` setpoint. `EntityPort` is where such a port would plug in later. It is not built here (nothing consumes it yet); the interface is deliberately the same four calls plus `async_sync`, so it would be additive.

## 13. Acceptance criteria

1. Each role accepts a `climate.*` entity in YAML and in the config, reconfigure and options flows.
2. Mixed setup (climate cooler, switch heater) cycles both correctly in one thermostat.
3. `on_off`: DST's loop turns the child on (mode plus target plus the role's offset) and off (`climate.turn_off`) with tolerances and min cycle respected.
4. `setpoint`: child stays engaged; target, mode and presets mirrored; openings pause and restore it; no DST cycling.
5. `target_sensor` omitted: current temperature, stale detection and startup use the child's `current_temperature`.
6. One climate in heater+cooler+fan+dryer never has two active roles; an idle role cannot stop an active one.
7. Unavailable child: no service calls; recovery resumes control. `assumed_state` child: control works with no state feedback.
8. Existing suite passes unchanged; `./scripts/docker-lint` passes.
9. Dependency validator (`python tools/config_validator.py`) knows the new keys.
10. Phase 5 checklist passes on both rigs.
11. DST Off sends `climate.turn_off` to every climate child in any mode.
12. A climate child's own `fan_modes` drive `fan_mode` for any role; a separately configured fan entity takes precedence and the AC's fan speed is then untouched; the mode is re-applied after each turn on, restored after restart and detected late.
13. With `follow_device_changes` on, an external change on a climate child (mode, off, target, fan mode, foreign mode) becomes DST's setting at once, without any command echoed back; own echoes (including out-of-order, split and context-stamped ones) and `assumed_state` devices adopt nothing; a remote A to B to A is followed each time; openings, floor limits and a stale sensor still win immediately; two thermostats on one child follow each other without fighting. With it off DST re-asserts on its next control run. First sight and reconnect adopt nothing (owner decision).
