# Climate Entity Devices - Phase 6: Follow Device Changes - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The physical remote (or the vendor app, or an automation acting on the child) takes priority: an external change on a climate child becomes the user's new DST setting at once, latest intent wins, with no command echoed back. Option `follow_device_changes` (default on); off keeps DST authoritative (it re-asserts on its next control run). Every scenario of the matrix below is an automated test.

**Architecture (revised after adversarial review against HA core).** Detection is by **value**, never by context or time: a state write within 5 s of a service call carries the caller's context, and coordinator refreshes are debounced for 10 s, so neither contexts nor timers can tell DST's echo from a remote press. Each thermostat keeps, on the shared `ClimateChild` but keyed by itself, a short list per attribute (`mode`, `target`, `fan_mode`) of the values it commanded and has not yet seen reported. A child state change whose new value is in the thermostat's list is an echo (that entry is consumed); any other change of those attributes is external. An external change is adopted immediately from a full snapshot of the child through DST's own public setters, followed by one normal forced control run. No settle window, no hold, no timers: safety stops never wait. Two short, thermostat-owned flags keep it sound: `adopting` (DST's commands to the child are dropped while the setters run, so a stale DST value cannot be pushed over the remote's) and `sending` (events during one of DST's own turn-on sequences are the device's side effects, e.g. a fan reset, not the user's).

**Tech Stack:** Python 3.14, Home Assistant 2026.3.2+, pytest.

**Spec:** `docs/superpowers/specs/2026-10-20-climate-entity-devices-design.md` (section 3.6)
**Previous phases:** 1 to 5 merged (this plan is written against the current `entity_port.py` `ClimateChild` / `ClimatePort`, `fan_speed.py`, `climate_roles.py`, `climate.py`). This phase supersedes the README sentence "A change made on the AC's own remote is re-asserted by the thermostat within seconds".

**Owner decision (restart, reconnect, first sight) = (b):** nothing is adopted from first sight or a reconnect; DST re-asserts its restored setting. Events whose old state is missing or unavailable are ignored; there is no flag.

---

## Testing Environment

```bash
./scripts/docker-test <pytest-args>
./scripts/docker-lint
./scripts/docker-lint --fix
```

Do **not** call `pytest` / `black` / `isort` / `flake8` directly. Test code follows the idioms already used in `tests/features/test_climate_backed_devices.py` (`_setup`, `common.add_fake_climate`); fix an import or fixture name in the red step if reality differs, the assertions are what matter.

---

## Decided

| Item | Decision |
|---|---|
| Pending list | at most 4 values per thermostat, child and attribute; consumed only by a matching report; cleared by an adoption and when the child goes unavailable; a skipped command adds nothing; a failed command removes its entry; assumed children record nothing |
| Echo matching | only the matched entry is consumed, so echoes may arrive in any order |
| Contexts | every DST command goes out with a fresh `Context` (parent id kept for logbook attribution); the DST entity's own `_context` is never passed down; no decision reads a context |
| Concurrency | adoptions are serialised per thermostat, read the snapshot when they run, and re-run if another external event arrived meanwhile |
| Stale poll after our command (F6) | followed as the device's truth, documented, and checked in P5 step 9 (a guard would need timers) |

---

## SCENARIO TEST MATRIX

Test file: `tests/features/test_climate_follow_device_changes.py` unless the Task column says otherwise (config tests live in the existing flow and unit files). "Red" = fails before the task's implementation; "guard" = passes already and pins behaviour that adoption must not break.

Rig used unless stated: **R1**, one fake AC in all four roles (heater, cooler, fan, dryer), `on_off`, `follow_device_changes` on, room sensor equal to the target after engagement so a running device keeps running (`_start`, below). "Commands" lists what is sent to the fake child; "other" lists other devices; `none` means an empty call list. "Adoptions" are counted with the `adoptions` spy fixture.

### A. Latest command wins, per source

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| A1 | `test_remote_mode_is_adopted` | R1 Heat engaged | remote sets child `cool` | DST `cool`, one adoption | child: none |
| A2 | `test_remote_target_is_adopted` | R1 Heat engaged, target 22 | remote sets child target 24 | DST target 24 | none |
| A3 | `test_remote_target_minus_heater_offset` | R1, `heater_setpoint_offset: 3`, Heat | remote sets child target 25 | DST target 22 | none |
| A4 | `test_remote_target_minus_cooler_offset` | R1, `cooler_setpoint_offset: -5`, Cool | remote sets child target 19 | DST target 24 | none |
| A5 | `test_remote_fan_mode_is_adopted` | R1 Heat engaged, DST fan `auto` | remote sets child fan `quiet` | DST `fan_mode` attribute `quiet` | none |
| A6 | `test_remote_off_is_adopted` | R1 Heat engaged | remote turns child off | DST `off` | none |
| A7 | `test_dst_ui_command_is_not_adopted_back` | R1 Off | DST UI sets Heat | child `heat`, DST `heat`, zero adoptions | one `set_hvac_mode`, one `set_temperature`, nothing after |
| A8 | `test_dst_ui_target_reaches_the_child_and_stays` | R1 Heat engaged | DST UI sets target 23 | child target 23, DST 23, zero adoptions | one `set_temperature(23)` |
| A9 | `test_automation_service_call_on_the_child_is_adopted` | R1 Heat engaged | automation (own context) calls `climate.set_hvac_mode cool` on the child | DST `cool` | only the automation's call, no DST command |
| A9b | `test_automation_service_call_on_dst_is_a_dst_command` | R1 Off | automation calls `climate.set_hvac_mode heat` on DST | child `heat`, DST `heat`, zero adoptions | one `set_hvac_mode`, one `set_temperature` |
| A10 | `test_preset_change_is_pushed_and_not_adopted_back` | R1 Heat engaged, preset `away` 17 | DST preset `away` | child target 17, DST preset `away`, target 17, zero adoptions | one `set_temperature(17)` |
| A11 | `test_remote_then_dst_in_the_same_second_dst_wins` | R1 Heat engaged | remote sets `cool` (adopted), then DST UI sets Off | DST `off`, child `off` | one `turn_off` |
| A12 | `test_dst_then_remote_in_the_same_second_remote_wins` | R1 Off | DST UI sets Heat, then remote sets `cool` | DST `cool`, one adoption | DST's `set_hvac_mode heat` + `set_temperature` only |
| A13 | `test_remote_mode_then_target_as_two_adoptions` | R1 Heat engaged, target 22 | remote sets `cool`, then remote sets target 24 | DST `cool`, target 24; two adoptions | none (no stale push over the remote's value) |
| A14 | `test_remote_target_then_mode_as_two_adoptions` | as A13 | remote target 24 first, then `cool` | DST `cool`, target 24 | none |
| A15 | `test_a_second_remote_change_right_after_the_first_wins` | R1 Heat engaged | remote `cool`, then `fan_only` | DST `fan_only` | none |

### B. Adoption variants

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| B1 | `test_foreign_mode_turns_dst_off_and_stays_hands_off` | R1 (roles heater/cooler only), Heat engaged | remote sets child `auto` | DST `off`; later sensor ticks too | child: none, ever |
| B2 | `test_shared_child_adopts_each_role_mode_without_a_loop` | R1 Heat engaged | remote `dry`, then remote `fan_only`, then 5 sensor ticks | DST `dry` then `fan_only` | child: none at any point |
| B3 | `test_heat_pump_owns_only_its_current_direction` | climate heat pump, flag `heating` | remote `cool` | `cool` is foreign for a heating pump: DST `off` | none |
| B4 | `test_setpoint_style_adopts_the_target_without_commands` | cooler climate, `setpoint`, `cooler_setpoint_offset: -2` | remote target 20 | DST target 22 | none |
| B5 | `test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode` | heater/cooler = AC, `fan` entity configured | remote fan `strong` on the AC | DST fan modes are the fan entity's, `fan_mode` unchanged, zero adoptions of fan | none |
| B6 | `test_adopted_target_outside_the_dst_range_is_clamped_and_pushed_once` | R1 Heat, DST `max_temp: 26` | remote target 29 | DST target 26 | exactly one `set_temperature(26)` |
| B7 | `test_mixed_rig_adopting_cool_stops_the_switch_heater_once` | switch heater + climate cooler, Heat engaged on the switch | remote turns the AC `cool` | DST `cool` | child: none; other: heater switch `turn_off` once |

### C. Echoes (value-based)

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| C1 | `test_own_command_echo_is_not_adopted` | R1 Off | sensor demand: DST turns the child on | zero adoptions | `set_hvac_mode` + `set_temperature` once each |
| C2 | `test_echo_with_a_foreign_context_is_not_adopted` | R1 Off, echoes held | DST commands `heat`; the echo is delivered with an unknown context and the commanded value | zero adoptions | the original command only |
| C3 | `test_out_of_order_echoes_are_not_adopted` | R1, echoes held | DST commands `cool`, then `off`; echoes delivered `off` then `cool` | zero adoptions | the two commands only |
| C4 | `test_split_mode_and_target_echo_is_not_adopted` | R1 Off, echoes held | DST turn-on (mode + target); the two echoes arrive separately | zero adoptions | the two commands only |
| C5 | `test_attribute_noise_is_ignored` | R1 Heat engaged | `current_temperature`, `hvac_action` change | zero adoptions | none |
| C6 | `test_a_command_the_child_already_satisfies_leaves_no_expectation` | R1 Heat engaged at 22 | DST UI sets target 22 (already there); later the remote sets 24, then 22 | two adoptions (24, then 22) | none |

### D. Safety precedence

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| D1 | `test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing` | R1 Heat, window open (child paused) | remote turns child `heat`, target 24 | DST `heat`/24; child paused again at once; after the window closes the child is heating at 24 | open: one `turn_off`; close: `set_hvac_mode heat`, `set_temperature(24)` |
| D2 | `test_floor_limit_wins_over_an_adopted_heat` | heater = AC, floor sensor above `max_floor_temp`, DST Off | remote `heat` | DST `heat` recorded, child stopped | one `turn_off` |
| D3 | `test_stale_sensor_stops_the_child_and_keeps_the_intent` | R1 Heat, stale duration elapsed (emergency stop done) | remote `heat`, then the sensor recovers | DST `heat`; child stopped; after recovery control resumes | stall: one `turn_off`; recovery: DST commands as normal |
| D4 | `test_min_cycle_still_applies_after_an_adoption` | R1 Off, `min_cycle_duration` 5 min, room hot | remote `heat` (goal already reached) | child not stopped inside 5 min, stopped after | none, then one `turn_off` after 6 min |
| D5 | `test_a_chatty_integration_cannot_keep_a_paused_device_running` | R1 Heat, window open | the integration flips the child to `heat` three times | each time DST adopts and the same control run stops the child; no delay | one `turn_off` per flip |

### E. Off

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| E1 | `test_transition_to_off_sends_one_unscoped_off` | R1, `follow_device_changes: false`, child in `auto` (no role owns it) | DST UI sets Off | child `off` | exactly one `turn_off` |
| E2 | `test_keep_alive_while_off_sends_nothing_to_climate_children` | R1 Off, `keep_alive` 1 min, child `heat` set by the remote, follow off | 3 keep-alive ticks | child stays `heat` | none |
| E3 | `test_remote_use_while_off_is_adopted_when_following` | R1 Off, follow on, room 22 | remote `heat`, target 22 | DST `heat`/22 | none |
| E4 | `test_remote_use_while_off_is_ignored_and_never_fought_when_not_following` | as E3 with follow off | remote `heat`, keep-alive ticks | DST stays `off`, child stays `heat` | none |

### F. `follow_device_changes: false`

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| F1 | `test_not_following_reasserts_the_mode_on_the_next_tick` | R1 Cool engaged, follow off | remote `heat`; sensor tick, room hot | DST stays `cool`, zero adoptions | one `set_hvac_mode cool` |
| F2 | `test_not_following_reasserts_the_target_on_the_next_run` | R1 Heat engaged 22, follow off | remote target 25; sensor tick | DST target 22 | one `set_temperature(22)` |

### G. Restart, reconnect, first sight (owner decision (b): DST re-asserts, nothing adopted)

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| G1 | `test_restored_setting_is_reasserted_not_adopted_at_startup` | restore cache: DST `cool`/24; child already `heat`/20; room hot | startup | zero adoptions; DST `cool`/24; the child ends `cool` at 24 | `set_hvac_mode cool`, `set_temperature(24)` |
| G2 | `test_reconnect_adopts_nothing_and_dst_reasserts` | R1 Heat engaged 22, room cold | child goes `unavailable`, comes back `cool` | zero adoptions; DST `heat`; next tick the child is set back to heat | `set_hvac_mode heat` (+ target) |
| G3 | `test_a_child_appearing_late_adopts_nothing` | R1 configured, child missing | child appears in `cool`, room cold | zero adoptions; DST `heat` | DST sets heat on its next control |

### H. `assumed_state` devices

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| H1 | `test_assumed_child_adopts_nothing` | child with `assumed_state`, DST Cool engaged | a reported change to `heat`, 28 | zero adoptions; DST `cool` | none from adoption |
| H2 | `test_a_remote_decoded_without_the_assumed_flag_is_followed` | child that decodes the remote, no `assumed_state` attribute | remote `cool` | DST `cool` (looks like a normal device) | none |
| H3 | `test_external_ignores_an_assumed_flag_on_either_side` | unit, `ClimateChild.external` | old assumed / new not, and the reverse | not external | n/a |

### I. Automation interference

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| I1 | `test_an_automation_forcing_the_fan_mode_on_each_mode_change_is_followed_without_a_storm` | R1, device resets fan on a mode change, an automation forces fan `strong` whenever the mode changes, DST selection `quiet` | DST cycles the AC on and off three times, then 5 idle ticks | DST `fan_mode` ends `strong`; idle ticks cause no commands | DST fan commands at most one per turn on, zero during idle ticks |
| I2 | `test_an_automation_forcing_the_mode_is_followed_without_a_loop` | R1 Cool engaged, an automation sets `heat` whenever the child leaves `heat` | automation fires | DST `heat` | none, also across 5 ticks |
| I3 | `test_not_following_an_automation_forced_fan_does_not_storm` | as I1 with follow off | automation fires, 5 idle ticks | DST selection stays `quiet` | no DST fan command during the idle ticks |

### L. Reviewer-found cases

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| L1 | `test_remote_target_a_b_a_is_followed_each_time` | R1 Heat, DST pushed 22 earlier (echo consumed) | remote 24, then remote 22 | two adoptions, DST 24 then 22 | none (DST must not re-push 24) |
| L2 | `test_remote_mode_a_b_a_is_followed_each_time` | R1 Heat engaged | remote `cool`, then `heat` | two adoptions, DST `cool` then `heat` | none |
| L3 | `test_a_remote_change_within_five_seconds_of_a_dst_command_is_adopted` | R1 Off | DST UI sets Heat; the remote then sets `cool`, stamped with DST's context (HA keeps it for 5 s) | one adoption, DST `cool` | DST's own two commands only |
| L4 | `test_a_fan_reset_caused_by_our_own_mode_command_is_not_adopted` | R1, device resets fan to `auto` on a mode change, DST selection `quiet` | DST UI sets Heat | zero adoptions; DST fan stays `quiet`; child fan back to `quiet` | `set_hvac_mode`, `set_temperature`, `set_fan_mode(quiet)` |
| L5 | `test_a_stale_value_reported_after_our_command_is_followed_as_the_devices_truth` | R1, echoes held | DST commands `cool`; the echo is delivered; later the device reports `heat` (old value polled back) | one adoption, DST `heat` (documented behaviour) | none |
| L6 | `test_an_adoption_clears_the_pending_expectations` | R1, echoes held | DST commands `heat` (pending `heat`); remote `cool` adopted; then `heat` is reported | the later `heat` is external, not an echo: second adoption | none |

### M. Two thermostats on one child

| ID | Test | Given | When | Then | Commands |
|---|---|---|---|---|---|
| M1 | `test_two_thermostats_on_one_child_follow_each_other_without_fighting` | thermostats A and B both on the AC, both Off | A's UI sets Heat | A commands once; B adopts `heat` without commanding; remote then sets `cool`: both adopt | child: A's two commands only |
| M2 | `test_one_thermostats_adoption_does_not_delay_the_others_safety_stop` | A plain, B with an open window; both on the AC | the remote turns the AC `heat` | B stops the AC at once; A follows the stop (A `off`); no ping-pong | one `turn_off` in total |

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
from unittest.mock import patch

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import Context, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest

from custom_components.dual_smart_thermostat.climate import DualSmartThermostat
from tests import common, setup_switch

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


@pytest.fixture
def adoptions():
    """The modes DST adopted from the child, in order (a spy on the adoption)."""
    adopted = []
    original = DualSmartThermostat._async_adopt_state

    async def spy(self, child, state):
        adopted.append(state.state)
        return await original(self, child, state)

    with patch.object(DualSmartThermostat, "_async_adopt_state", spy):
        yield adopted


def _dst(hass: HomeAssistant, entity="climate.test") -> State:
    return hass.states.get(entity)


async def _idle(hass) -> None:
    """Everything scheduled by the last event has run (adoptions are immediate)."""
    await hass.async_block_till_done()


async def _tick(hass, room: float) -> None:
    """A room sensor update (this is what drives DST's own control)."""
    hass.states.async_set(SENSOR, room)
    await hass.async_block_till_done()


async def _start(
    hass, mode=HVACMode.HEAT, target=22.0, *, child_kwargs=None, **cfg
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

    def remote(self, *, mode=None, temperature=None, fan_mode=None,
               reuse_context=False, **extra):
        """The user acts on the device: a state change from outside DST.

        reuse_context=True keeps the entity's current context, like HA does for
        any write within 5 s of a service call (a remote press then carries the
        context of DST's last command).
        """
        attrs = {
            key: value
            for key, value in {
                "hvac_mode": mode,
                "target_temperature": temperature,
                "fan_mode": fan_mode,
            }.items()
            if value is not None
        }
        self._write(attrs | extra, None if reuse_context else Context())

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

(`__init__` gains `self._echo_queue = None`; `async_set_hvac_mode`, `async_turn_off`, `async_set_temperature`, `async_set_fan_mode` keep recording `self.calls` and then call `self._apply(hvac_mode=...)` / `self._apply(target_temperature=...)` / `self._apply(fan_mode=...)`; the reset-fan-on-mode-change attrs ride in the same `_apply` as `fan_mode="auto"`. Add `HVACMode.AUTO` to the fake's `hvac_modes` so a foreign mode can be reported.)

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
git commit -m "Test support for external device changes (fake child remote, held echoes, adoption spy)

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

## Task 3: Expectations per thermostat, the `sending` flag, fresh contexts (rows C1 to C6, H3, L6)

**Files:**
- Modify: `hvac_device/entity_port.py` (`ClimateChild`, `ClimatePort`), `hvac_device/fan_speed.py`, `hvac_device/fan_device.py`, `hvac_device/hvac_device_factory.py`
- Test: `tests/features/test_climate_follow_device_changes.py`

At this point nothing adopts yet; the tests observe `ClimateChild.external` indirectly through the `adoptions` spy being empty, plus one direct unit test. Rows that need the adoption itself (L6) are written here and go green in Task 5.

- [ ] **Step 1: Write the failing tests**

```python
from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimateChild


async def test_own_command_echo_is_not_adopted(hass, adoptions):  # C1
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)  # demand: DST turns the AC on
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert adoptions == []


async def test_echo_with_a_foreign_context_is_not_adopted(hass, adoptions):  # C2
    child = await _start(hass, HVACMode.OFF)
    child.hold_echoes()
    await _tick(hass, 18.0)
    child.flush_echoes(context="foreign")  # polled integration: the right values, an unknown context
    await _idle(hass)
    assert adoptions == []
    assert len(child.calls) == 2


async def test_out_of_order_echoes_are_not_adopted(hass, adoptions):  # C3
    child = await _start(hass, HVACMode.OFF)
    child.hold_echoes()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # commands heat
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")   # then off
    child.flush_echoes([1, 0], context="foreign")  # off lands first, the older heat last
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.OFF


async def test_split_mode_and_target_echo_is_not_adopted(hass, adoptions):  # C4
    child = await _start(hass, HVACMode.OFF)
    child.hold_echoes()
    await _tick(hass, 18.0)
    child.flush_echoes(context="foreign")  # a mode event, then a target event
    await _idle(hass)
    assert adoptions == []


async def test_attribute_noise_is_ignored(hass, adoptions):  # C5
    child = await _start(hass, HVACMode.HEAT)
    child.set_current_temperature(23.1)
    child.remote(hvac_action="heating")
    await _idle(hass)
    assert adoptions == []


async def test_a_command_the_child_already_satisfies_leaves_no_expectation(hass, adoptions):  # C6
    child = await _start(hass, HVACMode.HEAT, target=22)
    await common.async_set_temperature(hass, 22, "climate.test")  # the child already has 22
    await _idle(hass)
    assert child.calls == []  # skipped, so nothing was expected
    child.remote(temperature=24.0)
    await _idle(hass)
    child.remote(temperature=22.0)  # must not be mistaken for the echo of the skipped command
    await _idle(hass)
    assert len(adoptions) == 2


async def test_external_ignores_an_assumed_flag_on_either_side(hass):  # H3
    child = ClimateChild(hass, AC)
    owner = object()
    off = State(AC, "off", {"assumed_state": True})
    cool = State(AC, "cool", {})
    assert not child.external(owner, off, cool)
    assert not child.external(owner, cool, State(AC, "off", {"assumed_state": True}))


async def test_external_ignores_a_missing_or_unavailable_old_state(hass):
    child = ClimateChild(hass, AC)
    owner = object()
    cool = State(AC, "cool", {})
    assert not child.external(owner, None, cool)  # first sight
    assert not child.external(owner, State(AC, "unavailable"), cool)  # reconnect


async def test_every_dst_command_uses_a_fresh_context(hass):
    entity = await common.add_fake_climate(hass, AC)
    child = ClimateChild(hass, AC)
    owner = object()
    parent = Context()
    await child.async_set_mode("cool", parent, owner)  # the DST entity's own context goes in
    await child.async_push_target(23.0, parent, owner)
    contexts = {c[2] for c in entity.contexts}  # recorded by the fake per call
    assert parent.id not in {ctx.id for ctx in contexts}
    assert len({ctx.id for ctx in contexts}) == 2
```

(The fake records `self.contexts.append(...)` next to `calls`: add `self.contexts: list[tuple[str, dict, Context]] = []` and append `(name, data, self._context)` in each handler. `child` and `entity` objects in the last test are separate on purpose: the real port path is covered by the integration tests.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "echo or noise or satisfies or assumed_flag or missing_or_unavailable or fresh_context" -v
```

Expected: FAIL (`AttributeError: 'ClimateChild' object has no attribute 'external'`; the spy fixture also fails until `_async_adopt_state` exists: create it as an empty method in this task so the spy can wrap it).

- [ ] **Step 3: Implement**

`entity_port.py`:

```python
from contextlib import contextmanager
import math

_MAX_PENDING = 4
_TRACKED = (
    ("mode", lambda s: s.state),
    ("target", lambda s: s.attributes.get(ATTR_TEMPERATURE)),
    ("fan_mode", lambda s: s.attributes.get(ATTR_FAN_MODE)),
)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, abs_tol=1e-6)
    return a == b
```

`ClimateChild.__init__`: `self._pending: dict[Any, dict[str, list[Any]]] = {}`, `self._sending: dict[Any, int] = {}`, `self._adopting: dict[Any, int] = {}`. All three are keyed by *owner*, the thermostat (its `FeatureManager`).

```python
    @contextmanager
    def sending(self, owner):
        """DST is sending a sequence: changes reported meanwhile are the device's side effects."""
        self._sending[owner] = self._sending.get(owner, 0) + 1
        try:
            yield
        finally:
            self._sending[owner] -= 1

    @contextmanager
    def adopting(self, owner):
        """This owner is adopting the child's state: its commands to the child are dropped."""
        self._adopting[owner] = self._adopting.get(owner, 0) + 1
        try:
            yield
        finally:
            self._adopting[owner] -= 1

    def _expect(self, owner, attr, value) -> None:
        if self.assumed:
            return  # an assumed child never reports back; nothing to match
        pending = self._pending.setdefault(owner, {}).setdefault(attr, [])
        pending.append(value)
        del pending[:-_MAX_PENDING]

    def _unexpect(self, owner, attr, value) -> None:
        pending = self._pending.get(owner, {}).get(attr, [])
        for index in range(len(pending) - 1, -1, -1):
            if _same(pending[index], value):
                del pending[index]
                return

    def clear(self, owner) -> None:
        """Forget what this owner expects (after an adoption, or when the child goes away)."""
        self._pending.pop(owner, None)

    def external(self, owner, old: State | None, new: State | None) -> bool:
        """Consume this owner's echoes; True when something changed from outside.

        Judged by value against what this owner commanded and has not yet seen
        reported. Contexts and time play no part: HA stamps a write within 5 s of
        a service call with the caller's context, and a polled device reports
        late.
        """
        if is_unavailable(old) or is_unavailable(new):
            self.clear(owner)  # first sight and reconnect adopt nothing (owner decision)
            return False
        if old.attributes.get(ATTR_ASSUMED_STATE) or new.attributes.get(ATTR_ASSUMED_STATE):
            return False  # an assumed child reports DST's own record
        external = False
        for attr, read in _TRACKED:
            before, after = read(old), read(new)
            if after is None or _same(before, after):
                continue
            pending = self._pending.get(owner, {}).get(attr, [])
            match = next((i for i, v in enumerate(pending) if _same(v, after)), None)
            if match is not None:
                del pending[match]  # an echo of ours; any order is fine
            else:
                external = True
        return external and not self._sending.get(owner)
```

Commands take the owner and use a fresh context: `_command(self, service, data, context, error, *args, owner, mode=None)`:

```python
        if self._adopting.get(owner):
            _LOGGER.debug("Adopting %s: not sending %s", self.entity_id, service)
            return False
        context = Context(parent_id=context.id if context else None)  # fresh; never the caller's
        ...
        # after the record and before the call:
        if mode is not None:
            self._expect(owner, "mode", mode)
        if ATTR_TEMPERATURE in data:
            self._expect(owner, "target", data[ATTR_TEMPERATURE])
        # on failure, next to the existing rollback:
            if mode is not None: self._unexpect(owner, "mode", mode)
            if ATTR_TEMPERATURE in data: self._unexpect(owner, "target", data[ATTR_TEMPERATURE])
```

`async_set_mode`, `async_turn_off`, `async_push_target` and `async_set_fan_mode` all gain `owner` (last positional) and forward it. `async_set_fan_mode` applies the same adopting drop, the fresh context, `_expect(owner, "fan_mode", fan_mode)` just before its service call and `_unexpect` if it raises. The skip rules already in the code (state already equals, target equals, child off) return before `_command`, so a skipped command adds no expectation.

`ClimatePort`: `owner = self._device.features` (a property `_owner`), pass it to every child call, and wrap the body of `async_turn_on` in `with self._child.sending(self._owner):` (mode, target and the fan re-apply are one sequence). `release()` also calls `self._child.clear(self._owner)` when this was the owner's last port on the child.

`FanSpeedControl(hass, entity_id, owner)`: stores `owner`, passes it to `child.async_set_fan_mode(fan_mode, None, self.owner)`. `FanDevice` builds it with `features`; `HVACDeviceFactory._select_fan_speed` with `self._features`.

`climate.py`: add the empty seam `async def _async_adopt_state(self, child, state): ...` (filled in Task 5) so the `adoptions` fixture can wrap it.

- [ ] **Step 4: Run to verify pass**

```bash
./scripts/docker-test tests/features -v
```

Expected: PASS (L6 stays red until Task 5).

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "ClimateChild: per-thermostat expectations, sending/adopting flags, fresh contexts

Refs #281"
```

---

## Task 5: Immediate adoption (rows A1 to A6, B1 to B7, L1, L2, L3, L4, L6)

**Files:**
- Modify: `climate.py`, `hvac_device/entity_port.py` (`devices()`, `device_for()`)
- Test: `tests/features/test_climate_follow_device_changes.py`

- [ ] **Step 1: Write the failing tests**

```python
async def test_remote_mode_is_adopted(hass, adoptions):  # A1 (and H2: this fake carries no assumed flag)
    child = await _start(hass, HVACMode.HEAT)
    assert not hass.states.get(AC).attributes.get("assumed_state")
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    assert adoptions == ["cool"]
    assert child.calls == []


async def test_remote_target_is_adopted(hass):  # A2
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 24.0
    assert child.calls == []


async def test_remote_target_minus_heater_offset(hass):  # A3
    child = await _start(hass, HVACMode.HEAT, heater_setpoint_offset=3)
    child.remote(temperature=25.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert child.calls == []


async def test_remote_target_minus_cooler_offset(hass):  # A4
    child = await _start(hass, HVACMode.COOL, target=24, cooler_setpoint_offset=-5)
    child.remote(temperature=19.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 24.0
    assert child.calls == []


async def test_remote_fan_mode_is_adopted(hass):  # A5
    child = await _start(hass, HVACMode.HEAT)
    assert _dst(hass).attributes["fan_mode"] == "auto"  # the stale display
    child.remote(fan_mode="quiet")
    await _idle(hass)
    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert child.calls == []


async def test_remote_off_is_adopted(hass):  # A6
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.OFF)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert child.calls == []


async def test_foreign_mode_turns_dst_off_and_stays_hands_off(hass):  # B1
    child = await _start(hass, HVACMode.HEAT, dryer=None, humidity_sensor=None,
                         target_humidity=None, fan=None, fan_mode=None)
    child.remote(mode=HVACMode.AUTO)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    for room in (21.0, 25.0, 15.0):
        await _tick(hass, room)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.AUTO  # hands-off: the remote's choice stays


async def test_shared_child_adopts_each_role_mode_without_a_loop(hass):  # B2
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.DRY)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.DRY
    child.remote(mode=HVACMode.FAN_ONLY)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.FAN_ONLY
    for room in (22.1, 22.0, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert child.calls == []  # one change, one adoption, no echo, no loop


async def test_heat_pump_owns_only_its_current_direction(hass):  # B3
    hass.states.async_set("binary_sensor.hp_cooling", "off")
    child = await _start(
        hass, HVACMode.HEAT, heater=AC, cooler=None, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
        heat_pump_cooling="binary_sensor.hp_cooling",
    )
    child.remote(mode=HVACMode.COOL)  # the pump is heating: cool is not its mode
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert child.calls == []


async def test_setpoint_style_adopts_the_target_without_commands(hass):  # B4
    child = await _start(
        hass, HVACMode.COOL, target=24, control_style="setpoint",
        cooler_setpoint_offset=-2, heater=HEATER, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
    )
    child.remote(temperature=20.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert child.calls == []


async def test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode(hass):  # B5
    hass.states.async_set("fan.test_fan", "off", {"preset_modes": ["low", "high"], "preset_mode": "low"})
    child = await _start(hass, HVACMode.HEAT, fan="fan.test_fan")
    child.remote(fan_mode="strong")
    await _idle(hass)
    assert _dst(hass).attributes["fan_modes"] == ["low", "high"]
    assert _dst(hass).attributes["fan_mode"] == "low"
    assert child.calls == []


async def test_adopted_target_outside_the_dst_range_is_clamped_and_pushed_once(hass):  # B6
    child = await _start(hass, HVACMode.HEAT, max_temp=26)
    child.remote(temperature=29.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 26.0
    assert child.calls == [("set_temperature", {"temperature": 26.0})]


async def test_mixed_rig_adopting_cool_stops_the_switch_heater_once(hass):  # B7
    heater_calls = setup_switch(hass, True, HEATER)
    child = await _start(hass, HVACMode.HEAT, heater=HEATER, cooler=AC,
                         fan=None, dryer=None, humidity_sensor=None, target_humidity=None, fan_mode=None)
    heater_calls.clear()
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    assert child.calls == []
    assert [c.service for c in heater_calls] == ["turn_off"]


async def test_remote_target_a_b_a_is_followed_each_time(hass, adoptions):  # L1
    child = await _start(hass, HVACMode.HEAT, target=22)  # DST pushed 22 earlier; that echo is consumed
    child.remote(temperature=24.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 24.0
    child.remote(temperature=22.0)  # back to the value DST once pushed: still the user's
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert len(adoptions) == 2
    assert child.calls == []  # DST must not re-push 24


async def test_remote_mode_a_b_a_is_followed_each_time(hass, adoptions):  # L2
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    child.remote(mode=HVACMode.HEAT)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert adoptions == ["cool", "heat"]
    assert child.calls == []


async def test_a_remote_change_within_five_seconds_of_a_dst_command_is_adopted(hass, adoptions):  # L3
    child = await _start(hass, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    # HA stamps any write within 5 s of a service call with that call's context:
    child.remote(mode=HVACMode.COOL, reuse_context=True)
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_a_fan_reset_caused_by_our_own_mode_command_is_not_adopted(hass, adoptions):  # L4
    child = await _start(hass, HVACMode.OFF, child_kwargs={"resets_fan_on_mode_change": True})
    await hass.services.async_call(
        "climate", "set_fan_mode", {"entity_id": "climate.test", "fan_mode": "quiet"}, blocking=True
    )
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"  # re-applied after the reset
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature", "set_fan_mode"]


async def test_an_adoption_clears_the_pending_expectations(hass, adoptions):  # L6
    child = await _start(hass, HVACMode.OFF)
    child.hold_echoes()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # pending: heat
    child.remote(mode=HVACMode.COOL)  # external: adopted, expectations cleared
    await _idle(hass)
    assert adoptions == ["cool"]
    child.remote(mode=HVACMode.HEAT)  # no longer anyone's echo
    await _idle(hass)
    assert adoptions == ["cool", "heat"]
```

(`from tests import setup_switch` for B7 is already imported by the module header. A real-time check for L3: `reuse_context=True` leaves the fake's `_context` from the DST call in place, which is what HA does for 5 s.)

- [ ] **Step 2: Run to verify failure**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "adopted or foreign or shared_child or heat_pump or setpoint_style or separate_fan or clamped or mixed_rig or a_b_a or within_five or fan_reset or clears_the_pending" -v
```

Expected: FAIL (DST stays on its own setting).

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
import asyncio
from .climate_roles import is_climate_entity
from .hvac_device.entity_port import peek_climate_child

        # __init__
        self._adopt_lock = asyncio.Lock()
        self._adopt_dirty = False
        self._startup_done = False
```

`_async_startup` ends with `self._startup_done = True`. In `_async_switch_changed_event`, after the existing body (before `_async_switch_changed`):

```python
        self._async_follow(event)
```

```python
    @callback
    def _async_follow(self, event: Event[EventStateChangedData]) -> None:
        """Consume our own echoes; adopt anything that came from outside."""
        entity_id = event.data["entity_id"]
        if not is_climate_entity(entity_id):
            return
        child = peek_climate_child(self.hass, entity_id)
        if child is None:
            return
        # Always classify (it consumes this thermostat's echoes), adopt only if following.
        external = child.external(self.features, event.data["old_state"], event.data["new_state"])
        if external and self.features.follow_device_changes and self._startup_done:
            self._adopt_dirty = True
            self.hass.async_create_task(self._async_adopt(child))

    async def _async_adopt(self, child) -> None:
        """Make the child's current settings DST's own, then carry on controlling."""
        if self._adopt_lock.locked():
            return  # the running adoption sees the dirty flag and goes round again
        async with self._adopt_lock:
            while self._adopt_dirty:
                self._adopt_dirty = False
                state = child.state
                if state is None or not child.available:
                    return
                with child.adopting(self.features):  # our commands to it are dropped, briefly
                    await self._async_adopt_state(child, state)
                child.clear(self.features)
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
            await self.async_set_fan_mode(fan_mode)  # records it; the dropped command sends nothing

        mode = state.state
        role = child.device_for(mode)
        if mode == HVACMode.OFF or role is None or mode not in self.hvac_modes:
            # off, or a mode no role owns: Off, and hands-off (commands are dropped)
            await self.async_set_hvac_mode(HVACMode.OFF)
            return
        await self.async_set_hvac_mode(HVACMode(mode))
        target = state.attributes.get(ATTR_TEMPERATURE)
        if target is not None:  # after the mode: a mode change reloads targets from presets
            await self.async_set_temperature(
                temperature=round(target - role.setpoint_offset(), 4)
            )
```

The commands DST would send inside `_async_adopt_state` are dropped by the `adopting` flag, so the setters can never push a stale value over the remote's. The flag is released before the explicit control run, so that run (including an opening's or the stale sensor's stop) sends commands normally. Nothing is held across time; the flag belongs to this thermostat only.

- [ ] **Step 4: Run to verify pass, then the suite**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -v
./scripts/docker-test
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Follow device changes: adopt external mode, target, fan and off at once

Refs #281"
```

---

## Task 6: Interleavings, DST sources, chatty integrations, two thermostats (rows A7 to A15, D5, M1, M2, L5)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py`

- [ ] **Step 1: Write the tests**

```python
async def test_dst_ui_command_is_not_adopted_back(hass, adoptions):  # A7 (guard)
    child = await _start(hass, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert adoptions == []
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_dst_ui_target_reaches_the_child_and_stays(hass, adoptions):  # A8 (guard)
    child = await _start(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 23, "climate.test")
    await _idle(hass)
    assert child.calls == [("set_temperature", {"temperature": 23.0})]
    assert _dst(hass).attributes["temperature"] == 23.0
    assert adoptions == []


async def test_automation_service_call_on_the_child_is_adopted(hass, adoptions):  # A9
    child = await _start(hass, HVACMode.HEAT)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": AC, "hvac_mode": "cool"},
        blocking=True, context=Context(),  # an automation, not DST
    )
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]  # the automation's own call only


async def test_automation_service_call_on_dst_is_a_dst_command(hass, adoptions):  # A9b (guard)
    child = await _start(hass, HVACMode.OFF)
    await hass.services.async_call(
        "climate", "set_hvac_mode", {"entity_id": "climate.test", "hvac_mode": "heat"},
        blocking=True, context=Context(),
    )
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.HEAT
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_preset_change_is_pushed_and_not_adopted_back(hass, adoptions):  # A10
    child = await _start(hass, HVACMode.HEAT, away={"temperature": 17})
    await common.async_set_preset_mode(hass, "away", "climate.test")
    await _idle(hass)
    assert child.calls == [("set_temperature", {"temperature": 17.0})]
    assert adoptions == []
    assert _dst(hass).attributes["preset_mode"] == "away"
    assert _dst(hass).attributes["temperature"] == 17.0


async def test_remote_then_dst_in_the_same_second_dst_wins(hass):  # A11
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")  # DST acts right after
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.OFF
    assert child.calls == [("turn_off", {})]


async def test_dst_then_remote_in_the_same_second_remote_wins(hass, adoptions):  # A12
    child = await _start(hass, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]  # DST's own only


async def test_remote_mode_then_target_as_two_adoptions(hass, adoptions):  # A13
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(mode=HVACMode.COOL)
    child.remote(temperature=24.0)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.COOL, 24.0)
    assert child.calls == []  # no stale push over the remote's value


async def test_remote_target_then_mode_as_two_adoptions(hass, adoptions):  # A14
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.COOL, 24.0)
    assert child.calls == []


async def test_a_second_remote_change_right_after_the_first_wins(hass):  # A15
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    child.remote(mode=HVACMode.FAN_ONLY)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.FAN_ONLY
    assert child.calls == []


async def test_a_chatty_integration_cannot_keep_a_paused_device_running(hass, adoptions):  # D5
    hass.states.async_set(WINDOW, "off")
    child = await _start(hass, HVACMode.HEAT, openings=[WINDOW])
    hass.states.async_set(WINDOW, "on")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # paused
    for _ in range(3):
        child.calls.clear()
        child.remote(mode=HVACMode.HEAT)  # the integration keeps flipping it back on
        await _idle(hass)
        assert hass.states.get(AC).state == HVACMode.OFF  # stopped again before anything else ran
        assert [c[0] for c in child.calls] == ["turn_off"]
    assert _dst(hass).state == HVACMode.HEAT  # the intent is kept


async def _second_thermostat(hass, **cfg):
    config = {"platform": "dual_smart_thermostat", "name": "test2", "target_sensor": SENSOR,
              "heater": AC, "cooler": AC, **cfg}
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: [config]})
    await hass.async_block_till_done()


async def test_two_thermostats_on_one_child_follow_each_other_without_fighting(hass, adoptions):  # M1
    child = await _start(hass, HVACMode.OFF, fan=None, dryer=None, humidity_sensor=None,
                         target_humidity=None, fan_mode=None)
    await _second_thermostat(hass, initial_hvac_mode=HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # A commands
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert _dst(hass, "climate.test2").state == HVACMode.HEAT  # B adopted, without commanding
    child.calls.clear()
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass, "climate.test2").state == HVACMode.COOL
    assert child.calls == []  # no ping-pong


async def test_one_thermostats_adoption_does_not_delay_the_others_safety_stop(hass):  # M2
    hass.states.async_set(WINDOW, "on")  # B's window is open
    child = await _start(hass, HVACMode.OFF, fan=None, dryer=None, humidity_sensor=None,
                         target_humidity=None, fan_mode=None)
    await _second_thermostat(hass, initial_hvac_mode=HVACMode.OFF, openings=[WINDOW])
    child.calls.clear()
    child.remote(mode=HVACMode.HEAT)
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # B stopped it at once
    assert _dst(hass, "climate.test2").state == HVACMode.HEAT  # B keeps the intent
    assert _dst(hass).state == HVACMode.OFF  # A followed the stop
    assert [c[0] for c in child.calls] == ["turn_off"]  # one stop in total
```

The `climate.test2` thermostat needs its own sensor sharing; both read `SENSOR`.

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "dst_ui or automation_service or preset_change or same_second or two_adoptions or second_remote or chatty or two_thermostats or safety_stop" -v
```

Expected: guards (A7, A8, A9b, A10) PASS; the rest PASS with task 5. If M1 pings (calls grow) or D5 leaves the child on, fix `climate.py` (the `adopting` flag must stay per thermostat, `_async_adopt` must run the control run after releasing it); never add a delay.

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Follow device changes: interleavings, chatty integrations and two thermostats covered

Refs #281"
```

---

## Task 7: Safety precedence (rows D1 to D4)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py`

- [ ] **Step 1: Write the tests**

```python
async def test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing(hass):  # D1
    hass.states.async_set(WINDOW, "off")
    child = await _start(hass, HVACMode.HEAT, openings=[WINDOW])
    hass.states.async_set(WINDOW, "on")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # paused by the opening
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=24.0)  # the remote switches it back on
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.HEAT, 24.0)
    assert hass.states.get(AC).state == HVACMode.OFF  # the window still wins
    assert [c[0] for c in child.calls] == ["turn_off"]

    child.calls.clear()
    hass.states.async_set(WINDOW, "off")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 24.0}) in child.calls


async def test_floor_limit_wins_over_an_adopted_heat(hass):  # D2
    hass.states.async_set("sensor.floor", 30.0)
    child = await _start(
        hass, HVACMode.OFF, heater=AC, cooler=None, fan=None, dryer=None,
        humidity_sensor=None, target_humidity=None, fan_mode=None,
        floor_sensor="sensor.floor", max_floor_temp=28,
    )
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["turn_off"]


async def test_stale_sensor_stops_the_child_and_keeps_the_intent(hass, freezer):  # D3
    child = await _start(hass, HVACMode.HEAT, sensor_stale_duration=timedelta(minutes=2))
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # emergency stop
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=23.0)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["turn_off"]

    child.calls.clear()
    await _tick(hass, 18.0)  # the sensor recovers
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_min_cycle_still_applies_after_an_adoption(hass, freezer):  # D4
    child = await _start(hass, HVACMode.OFF, min_cycle_duration=timedelta(minutes=5))
    await _tick(hass, 26.0)  # hot room
    child.remote(mode=HVACMode.HEAT, temperature=22.0)  # goal already reached
    await _idle(hass)
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

Expected: PASS when task 5 is right (the forced control run applies the existing openings, floor and min-cycle logic, and the stalled branch stops the child). D3 is the likeliest failure: if the child is not stopped, check `_async_adopt` takes the `_sensor_stalled` branch; if the flag clears elsewhere on recovery only, fix there.

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
async def test_transition_to_off_sends_one_unscoped_off(hass):  # E1
    child = await _start(
        hass, HVACMode.HEAT, follow_device_changes=False,
        fan=None, dryer=None, humidity_sensor=None, target_humidity=None, fan_mode=None,
    )
    child.remote(mode=HVACMode.AUTO)  # a mode no role owns; not followed
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await _idle(hass)
    assert child.calls == [("turn_off", {})]
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_keep_alive_while_off_sends_nothing_to_climate_children(hass):  # E2
    child = await _start(hass, HVACMode.OFF, follow_device_changes=False,
                         keep_alive=timedelta(minutes=1))
    child.remote(mode=HVACMode.HEAT)
    for minutes in (2, 4, 6):
        common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=minutes))
        await _idle(hass)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_remote_use_while_off_is_adopted_when_following(hass):  # E3
    child = await _start(hass, HVACMode.OFF, target=22)
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (HVACMode.HEAT, 22.0)
    assert child.calls == []


async def test_remote_use_while_off_is_ignored_and_never_fought_when_not_following(hass):  # E4
    child = await _start(hass, HVACMode.OFF, follow_device_changes=False,
                         keep_alive=timedelta(minutes=1))
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _idle(hass)
    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=3))
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert child.calls == []


async def test_not_following_reasserts_the_mode_on_the_next_tick(hass, adoptions):  # F1
    child = await _start(hass, HVACMode.COOL, follow_device_changes=False)
    child.remote(mode=HVACMode.HEAT)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL  # not adopted
    assert adoptions == []
    await _tick(hass, 26.0)  # hot room: DST wants cooling
    assert [c for c in child.calls if c[0] == "set_hvac_mode"] == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.COOL})
    ]


async def test_not_following_reasserts_the_target_on_the_next_run(hass):  # F2
    child = await _start(hass, HVACMode.HEAT, target=22, follow_device_changes=False)
    child.remote(temperature=25.0)
    await _idle(hass)
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
            await self._child.async_turn_off(context, self._owner)
```

(`ClimateChild.needs_off` loses its `resend` parameter if no other caller uses it; delete the assumed-child tick branch with it. Update earlier phase tests that pinned the assumed resend, if any, to the new rule.)

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

## Task 9: Restart, assumed state, automation interference, stale poll (rows G1 to G3, H1, H2, I1 to I3, L5)

**Files:**
- Test: `tests/features/test_climate_follow_device_changes.py`
- Modify (only if a test fails): `climate.py`

- [ ] **Step 1: Write the tests**

```python
async def test_restored_setting_is_reasserted_not_adopted_at_startup(hass, adoptions):  # G1
    common.mock_restore_cache(
        hass, [State("climate.test", "cool", {"temperature": 24, "fan_mode": "auto"})]
    )
    hass.states.async_set(SENSOR, 28.0)  # hot: DST wants cooling
    hass.states.async_set("sensor.hum", 50.0)
    child = await common.add_fake_climate(hass, AC, HVACMode.HEAT)  # up before DST, other settings
    child._attr_target_temperature = 20.0
    child.async_write_ha_state()
    await _setup(hass, **ALL_ROLES)
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] == 24.0
    assert hass.states.get(AC).state == HVACMode.COOL  # re-asserted once
    assert hass.states.get(AC).attributes["temperature"] == 24.0


async def test_reconnect_adopts_nothing_and_dst_reasserts(hass, adoptions):  # G2
    child = await _start(hass, HVACMode.HEAT)
    await _tick(hass, 18.0)  # cold room: DST wants heat
    hass.states.async_set(AC, "unavailable")
    await _idle(hass)
    child.calls.clear()
    child.remote(mode=HVACMode.COOL)  # comes back in another mode
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.HEAT
    await _tick(hass, 17.9)
    assert hass.states.get(AC).state == HVACMode.HEAT  # set back


async def test_a_child_appearing_late_adopts_nothing(hass, adoptions):  # G3
    hass.states.async_set(SENSOR, 18.0)
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(hass, **ALL_ROLES, initial_hvac_mode=HVACMode.HEAT)
    await common.add_fake_climate(hass, AC, HVACMode.COOL)  # first sight is not a change
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.HEAT


async def test_assumed_child_adopts_nothing(hass, adoptions):  # H1
    child = await _start(hass, HVACMode.COOL, child_kwargs={"assumed": True})
    child.remote(mode=HVACMode.HEAT, temperature=28.0)  # the integration reports it anyway
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] != 28.0


async def test_a_remote_decoded_without_the_assumed_flag_is_followed(hass, adoptions):  # H2
    child = await _start(hass, HVACMode.HEAT)
    assert not hass.states.get(AC).attributes.get("assumed_state")
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL


def _automation(hass, trigger, **forced):
    """An external automation: when `trigger` says so, force the child's values."""
    @callback
    def _on_change(event):
        new, old = event.data["new_state"], event.data["old_state"]
        if new is None or old is None or not trigger(old, new):
            return
        child_entity = hass.data["climate"].get_entity(AC)
        hass.async_create_task(_force(child_entity))

    async def _force(child_entity):
        current = hass.states.get(AC)
        if all(
            (current.state if key == "mode" else current.attributes.get(key)) == value
            for key, value in forced.items()
        ):
            return
        child_entity.remote(**{"mode" if key == "mode" else key: value for key, value in forced.items()})

    async_track_state_change_event(hass, [AC], _on_change)


async def test_an_automation_forcing_the_fan_mode_on_each_mode_change_is_followed_without_a_storm(hass, adoptions):  # I1
    child = await _start(hass, HVACMode.OFF, child_kwargs={"resets_fan_on_mode_change": True})
    await hass.services.async_call(
        "climate", "set_fan_mode", {"entity_id": "climate.test", "fan_mode": "quiet"}, blocking=True
    )
    _automation(hass, lambda old, new: old.state != new.state, fan_mode="strong")
    child.calls.clear()
    for room in (18.0, 22.0, 18.0, 22.0, 18.0):  # DST turns the AC on and off; the device resets its fan
        await _tick(hass, room)
    assert _dst(hass).attributes["fan_mode"] == "strong"  # followed
    turn_ons = len([c for c in child.calls if c[0] == "set_hvac_mode"])
    assert len([c for c in child.calls if c[0] == "set_fan_mode"]) <= turn_ons

    child.calls.clear()
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):  # idle: no storm
        await _tick(hass, room)
    assert child.calls == []


async def test_an_automation_forcing_the_mode_is_followed_without_a_loop(hass):  # I2
    child = await _start(hass, HVACMode.COOL)
    _automation(hass, lambda old, new: new.state != HVACMode.HEAT, mode=HVACMode.HEAT)
    child.remote(mode=HVACMode.OFF)  # something moves it off; the automation forces heat
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert child.calls == []


async def test_not_following_an_automation_forced_fan_does_not_storm(hass):  # I3
    child = await _start(
        hass, HVACMode.HEAT, follow_device_changes=False,
        child_kwargs={"resets_fan_on_mode_change": True},
    )
    await hass.services.async_call(
        "climate", "set_fan_mode", {"entity_id": "climate.test", "fan_mode": "quiet"}, blocking=True
    )
    _automation(hass, lambda old, new: old.state != new.state, fan_mode="strong")
    child.remote(mode=HVACMode.COOL)  # triggers the automation
    await _idle(hass)
    child.calls.clear()
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert [c for c in child.calls if c[0] == "set_fan_mode"] == []  # re-applied on turn on only


async def test_a_stale_value_reported_after_our_command_is_followed_as_the_devices_truth(hass, adoptions):  # L5
    child = await _start(hass, HVACMode.OFF)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await _idle(hass)
    assert adoptions == []
    child.remote(mode=HVACMode.HEAT)  # an old reading polled back later
    await _idle(hass)
    assert adoptions == ["heat"]  # documented: DST yields to what the device reports (P5 step 9)
    assert _dst(hass).state == HVACMode.HEAT
```

- [ ] **Step 2: Run**

```bash
./scripts/docker-test tests/features/test_climate_follow_device_changes.py -k "restored or reconnect or appearing_late or assumed or automation or stale_value" -v
```

Expected: PASS with tasks 3 and 5 (`external` ignores unavailable and missing old states; assumed children never adopt; startup re-assertion is the existing control path). A failing G1 means something adopted at startup: ensure `_startup_done` gates `_async_follow` and that no first-sight path calls `_async_adopt`. A failing I1 (a storm) means DST re-applies a stale selection: the adoption must set `FanSpeedControl.current_fan_mode` before the next turn on (it does through `async_set_fan_mode` under `adopting`).

- [ ] **Step 3: Commit**

```bash
git add -A && git commit -m "Follow device changes: restart, assumed state and automation interference covered

Refs #281"
```

---

## Task 10: Docs, P5 checklist, lint

- [ ] **Step 1: README.** Replace the sentence "A change made on the AC's own remote is re-asserted by the thermostat within seconds ..." in the climate section with: "By default the thermostat follows changes made on the device itself (remote, vendor app, an automation): the new mode, target, fan speed or off becomes the thermostat's setting at once; a mode the thermostat has no role for turns it off and leaves the device alone. Open windows, floor limits and a stale sensor still take precedence. After a Home Assistant restart or a reconnect the thermostat re-asserts its own setting (a remote change made while Home Assistant was down is overridden once). Turn `follow_device_changes` off to keep the thermostat in charge: it then puts the device back on its next control run. Devices that report an assumed state (infrared) are not followed." Add `follow_device_changes` to the key table and the example file.
- [ ] **Step 2: P5.** Update `2026-10-20-climate-entity-devices-phase-5-real-device-verification.md` as listed in the coverage map below.
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
| 4.4 Opening | `test_setpoint_style_opening_pauses_and_restores_the_child`, `test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing`, `test_a_chatty_integration_cannot_keep_a_paused_device_running` | |
| 4.5 Heat to cool swap | `test_mixed_rig_adopting_cool_stops_the_switch_heater_once`, `test_climate_cooler_cycles_with_switch_heater` | |
| 4.6 Keep-alive resend | `test_idle_role_keep_alive_does_not_stop_the_active_role`, `test_keep_alive_while_off_sends_nothing_to_climate_children` | an IR unit resynchronising from a resend |
| 5.1 Min cycle protection | `test_climate_respects_min_cycle_duration`, `test_min_cycle_still_applies_after_an_adoption` | actual compressor protection |
| 5.2 Device offline | `test_unavailable_child_receives_no_commands`, `test_reconnect_adopts_nothing_and_dst_reasserts` | |
| 5.3 Sensor loss | `test_stale_child_temperature_triggers_the_emergency_stop`, `test_stale_sensor_stops_the_child_and_keeps_the_intent` | |
| 5.4 Unsupported mode | `test_unsupported_mode_is_not_sent` | |
| 5.5 Remote use | `test_remote_mode_is_adopted`, `test_remote_target_is_adopted`, `test_remote_fan_mode_is_adopted`, `test_remote_off_is_adopted`, `test_remote_target_a_b_a_is_followed_each_time`, `test_a_remote_change_within_five_seconds_of_a_dst_command_is_adopted`, `test_not_following_reasserts_the_mode_on_the_next_tick` | the integration's real event timing and contexts |
| 5.6 Restart and reload | `test_restored_setting_is_reasserted_not_adopted_at_startup`, `test_a_child_appearing_late_adopts_nothing` | restore from the real database; an AC that powers up off after a power cut leaves DST on |
| 5.7 Self reference | `test_entity_cannot_be_its_own_device` | |
| 5.8 Automation interference | `test_an_automation_forcing_the_fan_mode_on_each_mode_change_is_followed_without_a_storm`, `test_an_automation_forcing_the_mode_is_followed_without_a_loop`, `test_not_following_an_automation_forced_fan_does_not_storm` | the real automation and the real unit's fan reset |
| 5.9 Stale poll and reset timing | `test_a_stale_value_reported_after_our_command_is_followed_as_the_devices_truth`, `test_a_fan_reset_caused_by_our_own_mode_command_is_not_adopted` | whether the real integration ever reports an old value after our command, and when it reports a fan reset (polled integrations report late) |
| 5b.1 to 5b.8 Fan speed | phase 3b tests (`test_cooler_only_ac_gets_fan_speed_control`, `test_fan_speed_is_reapplied_after_the_ac_resets_it`, `test_fan_speed_is_restored_after_a_restart`, `test_fan_speed_restore_waits_for_a_late_child`, `test_separate_fan_entity_owns_fan_mode_and_the_ac_is_left_alone`), `test_remote_fan_mode_is_adopted`, `test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode` | the unit runs at that speed after every start |
| 6.1 to 6.2 Switch-only regression | the whole existing suite | the valve really opens |
| two thermostats (new) | `test_two_thermostats_on_one_child_follow_each_other_without_fighting`, `test_one_thermostats_adoption_does_not_delay_the_others_safety_stop` | only if a second thermostat shares an AC in the room |

P5 checklist steps this phase changes (Task 5 of the P5 plan):

- [ ] **Step 5 (rewritten): Remote use.** With `follow_device_changes` on, change the mode, then the target, then the fan speed with the remote (and once with the vendor app): `DST` shows the same mode, target (minus the role's offset) and fan mode within a second or two of the integration reporting it, and the log shows the adoption with **no** command sent back to the device. Move the target away and back to the value `DST` last pushed: both are followed. Set `auto` on the remote: `DST` goes Off and the unit is left alone. Repeat with the option off: the thermostat puts the device back on its next control run. On the IR AC (assumed state) a remote change is neither adopted nor corrected: record this.
- [ ] **Step 8: Automation interference.** With an automation that forces the AC fan to one value on each mode change, let `DST` start and stop the AC several times: `DST` follows the automation's value, no repeating `set_fan_mode` storm in the log, no flapping.
- [ ] **Step 9: Stale poll and reset timing.** Command a mode from `DST` and watch the entity for 30 seconds: does the integration ever report the old mode back after the new one (a stale poll)? If it does, `DST` adopts that old value (documented behaviour) and the owner must be told. For a polled integration on a device that resets its fan on a mode change, note how long after the mode command the reset is reported; if it lands after the thermostat's command sequence it is followed as a remote change.

## Acceptance (phase 6)

1. Every row of the scenario matrix is an automated test and passes; the guard rows pass before and after the implementation.
2. With `follow_device_changes` on, an external mode, off, target (minus the role's offset), fan mode or foreign mode on a climate child becomes the DST setting at once, with no timers; nothing is echoed back; a remote A to B to A is followed each time, including within 5 s of a DST command.
3. Own echoes (late, out of order, split, context-stamped), the device's own side effects during a DST sequence, and `assumed_state` children adopt nothing. Nothing is adopted from first sight, a late child or a reconnect (owner decision (b)).
4. Open windows, floor limits, the stale sensor and the minimum cycle still win immediately over an adopted setting, even against a chatty integration; the intent is kept.
5. Two thermostats on one child follow each other without fighting and neither delays the other's safety stop.
6. The transition to Off sends one unscoped `turn_off`; keep-alive while Off sends nothing to climate children; remote use while Off is adopted when following and left alone (never fought) when not.
7. With the option off DST re-asserts on its next control run.
8. The option is in YAML validation, the config, reconfigure and options climate steps, `climate_roles`, dependency tracking and translations; defaults to on.
