# Climate Entity Devices - Phase 6: Follow Device Changes - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The physical remote (or the vendor app, or an automation acting on the child) takes priority: an external change on a climate child becomes the user's new DST setting, latest intent wins, with no command echoed back. Option `follow_device_changes` (default on); off keeps DST authoritative (it re-asserts on its next control run). Every scenario of the matrix below is an automated test.

**Architecture:** Detection and adoption sit where the code already has one place per concern. `ClimateChild` (one per real climate entity, `entity_port.py`) learns to recognise its own traffic: every command it sends carries a `Context` it records, and it remembers the values it commanded. `ClimateChild.classify(old, new, context)` answers "what changed externally". The climate entity (`climate.py`) registers one follower per child through the state listener it already has (`_async_switch_changed_event`), coalesces external events in a 2 s settle window during which the child is *held* (a single choke point makes every DST-to-child command a no-op), then reads the child's current state once and applies it through DST's own public setters (`async_set_fan_mode`, `async_set_hvac_mode`, `async_set_temperature`), so presets, clamping and all existing behaviour are reused. One normal forced control run follows. Because the held child already holds the adopted state, adoption cannot echo.

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md` (section 3.6)
**Previous phases:** 1 to 5 merged (this plan is written against the current `entity_port.py` `ClimateChild` / `ClimatePort`, `fan_speed.py`, `climate_roles.py`, `climate.py`). This phase supersedes the README sentence "A change made on the AC's own remote is re-asserted by the thermostat within seconds".

---

## Testing Environment

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly. Test code follows the idioms already used in `tests/features/test_climate_backed_devices.py` (`_setup`, `common.add_fake_climate`); fix an import or fixture name in the red step if reality differs, the assertions are what matter.

---

## Constants decided

| Name | Value | Meaning |
|---|---|---|
| `FOLLOW_SETTLE` | 2 s | external events coalesce for this long before adoption |
| `ECHO_WINDOW` | 30 s | values DST commanded in the last 30 s count as echoes; the latest commanded value always does |
| own contexts kept | 64 | ids of contexts DST used for child commands |

---

## SCENARIO TEST MATRIX

Test file: `tests/features/test_climate_follow_device_changes.py` unless the Task column says otherwise (config tests live in the existing flow and unit files). "Red" = fails before the task's implementation; "guard" = passes already and pins behaviour that adoption must not break (written before the implementation lands, run after it).

Rig used unless stated: **R1**, one fake AC in all four roles (heater, cooler, fan, dryer), `on_off`, `follow_device_changes` on, room sensor equal to the target after engagement so a running device keeps running (`_start`, below). "Commands" lists what is sent to the fake child; "other" lists other devices; `none` means an empty call list.

### A. Latest command wins, per source

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| A1 | `test_remote_mode_is_adopted` | R1 Heat engaged | remote sets child `cool`, settle | DST hvac_mode `cool` | child: none |
| A2 | `test_remote_target_is_adopted` | R1 Heat engaged, target 22 | remote sets child target 24 | DST target 24 | none |
| A3 | `test_remote_target_minus_heater_offset` | R1, `heater_setpoint_offset: 3`, Heat | remote sets child target 25 | DST target 22 | none |
| A4 | `test_remote_target_minus_cooler_offset` | R1, `cooler_setpoint_offset: -5`, Cool | remote sets child target 19 | DST target 24 | none |
| A5 | `test_remote_fan_mode_is_adopted` | R1 Heat engaged, DST fan `auto` | remote sets child fan `quiet` | DST `fan_mode` attribute `quiet` | none |
| A6 | `test_remote_off_is_adopted` | R1 Heat engaged | remote turns child off | DST `off` | none |
| A7 | `test_dst_ui_command_is_not_adopted_back` | R1 Off | DST UI sets Heat | child `heat` and DST `heat` after settle | child: one `set_hvac_mode`, one `set_temperature`, nothing after |
| A8 | `test_dst_ui_target_reaches_the_child_and_stays` | R1 Heat engaged | DST UI sets target 23 | child target 23, DST target 23 after settle | one `set_temperature(23)` |
| A9 | `test_automation_service_call_on_the_child_is_adopted` | R1 Heat engaged | `climate.set_hvac_mode cool` called on the child entity by an automation context | DST `cool` | child: only the automation's own call, no DST command |
| A9b | `test_automation_service_call_on_dst_is_a_dst_command` | R1 Off | automation calls `climate.set_hvac_mode heat` on DST | child `heat`, DST `heat` after settle | one `set_hvac_mode`, one `set_temperature`; no adoption |
| A10 | `test_preset_change_is_pushed_and_not_adopted_back` | R1 Heat engaged, preset `away` 17 | DST preset `away` | child target 17, DST preset still `away`, target 17 after settle | one `set_temperature(17)` |
| A11 | `test_remote_then_dst_in_the_same_second_dst_wins` | R1 Heat engaged | remote sets `cool`, then DST UI sets Off, no settle between | DST `off`, child `off`, the pending adoption is gone | child: one `turn_off` |
| A12 | `test_dst_then_remote_in_the_same_second_remote_wins` | R1 Off | DST UI sets Heat, then remote sets `cool` | DST `cool` | child: DST's `set_hvac_mode heat` + `set_temperature` only |
| A13 | `test_remote_mode_then_target_as_two_events` | R1 Heat engaged, target 22 | remote sets `cool`, 1 s later remote sets target 24, settle | DST `cool`, target 24, one adoption | none (no `set_temperature(22)` clobber) |
| A14 | `test_remote_target_then_mode_as_two_events` | as A13 | remote target 24 first, then `cool` | DST `cool`, target 24 | none |
| A15 | `test_a_second_remote_change_inside_the_window_wins` | R1 Heat engaged | remote `cool`, then `fan_only` within 1 s | DST `fan_only` | none |

### B. Adoption variants

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| B1 | `test_foreign_mode_turns_dst_off_and_stays_hands_off` | R1 (roles heater/cooler only), Heat engaged | remote sets child `auto` | DST `off`; later keep-alive ticks too | child: none, ever |
| B2 | `test_shared_child_adopts_each_role_mode_without_a_loop` | R1 Heat engaged | remote `dry`, settle, then remote `fan_only`, settle, then 5 sensor ticks | DST `dry` then `fan_only` | child: none at any point |
| B3 | `test_heat_pump_owns_only_its_current_direction` | climate heat pump, flag `heating` | remote `heat` (owned), then flag flips to cooling and remote sets `heat` | first: DST `heat`; second: `heat` is foreign, DST `off` | none |
| B4 | `test_setpoint_style_adopts_the_target_without_commands` | cooler climate, `setpoint`, `cooler_setpoint_offset: -2` | remote target 20 | DST target 22 | none |
| B5 | `test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode` | heater/cooler = AC, `fan` entity configured | remote fan `strong` on the AC | DST fan modes are the fan entity's, `fan_mode` unchanged | none |
| B6 | `test_adopted_target_outside_the_dst_range_is_clamped_and_pushed_once` | R1 Heat, DST `max_temp: 26` | remote target 29 | DST target 26 | child: exactly one `set_temperature(26)` |
| B7 | `test_mixed_rig_adopting_cool_stops_the_switch_heater_once` | switch heater + climate cooler, Heat engaged on the switch | remote turns the AC `cool` | DST `cool` | child: none; other: heater switch `turn_off` once |

### C. Echoes

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| C1 | `test_own_command_echo_is_not_adopted` | R1 Off | DST turns the child on (sensor demand) | no adoption, DST stays | `set_hvac_mode` + `set_temperature` once each, nothing more |
| C2 | `test_echo_without_a_dst_context_is_not_adopted` | R1 Off, echoes held | DST commands `heat`; the echo is delivered with a foreign context and the commanded value | no adoption | the original command only |
| C3 | `test_out_of_order_echoes_are_not_adopted` | R1, echoes held | DST commands `cool`, then `off`; echoes delivered `off` then `cool` | DST stays as commanded, no adoption | the two commands only |
| C4 | `test_split_mode_and_target_echo_is_not_adopted` | R1 Off, echoes held | DST turn-on (mode + target); the two echoes arrive separately | no adoption | the two commands only |
| C5 | `test_attribute_noise_is_ignored` | R1 Heat engaged | child `current_temperature` and fan-irrelevant attributes change | no adoption | none |
| C6 | `test_an_old_echo_after_the_window_is_external` | R1, held | DST commands `cool`; DST later commands `off`; 40 s later `cool` is reported | adopted (documented boundary) | none |

### D. Safety precedence

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| D1 | `test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing` | R1 Heat, window open (child paused) | remote turns child `heat`, target 24 | DST `heat`/24; child paused again; after the window closes the child is heating at 24 | open: one `turn_off`; close: `set_hvac_mode heat`, `set_temperature(24)` |
| D2 | `test_floor_limit_wins_over_an_adopted_heat` | heater = AC, floor sensor above `max_floor_temp`, DST Off | remote `heat` | DST `heat` recorded, child stopped | one `turn_off` |
| D3 | `test_stale_sensor_stops_the_child_and_keeps_the_intent` | R1 Heat, stale duration 2 min elapsed (emergency stop done) | remote `heat`, settle; then the sensor recovers | DST `heat`; child stopped; after recovery control resumes | stall: one `turn_off`; recovery: DST commands as normal |
| D4 | `test_min_cycle_still_applies_after_an_adoption` | R1 Off, `min_cycle_duration` 5 min, room hot | remote `heat` (goal already reached) | child not stopped inside 5 min, stopped after | none, then one `turn_off` after 6 min |

### E. Off

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| E1 | `test_transition_to_off_sends_one_unscoped_off` | R1, `follow_device_changes: false`, child in `auto` (no role owns it) | DST UI sets Off | child `off` | exactly one `turn_off` |
| E2 | `test_keep_alive_while_off_sends_nothing_to_climate_children` | R1 Off, `keep_alive` 1 min, child `heat` set by the remote, follow off | 3 keep-alive ticks | child stays `heat` | none |
| E3 | `test_remote_use_while_off_is_adopted_when_following` | R1 Off, follow on, room 22 | remote `heat`, target 22 | DST `heat`/22 | none |
| E4 | `test_remote_use_while_off_is_ignored_and_never_fought_when_not_following` | as E3 with follow off | remote `heat`, settle, keep-alive ticks | DST stays `off`, child stays `heat` | none |

### F. `follow_device_changes: false`

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| F1 | `test_not_following_reasserts_the_mode_on_the_next_tick` | R1 Cool engaged, follow off | remote `heat`; sensor tick, room hot | DST stays `cool` | one `set_hvac_mode cool` |
| F2 | `test_not_following_reasserts_the_target_on_the_next_run` | R1 Heat engaged 22, follow off | remote target 25; sensor tick | DST target 22 | one `set_temperature(22)` |

### G. Restart and reconnect

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| G1 | `test_restored_state_adopts_nothing` | restore cache: DST `cool`, 24; child already `heat`/20 | startup | DST `cool`/24 (restored, not adopted) | none attributable to adoption |
| G2 | `test_reconnect_adopts_nothing` | R1 Heat engaged | child goes `unavailable`, comes back `cool` | DST `heat` | none from adoption |
| G3 | `test_a_child_appearing_late_adopts_nothing` | R1 configured, child missing | child appears in `cool` | DST keeps its setting | none from adoption |

### H. `assumed_state` devices

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| H1 | `test_assumed_child_adopts_nothing` | child with `assumed_state`, DST Cool engaged | a reported change to `heat` with a foreign context | DST `cool` | none from adoption |
| H2 | `test_a_remote_decoded_without_the_assumed_flag_is_followed` | child that decodes the remote, no `assumed_state` attribute | remote `cool` | DST `cool` (looks like a normal device) | none |
| H3 | `test_classify_ignores_an_assumed_flag_on_either_side` | unit, `ClimateChild.classify` | old assumed / new not, and the reverse | no change reported | n/a |

### I. Automation interference (from the P5 real-device run)

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| I1 | `test_an_automation_forcing_the_fan_mode_is_followed_without_a_storm` | R1, child resets fan on mode change, an automation sets fan `strong` whenever the fan leaves `strong`, DST selection `quiet` | the automation fires, then DST cycles the AC on three times, then 5 idle ticks | DST `fan_mode` ends `strong`, the final idle ticks cause no commands | DST fan commands at most one per turn on, zero during the idle ticks |
| I2 | `test_an_automation_forcing_the_mode_is_followed_without_a_loop` | R1 Cool engaged, an automation sets `heat` whenever the child leaves `heat` | automation fires | DST `heat` | none, also across 5 ticks |
| I3 | `test_not_following_an_automation_forced_fan_does_not_storm` | as I1 with follow off | automation fires, 5 idle ticks | DST selection stays `quiet` | no DST fan command during the idle ticks |

### K. Hold

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| K1 | `test_the_child_is_held_while_an_external_change_settles` | R1 Heat engaged 22 | remote target 24; a sensor tick inside the settle window | no DST `set_temperature(22)` clobber; DST later 24 | none |

### J. Option, flows, tracking

| ID | Test | File | Given / When / Then |
|---|---|---|---|
| J1 | `test_follow_option_defaults_to_on` | `tests/unit/test_climate_roles.py` | schema without the key, with a climate role: FeatureManager says follow is on |
| J2 | `test_follow_option_needs_a_climate_role` | `tests/unit/test_climate_roles.py` | key set with switch-only roles: `vol.Invalid` |
| J3 | `test_follow_option_is_offered_for_any_climate_role` | `tests/unit/test_climate_roles.py` | `climate_control_keys` includes it for a fan-only or dryer-only climate, and `drop_inapplicable` drops it when the last climate role goes |
| J4 | `test_climate_control_step_offers_the_follow_option` | `tests/config_flow/test_heater_cooler_flow.py` | climate cooler: step schema has `follow_device_changes`, default on; submit stores it, including `False` |
| J5 | `test_follow_option_persists_to_the_options_flow` | `tests/config_flow/test_options_flow.py` | entry with `False`: options step prefills `False`; saving keeps it |
| J6 | `test_follow_option_is_dropped_when_no_climate_role_remains` | `tests/config_flow/test_reconfigure_flow_e2e_heater_cooler.py` | reconfigure climate to switches: key gone |
| J7 | `test_follow_option_translations_exist` | `tests/config_flow/test_translations.py` | config and options step strings exist |
| J8 | dependency validator | `python tools/config_validator.py` | key without climate role is reported (Task 2) |

---

## Test support (written first, used by every task)

`tests/features/test_climate_follow_device_changes.py` starts with these helpers (shared names from `test_climate_backed_devices.py`: `AC`, `SENSOR`, `HEATER`, `_setup`).

```python
"""Following changes made on the device itself (issue #281, phase 6)."""

from datetime import timedelta

from homeassistant.components.climate import HVACMode
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util
import pytest

from tests import common

from .test_climate_backed_devices import AC, HEATER, SENSOR, _setup

WINDOW = "binary_sensor.window"
ALL_ROLES = {
    "heater": AC,
    "cooler": AC,
    "fan": AC,
    "dryer": AC,
    "humidity_sensor": "sensor.hum",
    "target_humidity": 40,
    "fan_mode": True,
}


def _dst(hass: HomeAssistant) -> State:
    return hass.states.get("climate.test")


async def _settle(hass, freezer, seconds=3) -> None:
    """Let the follow window close (and any timers fire)."""
    freezer.tick(timedelta(seconds=seconds))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _tick(hass, room: float) -> None:
    """A room sensor update (this is what drives DST's own control)."""
    hass.states.async_set(SENSOR, room)
    await hass.async_block_till_done()


async def _start(
    hass, freezer, mode=HVACMode.HEAT, target=22.0, *, child_kwargs=None, **cfg
):
    """DST engaged in `mode`, room equal to the target, call list cleared.

    Engagement needs demand, so the room starts 4 degrees off, then moves to the
    target: a running device keeps running there (neither too cold nor too hot).
    """
    engage = target - 4 if mode == HVACMode.HEAT else target + 4
    hass.states.async_set(SENSOR, engage)
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(hass, **{**ALL_ROLES, **cfg, "initial_hvac_mode": mode})
    child = await common.add_fake_climate(hass, AC, **(child_kwargs or {}))
    await common.async_set_temperature(hass, target, "climate.test")
    await hass.async_block_till_done()
    await _tick(hass, target)
    child.calls.clear()
    return child
```

`tests/common.py`, additions to `FakeClimateChild` (route the four existing service handlers through `_apply` so echoes can be held; an assumed child still ignores commands):

```python
    def _apply(self, **attrs):
        """A command takes effect now, or is parked when echoes are held."""
        if self._attr_assumed_state:
            return
        if self._echo_queue is not None:
            self._echo_queue.append((attrs, self._context))
            return
        self._write(attrs, self._context)

    def _write(self, attrs, context):
        for key, value in attrs.items():
            setattr(self, f"_attr_{key}", value)
        if context is not None:
            self.async_set_context(context)
        self.async_write_ha_state()

    def remote(self, *, mode=None, temperature=None, fan_mode=None, **extra):
        """The user acts on the device: a state change with a foreign context."""
        attrs = {
            key: value
            for key, value in {
                "hvac_mode": mode,
                "target_temperature": temperature,
                "fan_mode": fan_mode,
            }.items()
            if value is not None
        }
        self._write(attrs | extra, Context())

    def hold_echoes(self):
        """Park command effects until flush_echoes (a slow or polled device)."""
        self._echo_queue = []

    def flush_echoes(self, order=None, *, context="own"):
        """Deliver parked effects, optionally reordered; context="foreign" strips DST's."""
        queue, self._echo_queue = self._echo_queue, None
        for index in order if order is not None else range(len(queue)):
            attrs, ctx = queue[index]
            self._write(attrs, Context() if context == "foreign" else ctx)
```

(`__init__` gains `self._echo_queue = None`; `async_set_hvac_mode`, `async_turn_off`, `async_set_temperature`, `async_set_fan_mode` keep recording `self.calls` and then call `self._apply(hvac_mode=...)` / `self._apply(target_temperature=...)` / `self._apply(fan_mode=...)`; the fan reset on mode change becomes part of the same `_apply` attrs. Add `HVACMode.AUTO` to the fake's `hvac_modes` so a foreign mode can be reported.)

- [ ] **Step 1: Write the helper sanity tests** (they fail until the helpers exist)

```python
async def test_remote_changes_state_with_a_foreign_context(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, AC)
    child.remote(mode=HVACMode.COOL, temperature=24.0, fan_mode="quiet")
    state = hass.states.get(AC)
    assert state.state == HVACMode.COOL
    assert (state.attributes["temperature"], state.attributes["fan_mode"]) == (24.0, "quiet")
    assert child.calls == []  # a remote is not a service call


async def test_held_echoes_are_delivered_on_demand_and_in_any_order(hass: HomeAssistant) -> None:
    child = await common.add_fake_climate(hass, AC)
    child.hold_echoes()
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": AC, "hvac_mode": "cool"}, blocking=True
    )
    await hass.services.async_call("climate", "turn_off", {"entity_id": AC}, blocking=True)
    assert hass.states.get(AC).state == HVACMode.OFF  # nothing delivered yet
    child.flush_echoes([1, 0])
    assert hass.states.get(AC).state == HVACMode.COOL  # last delivered
```

Run: `./scripts/docker-test tests/features/test_climate_follow_device_changes.py -v`. Expected FAIL (`AttributeError: ... 'remote'`), then implement the helpers, PASS.

- [ ] **Step 2: Commit**

```bash
git add -A
git commit -m "Test support for external device changes (fake child remote and held echoes)

Refs #281"
```

---

## Task 1: Option key and validation (rows J1, J2, J3)

**Files:**
- Modify: `const.py`, `climate_roles.py`, `managers/feature_manager.py`, `climate.py` (`PLATFORM_SCHEMA`)
- Test: `tests/unit/test_climate_roles.py`

- [ ] **Step 1: Write the failing tests**

```python
from custom_components.dual_smart_thermostat.climate import PLATFORM_SCHEMA
from custom_components.dual_smart_thermostat.climate_roles import (
    climate_control_keys,
    drop_inapplicable,
)


def _yaml(**extra):
    return {"platform": "dual_smart_thermostat", "name": "t", "target_sensor": "sensor.t", **extra}


def test_follow_option_defaults_to_on() -> None:
    cfg = PLATFORM_SCHEMA(_yaml(heater="switch.h", cooler="climate.ac"))
    assert "follow_device_changes" not in cfg  # default is applied by the FeatureManager
    from custom_components.dual_smart_thermostat.managers.feature_manager import FeatureManager

    assert FeatureManager(hass=None, config=cfg, environment=None).follow_device_changes is True


def test_follow_option_needs_a_climate_role() -> None:
    with pytest.raises(vol.Invalid, match="follow_device_changes"):
        PLATFORM_SCHEMA(_yaml(heater="switch.h", follow_device_changes=False))
    assert PLATFORM_SCHEMA(_yaml(heater="climate.ac", follow_device_changes=False))[
        "follow_device_changes"
    ] is False


def test_follow_option_is_offered_for_any_climate_role() -> None:
    assert "follow_device_changes" in climate_control_keys({"fan": "climate.ac"})
    assert "follow_device_changes" in climate_control_keys({"dryer": "climate.ac"})
    assert "follow_device_changes" not in climate_control_keys({"heater": "switch.h"})
    kept = drop_inapplicable({"heater": "switch.h", "follow_device_changes": False})
    assert "follow_device_changes" not in kept
```

(Construct `FeatureManager` the way `tests/unit` or `tests/managers` already do; the assertion is on the property.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/unit/test_climate_roles.py -k follow -v
```

Expected: FAIL (`extra keys not allowed`).

- [ ] **Step 3: Implement**

`const.py`: `CONF_FOLLOW_DEVICE_CHANGES = "follow_device_changes"`, `DEFAULT_FOLLOW_DEVICE_CHANGES = True`.

`climate_roles.py`: add the key to `CLIMATE_OPTION_KEYS`; in `climate_control_keys` return it for any climate role:

```python
    follow = [CONF_FOLLOW_DEVICE_CHANGES] if has_climate_role(config) else []
    return style + follow + applicable_offset_keys(config)
```

and in `validate_climate_roles`: `if CONF_FOLLOW_DEVICE_CHANGES in config and not has_role: raise vol.Invalid("follow_device_changes needs heater, cooler, fan or dryer to be a climate entity")`.

`climate.py` `PLATFORM_SCHEMA`: `vol.Optional(CONF_FOLLOW_DEVICE_CHANGES): cv.boolean`. `FeatureManager`: `self._follow_device_changes = bool(config.get(CONF_FOLLOW_DEVICE_CHANGES, DEFAULT_FOLLOW_DEVICE_CHANGES))` and a read-only `follow_device_changes` property.

- [ ] **Step 4: Run to verify pass, commit**

```bash
./scripts/docker-test tests/unit -v
git add -A && git commit -m "follow_device_changes option: key, validation, FeatureManager

Refs #281"
```

---

## Task 2: Flows, translations, dependency tracking (rows J4 to J8)

**Files:**
- Modify: `schemas.py` (`get_climate_control_schema`), `translations/en.json` (+ locales per `test_translations.py`), `tools/config_validator.py`, `tools/focused_config_dependencies.py` and `.json`, `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md`
- Test: `tests/config_flow/test_heater_cooler_flow.py`, `test_options_flow.py`, `test_reconfigure_flow_e2e_heater_cooler.py`, `test_translations.py`

- [ ] **Step 1: Write the failing tests**

`test_heater_cooler_flow.py` (class `TestClimateRolesInHeaterCoolerFlow`):

```python
    async def test_climate_control_step_offers_the_follow_option(self, mock_hass):
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        result = await flow.async_step_heater_cooler(
            {CONF_NAME: "T", CONF_SENSOR: "sensor.t", CONF_HEATER: "switch.h",
             CONF_COOLER: "climate.ac", CONF_HEAT_COOL_MODE: False}
        )
        keys = {str(k): k for k in result["data_schema"].schema}
        assert CONF_FOLLOW_DEVICE_CHANGES in keys
        assert keys[CONF_FOLLOW_DEVICE_CHANGES].default() is True

        await flow.async_step_climate_control(
            {CONF_CONTROL_STYLE: "on_off", CONF_FOLLOW_DEVICE_CHANGES: False}
        )
        assert flow.collected_config[CONF_FOLLOW_DEVICE_CHANGES] is False  # False is kept
```

`test_options_flow.py`:

```python
async def test_follow_option_persists_to_the_options_flow(mock_hass, climate_cooler_config_entry):
    climate_cooler_config_entry.data = {
        **climate_cooler_config_entry.data, CONF_FOLLOW_DEVICE_CHANGES: False
    }
    flow = OptionsFlowHandler(climate_cooler_config_entry)
    flow.hass = mock_hass
    result = await flow.async_step_init({})
    defaults = {str(k): k.default() for k in result["data_schema"].schema}
    assert defaults[CONF_FOLLOW_DEVICE_CHANGES] is False

    await flow.async_step_climate_control_options({CONF_CONTROL_STYLE: "on_off"})
    assert flow.collected_config.get(CONF_FOLLOW_DEVICE_CHANGES, False) is False
```

`test_reconfigure_flow_e2e_heater_cooler.py`: extend `test_reconfigure_from_climate_to_switches_drops_climate_keys` data with `"follow_device_changes": False` and assert `"follow_device_changes" not in updated.data` (row J6).

`test_translations.py`: add `follow_device_changes` to the `data` and `data_description` key sets asserted for `climate_control` and `climate_control_options` (row J7).

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/config_flow -k "follow or climate_control or drops_climate_keys" -v
```

Expected: FAIL.

- [ ] **Step 3: Implement**

`get_climate_control_schema`: add, after `control_style`:

```python
    if CONF_FOLLOW_DEVICE_CHANGES in keys:
        schema[
            vol.Optional(
                CONF_FOLLOW_DEVICE_CHANGES,
                default=config.get(CONF_FOLLOW_DEVICE_CHANGES, DEFAULT_FOLLOW_DEVICE_CHANGES),
            )
        ] = selector.BooleanSelector()
```

(`keys = climate_control_keys(config)` is already the source of which fields show; the step handlers and `drop_inapplicable` need no change.) Translations (`en.json`, `config.step.climate_control` and `options.step.climate_control_options`):

```json
"follow_device_changes": "Follow changes made on the device",
...
"follow_device_changes": "When you change the device with its remote or app, this thermostat adopts that as the new setting (mode, target, fan speed, off). A mode this thermostat has no role for turns it off and leaves the device alone. Turn off to keep the thermostat in charge: it then puts the device back on its next control run. Devices that report an assumed state are never followed."
```

Dependency tracking: in `tools/config_validator.py` add `follow_device_changes` to `climate_role_parameters` (validated like `control_style`); add it to `focused_config_dependencies.py` / `.json` and `docs/config/CRITICAL_CONFIG_DEPENDENCIES.md` with the example `heater: climate.ac -> follow_device_changes: false`. Verify (row J8):

```bash
python tools/config_validator.py /tmp/follow_bad.yaml    # switch heater + follow_device_changes: false -> error
python tools/config_validator.py /tmp/follow_good.yaml   # climate heater -> valid
```

- [ ] **Step 4: Run to verify pass, commit**

```bash
./scripts/docker-test tests/config_flow tests/unit -v
git add -A && git commit -m "follow_device_changes in the climate flows, translations and dependency tracking

Refs #281"
```

---

## Task 3: Recognising our own traffic (rows C1, C2, C3, C4, C5, C6, H3)

**Files:**
- Modify: `hvac_device/entity_port.py` (`ClimateChild`)
- Test: `tests/features/test_climate_follow_device_changes.py`

These are unit-level tests on `ClimateChild.classify`, driven through real ports and the fake child, before any adoption exists.

- [ ] **Step 1: Write the failing tests**

```python
from custom_components.dual_smart_thermostat.hvac_device.entity_port import peek_climate_child


def _changes(hass, hass_events):
    """Run classify over a list of state_changed events captured in `hass_events`."""
    child = peek_climate_child(hass, AC)
    return [child.classify(e.data["old_state"], e.data["new_state"], e.context) for e in hass_events]


@pytest.fixture
def events(hass):
    captured = []
    hass.bus.async_listen("state_changed", lambda e: captured.append(e) if e.data["entity_id"] == AC else None)
    return captured


async def test_own_command_echo_is_not_adopted(hass, freezer, events):  # C1
    child = await _start(hass, freezer, HVACMode.OFF)
    hass.states.async_set(SENSOR, 18.0)  # demand: DST turns the AC on
    await hass.async_block_till_done()
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert not any(_changes(hass, events))


async def test_echo_without_a_dst_context_is_not_adopted(hass, freezer, events):  # C2
    child = await _start(hass, freezer, HVACMode.OFF)
    child.hold_echoes()
    hass.states.async_set(SENSOR, 18.0)
    await hass.async_block_till_done()
    events.clear()
    child.flush_echoes(context="foreign")  # polled integration: right value, unknown context
    assert not any(_changes(hass, events))


async def test_out_of_order_echoes_are_not_adopted(hass, freezer, events):  # C3
    child = await _start(hass, freezer, HVACMode.OFF)
    child.hold_echoes()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # commands heat
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")   # then off
    events.clear()
    child.flush_echoes([1, 0], context="foreign")  # off lands first, the older heat last
    assert not any(_changes(hass, events))


async def test_split_mode_and_target_echo_is_not_adopted(hass, freezer, events):  # C4
    child = await _start(hass, freezer, HVACMode.OFF)
    child.hold_echoes()
    hass.states.async_set(SENSOR, 18.0)
    await hass.async_block_till_done()
    events.clear()
    child.flush_echoes(context="foreign")  # mode event, then target event
    assert len(events) == 2
    assert not any(_changes(hass, events))


async def test_attribute_noise_is_ignored(hass, freezer, events):  # C5
    child = await _start(hass, freezer)
    events.clear()
    child.set_current_temperature(23.1)
    child.remote(hvac_action="heating")
    assert not any(_changes(hass, events))


async def test_an_old_echo_after_the_window_is_external(hass, freezer, events):  # C6
    child = await _start(hass, freezer, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    freezer.tick(timedelta(seconds=40))
    events.clear()
    child.remote(mode=HVACMode.COOL)  # same value as a 40 s old command
    assert any(_changes(hass, events))  # documented boundary: now indistinguishable from the remote


async def test_classify_ignores_an_assumed_flag_on_either_side(hass):  # H3
    child_entity = await common.add_fake_climate(hass, AC)
    from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimateChild

    child = ClimateChild(hass, AC)
    off = State(AC, "off", {"assumed_state": True})
    cool = State(AC, "cool", {})
    assert not child.classify(off, cool, Context())
    assert not child.classify(cool, State(AC, "off", {"assumed_state": True}), Context())
    assert child_entity is not None
```

(`remote(hvac_action=...)` relies on the fake's `**extra`.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "echo or noise or window or assumed_flag" -v
```

Expected: FAIL (`AttributeError: 'ClimateChild' object has no attribute 'classify'`).

- [ ] **Step 3: Implement**

`entity_port.py`:

```python
from collections import deque
from dataclasses import dataclass
import math

FOLLOW_SETTLE = timedelta(seconds=2)
ECHO_WINDOW = timedelta(seconds=30)
_OWN_CONTEXTS = 64


@dataclass(frozen=True)
class ExternalChange:
    """Which of the child's settings changed from outside DST."""

    mode: bool = False
    target: bool = False
    fan_mode: bool = False

    def __bool__(self) -> bool:
        return self.mode or self.target or self.fan_mode
```

`ClimateChild.__init__`: `self._own_contexts: deque[str] = deque(maxlen=_OWN_CONTEXTS)`, `self._expected: dict[str, list[tuple[Any, datetime]]] = {}`, `self.held = 0`.

```python
    def _context(self, context: Context | None) -> Context:
        """The context a command is sent with; its id is remembered as ours."""
        context = context or Context()
        self._own_contexts.append(context.id)
        return context

    def _expect(self, attr: str, value: Any) -> None:
        now = dt_util.utcnow()
        entries = [e for e in self._expected.get(attr, []) if now - e[1] <= ECHO_WINDOW]
        self._expected[attr] = [*entries[-8:], (value, now)]

    def _is_expected(self, attr: str, value: Any) -> bool:
        """The latest commanded value, or anything commanded inside the window."""
        entries = self._expected.get(attr, [])
        now = dt_util.utcnow()
        for index, (expected, at) in enumerate(entries):
            latest = index == len(entries) - 1
            if (latest or now - at <= ECHO_WINDOW) and _same(expected, value):
                return True
        return False

    def classify(
        self, old: State | None, new: State | None, context: Context | None
    ) -> ExternalChange:
        """What changed from outside DST between two states of the child."""
        if is_unavailable(old) or is_unavailable(new):
            return ExternalChange()  # reconnects and first sight adopt nothing
        if old.attributes.get(ATTR_ASSUMED_STATE) or new.attributes.get(ATTR_ASSUMED_STATE):
            return ExternalChange()  # an assumed child reports DST's own record
        if context is not None and context.id in self._own_contexts:
            return ExternalChange()

        def changed(attr, before, after):
            return after is not None and not _same(before, after) and not self._is_expected(attr, after)

        return ExternalChange(
            mode=changed("mode", old.state, new.state),
            target=changed("target", old.attributes.get(ATTR_TEMPERATURE), new.attributes.get(ATTR_TEMPERATURE)),
            fan_mode=changed("fan_mode", old.attributes.get(ATTR_FAN_MODE), new.attributes.get(ATTR_FAN_MODE)),
        )
```

`_same(a, b)`: floats compared with `math.isclose(..., abs_tol=1e-6)`, everything else `==`. `_command`: before the service call, `context = self._context(context)`, and after `_record`: `for attr, key in (("target", ATTR_TEMPERATURE),) : if key in data: self._expect(attr, data[key])`; `if mode is not None: self._expect("mode", mode)`; `async_set_fan_mode` does `context = self._context(context)` and `self._expect("fan_mode", fan_mode)` and passes the context to its service call.

- [ ] **Step 4: Run to verify pass, commit**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py tests/features/test_climate_backed_devices.py -v
git add -A && git commit -m "ClimateChild recognises its own traffic: contexts, expected values, classify

Refs #281"
```

---

## Task 4: The hold (rows K1 and the guard half of A7, A8)

**Files:**
- Modify: `hvac_device/entity_port.py`
- Test: `tests/features/test_climate_follow_device_changes.py`

- [ ] **Step 1: Write the failing test (unit)**

```python
async def test_a_held_child_receives_no_command(hass):
    child_entity = await common.add_fake_climate(hass, AC)
    from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimateChild

    child = ClimateChild(hass, AC)
    child.held += 1
    assert await child.async_set_mode("cool", None) is False
    await child.async_push_target(23.0, None)
    await child.async_set_fan_mode("quiet", None)
    await child.async_turn_off(None)
    assert child_entity.calls == []

    child.held -= 1
    assert await child.async_set_mode("cool", None) is True
    assert [c[0] for c in child_entity.calls] == ["set_hvac_mode"]
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k held_child -v
```

Expected: FAIL (the first assertion: a command was sent).

- [ ] **Step 3: Implement**

The single choke point, at the top of `_command` and of `async_set_fan_mode` (the only two places a command leaves the child):

```python
        if self.held:
            _LOGGER.debug("%s is held while an external change settles; not sending", self.entity_id)
            return False
```

(`async_set_fan_mode` returns `None`; simply `return`.) No port, device or controller changes: they all reach the child through these two methods.

- [ ] **Step 4: Run to verify pass, commit**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -v
git add -A && git commit -m "ClimateChild hold: one choke point silences DST commands

Refs #281"
```

---

## Task 5: Adoption (rows A1 to A6, B1 to B7, K1, H2)

**Files:**
- Modify: `climate.py`, `hvac_device/entity_port.py` (helpers `devices()`), `hvac_device/fan_speed.py` (nothing expected)
- Test: `tests/features/test_climate_follow_device_changes.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_remote_mode_is_adopted(hass, freezer):  # A1 (and H2: this fake carries no assumed flag)
    child = await _start(hass, freezer, HVACMode.HEAT)
    assert "assumed_state" not in hass.states.get(AC).attributes or not hass.states.get(AC).attributes["assumed_state"]
    child.remote(mode=HVACMode.COOL)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert child.calls == []


async def test_remote_target_is_adopted(hass, freezer):  # A2
    child = await _start(hass, freezer, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 24.0
    assert child.calls == []


async def test_remote_target_minus_heater_offset(hass, freezer):  # A3
    child = await _start(hass, freezer, HVACMode.HEAT, heater_setpoint_offset=3)
    child.remote(temperature=25.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert child.calls == []


async def test_remote_target_minus_cooler_offset(hass, freezer):  # A4
    child = await _start(hass, freezer, HVACMode.COOL, target=24, cooler_setpoint_offset=-5)
    child.remote(temperature=19.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 24.0
    assert child.calls == []


async def test_remote_fan_mode_is_adopted(hass, freezer):  # A5
    child = await _start(hass, freezer, HVACMode.HEAT)
    assert _dst(hass).attributes["fan_mode"] == "auto"  # the stale display
    child.remote(fan_mode="quiet")
    await _settle(hass, freezer)
    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert child.calls == []


async def test_remote_off_is_adopted(hass, freezer):  # A6
    child = await _start(hass, freezer, HVACMode.HEAT)
    child.remote(mode=HVACMode.OFF)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.OFF
    assert child.calls == []


async def test_foreign_mode_turns_dst_off_and_stays_hands_off(hass, freezer):  # B1
    child = await _start(hass, freezer, HVACMode.HEAT, dryer=None, humidity_sensor=None,
                         target_humidity=None, fan=None, fan_mode=None)
    child.remote(mode=HVACMode.AUTO)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.OFF
    for room in (21.0, 25.0, 15.0):
        await _tick(hass, room)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.AUTO  # hands-off: the remote's choice stays


async def test_shared_child_adopts_each_role_mode_without_a_loop(hass, freezer):  # B2
    child = await _start(hass, freezer, HVACMode.HEAT)
    child.remote(mode=HVACMode.DRY)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.DRY
    child.remote(mode=HVACMode.FAN_ONLY)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.FAN_ONLY
    for room in (22.1, 22.0, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert child.calls == []  # one change, one adoption, no echo, no loop


async def test_heat_pump_owns_only_its_current_direction(hass, freezer):  # B3
    hass.states.async_set("binary_sensor.hp_cooling", "off")
    child = await _start(
        hass, freezer, HVACMode.HEAT, heater=AC, cooler=None, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
        heat_pump_cooling="binary_sensor.hp_cooling",
    )
    child.remote(mode=HVACMode.COOL)  # the pump is heating: cool is not its mode
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.OFF
    assert child.calls == []


async def test_setpoint_style_adopts_the_target_without_commands(hass, freezer):  # B4
    child = await _start(
        hass, freezer, HVACMode.COOL, target=24, control_style="setpoint",
        cooler_setpoint_offset=-2, heater=HEATER, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
    )
    child.remote(temperature=20.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert child.calls == []


async def test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode(hass, freezer):  # B5
    hass.states.async_set("fan.test_fan", "off", {"preset_modes": ["low", "high"], "preset_mode": "low"})
    child = await _start(hass, freezer, HVACMode.HEAT, fan="fan.test_fan")
    child.remote(fan_mode="strong")
    await _settle(hass, freezer)
    assert _dst(hass).attributes["fan_modes"] == ["low", "high"]
    assert _dst(hass).attributes["fan_mode"] == "low"
    assert child.calls == []


async def test_adopted_target_outside_the_dst_range_is_clamped_and_pushed_once(hass, freezer):  # B6
    child = await _start(hass, freezer, HVACMode.HEAT, max_temp=26)
    child.remote(temperature=29.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 26.0
    assert child.calls == [("set_temperature", {"temperature": 26.0})]


async def test_mixed_rig_adopting_cool_stops_the_switch_heater_once(hass, freezer):  # B7
    heater_calls = setup_switch(hass, True, HEATER)
    child = await _start(hass, freezer, HVACMode.HEAT, heater=HEATER, cooler=AC,
                         fan=None, dryer=None, humidity_sensor=None, target_humidity=None, fan_mode=None)
    heater_calls.clear()
    child.remote(mode=HVACMode.COOL)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert child.calls == []
    assert [c.service for c in heater_calls] == ["turn_off"]


async def test_the_child_is_held_while_an_external_change_settles(hass, freezer):  # K1
    child = await _start(hass, freezer, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    await _tick(hass, 22.1)  # DST control runs inside the settle window
    assert child.calls == []  # DST's stale 22 must not clobber the remote's 24
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 24.0
```

(`from tests import setup_switch` for B7.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "adopted or foreign or shared_child or heat_pump or setpoint_style or separate_fan or clamped or mixed_rig or held_while" -v
```

Expected: FAIL (DST stays on its own setting; K1 sees `set_temperature(22)`).

- [ ] **Step 3: Implement**

`entity_port.py`, on `ClimateChild`:

```python
    def devices(self) -> list[Any]:
        """The devices (roles) living on this child."""
        return [port.device for port in self.ports]

    def device_for(self, mode: str) -> Any | None:
        """The role whose mode this is, if any role owns it."""
        return next((d for d in self.devices() if mode in d.role_modes()), None)
```

`climate.py` (`DualSmartThermostat`):

```python
from .climate_roles import is_climate_entity
from .hvac_device.entity_port import FOLLOW_SETTLE, peek_climate_child

        # __init__
        self._follow_cancel: Callable[[], None] | None = None
        self._follow_child: ClimateChild | None = None
        self._adopting = False
        self._startup_done = False
```

`_async_startup` ends with `self._startup_done = True`. In `_async_switch_changed_event`, after the existing body (before `_async_switch_changed`):

```python
        self._async_follow(event)
```

```python
    @callback
    def _async_follow(self, event: Event[EventStateChangedData]) -> None:
        """An external change on a climate child opens (or extends) the follow window."""
        entity_id = event.data["entity_id"]
        if (
            not self.features.follow_device_changes
            or not self._startup_done
            or not is_climate_entity(entity_id)
        ):
            return
        child = peek_climate_child(self.hass, entity_id)
        if child is None or not child.classify(
            event.data["old_state"], event.data["new_state"], event.context
        ):
            return
        if self._follow_cancel is None:
            child.held += 1  # nothing is sent to the device until its change is adopted
            self._follow_child = child
        else:
            self._follow_cancel()
        self._follow_cancel = async_call_later(self.hass, FOLLOW_SETTLE, self._async_adopt)

    def _cancel_follow(self) -> None:
        """A DST user action beats a pending adoption (latest intent wins)."""
        if self._follow_cancel is not None:
            self._follow_cancel()
            self._follow_cancel = None
            self._follow_child.held -= 1
            self._follow_child = None

    async def _async_adopt(self, _now=None) -> None:
        """Make the child's current settings DST's own, then carry on controlling."""
        child, self._follow_cancel, self._follow_child = self._follow_child, None, None
        state = child.state
        self._adopting = True
        try:
            if state is not None and child.available:
                await self._async_adopt_state(child, state)
        finally:
            self._adopting = False
            child.held -= 1
        if self._sensor_stalled:
            # Safety first: the emergency stop stands; the intent is recorded.
            await self.hvac_device.async_turn_off()
        else:
            await self._async_control_climate(force=True)
        self.async_write_ha_state()

    async def _async_adopt_state(self, child, state: State) -> None:
        speed = self.features.fan_speed
        fan_mode = state.attributes.get(ATTR_FAN_MODE)
        if speed is not None and speed.entity_id == child.entity_id and fan_mode in speed.fan_modes:
            await self.async_set_fan_mode(fan_mode)  # held child: records, sends nothing

        mode = state.state
        role = child.device_for(mode)
        if mode == HVACMode.OFF or role is None or mode not in self.hvac_modes:
            # off, or a mode no role owns: Off, and hands-off (the held child gets nothing)
            await self.async_set_hvac_mode(HVACMode.OFF)
            return
        await self.async_set_hvac_mode(HVACMode(mode))
        target = state.attributes.get(ATTR_TEMPERATURE)
        if target is not None:  # after the mode: a mode change reloads targets from presets
            await self.async_set_temperature(
                temperature=round(target - role.setpoint_offset(), 4)
            )
```

Cancel on user action: first line of `async_set_hvac_mode`, `async_set_temperature`, `async_set_fan_mode` and `async_set_preset_mode`: `if not self._adopting: self._cancel_follow()`. `async_will_remove_from_hass`: `self._cancel_follow()`.

Note on the foreign-mode / off branch: `async_set_hvac_mode(OFF)` runs `async_stop` on a held child, which sends nothing (choke point); the following forced control run is skipped for Off by the existing "Climate is off" guard. In `async_set_fan_mode` the held child records nothing on the wire and `FanSpeedControl` keeps the new `current_fan_mode`.

- [ ] **Step 4: Run to verify pass, then the suite**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Follow device changes: adopt external mode, target, fan and off

Refs #281"
```

---

## Task 6: Interleavings and DST sources (rows A7 to A15)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py` (`_cancel_follow` placement), `entity_port.py`

- [ ] **Step 1: Write the tests**

```python
async def test_dst_ui_command_is_not_adopted_back(hass, freezer):  # A7 (guard)
    child = await _start(hass, freezer, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await hass.async_block_till_done()
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_dst_ui_target_reaches_the_child_and_stays(hass, freezer):  # A8 (guard)
    child = await _start(hass, freezer, HVACMode.HEAT)
    await common.async_set_temperature(hass, 23, "climate.test")
    await _settle(hass, freezer)
    assert child.calls == [("set_temperature", {"temperature": 23.0})]
    assert _dst(hass).attributes["temperature"] == 23.0


async def test_automation_service_call_on_the_child_is_adopted(hass, freezer):  # A9
    child = await _start(hass, freezer, HVACMode.HEAT)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": AC, "hvac_mode": "cool"},
        blocking=True, context=Context(),  # an automation, not DST
    )
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]  # the automation's own call only


async def test_automation_service_call_on_dst_is_a_dst_command(hass, freezer):  # A9b (guard)
    child = await _start(hass, freezer, HVACMode.OFF)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": "climate.test", "hvac_mode": "heat"},
        blocking=True, context=Context(),
    )
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_preset_change_is_pushed_and_not_adopted_back(hass, freezer):  # A10
    child = await _start(hass, freezer, HVACMode.HEAT, away={"temperature": 17})
    await common.async_set_preset_mode(hass, "away", "climate.test")
    await _settle(hass, freezer)
    assert child.calls == [("set_temperature", {"temperature": 17.0})]
    assert _dst(hass).attributes["preset_mode"] == "away"
    assert _dst(hass).attributes["temperature"] == 17.0


async def test_remote_then_dst_in_the_same_second_dst_wins(hass, freezer):  # A11
    child = await _start(hass, freezer, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)  # opens the follow window
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")  # DST acts inside it
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.OFF
    assert child.calls == [("turn_off", {})]


async def test_dst_then_remote_in_the_same_second_remote_wins(hass, freezer):  # A12
    child = await _start(hass, freezer, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    child.remote(mode=HVACMode.COOL)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]  # DST's own only


async def test_remote_mode_then_target_as_two_events(hass, freezer):  # A13
    child = await _start(hass, freezer, HVACMode.HEAT, target=22)
    child.remote(mode=HVACMode.COOL)
    freezer.tick(timedelta(seconds=1))
    child.remote(temperature=24.0)
    await _settle(hass, freezer)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.COOL, 24.0)
    assert child.calls == []


async def test_remote_target_then_mode_as_two_events(hass, freezer):  # A14
    child = await _start(hass, freezer, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    freezer.tick(timedelta(seconds=1))
    child.remote(mode=HVACMode.COOL)
    await _settle(hass, freezer)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.COOL, 24.0)
    assert child.calls == []


async def test_a_second_remote_change_inside_the_window_wins(hass, freezer):  # A15
    child = await _start(hass, freezer, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    freezer.tick(timedelta(seconds=1))
    child.remote(mode=HVACMode.FAN_ONLY)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.FAN_ONLY
    assert child.calls == []
```

For A13/A14 the second `remote()` must land after the first timer was re-armed: `_async_follow` cancels and re-creates the timer on each external event (task 5), so the window closes 2 s after the *last* event; `_settle` ticks 3 s.

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "dst_ui or automation_service or preset_change or same_second or two_events or second_remote" -v
```

Expected: guards (A7, A8, A9b, A10) PASS; A9 PASS; A11 FAILS if the cancel on user action is missing or the user action reads a held child (fix: `_cancel_follow()` must run before the setter's own logic and release the hold); the others PASS with task 5. Fix failures in `climate.py`, not in the tests.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Follow device changes: interleavings and DST sources covered

Refs #281"
```

---

## Task 7: Safety precedence (rows D1 to D4)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py`

- [ ] **Step 1: Write the tests**

```python
async def test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing(hass, freezer):  # D1
    hass.states.async_set(WINDOW, "off")
    child = await _start(hass, freezer, HVACMode.HEAT, openings=[WINDOW])
    hass.states.async_set(WINDOW, "on")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF  # paused by the opening
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=24.0)  # the remote switches it back on
    await _settle(hass, freezer)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.HEAT, 24.0)
    assert hass.states.get(AC).state == HVACMode.OFF  # the window still wins
    assert [c[0] for c in child.calls] == ["turn_off"]

    child.calls.clear()
    hass.states.async_set(WINDOW, "off")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 24.0}) in child.calls


async def test_floor_limit_wins_over_an_adopted_heat(hass, freezer):  # D2
    hass.states.async_set("sensor.floor", 30.0)
    child = await _start(
        hass, freezer, HVACMode.OFF, heater=AC, cooler=None, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
        floor_sensor="sensor.floor", max_floor_temp=28,
    )
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["turn_off"]


async def test_stale_sensor_stops_the_child_and_keeps_the_intent(hass, freezer):  # D3
    child = await _start(hass, freezer, HVACMode.HEAT, sensor_stale_duration=timedelta(minutes=2))
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF  # emergency stop
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=23.0)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["turn_off"]

    child.calls.clear()
    await _tick(hass, 18.0)  # the sensor recovers
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_min_cycle_still_applies_after_an_adoption(hass, freezer):  # D4
    child = await _start(hass, freezer, HVACMode.OFF, min_cycle_duration=timedelta(minutes=5))
    await _tick(hass, 26.0)  # hot room
    child.remote(mode=HVACMode.HEAT, temperature=22.0)  # goal already reached
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    assert child.calls == []  # not stopped inside the minimum cycle

    freezer.tick(timedelta(minutes=6))
    await _tick(hass, 26.1)
    assert [c[0] for c in child.calls] == ["turn_off"]
```

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "window or floor_limit or stale_sensor or min_cycle_still" -v
```

Expected: PASS when task 5 is right (the forced control run applies the existing openings, floor and min-cycle logic, and the stalled branch stops the child). D3 is the likeliest failure: if the child is not stopped, check `_async_adopt` takes the `_sensor_stalled` branch; if it was not stalled because the emergency-stop flag clears on recovery only, fix there. Fix in `climate.py`.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Follow device changes: openings, floor limits, stale sensor and min cycle still win

Refs #281"
```

---

## Task 8: Off, and `follow_device_changes: false` (rows E1 to E4, F1, F2)

**Files:**
- Modify: `hvac_device/entity_port.py` (`ClimatePort.async_stop`)
- Test: `tests/features/test_climate_follow_device_changes.py`

- [ ] **Step 1: Write the tests**

```python
async def test_transition_to_off_sends_one_unscoped_off(hass, freezer):  # E1
    child = await _start(
        hass, freezer, HVACMode.HEAT, follow_device_changes=False,
        fan=None, dryer=None, humidity_sensor=None, target_humidity=None, fan_mode=None,
    )
    child.remote(mode=HVACMode.AUTO)  # a mode no role owns; not followed
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()
    assert child.calls == [("turn_off", {})]
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_keep_alive_while_off_sends_nothing_to_climate_children(hass, freezer):  # E2
    child = await _start(hass, freezer, HVACMode.OFF, follow_device_changes=False,
                         keep_alive=timedelta(minutes=1))
    child.remote(mode=HVACMode.HEAT)
    for minutes in (2, 4, 6):
        common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minutes))
        await hass.async_block_till_done()
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_remote_use_while_off_is_adopted_when_following(hass, freezer):  # E3
    child = await _start(hass, freezer, HVACMode.OFF, target=22)
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _settle(hass, freezer)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.HEAT, 22.0)
    assert child.calls == []


async def test_remote_use_while_off_is_ignored_and_never_fought_when_not_following(hass, freezer):  # E4
    child = await _start(hass, freezer, HVACMode.OFF, follow_device_changes=False,
                         keep_alive=timedelta(minutes=1))
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _settle(hass, freezer)
    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=3))
    await hass.async_block_till_done()
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert child.calls == []


async def test_not_following_reasserts_the_mode_on_the_next_tick(hass, freezer):  # F1
    child = await _start(hass, freezer, HVACMode.COOL, follow_device_changes=False)
    child.remote(mode=HVACMode.HEAT)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL  # not adopted
    await _tick(hass, 26.0)  # hot room: DST wants cooling
    assert [c for c in child.calls if c[0] == "set_hvac_mode"] == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.COOL})
    ]


async def test_not_following_reasserts_the_target_on_the_next_run(hass, freezer):  # F2
    child = await _start(hass, freezer, HVACMode.HEAT, target=22, follow_device_changes=False)
    child.remote(temperature=25.0)
    await _settle(hass, freezer)
    assert _dst(hass).attributes["temperature"] == 22.0
    await _tick(hass, 22.1)
    assert child.calls == [("set_temperature", {"temperature": 22.0})]
```

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "off or not_following" -v
```

Expected: E2 FAILS (the keep-alive tick turns the remote-started child off: the current `ClimatePort.async_stop` passes `keep_alive` to `needs_off`). E1, E3, E4 (after E2's fix), F1, F2 are guards or pass with task 5.

- [ ] **Step 3: Implement**

`ClimatePort.async_stop`: a keep-alive tick sends nothing to a climate child (a switch keeps its behaviour). Off is enforced once, at the transition; with follow on a remote use is adopted, with follow off it is left alone:

```python
    async def async_stop(self, context, *, keep_alive: bool = False) -> None:
        if keep_alive:
            return  # nothing to hold: Off was enforced at the transition
        if self._child.wanted_on:
            await self.async_turn_off(context)
        elif self._child.needs_off(False):
            await self._child.async_turn_off(context)
```

(`ClimateChild.needs_off` loses its `resend` parameter if no other caller uses it; delete the assumed-child tick branch with it. Update the earlier phase tests that pinned the assumed resend, if any, to the new rule.)

- [ ] **Step 4: Run to verify pass, then the suite**

```bash
./scripts/docker-test tests/features -v
./scripts/docker-test
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Off sends one unscoped off; keep-alive while Off leaves climate children alone

Refs #281"
```

---

## Task 9: Restart, assumed state, automation interference (rows G1 to G3, H1, I1 to I3)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py`

- [ ] **Step 1: Write the tests**

```python
async def test_restored_state_adopts_nothing(hass, freezer):  # G1
    common.mock_restore_cache(
        hass, [State("climate.test", "cool", {"temperature": 24, "fan_mode": "auto"})]
    )
    hass.states.async_set(SENSOR, 24.0)
    hass.states.async_set("sensor.hum", 50.0)
    child = await common.add_fake_climate(hass, AC, HVACMode.HEAT)  # up before DST, other settings
    child._attr_target_temperature = 20.0
    child.async_write_ha_state()
    await _setup(hass, **ALL_ROLES)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] == 24.0


async def test_reconnect_adopts_nothing(hass, freezer):  # G2
    child = await _start(hass, freezer, HVACMode.HEAT)
    hass.states.async_set(AC, "unavailable")
    await hass.async_block_till_done()
    child.remote(mode=HVACMode.COOL)  # comes back in another mode
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT


async def test_a_child_appearing_late_adopts_nothing(hass, freezer):  # G3
    hass.states.async_set(SENSOR, 22.0)
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(hass, **ALL_ROLES, initial_hvac_mode=HVACMode.HEAT)
    await common.add_fake_climate(hass, AC, HVACMode.COOL)  # first sight is not an event
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT


async def test_assumed_child_adopts_nothing(hass, freezer):  # H1
    child = await _start(hass, freezer, HVACMode.COOL, child_kwargs={"assumed": True})
    child.remote(mode=HVACMode.HEAT, temperature=28.0)  # the integration reports it anyway
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] != 28.0


def _automation_forcing(hass, **forced):
    """An external automation: whenever the child leaves the forced value, force it back."""
    child = None

    @callback
    def _on_change(event):
        new = event.data["new_state"]
        if new is None or (event.context is not None and event.context.id == "automation"):
            return
        for attr, value in forced.items():
            current = new.state if attr == "mode" else new.attributes.get(attr)
            if current != value:
                hass.async_create_task(_force(attr, value))

    async def _force(attr, value):
        child_entity = hass.data["climate"].get_entity(AC)
        child_entity.remote(**{"mode" if attr == "mode" else attr: value})

    async_track_state_change_event(hass, [AC], _on_change)


async def test_an_automation_forcing_the_fan_mode_is_followed_without_a_storm(hass, freezer):  # I1
    child = await _start(hass, freezer, HVACMode.OFF, child_kwargs={"resets_fan_on_mode_change": True})
    await hass.services.async_call(
        "climate", "set_fan_mode", {"entity_id": "climate.test", "fan_mode": "quiet"}, blocking=True
    )
    _automation_forcing(hass, fan_mode="strong")
    child.remote(fan_mode="strong")  # the automation fires once
    await _settle(hass, freezer)
    assert _dst(hass).attributes["fan_mode"] == "strong"

    child.calls.clear()
    for room in (18.0, 22.0, 18.0, 22.0, 18.0):  # DST cycles the AC; the device resets its fan
        await _tick(hass, room)
        await _settle(hass, freezer)
    assert _dst(hass).attributes["fan_mode"] == "strong"
    fan_commands = [c for c in child.calls if c[0] == "set_fan_mode"]
    assert len(fan_commands) <= len([c for c in child.calls if c[0] == "set_hvac_mode"])

    child.calls.clear()
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):  # idle: no storm
        await _tick(hass, room)
    assert child.calls == []


async def test_an_automation_forcing_the_mode_is_followed_without_a_loop(hass, freezer):  # I2
    child = await _start(hass, freezer, HVACMode.COOL)
    _automation_forcing(hass, mode=HVACMode.HEAT)
    child.remote(mode=HVACMode.HEAT)
    await _settle(hass, freezer)
    assert _dst(hass).state == HVACMode.HEAT
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert child.calls == []


async def test_not_following_an_automation_forced_fan_does_not_storm(hass, freezer):  # I3
    child = await _start(
        hass, freezer, HVACMode.HEAT, follow_device_changes=False,
        child_kwargs={"resets_fan_on_mode_change": True},
    )
    await hass.services.async_call(
        "climate", "set_fan_mode", {"entity_id": "climate.test", "fan_mode": "quiet"}, blocking=True
    )
    _automation_forcing(hass, fan_mode="strong")
    child.remote(fan_mode="strong")
    await _settle(hass, freezer)
    assert _dst(hass).attributes["fan_mode"] == "quiet"  # not adopted
    child.calls.clear()
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert [c for c in child.calls if c[0] == "set_fan_mode"] == []  # re-applied on turn on only
```

(Import `callback` from `homeassistant.core`. In `_automation_forcing`, the forced write uses `remote()`, which carries a fresh foreign context like a real automation's service call; the guard on `context.id == "automation"` can be dropped, `current != value` already stops the recursion once the value matches.)

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "restored or reconnect or appearing_late or assumed or automation" -v
```

Expected: PASS with task 5 (classify refuses unavailable/None old state and assumed flags; `_startup_done` gates early events). A failing G1 means the restored-state path adopted: ensure `_async_follow` returns while `_startup_done` is false and that `classify` refuses `old_state is None`. A failing I1 (a storm) means DST re-applies a stale selection: the adoption must set `FanSpeedControl.current_fan_mode` before the next turn on (it does through `async_set_fan_mode` on the held child).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Follow device changes: restart, assumed state and automation interference covered

Refs #281"
```

---

## Task 10: Docs, P5 checklist, lint

- [ ] **Step 1: README.** Replace the sentence "A change made on the AC's own remote is re-asserted by the thermostat within seconds ..." in the climate section with: "By default the thermostat follows changes made on the device itself (remote, vendor app, an automation): the new mode, target, fan speed or off becomes the thermostat's setting; a mode the thermostat has no role for turns it off and leaves the device alone. Open windows, floor limits and a stale sensor still take precedence. Turn `follow_device_changes` off to keep the thermostat in charge: it then puts the device back on its next control run. Devices that report an assumed state (infrared) are not followed." Add `follow_device_changes` to the key table and the example file.
- [ ] **Step 2: P5.** Update `2026-10-20-climate-entity-devices-phase-5-real-device-verification.md` as listed in the coverage map below (new Task 5 steps 8 and 9, Step 5 rewritten for following).
- [ ] **Step 3:** `./scripts/docker-lint --fix && ./scripts/docker-lint`, then `./scripts/docker-test`.
- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "Docs and lint for follow_device_changes

Refs #281"
```

---

## P5 coverage map: which automated test covers which real-device case

"Logic" = proven by the automated test named (names as in the phase plans; confirm against the merged tests). "Device only" = only a real device can prove it (the physical effect, timing of the vendor integration, or behaviour of the unit itself); the checklist still runs it.

| P5 case | Automated test covering the logic | Device only |
|---|---|---|
| 1.1 Config flow | `test_climate_control_step_offers_the_follow_option`, phase 4 flow tests | the UI rendering |
| 1.2 Options flow | `test_follow_option_persists_to_the_options_flow`, phase 4 options tests | reload without errors on the instance |
| 1.3 Reconfigure | `test_follow_option_is_dropped_when_no_climate_role_remains`, `test_reconfigure_from_climate_to_switches_drops_climate_keys` | |
| 1.4 YAML | `test_follow_option_needs_a_climate_role`, phase 2 validation tests | |
| 2.1 Temperature source | `test_standalone_ac_uses_its_own_temperature` | the vendor integration really reports it |
| 2.2 Heat | `test_climate_heater_turns_on_and_off`, `test_target_change_while_engaged_is_mirrored` | the unit heats |
| 2.3 Target reached | `test_climate_heater_turns_on_and_off`, `test_climate_respects_min_cycle_duration` | compressor timing |
| 2.4 Cool | `test_climate_cooler_cycles_with_switch_heater` | the unit cools |
| 2.5 Fan only and Dry | `test_fan_and_dryer_roles_use_their_climate_mode` | the unit runs that mode |
| 2.6 Mode walk | `test_single_ac_walks_through_every_mode_one_at_a_time`, `test_shared_child_adopts_each_role_mode_without_a_loop` | |
| 2.7 Off | `test_hvac_off_stops_the_child`, `test_keep_alive_while_off_sends_nothing_to_climate_children` | the unit stops |
| 2.8 Off means off | `test_transition_to_off_sends_one_unscoped_off`, `test_foreign_mode_turns_dst_off_and_stays_hands_off` | the unit really turns off from `auto` |
| 3.1 to 3.3 Setpoint engage, no cycling, mirror | `test_setpoint_style_never_turns_the_child_off_at_target`, `test_target_change_while_engaged_is_mirrored`, `test_preset_change_is_pushed_and_not_adopted_back` | the unit regulates itself |
| 3.4 Per-role offsets | `test_setpoint_style_each_role_uses_its_own_offset`, `test_remote_target_minus_heater_offset`, `test_remote_target_minus_cooler_offset` | the unit's range and step in practice |
| 3.5 Min cycle ignored | `test_setpoint_style_ignores_min_cycle_duration` | |
| 4.1 Independence | `test_climate_cooler_cycles_with_switch_heater` | |
| 4.2 Assumed state | `test_assumed_state_child_is_not_commanded_twice`, `test_assumed_child_adopts_nothing` | the IR unit actually responds |
| 4.3 Stop | `test_climate_cooler_cycles_with_switch_heater` | the unit really stopped |
| 4.4 Opening | `test_setpoint_style_opening_pauses_and_restores_the_child`, `test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing` | |
| 4.5 Heat to cool swap | `test_mixed_rig_adopting_cool_stops_the_switch_heater_once`, `test_climate_cooler_cycles_with_switch_heater` | |
| 4.6 Keep-alive resend | `test_idle_role_keep_alive_does_not_stop_the_active_role`, `test_keep_alive_while_off_sends_nothing_to_climate_children` | an IR unit resynchronising from a resend |
| 5.1 Min cycle protection | `test_climate_respects_min_cycle_duration`, `test_min_cycle_still_applies_after_an_adoption` | actual compressor protection |
| 5.2 Device offline | `test_unavailable_child_receives_no_commands`, `test_reconnect_adopts_nothing` | |
| 5.3 Sensor loss | `test_stale_child_temperature_triggers_the_emergency_stop`, `test_stale_sensor_stops_the_child_and_keeps_the_intent` | |
| 5.4 Unsupported mode | `test_unsupported_mode_is_not_sent` | |
| 5.5 Manual override (remote) | `test_remote_mode_is_adopted`, `test_remote_target_is_adopted`, `test_remote_fan_mode_is_adopted`, `test_remote_off_is_adopted`, `test_not_following_reasserts_the_mode_on_the_next_tick` | the integration's real event timing and contexts (does a remote change arrive as a state change with a foreign context?) |
| 5.6 Restart and reload | `test_restored_state_adopts_nothing`, `test_a_child_appearing_late_adopts_nothing` | restore from the real database |
| 5.7 Self reference | `test_entity_cannot_be_its_own_device` | |
| 5.8 Automation interference (new) | `test_an_automation_forcing_the_fan_mode_is_followed_without_a_storm`, `test_an_automation_forcing_the_mode_is_followed_without_a_loop`, `test_not_following_an_automation_forced_fan_does_not_storm` | the real automation and the real unit's fan reset |
| 5.9 Follow window timing (new) | `test_remote_mode_then_target_as_two_events`, `test_remote_then_dst_in_the_same_second_dst_wins` | how long the real integration takes to report a remote change (confirm `FOLLOW_SETTLE` 2 s is enough) |
| 5b.1 to 5b.8 Fan speed | phase 3b tests (`test_cooler_only_ac_gets_fan_speed_control`, `test_fan_speed_is_reapplied_after_the_ac_resets_it`, `test_fan_speed_is_restored_after_a_restart`, `test_fan_speed_restore_waits_for_a_late_child`, `test_separate_fan_entity_owns_fan_mode_and_the_ac_is_left_alone`), `test_remote_fan_mode_is_adopted`, `test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode` | the unit runs at that speed after every start |
| 6.1 to 6.2 Switch-only regression | the whole existing suite | the valve really opens |

New P5 checklist steps (Task 5 of the P5 plan):

- [ ] **Step 5 (rewritten): Remote use.** With `follow_device_changes` on, change the mode, then the target, then the fan speed with the remote (and once with the vendor app): within about 3 seconds `DST` shows the same mode, target (minus the role's offset), and fan mode, and the log shows adoption with **no** command sent back to the device. Set `auto` on the remote: `DST` goes Off and the unit is left alone. Repeat with the option off: the thermostat puts the device back on its next control run. On the IR AC (assumed state): a remote change is not adopted and not corrected (record this).
- [ ] **Step 8: Automation interference.** With an automation that forces the AC fan to one value whenever it changes, let `DST` start and stop the AC several times: `DST` follows the automation's value, no repeating `set_fan_mode` storm in the log, no flapping.
- [ ] **Step 9: Follow window.** Operate the remote twice within a second (mode then target): one adoption, the final state wins. Note how long the vendor integration takes to report a remote change; if it can exceed 2 seconds, raise `FOLLOW_SETTLE` and say so.

## Acceptance (phase 6)

1. Every row of the scenario matrix is an automated test and passes; the guard rows pass before and after the implementation.
2. With `follow_device_changes` on, an external mode, off, target (minus the role's offset), fan mode or foreign mode on a climate child becomes the DST setting; nothing is echoed back; one change is one adoption, including on a child shared by all roles.
3. Own echoes (late, out of order, split), restored state, reconnects, late children and `assumed_state` children adopt nothing.
4. Open windows, floor limits, the stale sensor and the minimum cycle still win over an adopted setting; the intent is kept.
5. The transition to Off sends one unscoped `turn_off`; keep-alive while Off sends nothing to climate children; remote use while Off is adopted when following and left alone (never fought) when not.
6. With the option off DST re-asserts on its next control run.
7. The option is in YAML validation, the config, reconfigure and options climate steps, `climate_roles`, dependency tracking and translations; defaults to on.
