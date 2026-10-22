"""Tests for climate entities used as device roles (issue #281)."""

from datetime import timedelta

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_device.entity_port import (
    ClimatePort,
    SwitchPort,
    make_port,
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
    assert port.self_regulating is False


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
