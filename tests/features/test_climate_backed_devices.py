"""Tests for climate entities used as device roles (issue #281)."""

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant

from tests import common


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
