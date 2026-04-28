"""Integration tests for AUTO mode end-to-end through the climate entity."""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common


@pytest.mark.asyncio
async def test_auto_in_hvac_modes_when_two_capabilities(hass: HomeAssistant) -> None:
    """AUTO appears in hvac_modes when heater + cooler are both configured."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "cooler": "switch.cooler_test",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO in state.attributes["hvac_modes"]


@pytest.mark.asyncio
async def test_auto_absent_from_hvac_modes_for_heater_only(
    hass: HomeAssistant,
) -> None:
    """AUTO is NOT in hvac_modes for a heater-only setup (1 capability)."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO not in state.attributes["hvac_modes"]
