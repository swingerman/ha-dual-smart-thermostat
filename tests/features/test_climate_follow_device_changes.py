"""Following changes made on the device itself (issue #281, phase 6)."""

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import Context, HomeAssistant, State, callback
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.climate import DualSmartThermostat
from custom_components.dual_smart_thermostat.const import DOMAIN
from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimateChild
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
    assert child.calls == []
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
    # pushed to the running child (17 is below the room, so it then stops: normal control)
    assert child.calls[0] == ("set_temperature", {"temperature": 17.0})
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


async def test_two_thermostats_on_one_child_follow_each_other_without_fighting(
    hass, adoptions
):  # M1
    child = await _start_two(hass)
    await _tick(hass, 18.0)
    child.calls.clear()
    await common.async_set_hvac_mode(hass, HVACMode.HEAT, "climate.test")  # A commands
    await _idle(hass)
    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]
    assert _dst(hass, "climate.test2").state == HVACMode.HEAT  # B adopted, no command
    await _tick(hass, 22.0)
    child.calls.clear()
    child.remote(mode=HVACMode.COOL)
    await _idle(hass)
    assert _dst(hass).state == HVACMode.COOL
    assert _dst(hass, "climate.test2").state == HVACMode.COOL
    assert _no_stale_push(child) == []  # no ping-pong


async def test_one_thermostats_adoption_does_not_delay_the_others_safety_stop(
    hass,
):  # M2
    hass.states.async_set(WINDOW, "on")  # B's window is open
    child = await _start_two(hass, second={"openings": [WINDOW]})
    child.remote(mode=HVACMode.HEAT)
    await _idle(hass)
    assert hass.states.get(AC).state == HVACMode.OFF  # B stopped it at once
    assert _dst(hass, "climate.test2").state == HVACMode.HEAT  # B keeps the intent
    assert _dst(hass).state == HVACMode.OFF  # A followed the stop
    assert [c[0] for c in child.calls] == ["turn_off"]  # one stop in total


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
    assert not any(shared._adopting.values())

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
