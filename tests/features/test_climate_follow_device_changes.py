"""Following changes made on the device itself (issue #281, phase 6)."""

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import Context, HomeAssistant, State, callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from custom_components.dual_smart_thermostat.hvac_device.climate_child import (
    ClimateChild,
    peek_climate_child,
)
from custom_components.dual_smart_thermostat.hvac_device.climate_follow import (
    ClimateFollower,
)
from tests import common, setup_switch

AC = "climate.test_ac"
WINDOW = "binary_sensor.window"
SENSOR = "sensor.room_temperature"
ALL_ROLES = {
    "heater": AC,
    "cooler": AC,
    "fan": AC,
    "dryer": AC,
    "humidity_sensor": "sensor.hum",
    "target_humidity": 40,
    "fan_mode": True,
}


async def _setup(hass, **config):
    hass.config.units = METRIC_SYSTEM
    base = {
        "platform": DOMAIN,
        "name": "test",
        "target_sensor": SENSOR,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    config = {k: v for k, v in config.items() if v is not None}
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: {**base, **config}})
    await hass.async_block_till_done()


@pytest.fixture
def adoptions():
    """The modes DST adopted from the child, in order (a spy on the adoption)."""
    adopted = []
    original = ClimateFollower._async_adopt_state

    async def spy(self, child, state, changed):
        adopted.append(state.state)
        return await original(self, child, state, changed)

    with patch.object(ClimateFollower, "_async_adopt_state", spy):
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


async def _start(hass, mode=HVACMode.HEAT, target=22.0, *, child_kwargs=None, **cfg):
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


# ---------------------------------------------------------------- test support


async def test_remote_changes_state_with_a_foreign_context(hass: HomeAssistant) -> None:
    """The fake child's remote() is a state change from outside, not a service call."""
    child = await common.add_fake_climate(hass, AC)
    child.remote(mode=HVACMode.COOL, temperature=24.0, fan_mode="quiet")
    state = hass.states.get(AC)
    assert state.state == HVACMode.COOL
    assert (state.attributes["temperature"], state.attributes["fan_mode"]) == (
        24.0,
        "quiet",
    )
    assert child.calls == []


async def test_held_echoes_are_delivered_on_demand_and_in_any_order(
    hass: HomeAssistant,
) -> None:
    """A slow or polled device: effects are parked, then delivered reordered."""
    child = await common.add_fake_climate(hass, AC)
    child.hold_echoes()
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": AC, "hvac_mode": "cool"},
        blocking=True,
    )
    await hass.services.async_call(
        "climate", "turn_off", {"entity_id": AC}, blocking=True
    )
    assert hass.states.get(AC).state == HVACMode.OFF  # nothing delivered yet
    child.flush_echoes([1, 0])
    assert hass.states.get(AC).state == HVACMode.COOL  # last delivered


# ------------------------------------------- expectations (C, H3, L6) and contexts


async def _heat_idle(hass):
    """DST in Heat with the child off: demand has stopped it, call list cleared."""
    child = await _start(hass, HVACMode.HEAT)
    await _tick(hass, 26.0)
    assert hass.states.get(AC).state == HVACMode.OFF
    # a new target, so that turning on sends a mode and a target (the child keeps 22)
    await common.async_set_temperature(hass, 23, "climate.test")
    await _idle(hass)
    child.calls.clear()
    return child


async def test_own_command_echo_is_not_adopted(hass, adoptions):  # C1
    child = await _heat_idle(hass)
    await _tick(hass, 18.0)  # demand: DST turns the AC on
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert adoptions == []


async def test_echo_with_a_foreign_context_is_not_adopted(hass, adoptions):  # C2
    child = await _heat_idle(hass)
    child.hold_echoes()
    await _tick(hass, 18.0)
    child.flush_echoes(context="foreign")  # right values, an unknown context
    await _idle(hass)
    assert adoptions == []
    assert len(child.calls) == 2


async def test_out_of_order_echoes_are_not_adopted(hass, adoptions):  # C3
    child = await _heat_idle(hass)
    child.hold_echoes()
    await _tick(hass, 18.0)  # commands: the mode, then the target
    child.flush_echoes([1, 0], context="foreign")  # the target is reported first
    await _idle(hass)
    assert adoptions == []
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_split_mode_and_target_echo_is_not_adopted(hass, adoptions):  # C4
    child = await _heat_idle(hass)
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


async def test_a_command_the_child_already_satisfies_leaves_no_expectation(
    hass, adoptions
):  # C6
    child = await _start(hass, HVACMode.HEAT, target=22)
    await common.async_set_temperature(hass, 22, "climate.test")  # already there
    await _idle(hass)
    assert child.calls == []  # skipped, so nothing was expected
    child.remote(temperature=24.0)
    await _idle(hass)
    child.remote(temperature=22.0)  # not the echo of the skipped command
    await _idle(hass)
    assert len(adoptions) == 2


async def test_external_ignores_an_assumed_flag_on_either_side(hass):  # H3
    child = ClimateChild(hass, AC)
    owner = object()
    off = State(AC, "off", {"assumed_state": True})
    cool = State(AC, "cool", {})
    assert not child.echo.external(owner, off, cool).changed
    assert not child.echo.external(
        owner, cool, State(AC, "off", {"assumed_state": True})
    ).changed


async def test_external_ignores_a_missing_or_unavailable_old_state(hass):
    child = ClimateChild(hass, AC)
    owner = object()
    cool = State(AC, "cool", {})
    assert not child.echo.external(owner, None, cool).changed  # first sight
    assert not child.echo.external(
        owner, State(AC, "unavailable"), cool
    ).changed  # reconnect


async def test_every_dst_command_uses_a_fresh_context(hass):
    entity = await common.add_fake_climate(hass, AC)
    child = ClimateChild(hass, AC)
    owner = object()
    parent = Context()
    await child.async_set_mode("cool", parent, owner)  # DST's own context goes in
    await child.async_push_target(23.0, parent, owner)
    contexts = [ctx for _, ctx in entity.contexts]
    assert len(contexts) == 2
    assert parent.id not in {ctx.id for ctx in contexts}
    assert len({ctx.id for ctx in contexts}) == 2
    assert all(ctx.parent_id == parent.id for ctx in contexts)


# ---------------------------------------------------------- immediate adoption


async def test_remote_mode_is_adopted(hass, adoptions):  # A1, H2 (no assumed flag)
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


_HEATER_COOLER_ONLY = {
    "dryer": None,
    "humidity_sensor": None,
    "target_humidity": None,
    "fan": None,
    "fan_mode": None,
}


async def test_foreign_mode_turns_dst_off_and_stays_hands_off(hass):  # B1
    child = await _start(hass, HVACMode.HEAT, **_HEATER_COOLER_ONLY)
    child.remote(mode=HVACMode.AUTO)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    for room in (21.0, 25.0, 15.0):
        await _tick(hass, room)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.AUTO  # the remote's choice stays


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
        hass,
        HVACMode.HEAT,
        heater=AC,
        cooler=None,
        heat_pump_cooling="binary_sensor.hp_cooling",
        **_HEATER_COOLER_ONLY,
    )
    child.remote(mode=HVACMode.COOL)  # the pump is heating: cool is not its mode
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert child.calls == []


async def test_setpoint_style_adopts_the_target_without_commands(hass):  # B4
    child = await _start(
        hass,
        HVACMode.COOL,
        target=24,
        control_style="setpoint",
        cooler_setpoint_offset=-2,
        heater="switch.room_heater",
        **_HEATER_COOLER_ONLY,
    )
    child.remote(temperature=20.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 22.0
    assert child.calls == []


async def test_fan_change_is_ignored_when_a_separate_fan_entity_owns_fan_mode(
    hass,
):  # B5
    hass.states.async_set(
        "fan.test_fan", "off", {"preset_modes": ["low", "high"], "preset_mode": "low"}
    )
    child = await _start(hass, HVACMode.HEAT, fan="fan.test_fan")
    child.remote(fan_mode="strong")
    await _idle(hass)
    assert _dst(hass).attributes["fan_modes"] == ["low", "high"]
    assert _dst(hass).attributes["fan_mode"] == "low"
    assert child.calls == []


async def test_adopted_target_outside_the_dst_range_is_clamped_and_pushed_once(
    hass,
):  # B6
    child = await _start(hass, HVACMode.HEAT, max_temp=26)
    child.remote(temperature=29.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 26.0
    assert child.calls == [("set_temperature", {"temperature": 26.0})]


async def test_mixed_rig_adopting_cool_stops_the_switch_heater_once(hass):  # B7
    heater_calls = setup_switch(hass, True, "switch.room_heater")

    def real_switch(state):  # a real switch really changes state
        @callback
        def handler(call) -> None:
            heater_calls.append(call)
            hass.states.async_set("switch.room_heater", state)

        return handler

    hass.services.async_register("homeassistant", "turn_on", real_switch("on"))
    hass.services.async_register("homeassistant", "turn_off", real_switch("off"))
    child = await _start(
        hass,
        HVACMode.HEAT,
        heater="switch.room_heater",
        **_HEATER_COOLER_ONLY,
    )
    heater_calls.clear()
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    # only the mode changed on the remote: DST's own target goes to the cooler
    assert child.calls == [("set_temperature", {"temperature": 22.0})]
    assert [c.service for c in heater_calls] == ["turn_off"]


async def test_remote_target_a_b_a_is_followed_each_time(hass, adoptions):  # L1
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 24.0
    child.remote(
        temperature=22.0
    )  # back to the value DST once pushed: still the user's
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


async def test_a_remote_change_within_five_seconds_of_a_dst_command_is_adopted(
    hass, adoptions
):  # L3
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _tick(hass, 22.0)  # the room is at the target: a running device keeps running
    # HA stamps any write within 5 s of a service call with that call's context:
    child.remote(mode=HVACMode.COOL, reuse_context=True)
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_a_fan_reset_caused_by_our_own_mode_command_is_not_adopted(
    hass, adoptions
):  # L4
    child = await _start(
        hass, HVACMode.OFF, child_kwargs={"resets_fan_on_mode_change": True}
    )
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    await _tick(hass, 18.0)
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"  # re-applied
    assert [c[0] for c in child.calls][-1] == "set_fan_mode"


async def test_an_adoption_clears_the_pending_expectations(hass, adoptions):  # L6
    child = await _start(hass, HVACMode.HEAT)
    await _tick(hass, 26.0)  # the heater stops
    child.hold_echoes()
    await _tick(hass, 18.0)  # commands heat: pending
    child.remote(mode=HVACMode.COOL)  # external: adopted, expectations cleared
    await _idle(hass)
    assert adoptions == ["cool"]
    child.remote(mode=HVACMode.HEAT)  # no longer anyone's echo
    await _idle(hass)
    assert adoptions == ["cool", "heat"]


# ------------------------------- interleavings, DST sources, chatty integrations, M


def _no_stale_push(child):
    """Nothing re-sent the mode or the target over what the remote set."""
    return [c for c in child.calls if c[0] in ("set_hvac_mode", "set_temperature")]


async def test_dst_ui_command_is_not_adopted_back(hass, adoptions):  # A7 (guard)
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
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
        "climate",
        "set_hvac_mode",
        {"entity_id": AC, "hvac_mode": "cool"},
        blocking=True,
        context=Context(),  # an automation, not DST
    )
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]  # the automation's own call


async def test_automation_service_call_on_dst_is_a_dst_command(hass, adoptions):  # A9b
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test", "hvac_mode": "heat"},
        blocking=True,
        context=Context(),
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
    # 17 is below the room: the run stops the child, so no setpoint is pushed first
    assert child.calls == [("turn_off", {})]
    assert adoptions == []
    assert _dst(hass).attributes["preset_mode"] == "away"
    assert _dst(hass).attributes["temperature"] == 17.0


async def test_remote_then_dst_in_the_same_second_dst_wins(hass):  # A11
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await _idle(hass)
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.OFF
    assert child.calls == [("turn_off", {})]


async def test_dst_then_remote_in_the_same_second_remote_wins(hass, adoptions):  # A12
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _tick(hass, 22.0)  # at the target: a running device keeps running
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert adoptions == ["cool"]
    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == [
        "set_hvac_mode",
        "set_temperature",
    ]  # DST's own


async def test_remote_mode_then_target_as_two_adoptions(hass, adoptions):  # A13
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(mode=HVACMode.COOL)
    child.remote(temperature=24.0)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (
        HVACMode.COOL,
        24.0,
    )
    assert _no_stale_push(child) == []  # nothing pushed over the remote's value


async def test_remote_target_then_mode_as_two_adoptions(hass, adoptions):  # A14
    child = await _start(hass, HVACMode.HEAT, target=22)
    child.remote(temperature=24.0)
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (
        HVACMode.COOL,
        24.0,
    )
    assert _no_stale_push(child) == []


async def test_a_second_remote_change_right_after_the_first_wins(hass):  # A15
    child = await _start(hass, HVACMode.HEAT)
    child.remote(mode=HVACMode.COOL)
    child.remote(mode=HVACMode.FAN_ONLY)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.FAN_ONLY
    assert _no_stale_push(child) == []


async def test_a_chatty_integration_cannot_keep_a_paused_device_running(
    hass, adoptions
):  # D5
    hass.states.async_set(WINDOW, "off")
    child = await _start(hass, HVACMode.HEAT, openings=[WINDOW])
    hass.states.async_set(WINDOW, "on")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # paused
    for _ in range(3):
        child.calls.clear()
        child.remote(mode=HVACMode.HEAT)  # the integration keeps flipping it back on
        await _idle(hass)
        assert hass.states.get(AC).state == HVACMode.OFF  # stopped again at once
        assert [c[0] for c in child.calls] == ["turn_off"]
    assert _dst(hass).state == HVACMode.HEAT  # the intent is kept


async def _start_two(hass, second=None, **first):
    """Two thermostats (test, test2) on the one AC, both Off, room at the target."""
    hass.config.units = METRIC_SYSTEM
    hass.states.async_set(SENSOR, 26.0)
    base = {
        "platform": DOMAIN,
        "target_sensor": SENSOR,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
        "heater": AC,
        "cooler": AC,
        "initial_hvac_mode": HVACMode.OFF,
    }
    configs = [
        {**base, "name": "test", **first},
        {**base, "name": "test2", **(second or {})},
    ]
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: configs})
    await hass.async_block_till_done()
    child = await common.add_fake_climate(hass, AC)
    for entity in ("climate.test", "climate.test2"):
        await common.async_set_temperature(hass, 22, entity)
    await _tick(hass, 22.0)
    child.calls.clear()
    return child


async def test_a_peer_thermostats_commands_are_not_adopted_but_the_remote_is(
    hass, adoptions
):  # M1
    child = await _start_two(hass)
    await _tick(hass, 18.0)
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # A commands
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert adoptions == []  # B takes A's commands for echoes, not for the user
    assert _dst(hass, "climate.test2").state == HVACMode.OFF
    await _tick(hass, 22.0)
    child.calls.clear()
    child.remote(mode=HVACMode.COOL)  # a change from outside DST: both follow
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass, "climate.test2").state == HVACMode.COOL
    assert _no_stale_push(child) == []  # no ping-pong


async def test_one_thermostats_safety_stop_is_not_adopted_by_the_other_as_user_off(
    hass,
):  # M2
    hass.states.async_set(WINDOW, "on")  # B's window is open
    child = await _start_two(hass, second={"openings": [WINDOW]})
    child.remote(mode=HVACMode.HEAT)
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # B stopped it at once
    assert _dst(hass, "climate.test2").state == HVACMode.HEAT  # B keeps the intent
    # A saw B's stop as DST's own command, not as the user switching the AC off
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls].count("turn_off") == 1  # one stop in total


async def test_a_stale_value_reported_after_our_command_is_followed_as_the_devices_truth(
    hass, adoptions
):  # L5
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await _idle(hass)
    assert adoptions == []
    child.remote(mode=HVACMode.HEAT)  # an old reading polled back later
    await _idle(hass)
    assert adoptions == ["heat"]  # documented: DST yields to what the device reports
    assert _dst(hass).state == HVACMode.HEAT


# ------------------------------------------------------------ safety precedence


async def test_open_window_keeps_the_adopted_intent_and_applies_it_after_closing(
    hass,
):  # D1
    hass.states.async_set(WINDOW, "off")
    child = await _start(hass, HVACMode.HEAT, openings=[WINDOW])
    hass.states.async_set(WINDOW, "on")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # paused by the opening
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=24.0)  # the remote switches it back on
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (
        HVACMode.HEAT,
        24.0,
    )
    assert hass.states.get(AC).state == HVACMode.OFF  # the window still wins
    assert [c[0] for c in child.calls] == ["turn_off"]
    # the adoption's flag is released before the control run: nothing is held back
    shared = hass.data["dual_smart_thermostat_climate_children"][AC]
    assert not any(shared.echo._adopting.values())

    child.calls.clear()
    hass.states.async_set(WINDOW, "off")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.HEAT
    assert hass.states.get(AC).attributes["temperature"] == 24.0


async def test_an_openings_stop_goes_out_while_a_remote_change_is_being_adopted(
    hass,
):
    """adopting drops DST's commands only while the setters run, never the stop."""
    hass.states.async_set(WINDOW, "on")
    child = await _start(hass, HVACMode.OFF, openings=[WINDOW])
    child.calls.clear()

    child.remote(mode=HVACMode.COOL)  # in a room whose window is open
    await _idle(hass)

    assert _dst(hass).state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["turn_off"]
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_floor_limit_wins_over_an_adopted_heat(hass):  # D2
    hass.states.async_set("sensor.floor", 30.0)
    child = await _start(
        hass,
        HVACMode.OFF,
        cooler=None,
        floor_sensor="sensor.floor",
        max_floor_temp=28,
        **_HEATER_COOLER_ONLY,
    )
    await _tick(hass, 18.0)
    child.calls.clear()
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert [c[0] for c in child.calls] == ["turn_off"]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_stale_sensor_stops_the_child_and_keeps_the_intent(hass, freezer):  # D3
    child = await _start(
        hass, HVACMode.HEAT, sensor_stale_duration=timedelta(minutes=2)
    )
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


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_min_cycle_still_applies_to_ticks_after_an_adoption(hass, freezer):  # D4
    """The adoption's own control run is forced, like a manual change (the user's new
    intent is not held back by the minimum cycle). Automatic ticks afterwards still
    wait for it."""
    child = await _start(hass, HVACMode.OFF, min_cycle_duration=timedelta(minutes=5))
    await _tick(hass, 22.0)
    child.remote(mode=HVACMode.HEAT, temperature=22.0)  # at the target: keeps running
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert child.calls == []

    await _tick(hass, 26.0)  # goal reached, but the minimum cycle has not run out
    assert child.calls == []

    freezer.tick(timedelta(minutes=6))
    await _tick(hass, 26.1)
    assert [c[0] for c in child.calls] == ["turn_off"]


# ------------------------------------------------- Off, and follow_device_changes: false


async def test_transition_to_off_sends_one_unscoped_off(hass):  # E1
    child = await _start(
        hass, HVACMode.HEAT, follow_device_changes=False, **_HEATER_COOLER_ONLY
    )
    child.remote(mode=HVACMode.AUTO)  # a mode no role owns; not followed
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await _idle(hass)
    assert child.calls == [("turn_off", {})]
    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_keep_alive_while_off_sends_nothing_to_climate_children(hass):  # E2
    child = await _start(
        hass,
        HVACMode.OFF,
        follow_device_changes=False,
        keep_alive=timedelta(minutes=1),
    )
    child.remote(mode=HVACMode.HEAT)
    for minutes in (2, 4, 6):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await _idle(hass)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_remote_use_while_off_is_adopted_when_following(hass):  # E3
    child = await _start(hass, HVACMode.OFF, target=22)
    await _tick(hass, 22.0)
    child.remote(mode=HVACMode.HEAT, temperature=22.0)
    await _idle(hass)
    assert (_dst(hass).state, _dst(hass).attributes["temperature"]) == (
        HVACMode.HEAT,
        22.0,
    )
    assert child.calls == []


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_remote_use_while_off_is_ignored_and_never_fought_when_not_following(
    hass,
):  # E4
    child = await _start(
        hass,
        HVACMode.OFF,
        follow_device_changes=False,
        keep_alive=timedelta(minutes=1),
    )
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


# --------------------------------- restored Off: asserted once at setup, then hands-off


async def _restored_off(hass, *, child_mode, **cfg):
    """DST restored as Off (a reload or restart) on the one AC in all four roles."""
    common.mock_restore_cache(
        hass, [State("climate.test", "off", {"temperature": 22, "fan_mode": "auto"})]
    )
    hass.states.async_set(SENSOR, 22.0)
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(hass, **{**ALL_ROLES, **cfg})
    # the child shows up (or is first seen) in its mode, after the platform is set up
    child = await common.add_fake_climate(hass, AC, child_mode)
    await _idle(hass)
    return child


async def test_restored_off_with_the_child_already_running_sends_one_off_at_setup(
    hass,
):  # G4
    child = await _restored_off(hass, child_mode=HVACMode.HEAT)
    assert _dst(hass).state == HVACMode.OFF
    assert hass.states.get(AC).state == HVACMode.OFF
    # one child, one off: not one per role
    assert [c[0] for c in child.calls].count("turn_off") == 1


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_external_heat_after_a_restored_off_is_left_alone_by_keep_alive(
    hass,
):  # G5
    child = await _restored_off(
        hass,
        child_mode=HVACMode.OFF,
        follow_device_changes=False,
        keep_alive=timedelta(minutes=2),
    )
    assert child.calls == []  # already off: nothing to assert at setup
    child.remote(mode=HVACMode.HEAT)  # the remote
    for minutes in (2, 4, 6):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await _idle(hass)
    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.HEAT


# ----------------- restart, reconnect, assumed state, automation interference, stale poll


async def test_restored_setting_is_reasserted_not_adopted_at_startup(
    hass, adoptions
):  # G1
    common.mock_restore_cache(
        hass,
        [State("climate.test", "cool", {"temperature": 24, "fan_mode": "auto"})],
    )
    hass.states.async_set(SENSOR, 28.0)  # hot: DST wants cooling
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(hass, **ALL_ROLES)
    # the child is up with other settings when DST first sees it
    child = await common.add_fake_climate(hass, AC, HVACMode.HEAT)
    await _idle(hass)
    assert child.calls  # DST re-asserted its setting
    assert adoptions == []
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] == 24.0
    assert hass.states.get(AC).state == HVACMode.COOL  # re-asserted
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
    await common.add_fake_climate(hass, AC, HVACMode.COOL)  # first sight: not a change
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.HEAT


async def test_assumed_child_adopts_nothing(hass, adoptions):  # H1
    child = await _start(hass, HVACMode.COOL, child_kwargs={"assumed": True})
    child.remote(mode=HVACMode.HEAT, temperature=28.0)  # reported anyway
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass).attributes["temperature"] != 28.0


def _automation(hass, trigger, **forced):
    """An external automation: when `trigger` says so, force the child's values."""

    @callback
    def _on_change(event):
        new, old = event.data["new_state"], event.data["old_state"]
        if new is None or old is None or not trigger(old, new):
            return
        hass.async_create_task(_force())

    async def _force():
        current = hass.states.get(AC)
        if all(
            (current.state if key == "mode" else current.attributes.get(key)) == value
            for key, value in forced.items()
        ):
            return
        hass.data["climate"].get_entity(AC).remote(**forced)

    async_track_state_change_event(hass, [AC], _on_change)


async def test_an_automation_forcing_the_fan_mode_on_each_mode_change_is_followed_without_a_storm(
    hass, adoptions
):  # I1
    child = await _start(
        hass, HVACMode.HEAT, child_kwargs={"resets_fan_on_mode_change": True}
    )
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    _automation(hass, lambda old, new: old.state != new.state, fan_mode="strong")
    child.calls.clear()
    for room in (26.0, 18.0, 26.0, 18.0, 26.0):  # DST turns the AC on and off
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
    child.remote(
        mode=HVACMode.OFF
    )  # something moves it off; the automation forces heat
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert _no_stale_push(child) == []


async def test_not_following_an_automation_forced_fan_does_not_storm(hass):  # I3
    child = await _start(
        hass,
        HVACMode.HEAT,
        follow_device_changes=False,
        child_kwargs={"resets_fan_on_mode_change": True},
    )
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "quiet"},
        blocking=True,
    )
    _automation(hass, lambda old, new: old.state != new.state, fan_mode="strong")
    child.remote(mode=HVACMode.COOL)  # triggers the automation
    await _idle(hass)
    child.calls.clear()
    for room in (22.0, 22.1, 21.9, 22.0, 22.1):
        await _tick(hass, room)
    assert [c for c in child.calls if c[0] == "set_fan_mode"] == []


# ----------------------------------------------- adoption is per changed attribute


async def test_a_remote_fan_change_does_not_import_a_target_dst_never_pushed(
    hass,
):  # review 1
    child = await _start(hass, HVACMode.HEAT, target=22)
    await _tick(hass, 26.0)  # the heater stops; the child keeps its 22
    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY, "climate.test")
    await common.async_set_temperature(hass, 20, "climate.test")  # fan pushes no target
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 20.0
    assert hass.states.get(AC).attributes["temperature"] == 22.0  # stale, never pushed
    child.calls.clear()

    child.remote(fan_mode="quiet")  # only the fan changes
    await _idle(hass)

    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert _dst(hass).attributes["temperature"] == 20.0  # not the child's stale 22
    assert _dst(hass).state == HVACMode.FAN_ONLY


async def test_a_remote_target_change_is_ignored_while_the_child_is_off(hass):
    """No role owns an off child: its target is not DST's to take."""
    child = await _start(hass, HVACMode.HEAT, target=22)
    await _tick(hass, 26.0)  # stopped
    assert hass.states.get(AC).state == HVACMode.OFF
    child.calls.clear()
    child.remote(temperature=28.0)
    await _idle(hass)
    assert _dst(hass).attributes["temperature"] == 22.0


# ----------------------------------------------------- first sight while Off (review 3)


async def test_no_off_is_asserted_before_the_restore_has_finished(hass):
    await _setup(hass, **ALL_ROLES, initial_hvac_mode=HVACMode.OFF)
    thermostat = hass.data["climate"].get_entity("climate.test")
    thermostat._follower.restored = False  # the restore is still running

    child = await common.add_fake_climate(hass, AC, HVACMode.HEAT)  # first sight
    await _idle(hass)

    assert child.calls == []
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_the_off_assertion_rechecks_the_mode_when_it_runs(hass):
    await _setup(hass, **ALL_ROLES, initial_hvac_mode=HVACMode.OFF)
    thermostat = hass.data["climate"].get_entity("climate.test")
    child = await common.add_fake_climate(hass, AC, HVACMode.HEAT)
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # first sight while Off: one off
    child.remote(mode=HVACMode.HEAT)  # then the user starts it (not followed here)
    thermostat.hvac_device.hvac_mode = HVACMode.HEAT  # and DST is no longer Off
    child.calls.clear()

    await thermostat._follower._async_assert_off()  # a task that was scheduled earlier

    assert child.calls == []


# --------------------------------------------- stale expectations (review 4) and mutants


async def test_an_ignored_command_does_not_swallow_a_later_remote_press(hass):
    """The device never obeyed heat; once it reports something else the older
    expectation is stale, so pressing heat later is the user's, not an echo."""
    child = ClimateChild(hass, AC)
    owner = object()
    child.ports.add(type("P", (), {"owner": owner})())
    off = State(AC, "off", {})
    child.echo.expect(owner, {"mode": "heat"})  # commanded, never reported
    assert child.echo.external(owner, off, State(AC, "cool", {})).changed == {
        "mode"
    }  # remote cool
    assert child.echo.external(
        owner, State(AC, "cool", {}), State(AC, "heat", {})
    ).changed == {
        "mode"
    }  # remote heat: not swallowed by the stale entry


async def test_a_failing_service_call_removes_its_expectation(hass, adoptions):  # M4
    child = await _start(hass, HVACMode.HEAT)
    await _tick(hass, 26.0)  # stopped
    child.calls.clear()

    async def fail(hvac_mode):
        raise RuntimeError("the device is offline")

    real = child.async_set_hvac_mode
    child.async_set_hvac_mode = fail
    await _tick(hass, 18.0)  # DST commands heat; the call fails
    child.async_set_hvac_mode = real
    child.remote(mode=HVACMode.HEAT)  # the user presses heat
    await _idle(hass)

    assert adoptions == ["heat"]  # not taken for the echo of the command that failed


async def test_several_commands_in_flight_are_all_matched_as_echoes(
    hass, adoptions
):  # M10
    child = await _start(hass, HVACMode.HEAT)  # running
    child.hold_echoes()
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    await common.async_set_temperature(hass, 25, "climate.test")
    assert [c[0] for c in child.calls] == [
        "set_temperature",
        "set_fan_mode",
        "set_temperature",
    ]  # three commands in flight, none reported yet
    child.flush_echoes([2, 0, 1], context="foreign")  # all arrive later, reordered
    await _idle(hass)
    assert adoptions == []


async def test_a_child_event_before_the_restore_completes_adopts_nothing(
    hass, adoptions
):  # M9
    child = await _start(hass, HVACMode.HEAT)
    thermostat = hass.data["climate"].get_entity("climate.test")
    thermostat._follower.restored = False
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).state == HVACMode.HEAT


# ------------------------------------------- the adoption's forced run and min cycle (M6)


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_adoption_run_is_forced_so_a_safety_stop_is_not_held_by_min_cycle(
    hass,
):  # M6
    hass.states.async_set(WINDOW, "on")
    child = await _start(
        hass,
        HVACMode.OFF,
        openings=[WINDOW],
        min_cycle_duration=timedelta(minutes=5),
    )
    child.calls.clear()
    child.remote(mode=HVACMode.HEAT)  # inside the minimum cycle of the child
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["turn_off"]  # the window wins at once


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_adoption_run_does_not_restart_inside_min_cycle(hass, freezer):  # M6
    child = await _start(hass, HVACMode.HEAT, min_cycle_duration=timedelta(minutes=5))
    freezer.tick(timedelta(minutes=6))
    await _tick(hass, 26.0)  # the heater stops (it ran long enough)
    assert hass.states.get(AC).state == HVACMode.OFF
    await _tick(hass, 18.0)  # cold, but the minimum cycle holds the restart
    assert child.calls == [("turn_off", {})]
    child.calls.clear()

    child.remote(fan_mode="quiet")  # the user touches the device: a forced run
    await _idle(hass)
    assert "set_hvac_mode" not in [c[0] for c in child.calls]  # compressor protected

    freezer.tick(timedelta(minutes=6))
    await _tick(hass, 18.1)
    assert ("set_hvac_mode", {"hvac_mode": HVACMode.HEAT}) in child.calls


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_adoption_run_does_not_short_cycle_a_child_that_just_started(
    hass, freezer
):  # M6
    child = await _start(hass, HVACMode.OFF, min_cycle_duration=timedelta(minutes=5))
    await _tick(hass, 26.0)  # hot room
    child.calls.clear()

    child.remote(mode=HVACMode.HEAT, temperature=22.0)  # goal already reached
    await _idle(hass)
    assert _dst(hass).state == HVACMode.HEAT
    assert child.calls == []  # it started a moment ago: no stop inside the cycle

    freezer.tick(timedelta(minutes=6))
    await _tick(hass, 26.1)
    assert [c[0] for c in child.calls] == ["turn_off"]  # an ordinary tick stops it


# ------------------------------------------------ a combined set_temperature(hvac_mode)


async def test_set_temperature_with_a_mode_sends_the_mode_once_and_the_final_target(
    hass,
):
    """HA sets the mode first (old target), then the temperature. On a device that
    has not reported heat yet that used to send heat twice and the old target too."""
    child = await _start(hass, HVACMode.OFF, heater_setpoint_offset=1)
    await _tick(hass, 18.0)  # cold: heating is wanted
    child.calls.clear()
    child.hold_echoes()  # a slow device: nothing is reported meanwhile

    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.test", "hvac_mode": "heat", "temperature": 31},
        blocking=True,
    )
    await _idle(hass)

    assert child.calls == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.HEAT}),
        (
            "set_temperature",
            {"temperature": 30.0},
        ),  # 31 + 1, clamped to the child's max
    ]


async def test_a_turn_on_lands_the_selected_fan_on_a_device_slow_to_report(hass):
    """DST Off, fan picked (recorded only), then heat: the child still reports off
    when the fan is re-applied, but DST's own mode command counts as running."""
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, 18.0)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    assert child.calls == []  # Off: recorded, nothing sent
    child.hold_echoes()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)

    assert [c[0] for c in child.calls] == [
        "set_hvac_mode",
        "set_temperature",
        "set_fan_mode",
    ]
    assert child.calls[-1][1] == {"fan_mode": "strong"}


async def test_the_last_command_wins_over_an_automation_that_keeps_the_fan_quiet(
    hass,
):
    child = await _start(hass, HVACMode.OFF, child_kwargs={"fan_mode": "quiet"})
    await _tick(hass, 18.0)
    _automation(hass, lambda old, new: True, fan_mode="quiet")
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)

    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls  # DST sent it
    assert hass.states.get(AC).attributes["fan_mode"] == "quiet"  # automation flipped
    assert _dst(hass).attributes["fan_mode"] == "quiet"  # adopted: last wins


async def _stale_fan_display(hass, **cfg):
    """A restart: the child was already there, saying quiet; DST restored strong."""
    common.mock_restore_cache(
        hass, [State("climate.test", "off", {"temperature": 22, "fan_mode": "strong"})]
    )
    hass.states.async_set(SENSOR, 22.0)
    hass.states.async_set("sensor.hum", 50.0)
    attrs = {"fan_modes": ["quiet", "strong", "auto"], "fan_mode": "quiet"}
    hass.states.async_set(AC, "off", {**attrs, "hvac_modes": ["off", "heat", "cool"]})
    await _setup(hass, **{**ALL_ROLES, **cfg})
    await _idle(hass)
    assert _dst(hass).attributes["fan_mode"] == "strong"  # stale
    hass.states.async_remove(AC)  # the integration reloads: the real entity is new
    await _idle(hass)
    child = await common.add_fake_climate(hass, AC, fan_mode="quiet")
    await _idle(hass)
    return child


async def test_a_child_first_seen_shows_its_fan_mode_and_sends_nothing(hass):
    child = await _stale_fan_display(hass)
    assert _dst(hass).attributes["fan_mode"] == "quiet"
    assert child.calls == []


async def test_first_sight_leaves_the_display_alone_when_not_following(hass):
    child = await _stale_fan_display(hass, follow_device_changes=False)
    assert _dst(hass).attributes["fan_mode"] == "strong"
    assert child.calls == []


@pytest.mark.parametrize(
    ("start", "to", "room"),
    [
        (HVACMode.FAN_ONLY, HVACMode.COOL, 26.0),
        (HVACMode.COOL, HVACMode.FAN_ONLY, 26.0),
    ],
)
async def test_switching_between_roles_of_one_child_sends_no_off_in_between(
    hass, start, to, room
):
    child = await _start(hass, HVACMode.OFF)
    await _tick(hass, room)
    await common.async_set_hvac_mode(hass, start, "climate.test")
    await _idle(hass)
    assert hass.states.get(AC).state == start
    child.calls.clear()
    await common.async_set_hvac_mode(hass, to, "climate.test")
    await _idle(hass)
    assert "turn_off" not in [c[0] for c in child.calls], child.calls
    assert hass.states.get(AC).state == to


async def test_off_sends_exactly_one_off_to_a_shared_child(hass):
    child = await _start(hass, HVACMode.COOL)
    assert hass.states.get(AC).state == HVACMode.COOL
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await _idle(hass)
    assert [c[0] for c in child.calls].count("turn_off") == 1


async def test_a_combined_mode_and_target_call_that_switches_roles_sends_no_off(hass):
    child = await _start(hass, HVACMode.COOL)  # cooling, room above target
    assert hass.states.get(AC).state == HVACMode.COOL
    child.calls.clear()
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {"entity_id": "climate.test", "hvac_mode": "heat", "temperature": 30},
        blocking=True,
    )
    await _idle(hass)
    assert "turn_off" not in [c[0] for c in child.calls], child.calls
    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_no_entry_point_stops_a_shared_child_before_the_new_role_starts(hass):
    """The pass belongs to the device, not to each caller: a bare control call too."""
    child = await _start(hass, HVACMode.HEAT, follow_device_changes=False)
    child.remote(mode=HVACMode.FAN_ONLY)  # the device runs a role DST is not in
    entity = hass.data["climate"].get_entity("climate.test")
    entity.environment.set_temperature_target(30)  # the heater has demand
    child.calls.clear()
    await entity.hvac_device.async_control_hvac(force=True)
    await _idle(hass)
    assert "turn_off" not in [c[0] for c in child.calls], child.calls
    assert ("set_hvac_mode", {"hvac_mode": HVACMode.HEAT}) in child.calls


# ----------------------------------------- min cycle protects a climate's compressor


async def _heating_with_min_cycle(hass, freezer, **extra):
    """Heating on one climate with a 5 min minimum cycle, running for long enough."""
    hass.states.async_set(SENSOR, 18.0)
    hass.states.async_set("sensor.hum", 50.0)
    await _setup(
        hass,
        **{
            **ALL_ROLES,
            "initial_hvac_mode": HVACMode.HEAT,
            "min_cycle_duration": {"seconds": 300},
            **extra,
        },
    )
    child = await common.add_fake_climate(hass, AC)
    freezer.tick(timedelta(seconds=400))  # the climate has been off for long
    await common.async_set_temperature(hass, 22, "climate.test")
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.HEAT
    child.calls.clear()
    return child


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_target_change_does_not_stop_a_climate_inside_its_min_cycle(
    hass, freezer
):
    child = await _heating_with_min_cycle(hass, freezer)
    await common.async_set_temperature(hass, 15, "climate.test")  # goal reached
    await _idle(hass)
    assert "turn_off" not in [c[0] for c in child.calls]
    assert hass.states.get(AC).state == HVACMode.HEAT  # held

    freezer.tick(timedelta(seconds=301))  # the next tick acts on it
    await _tick(hass, 18.1)
    assert "turn_off" in [c[0] for c in child.calls]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_target_change_does_not_restart_a_climate_inside_its_min_cycle(
    hass, freezer
):
    child = await _heating_with_min_cycle(hass, freezer)
    await common.async_set_temperature(hass, 15, "climate.test")
    freezer.tick(timedelta(seconds=301))
    await _tick(hass, 18.1)  # the held stop goes out
    assert hass.states.get(AC).state == HVACMode.OFF
    child.calls.clear()

    await common.async_set_temperature(hass, 25, "climate.test")  # wants heat again
    await _idle(hass)
    assert "set_hvac_mode" not in [c[0] for c in child.calls]  # stopped just now
    assert hass.states.get(AC).state == HVACMode.OFF

    freezer.tick(timedelta(seconds=301))
    await _tick(hass, 18.2)  # the next tick starts it
    assert hass.states.get(AC).state == HVACMode.HEAT


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_off_stops_a_climate_inside_its_min_cycle(hass, freezer):
    child = await _heating_with_min_cycle(hass, freezer)
    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await _idle(hass)
    assert [c[0] for c in child.calls].count("turn_off") == 1


# ----------------------- a device answering our command with its power-on default


async def _turned_on_with_fan_picked(hass):
    child = await _start(hass, HVACMode.OFF, child_kwargs={"fan_mode": "quiet"})
    await _tick(hass, 18.0)
    await hass.services.async_call(
        "climate",
        "set_fan_mode",
        {"entity_id": "climate.test", "fan_mode": "strong"},
        blocking=True,
    )
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    assert ("set_fan_mode", {"fan_mode": "strong"}) in child.calls
    return child


async def test_a_power_on_default_under_our_own_context_is_resent_not_adopted(
    hass, adoptions
):
    child = await _turned_on_with_fan_picked(hass)
    child.power_on_default("auto")  # reported under the context of our command
    await _idle(hass)
    assert adoptions == []
    assert _dst(hass).attributes["fan_mode"] == "strong"
    assert [c for c in child.calls if c[0] == "set_fan_mode"] == [
        ("set_fan_mode", {"fan_mode": "strong"})
    ] * 2
    assert hass.states.get(AC).attributes["fan_mode"] == "strong"


async def test_the_resend_is_bounded(hass, adoptions):
    child = await _turned_on_with_fan_picked(hass)
    child.power_on_default("auto")
    await _idle(hass)
    child.power_on_default("auto")  # the device keeps doing it
    await _idle(hass)
    assert len([c for c in child.calls if c[0] == "set_fan_mode"]) == 2
    assert adoptions == []


async def test_an_automation_fan_after_the_reset_is_adopted(hass, adoptions):
    child = await _turned_on_with_fan_picked(hass)
    child.power_on_default("auto")
    await _idle(hass)
    child.remote(fan_mode="quiet")  # an automation's or the UI's own context
    await _idle(hass)
    assert _dst(hass).attributes["fan_mode"] == "quiet"  # last command wins


async def test_a_child_the_run_stops_gets_no_setpoint_push_first(hass):
    child = await _start(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 18, "climate.test")  # goal reached
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["turn_off"]


async def test_a_child_the_run_keeps_running_gets_its_new_setpoint(hass):
    child = await _start(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 25, "climate.test")  # still heating
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["set_temperature"]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_zero_keep_alive_does_not_switch_the_min_cycle_off(hass, freezer):
    """keep_alive is stored as 0:00:00 when unset in the UI (#668)."""
    child = await _heating_with_min_cycle(hass, freezer, keep_alive={"seconds": 0})
    await common.async_set_temperature(hass, 15, "climate.test")
    await _idle(hass)
    assert "turn_off" not in [c[0] for c in child.calls]


def _mentions(child, owner) -> list[str]:
    """Every place in the child's per-owner records that still names `owner`."""
    found = []
    for name, value in {**vars(child), **vars(child.echo)}.items():
        if isinstance(value, dict):
            if owner in value:
                found.append(name)
            for inner in value.values():
                if isinstance(inner, dict):
                    for entries in inner.values():
                        if any(
                            getattr(e, "origin", None) is owner
                            or (isinstance(e, tuple) and e[1:2] == (owner,))
                            for e in entries
                        ):
                            found.append(f"{name}[..]")
        elif isinstance(value, set) and owner in value:
            found.append(name)
    return found


async def test_releasing_one_of_two_thermostats_leaves_no_trace_of_it_on_the_child(
    hass,
):
    await _start_two(hass)
    child = peek_climate_child(hass, AC)  # the shared record, not the fake entity
    await _tick(hass, 18.0)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test2")
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")
    await _idle(hass)
    gone = hass.data["climate"].get_entity("climate.test2")
    owner = gone.features
    assert _mentions(child, owner)  # it was there

    gone.hvac_device.release()

    assert _mentions(child, owner) == []
