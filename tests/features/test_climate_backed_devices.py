"""Tests for climate entities used as device roles (issue #281)."""

from datetime import timedelta
import logging

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN, ControlStyle
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


def _port(hass, entity_id, mode, target=lambda: 24.0, *, offset=0.0):
    # offset is read lazily through a callable (a heat pump switches between two keys)
    return make_port(
        hass,
        entity_id,
        role_mode=lambda: mode,
        target=target,
        offset=lambda: offset,
    )


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
    await cool.async_stop(None, keep_alive=True)  # keep-alive resend of off
    freezer.tick(timedelta(minutes=3))

    assert cool.ran_long_enough(timedelta(minutes=5)) is True


async def test_keep_alive_stop_resends_off_to_an_assumed_child(
    hass: HomeAssistant,
) -> None:
    """The IR device may have missed the first off, so keep-alive resends it."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL)

    await cool.async_stop(None)  # record already says off: nothing sent
    assert child.calls == []

    await cool.async_stop(None, keep_alive=True)
    await cool.async_stop(None, keep_alive=True)
    assert child.calls == [("turn_off", {}), ("turn_off", {})]


async def test_keep_alive_stop_on_a_switch_only_acts_when_it_is_running(
    hass: HomeAssistant,
) -> None:
    """A switch's state is trustworthy: keep-alive stop keeps master's rule (#587)."""
    calls = setup_switch(hass, False, "switch.heater")
    port = make_port(hass, "switch.heater", role_mode=lambda: None, target=lambda: None)

    await port.async_stop(None, keep_alive=True)

    assert calls == []


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


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lone_assumed_climate_in_off_gets_turn_off_each_keep_alive(
    hass: HomeAssistant,
) -> None:
    """Single-device thermostat: the IR child is told off on every tick."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )
    child = await common.add_fake_climate(hass, AC, assumed=True)

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert [c[0] for c in child.calls].count("turn_off") == 2


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_lone_switch_in_off_keep_alive_sends_nothing_when_already_off(
    hass: HomeAssistant,
) -> None:
    """Master behaviour (#587): a lone switch is only stopped if it is running."""
    hass.states.async_set(SENSOR, 20.0)
    calls = setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.OFF,
    )

    for minutes in (2, 4):
        common.async_fire_time_changed(
            hass, dt_util.utcnow() + timedelta(minutes=minutes)
        )
        await hass.async_block_till_done()

    assert calls == []


async def test_offset_is_added_to_the_pushed_target(hass: HomeAssistant) -> None:
    """The role's offset is added as-is to the pushed target."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    cool = _port(hass, "climate.test_ac", HVACMode.COOL, lambda: 24.0, offset=-2.0)

    await cool.async_turn_on(None)

    assert ("set_temperature", {"temperature": 22.0}) in child.calls


async def test_pushed_target_is_clamped_to_the_child_range(hass: HomeAssistant) -> None:
    """Target plus offset never leaves the child's min/max."""
    child = await common.add_fake_climate(hass, "climate.test_ac")  # 16..30
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 29.0, offset=5.0)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 30}) in child.calls


async def test_pushed_target_is_rounded_to_the_child_step(hass: HomeAssistant) -> None:
    """The pushed value is rounded to the child's target_temp_step."""
    child = await common.add_fake_climate(hass, "climate.test_ac")  # step 0.5
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 21.3)

    await heat.async_turn_on(None)

    assert ("set_temperature", {"temperature": 21.5}) in child.calls


async def test_target_not_resent_when_child_already_has_it(hass: HomeAssistant) -> None:
    """A value the child already reports is not pushed again."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_target_temperature = 22.0
    child.async_write_ha_state()
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 22.0)

    await heat.async_turn_on(None)

    assert [c[0] for c in child.calls] == ["set_hvac_mode"]


async def test_assumed_child_target_resent_only_after_a_mode_change(
    hass: HomeAssistant,
) -> None:
    """An assumed child cannot report its target: DST's last push stands in."""
    child = await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    cool = _port(hass, "climate.test_ir", HVACMode.COOL, lambda: 24.0)

    await cool.async_turn_on(None)
    await cool.async_turn_on(None)  # keep-alive resend of the same mode
    assert [c[0] for c in child.calls].count("set_temperature") == 1

    await cool.async_turn_off(None)
    await cool.async_turn_on(None)  # mode changed: the device may have dropped it
    assert [c[0] for c in child.calls].count("set_temperature") == 2


async def test_target_change_while_engaged_is_mirrored(hass: HomeAssistant) -> None:
    """A new target reaches the child that is serving the role."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_temperature(hass, 23, "climate.test")
    await hass.async_block_till_done()

    assert child.calls == [("set_temperature", {"temperature": 23.0})]


async def test_unchanged_target_is_not_resent_on_sensor_ticks(
    hass: HomeAssistant,
) -> None:
    """Sync is idempotent: sensor ticks send nothing when the target is current."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    for temp in (20.1, 20.2, 20.3):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    assert child.calls == []


async def test_preset_target_is_mirrored(hass: HomeAssistant) -> None:
    """Switching preset changes the target, which is mirrored."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        away={"temperature": 17},
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    child.calls.clear()

    await common.async_set_preset_mode(hass, "away", "climate.test")
    await hass.async_block_till_done()

    assert ("set_temperature", {"temperature": 17.0}) in child.calls


async def test_target_is_never_pushed_before_the_role_owns_the_mode(
    hass: HomeAssistant,
) -> None:
    """Child is in a mode this role does not own: mode first, then target."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)
    child = await common.add_fake_climate(hass, AC, HVACMode.COOL)  # not our mode

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert [c[0] for c in child.calls] == ["set_hvac_mode", "set_temperature"]


async def test_setpoint_style_never_turns_the_child_off_at_target(
    hass: HomeAssistant,
) -> None:
    """The child regulates itself: DST does not stop it when the goal is met."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass, heater=AC, initial_hvac_mode=HVACMode.HEAT, control_style="setpoint"
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(SENSOR, 25.0)  # far above target: on_off would stop here
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    assert "turn_off" not in [c[0] for c in child.calls]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_setpoint_style_ignores_min_cycle_duration(hass: HomeAssistant) -> None:
    """DST adds no cycle limit on a self-regulating child."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        min_cycle_duration=timedelta(minutes=30),
        openings=["binary_sensor.window"],
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    # An opening must pause the child at once, not after the 30 minute "cycle".
    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(SENSOR, 20.1)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_setpoint_style_opening_pauses_and_restores_the_child(
    hass: HomeAssistant,
) -> None:
    """Openings and restore go through the unchanged controller."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        openings=["binary_sensor.window"],
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set("binary_sensor.window", "on")
    hass.states.async_set(SENSOR, 20.1)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child.calls.clear()
    hass.states.async_set("binary_sensor.window", "off")
    hass.states.async_set(SENSOR, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT
    # the child kept its 22 degree setpoint, so only the mode is restored
    assert child.calls == [("set_hvac_mode", {"hvac_mode": HVACMode.HEAT})]


async def test_setpoint_style_each_role_uses_its_own_offset(
    hass: HomeAssistant,
) -> None:
    """Heater and cooler children get their own role's offset only."""
    heater_ac = "climate.test_heater_ac"
    hass.states.async_set(SENSOR, 18.0)
    await _setup(
        hass,
        heater=heater_ac,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.HEAT,
        control_style="setpoint",
        heater_setpoint_offset=3,
        cooler_setpoint_offset=-5,
    )
    heater_child = await common.add_fake_climate(hass, heater_ac)
    cooler_child = await common.add_fake_climate(hass, AC)

    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 25.0}) in heater_child.calls  # 22 + 3

    hass.states.async_set(SENSOR, 28.0)
    await common.async_set_hvac_mode(hass, HVACMode.COOL, "climate.test")
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert ("set_temperature", {"temperature": 19.0}) in cooler_child.calls  # 24 - 5
    assert all(c[1].get("temperature") != 19.0 for c in heater_child.calls)


async def test_on_off_style_is_unchanged_by_the_new_code(hass: HomeAssistant) -> None:
    """Default style still stops the child at the goal."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, initial_hvac_mode=HVACMode.HEAT)  # default style
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    hass.states.async_set(SENSOR, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_setpoint_style_cooler_stays_engaged_below_target(
    hass: HomeAssistant,
) -> None:
    """The cooler goal is never reached either (LOWER direction)."""
    hass.states.async_set(SENSOR, 28.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        heat_cool_mode=False,
        initial_hvac_mode=HVACMode.COOL,
        control_style="setpoint",
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.COOL

    hass.states.async_set(SENSOR, 20.0)  # far below target: on_off would stop here
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.COOL
    assert "turn_off" not in [c[0] for c in child.calls]


async def test_same_climate_as_heater_and_cooler_is_accepted(
    hass: HomeAssistant, caplog
) -> None:
    """One climate may fill both roles: the cooler is not dropped."""
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    assert "cannot be equal" not in caplog.text


async def test_shared_climate_is_listened_to_once(hass: HomeAssistant) -> None:
    """A shared entity registers one state listener, not one per role."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC, initial_hvac_mode=HVACMode.HEAT)

    thermostat = hass.data["climate"].get_entity("climate.test")

    assert thermostat.hvac_device.get_device_ids() == [AC]


async def test_switch_entity_in_two_roles_is_still_ignored(
    hass: HomeAssistant, caplog
) -> None:
    """Existing behaviour is kept for switches."""
    hass.states.async_set(SENSOR, 20.0)
    with caplog.at_level(logging.WARNING):
        await _setup(
            hass, heater=HEATER, cooler=HEATER, initial_hvac_mode=HVACMode.HEAT
        )

    assert "cannot be equal" in caplog.text


async def test_single_ac_walks_through_every_mode_one_at_a_time(
    hass: HomeAssistant,
) -> None:
    """Four roles on one climate never fight: one command per transition."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("sensor.hum", 60.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        fan=AC,
        dryer=AC,
        humidity_sensor="sensor.hum",
        target_humidity=40,
        fan_mode=True,
        initial_hvac_mode=HVACMode.HEAT,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    expected = {
        HVACMode.HEAT: HVACMode.HEAT,
        HVACMode.COOL: HVACMode.OFF,  # 20 degrees: nothing to cool
        HVACMode.FAN_ONLY: HVACMode.FAN_ONLY,
        HVACMode.DRY: HVACMode.DRY,
        HVACMode.OFF: HVACMode.OFF,
    }
    for dst_mode, child_mode in expected.items():
        await common.async_set_hvac_mode(hass, dst_mode, "climate.test")
        if dst_mode == HVACMode.FAN_ONLY:
            hass.states.async_set(SENSOR, 26.0)  # the fan only runs when it is hot
        await hass.async_block_till_done()
        assert hass.states.get(AC).state == child_mode, dst_mode

    # One command per transition: no role ever re-commanded another's mode.
    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.DRY]


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_idle_role_keep_alive_does_not_stop_the_active_role(
    hass: HomeAssistant,
) -> None:
    """The idle cooler's keep-alive must not switch off the heating child."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(
        hass,
        heater=AC,
        cooler=AC,
        keep_alive=timedelta(minutes=1),
        initial_hvac_mode=HVACMode.HEAT,
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    common.async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=2))
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_ran_long_enough_without_a_min_cycle_is_always_true(
    hass: HomeAssistant,
) -> None:
    """Callers may ask with no min_cycle_duration configured (it is None)."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.COOL)
    cool = _port(hass, "climate.test_ac", HVACMode.COOL)

    assert cool.ran_long_enough(None) is True


async def test_setpoint_style_does_not_apply_to_a_climate_fan(
    hass: HomeAssistant,
) -> None:
    """Only roles that push a setpoint can be self-regulating: a fan still stops."""
    hass.states.async_set(SENSOR, 26.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        fan=AC,
        initial_hvac_mode=HVACMode.FAN_ONLY,
        control_style="setpoint",
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.FAN_ONLY

    hass.states.async_set(SENSOR, 20.0)  # fan goal reached
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_child_without_a_step_gets_whole_degrees_and_one_push(
    hass: HomeAssistant,
) -> None:
    """The pushed value is one the child can hold, so it is never re-pushed."""
    child = await common.add_fake_climate(hass, "climate.test_ac")
    child._attr_target_temperature_step = None  # reports no step
    child.async_write_ha_state()
    heat = _port(hass, "climate.test_ac", HVACMode.HEAT, lambda: 22.3)

    for _ in range(3):
        await heat.async_sync(None)  # inactive: nothing
        await heat.async_turn_on(None)

    assert [c for c in child.calls if c[0] == "set_temperature"] == [
        ("set_temperature", {"temperature": 22.0})
    ]


async def test_target_change_during_an_opening_is_not_pushed(
    hass: HomeAssistant,
) -> None:
    """No push-then-off: while an opening is open the setpoint is left alone."""
    hass.states.async_set(SENSOR, 20.0)
    hass.states.async_set("binary_sensor.window", "off")
    await _setup(
        hass,
        heater=AC,
        initial_hvac_mode=HVACMode.HEAT,
        openings=["binary_sensor.window"],
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    async def ignore_off():  # the device is slow: still engaged when control runs
        child.calls.append(("turn_off", {}))

    child.async_turn_off = ignore_off
    child.calls.clear()

    hass.states.async_set("binary_sensor.window", "on")
    await common.async_set_temperature(hass, 23, "climate.test")
    await hass.async_block_till_done()

    assert ("set_temperature", {"temperature": 23.0}) not in child.calls
    assert ("turn_off", {}) in child.calls


async def test_setpoint_port_keeps_the_users_min_cycle(hass: HomeAssistant) -> None:
    """Style does not change min cycle: openings force past it, nothing else does."""
    await common.add_fake_climate(hass, "climate.test_ac", HVACMode.HEAT)
    port = make_port(
        hass,
        "climate.test_ac",
        role_mode=lambda: HVACMode.HEAT,
        target=lambda: 22.0,
        style=ControlStyle.SETPOINT,
    )

    assert port.ran_long_enough(timedelta(minutes=5)) is False


async def test_standalone_ac_uses_its_own_temperature(hass: HomeAssistant) -> None:
    """No target_sensor: the AC's current_temperature drives everything."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "cooler": AC,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=22.0)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get("climate.test").attributes["current_temperature"] == 22.0

    child.set_current_temperature(26.0)  # hotter than target + tolerance
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 26.0
    assert hass.states.get(AC).state == HVACMode.COOL

    child.set_current_temperature(23.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


async def test_child_temperature_read_at_startup(hass: HomeAssistant) -> None:
    """The first reading comes from the child before any change event."""
    # Only the state matters at startup; the real entity comes later (adding it
    # would set the climate component up without the platform config).
    hass.states.async_set(AC, "off", {"current_temperature": 21.5})
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {CLIMATE: {"platform": DOMAIN, "name": "test", "heater": AC}},
    )
    await hass.async_block_till_done()

    assert hass.states.get("climate.test").attributes["current_temperature"] == 21.5


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_stale_child_temperature_triggers_the_emergency_stop(
    hass: HomeAssistant, freezer
) -> None:
    """A child that stops reporting is treated like a stale sensor."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "sensor_stale_duration": timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=18.0)
    await common.async_set_temperature(hass, 22, "climate.test")
    child.set_current_temperature(18.5)  # a real reading arms the watchdog
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


COOLING_FLAG = "binary_sensor.hp_cooling"


@pytest.mark.parametrize(
    ("cooling", "dst_mode", "room", "expected"),
    [
        ("off", HVACMode.HEAT, 18.0, HVACMode.HEAT),
        ("on", HVACMode.COOL, 27.0, HVACMode.COOL),
    ],
)
async def test_climate_heat_pump_follows_the_cooling_flag(
    hass: HomeAssistant, cooling, dst_mode, room, expected
) -> None:
    """The child's mode is heat or cool, following heat_pump_cooling."""
    hass.states.async_set(COOLING_FLAG, cooling)
    hass.states.async_set(SENSOR, room)
    await _setup(
        hass, heater=AC, heat_pump_cooling=COOLING_FLAG, initial_hvac_mode=dst_mode
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == expected


async def test_shared_fan_with_ac_flag_does_not_flap(hass: HomeAssistant) -> None:
    """fan_on_with_ac cannot stack two modes on one climate: it is forced off."""
    hass.states.async_set(SENSOR, 27.0)
    setup_switch(hass, False, HEATER)
    await _setup(
        hass,
        heater=HEATER,
        cooler=AC,
        fan=AC,
        fan_on_with_ac=True,
        initial_hvac_mode=HVACMode.COOL,
    )
    child = await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 24, "climate.test")
    await hass.async_block_till_done()

    for temp in (27.1, 27.2, 27.3, 27.4):
        hass.states.async_set(SENSOR, temp)
        await hass.async_block_till_done()

    sent = [c[1]["hvac_mode"] for c in child.calls if c[0] == "set_hvac_mode"]
    assert sent == [HVACMode.COOL]  # never fan_only, never repeated
    assert hass.states.get(AC).state == HVACMode.COOL


async def test_entity_cannot_be_its_own_device(hass: HomeAssistant, caplog) -> None:
    """A role pointing at the thermostat itself would loop: it is refused."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater="climate.test")

    assert hass.states.get("climate.test") is None
    assert "itself" in caplog.text


CHILDREN_KEY = "dual_smart_thermostat_climate_children"


async def test_child_is_shared_until_the_last_port_releases_it(
    hass: HomeAssistant,
) -> None:
    """One thermostat going away must not pull the child from under another."""
    await common.add_fake_climate(hass, "climate.test_ac")
    first = _port(hass, "climate.test_ac", HVACMode.HEAT)
    second = _port(hass, "climate.test_ac", HVACMode.COOL)
    assert first._child is second._child

    first.release()
    first.release()  # idempotent: a double release cannot steal the other's reference
    assert "climate.test_ac" in hass.data[CHILDREN_KEY]

    second.release()
    assert "climate.test_ac" not in hass.data[CHILDREN_KEY]


async def test_reload_starts_from_a_fresh_child_record(hass: HomeAssistant) -> None:
    """A stale DST record of an IR child cannot survive its thermostat."""
    await common.add_fake_climate(hass, "climate.test_ir", assumed=True)
    old = _port(hass, "climate.test_ir", HVACMode.COOL)
    await old.async_turn_on(None)
    assert old.is_active is True
    old.release()

    new = _port(hass, "climate.test_ir", HVACMode.COOL)

    assert new.is_active is False  # adopted from the reported state (off), not stale


async def test_removing_a_thermostat_releases_its_children(
    hass: HomeAssistant,
) -> None:
    """Entity removal drops the thermostat's references."""
    hass.states.async_set(SENSOR, 20.0)
    await _setup(hass, heater=AC, cooler=AC)
    await common.add_fake_climate(hass, AC)
    assert AC in hass.data[CHILDREN_KEY]

    await hass.data["climate"].get_entity("climate.test").async_remove()

    assert AC not in hass.data[CHILDREN_KEY]


async def _stale_heating_child(hass: HomeAssistant, freezer):
    """A heating AC whose only temperature source is itself, watchdog armed."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            CLIMATE: {
                "platform": DOMAIN,
                "name": "test",
                "heater": AC,
                "sensor_stale_duration": timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    child = await common.add_fake_climate(hass, AC, current=18.0)
    await common.async_set_temperature(hass, 22, "climate.test")
    child.set_current_temperature(18.5)  # a real reading arms the watchdog
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT
    return child


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_empty_readings_do_not_feed_the_stale_watchdog(
    hass: HomeAssistant, freezer
) -> None:
    """A child reporting no temperature is silent: the emergency stop still fires."""
    child = await _stale_heating_child(hass, freezer)

    for _ in range(3):
        freezer.tick(timedelta(minutes=1))
        child.set_current_temperature(None)
        common.async_fire_time_changed(hass)
        await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_our_own_echo_does_not_recover_a_stalled_child(
    hass: HomeAssistant, freezer
) -> None:
    """After the emergency stop only a new reading restarts control."""
    child = await _stale_heating_child(hass, freezer)
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child._attr_target_temperature = 23.0  # any event, same temperature
    child.async_write_ha_state()
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.OFF


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_a_new_reading_recovers_a_stalled_child(
    hass: HomeAssistant, freezer
) -> None:
    """A changed temperature is a real reading: control resumes."""
    child = await _stale_heating_child(hass, freezer)
    freezer.tick(timedelta(minutes=3))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.OFF

    child.set_current_temperature(19.0)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state == HVACMode.HEAT


async def test_climate_heat_pump_is_stopped_when_the_flag_flips_while_heating(
    hass: HomeAssistant,
) -> None:
    """A switch heat pump is turned off on a flip; a climate must not keep heating."""
    hass.states.async_set(COOLING_FLAG, "off")
    hass.states.async_set(SENSOR, 18.0)
    await _setup(
        hass,
        heater=AC,
        heat_pump_cooling=COOLING_FLAG,
        initial_hvac_mode=HVACMode.HEAT,
    )
    await common.add_fake_climate(hass, AC)
    await common.async_set_temperature(hass, 22, "climate.test")
    await hass.async_block_till_done()
    assert hass.states.get(AC).state == HVACMode.HEAT

    hass.states.async_set(COOLING_FLAG, "on")
    hass.states.async_set(SENSOR, 18.1)
    await hass.async_block_till_done()

    assert hass.states.get(AC).state != HVACMode.HEAT
