"""Tests for climate entities used as device roles (issue #281)."""

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.hvac_device.entity_port import (
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
