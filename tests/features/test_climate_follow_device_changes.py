"""Following changes made on the device itself (issue #281, phase 6)."""

from unittest.mock import patch

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import Context, HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.climate import DualSmartThermostat
from custom_components.dual_smart_thermostat.const import DOMAIN
from custom_components.dual_smart_thermostat.hvac_device.entity_port import ClimateChild
from tests import common

AC = "climate.test_ac"
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
    # (the two adoptions this must cause are asserted once adoption exists)


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
