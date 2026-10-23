"""Following changes made on the device itself (issue #281, phase 6)."""

from unittest.mock import patch

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import HomeAssistant, State
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.climate import DualSmartThermostat
from custom_components.dual_smart_thermostat.const import DOMAIN
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
