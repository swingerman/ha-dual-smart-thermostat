"""Tests for multiple heater/cooler entity support."""

import pytest
from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common


async def test_multi_heater_setup(hass: HomeAssistant) -> None:
    """Test setup with multiple heater entities."""
    heater_switches = ["input_boolean.heater1", "input_boolean.heater2"]
    
    # Setup the input_boolean entities for testing
    for switch in heater_switches:
        hass.states.async_set(switch, STATE_OFF)
    
    await common.setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert await common.async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_multi_heater",
                "heater": heater_switches,  # Multiple heaters
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "heat",
            }
        },
    )
    await hass.async_block_till_done()

    # Verify the climate entity was created
    state = hass.states.get("climate.test_multi_heater")
    assert state is not None
    assert state.state == "heat"


async def test_multi_cooler_setup(hass: HomeAssistant) -> None:
    """Test setup with multiple cooler entities."""
    cooler_switches = ["input_boolean.cooler1", "input_boolean.cooler2"]
    
    # Setup the input_boolean entities for testing
    for switch in cooler_switches:
        hass.states.async_set(switch, STATE_OFF)
    
    await common.setup_sensor(hass, 22)
    await hass.async_block_till_done()

    assert await common.async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_multi_cooler",
                "heater": "input_boolean.heater",  # Single heater
                "cooler": cooler_switches,  # Multiple coolers
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "cool",
            }
        },
    )
    await hass.async_block_till_done()

    # Verify the climate entity was created
    state = hass.states.get("climate.test_multi_cooler")
    assert state is not None
    assert state.state == "cool"


async def test_multi_heater_operation(hass: HomeAssistant) -> None:
    """Test that multiple heaters turn on/off together."""
    heater_switches = ["input_boolean.heater1", "input_boolean.heater2"]
    
    # Setup the input_boolean entities for testing
    for switch in heater_switches:
        hass.states.async_set(switch, STATE_OFF)
    
    await common.setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert await common.async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_multi_heater",
                "heater": heater_switches,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "heat",
            }
        },
    )
    await hass.async_block_till_done()

    # Set target temperature to trigger heating
    await common.async_set_temperature(hass, 25, "climate.test_multi_heater")
    await hass.async_block_till_done()

    # Both heaters should be on
    for switch in heater_switches:
        assert hass.states.get(switch).state == STATE_ON

    # Now set high temperature to turn off heating
    await common.setup_sensor(hass, 26)
    await hass.async_block_till_done()

    # Both heaters should be off
    for switch in heater_switches:
        assert hass.states.get(switch).state == STATE_OFF


async def test_backward_compatibility_single_entities(hass: HomeAssistant) -> None:
    """Test that single entity configurations still work (backward compatibility)."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    
    # Setup the input_boolean entities for testing
    hass.states.async_set(heater_switch, STATE_OFF)
    hass.states.async_set(cooler_switch, STATE_OFF)
    
    await common.setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert await common.async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_single_entity",
                "heater": heater_switch,  # Single heater (string)
                "cooler": cooler_switch,  # Single cooler (string)
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "heat",
            }
        },
    )
    await hass.async_block_till_done()

    # Verify the climate entity was created
    state = hass.states.get("climate.test_single_entity")
    assert state is not None
    assert state.state == "heat"


async def test_mixed_single_and_multi_entities(hass: HomeAssistant) -> None:
    """Test configuration with single heater and multiple coolers."""
    heater_switch = "input_boolean.heater"
    cooler_switches = ["input_boolean.cooler1", "input_boolean.cooler2"]
    
    # Setup the input_boolean entities for testing
    hass.states.async_set(heater_switch, STATE_OFF)
    for switch in cooler_switches:
        hass.states.async_set(switch, STATE_OFF)
    
    await common.setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert await common.async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_mixed",
                "heater": heater_switch,      # Single heater
                "cooler": cooler_switches,    # Multiple coolers
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": "auto",
            }
        },
    )
    await hass.async_block_till_done()

    # Verify the climate entity was created
    state = hass.states.get("climate.test_mixed")
    assert state is not None
    assert state.state == "auto"