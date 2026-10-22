"""Tests for climate entities used as device roles (issue #281)."""

from datetime import timedelta

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from custom_components.dual_smart_thermostat.hvac_device.entity_port import (
    ClimatePort,
    SwitchPort,
    make_port,
)
from custom_components.dual_smart_thermostat.hvac_device.generic_hvac_device import (
    GenericHVACDevice,
)
from tests import common, setup_switch


async def test_fake_child_follows_real_climate_services(hass: HomeAssistant) -> None:
    """The fake child is driven by the real climate services."""
    child = await common.add_fake_climate(hass, "climate.test_ac")

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ac", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ac").state == HVACMode.COOL
    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_fake_assumed_child_never_confirms(hass: HomeAssistant) -> None:
    """An assumed-state child records the call but its state never changes."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.test_ir", "hvac_mode": HVACMode.COOL},
        blocking=True,
    )

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF
    assert hass.states.get("climate.test_ir").attributes["assumed_state"] is True
    assert child.calls


async def test_make_port_returns_switch_port_for_switch_like(
    hass: HomeAssistant,
) -> None:
    """Switch-like entities get a SwitchPort that reads on/off."""
    hass.states.async_set("switch.heater", STATE_OFF)
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)
    assert isinstance(port, SwitchPort)
    assert port.is_active is False
    hass.states.async_set("switch.heater", STATE_ON)
    assert port.is_active is True


async def test_switch_port_valve_is_active_when_open(hass: HomeAssistant) -> None:
    """A valve counts as active while open."""
    hass.states.async_set("valve.loop", "open")
    port = make_port(hass, "valve.loop", role_mode=lambda: None, target=lambda: None)
    assert port.is_active is True


async def test_switch_port_skips_command_when_unavailable(
    hass: HomeAssistant,
) -> None:
    """No service call goes to an unavailable switch."""
    calls = setup_switch(hass, True, "switch.heater")
    hass.states.async_set("switch.heater", "unavailable")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)

    await port.async_turn_off(None)

    assert calls == []


def _port(hass, entity_id, mode, target=lambda: 24.0):
    return make_port(hass, entity_id, role_mode=lambda: mode, target=target)


async def test_climate_port_is_active_follows_child_mode(hass: HomeAssistant) -> None:
    """Active is derived from the child's mode, so roles exclude each other."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    assert isinstance(cool, ClimatePort)
    assert cool.is_active is True
    assert heat.is_active is False  # one mode at a time, by construction


async def test_turn_on_sets_mode_then_pushes_target(hass: HomeAssistant) -> None:
    """Turning on sets the mode first, then the target."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, target=lambda: 24.0)

    await cool.async_turn_on(None)

    assert child.calls == [
        ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}),
        ("set_temperature", {"temperature": 24.0}),
    ]
    assert cool.is_active is True


async def test_fan_role_sends_no_target(hass: HomeAssistant) -> None:
    """A role without a target only sets the mode."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    fan = _port(hass, "climate.test_ac", HVACMode.FAN_ONLY, target=lambda: None)

    await fan.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_turn_off_only_when_child_is_in_my_mode(hass: HomeAssistant) -> None:
    """An idle role cannot stop a child serving another role."""
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)

    await cool.async_turn_off(None)  # idle cooler must not stop the heater
    assert child.calls == []
    assert heat.is_active is True

    await heat.async_turn_off(None)
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF


async def test_stop_turns_the_child_off_in_any_mode(hass: HomeAssistant) -> None:
    """Off means off: stop ignores which role owns the current mode."""
    child = await common.add_fake_climate(hass, "climate.test_ac", HVACMode.FAN_ONLY)
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT)  # no role owns fan_only here

    await heat.async_turn_off(None)  # role stop: not its mode, nothing happens
    assert child.calls == []

    await heat.async_stop(None)  # Off means off
    assert child.calls == [("turn_off", {})]
    assert hass.states.get("climate.test_ac").state == HVACMode.OFF

    await heat.async_stop(None)  # already off: nothing more is sent
    assert child.calls == [("turn_off", {})]


async def test_stop_on_a_switch_only_acts_when_it_is_running(
    hass: HomeAssistant,
) -> None:
    """A switch's stop keeps today's behaviour: only when it is on."""
    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)
    await port.async_stop(None)
    assert calls == []

    hass.states.async_set("switch.heater", STATE_ON)
    await port.async_stop(None)
    assert len(calls) == 1


async def test_unavailable_child_gets_no_commands(hass: HomeAssistant) -> None:
    """No service call goes to an unavailable child."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    hass.states.async_set("climate.test_ac", "unavailable")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert child.calls == []
    assert cool.is_active is False


async def test_unsupported_mode_is_not_sent(hass: HomeAssistant, caplog) -> None:
    """A mode the child does not list is logged once and not sent."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    child.async_write_ha_state()
    dry = _port(hass, "climate.test_ac", HVACMode.DRY)

    await dry.async_turn_on(None)
    await dry.async_turn_on(None)

    assert child.calls == []
    assert caplog.text.count("does not support") == 1  # logged once


async def test_assumed_child_uses_commanded_mode_not_reported_state(
    hass: HomeAssistant,
) -> None:
    """An IR child never confirms: DST's own last command is the truth."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    assert cool.is_active is False
    await cool.async_turn_on(None)

    assert hass.states.get("climate.test_ir").state == HVACMode.OFF  # no feedback
    assert cool.is_active is True  # DST's own record

    await cool.async_turn_off(None)
    assert cool.is_active is False
    assert [c[0] for c in child.calls] == [
        "set_hvac_mode",
        "set_temperature",
        "turn_off",
    ]


async def test_ran_long_enough_uses_child_mode_age(
    hass: HomeAssistant, freezer
) -> None:
    """Min cycle is measured on the child's time in its current mode."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    assert cool.ran_long_enough(timedelta(minutes=5)) is False
    freezer.tick(timedelta(minutes=6))
    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_failed_command_rolls_back_the_assumed_record(
    hass: HomeAssistant,
) -> None:
    """A failed mode command must not leave DST believing it is on."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)

    async def boom(*_, **__):
        raise RuntimeError("device offline")

    child.async_set_hvac_mode = boom  # the real service now raises
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    await cool.async_turn_on(None)

    assert cool.is_active is False


AC = "climate.test_ac"
SENSOR = "sensor.room_temperature"
HEATER = "switch.room_heater"


async def _setup(hass, **config):
    hass.config.units = METRIC_SYSTEM
    base = {
        "platform": DOMAIN,
        "name": "test",
        "target_sensor": SENSOR,
        "cold_tolerance": 0.3,
        "hot_tolerance": 0.3,
    }
    assert await async_setup_component(hass, CLIMATE, {CLIMATE: {**base, **config}})
    await hass.async_block_till_done()


async def test_climate_cooler_cycles_with_switch_heater(hass: HomeAssistant) -> None:
    """Mixed setup: relay heater and climate cooler in one thermostat."""
    heater_calls = setup_switch(hass, False, HEATER)
    hass.states.async_set(SENSOR, 22.0)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": HVACMode.COOL}) in child.calls
    assert hass.states.get(AC).state == HVACMode.COOL
    assert hass.states.get("climate.test").attributes["hvac_action"] == "cooling"

    hass.states.async_set(SENSOR, 23.0)  # below target - tolerance
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert heater_calls == []  # the relay heater was never involved


async def test_climate_heater_turns_on_and_off(hass: HomeAssistant) -> None:
    """A climate heater gets mode and target, then turns off at the goal."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert ("set_temperature", {"temperature": 22.0}) in child.calls

    hass.states.async_set(SENSOR, 23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_hvac_off_stops_the_child(hass: HomeAssistant) -> None:
    """Setting the thermostat Off turns the climate child off."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_climate_respects_min_cycle_duration(
    hass: HomeAssistant, freezer
) -> None:
    """The child's time in its mode gates turning it off."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        min_cycle_duration=timedelta(minutes=5),
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 24.0)  # goal reached, but too soon to stop
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=6))
    hass.states.async_set(SENSOR, 24.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF


async def test_assumed_state_child_is_not_commanded_twice(
    hass: HomeAssistant,
) -> None:
    """IR device: state never confirms, DST must still know it is cooling."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, assumed=True)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (26.5, 27.0, 26.8):  # more sensor ticks while "on"
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("set_hvac_mode") == 1


async def test_unavailable_child_receives_no_commands(hass: HomeAssistant) -> None:
    """No calls while the child is unavailable."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC)
    hass.states.async_set(AC, "unavailable")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == []


@pytest.mark.parametrize(
    ("role", "extra", "mode"),
    [
        ("fan", {"heater": HEATER}, HVACMode.FAN_ONLY),
        (
            "dryer",
            {"heater": HEATER, "humidity_sensor": "sensor.hum", "target_humidity": 40},
            HVACMode.DRY,
        ),
    ],
)
async def test_fan_and_dryer_roles_use_their_climate_mode(
    hass: HomeAssistant, role, extra, mode
) -> None:
    """Fan and dryer roles drive the child's fan_only / dry modes."""
    hass.states.async_set(SENSOR, 26.0)
    hass.states.async_set("sensor.hum", 60.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, **extra, **{role: AC}, initial_hvac_mode=mode)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_hvac_mode(hass, mode, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    assert ("set_hvac_mode", {"hvac_mode": mode}) in child.calls
    assert not [c for c in child.calls if c[0] == "set_temperature"]


def test_role_mode_is_abstract() -> None:
    """A device class cannot be built without a role mode."""
    assert "role_mode" in GenericHVACDevice.__abstractmethods__


async def test_hvac_off_stops_a_child_running_a_mode_no_role_owns(
    hass: HomeAssistant,
) -> None:
    """Off means off, even for a mode set from a remote that no role owns."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)  # no fan role

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert [c[0] for c in child.calls].count("turn_off") == 1


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_keep_alive_in_off_stops_a_child_set_to_a_foreign_mode(
    hass: HomeAssistant,
) -> None:
    """Keep-alive while Off also enforces Off on a child in a foreign mode."""
    hass.states.async_set(SENSOR, 20.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, HVACMode.FAN_ONLY)

    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF
    assert ("turn_off", {}) in child.calls


async def test_hvac_off_sends_nothing_to_a_switch_that_is_already_off(
    hass: HomeAssistant,
) -> None:
    """Switch behaviour is unchanged: Off only stops a running switch."""
    calls = setup_switch(hass, False, HEATER)
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=HEATER, cooler=AC, initial_hvac_mode=HVACMode.COOL)
    await common.add_fake_climate(hass, AC)

    await common.async_set_hvac_mode(hass, HVACMode.OFF, "climate.test")
    await hass.async_block_till_done()

    assert calls == []


async def test_valve_ran_long_enough_when_open(hass: HomeAssistant, freezer) -> None:
    """A valve reports open/closed, so min cycle must be measured against open."""
    hass.states.async_set("valve.loop", "open")
    port = make_port(hass, "valve.loop", role_mode=lambda: None, target=lambda: None)
    freezer.tick(timedelta(minutes=6))

    assert port.ran_long_enough(timedelta(minutes=5)) is True


async def test_assumed_child_keep_alive_resend_does_not_reset_min_cycle(
    hass: HomeAssistant, freezer
) -> None:
    """Re-sending the mode it is already in must not restart the cycle clock."""
    await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)
    await cool.async_turn_on(None)

    freezer.tick(timedelta(minutes=3))
    await cool.async_turn_on(None)  # keep-alive resend
    freezer.tick(timedelta(minutes=3))

    assert cool.ran_long_enough(timedelta(minutes=5)) is True

    await cool.async_turn_off(None)
    freezer.tick(timedelta(minutes=3))
    await cool.async_stop(None, force=True)  # keep-alive resend of off
    freezer.tick(timedelta(minutes=3))

    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_forced_stop_resends_off_to_an_assumed_child(
    hass: HomeAssistant,
) -> None:
    """The IR device may have missed the first off, so keep-alive resends it."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    await cool.async_stop(None)  # record already says off: nothing sent
    assert child.calls == []

    await cool.async_stop(None, force=True)
    await cool.async_stop(None, force=True)
    assert child.calls == [("turn_off", {}), ("turn_off", {})]


async def test_forced_stop_on_a_switch_always_turns_it_off(
    hass: HomeAssistant,
) -> None:
    """Keep-alive semantics for switches: unconditional turn_off."""
    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)

    await port.async_stop(None, force=True)

    assert len(calls) == 1


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_keep_alive_in_off_resends_to_assumed_child_and_once_to_switch(
    hass: HomeAssistant,
) -> None:
    """Each Off keep-alive: one turn_off per switch, one per assumed child."""
    hass.states.async_set(SENSOR, 20.0)
    heater_calls = setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert len(heater_calls) == 2
    assert [c[0] for c in child.calls].count("turn_off") == 2
