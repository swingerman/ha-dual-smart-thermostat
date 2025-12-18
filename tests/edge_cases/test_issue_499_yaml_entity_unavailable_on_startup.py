"""Test for issue #499 - YAML config with entities unavailable during startup.

Issue: After HA restart with YAML configuration, thermostats become unavailable
when their cooler/heater entities are not yet available during thermostat setup.

Key insight: The user is using YAML configuration, not config entries.
With config_flow enabled in manifest.json, there may be timing differences
in how entities are initialized during startup.

This test focuses on the scenario where:
1. Thermostat is set up via YAML (async_setup_platform)
2. Cooler/heater entities are UNAVAILABLE during thermostat initialization
3. Entities become available AFTER thermostat is already set up
"""

import logging

from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
import pytest

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_yaml_heater_cooler_unavailable_entities_on_startup(hass: HomeAssistant):
    """Test YAML-configured heater_cooler thermostat when cooler entity is unavailable during startup.

    This simulates the issue #499 scenario:
    1. Thermostat configured via YAML
    2. Cooler/heater entities are UNAVAILABLE when thermostat initializes
    3. Thermostat should not become unavailable itself
    4. When entities become available, thermostat should work normally
    """
    _LOGGER.info("=== Testing YAML setup with unavailable entities on startup ===")

    # Set up temperature sensor (available)
    hass.states.async_set(
        "sensor.bedroom_temperature", "70.0", {"unit_of_measurement": "°F"}
    )

    # Set up heater and cooler as UNAVAILABLE initially
    # This simulates entities not ready during HA startup
    hass.states.async_set("switch.bedroom_heater", STATE_UNAVAILABLE)
    hass.states.async_set("switch.bedroom_air_conditioner", STATE_UNAVAILABLE)

    _LOGGER.info("Initial entity states:")
    _LOGGER.info(
        "  Temperature sensor: %s", hass.states.get("sensor.bedroom_temperature").state
    )
    _LOGGER.info("  Heater: %s", hass.states.get("switch.bedroom_heater").state)
    _LOGGER.info(
        "  Cooler: %s", hass.states.get("switch.bedroom_air_conditioner").state
    )

    # Configure thermostat via YAML (like the user's setup)
    config = {
        CLIMATE_DOMAIN: {
            "platform": "dual_smart_thermostat",
            "name": "Bedroom Thermostat",
            "unique_id": "bedroom_thermostat_yaml",
            "heater": "switch.bedroom_heater",
            "cooler": "switch.bedroom_air_conditioner",
            "target_sensor": "sensor.bedroom_temperature",
            "initial_hvac_mode": "heat_cool",
            "heat_cool_mode": True,
            "heat_tolerance": 1.0,
            "cool_tolerance": 1.0,
            "min_temp": 62,
            "max_temp": 80,
        }
    }

    # Set up via YAML (this is what the user does)
    result = await async_setup_component(hass, CLIMATE_DOMAIN, config)
    assert result, "Climate platform should set up successfully"
    await hass.async_block_till_done()

    # Check thermostat state immediately after setup
    entity_id = "climate.bedroom_thermostat"
    state = hass.states.get(entity_id)

    _LOGGER.info(
        "Thermostat state after setup: %s", state.state if state else "NOT FOUND"
    )
    if state:
        _LOGGER.info("Thermostat attributes: %s", state.attributes)

    # THIS IS THE KEY TEST: Thermostat should exist even if entities are unavailable
    assert (
        state is not None
    ), "Thermostat entity should be created even when heater/cooler are unavailable"

    # With the fix for issue #499, the thermostat should NOT be unavailable
    # even when its heater/cooler entities are unavailable during startup
    assert (
        state.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable when entities are unavailable during startup. State: {state.state}"

    # The thermostat might be in various states, but should NOT be unavailable itself
    # It should be able to handle unavailable switch entities gracefully
    _LOGGER.info("Current thermostat state: %s", state.state)

    # Now simulate entities becoming available (as they would after startup completes)
    _LOGGER.info("=== Simulating entities becoming available ===")
    hass.states.async_set("switch.bedroom_heater", STATE_OFF)
    hass.states.async_set("switch.bedroom_air_conditioner", STATE_OFF)
    await hass.async_block_till_done()

    # Check thermostat state after entities become available
    state_after = hass.states.get(entity_id)
    _LOGGER.info("Thermostat state after entities available: %s", state_after.state)
    _LOGGER.info("Thermostat attributes: %s", state_after.attributes)

    # Now the thermostat should definitely not be unavailable
    assert state_after is not None, "Thermostat should still exist"
    assert (
        state_after.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable. State: {state_after.state}"
    assert (
        state_after.state != STATE_UNKNOWN
    ), f"Thermostat should not be unknown. State: {state_after.state}"

    # Verify thermostat is functional by setting temperature
    await hass.services.async_call(
        "climate",
        "set_temperature",
        {
            "entity_id": entity_id,
            "target_temp_low": 68.0,
            "target_temp_high": 72.0,
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    state_final = hass.states.get(entity_id)
    _LOGGER.info("Thermostat state after set_temperature: %s", state_final.state)
    assert state_final.attributes.get("target_temp_low") == 68.0
    assert state_final.attributes.get("target_temp_high") == 72.0


@pytest.mark.asyncio
async def test_yaml_secondary_heater_cooler_unavailable_on_startup(hass: HomeAssistant):
    """Test YAML-configured thermostat with secondary heater when entities are unavailable during startup.

    This matches the Master Bedroom configuration from issue #499:
    - heater: binary_sensor
    - secondary_heater: switch
    - cooler: switch
    """
    _LOGGER.info(
        "=== Testing YAML setup with secondary heater and unavailable entities ==="
    )

    # Set up temperature sensor (available)
    hass.states.async_set(
        "sensor.master_bedroom_temperature", "70.0", {"unit_of_measurement": "°F"}
    )

    # Set up entities as UNAVAILABLE initially
    hass.states.async_set("binary_sensor.master_bedroom_vent", STATE_UNAVAILABLE)
    hass.states.async_set("switch.master_bedroom_heater", STATE_UNAVAILABLE)
    hass.states.async_set("switch.master_bedroom_air_conditioner", STATE_UNAVAILABLE)

    _LOGGER.info("Initial entity states:")
    _LOGGER.info(
        "  Temperature sensor: %s",
        hass.states.get("sensor.master_bedroom_temperature").state,
    )
    _LOGGER.info(
        "  Primary heater: %s",
        hass.states.get("binary_sensor.master_bedroom_vent").state,
    )
    _LOGGER.info(
        "  Secondary heater: %s", hass.states.get("switch.master_bedroom_heater").state
    )
    _LOGGER.info(
        "  Cooler: %s", hass.states.get("switch.master_bedroom_air_conditioner").state
    )

    # Configure thermostat via YAML matching user's config
    config = {
        CLIMATE_DOMAIN: {
            "platform": "dual_smart_thermostat",
            "name": "Master Bedroom Thermostat",
            "unique_id": "master_bedroom_yaml",
            "heater": "binary_sensor.master_bedroom_vent",
            "secondary_heater": "switch.master_bedroom_heater",
            "secondary_heater_timeout": 600,  # 10 minutes
            "secondary_heater_dual_mode": False,
            "cooler": "switch.master_bedroom_air_conditioner",
            "target_sensor": "sensor.master_bedroom_temperature",
            "initial_hvac_mode": "heat_cool",
            "heat_cool_mode": True,
            "heat_tolerance": 1.0,
            "cool_tolerance": 1.0,
            "min_temp": 62,
            "max_temp": 80,
        }
    }

    # Set up via YAML
    result = await async_setup_component(hass, CLIMATE_DOMAIN, config)
    assert result, "Climate platform should set up successfully"
    await hass.async_block_till_done()

    # Check thermostat state
    entity_id = "climate.master_bedroom_thermostat"
    state = hass.states.get(entity_id)

    _LOGGER.info(
        "Thermostat state after setup: %s", state.state if state else "NOT FOUND"
    )
    if state:
        _LOGGER.info("Thermostat attributes: %s", state.attributes)

    assert state is not None, "Thermostat entity should be created"

    # Make entities available
    _LOGGER.info("=== Making entities available ===")
    hass.states.async_set("binary_sensor.master_bedroom_vent", STATE_OFF)
    hass.states.async_set("switch.master_bedroom_heater", STATE_OFF)
    hass.states.async_set("switch.master_bedroom_air_conditioner", STATE_OFF)
    await hass.async_block_till_done()

    # Verify thermostat is not unavailable
    state_after = hass.states.get(entity_id)
    _LOGGER.info("Thermostat state after entities available: %s", state_after.state)

    assert (
        state_after.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable. State: {state_after.state}"


@pytest.mark.asyncio
async def test_yaml_multiple_thermostats_unavailable_entities(hass: HomeAssistant):
    """Test multiple YAML-configured thermostats with unavailable entities during startup.

    This simulates the full issue #499 scenario:
    - Multiple thermostats (5 in the original report)
    - All configured via YAML
    - Some or all control entities unavailable during startup
    """
    _LOGGER.info("=== Testing multiple YAML thermostats with unavailable entities ===")

    # Set up 3 thermostats (simplified from the user's 5)
    thermostats = [
        {
            "name": "Master Bedroom",
            "sensor": "sensor.master_bedroom_temp",
            "heater": "binary_sensor.master_bedroom_vent",
            "secondary_heater": "switch.master_bedroom_heater",
            "cooler": "switch.master_bedroom_ac",
        },
        {
            "name": "Computer Room",
            "sensor": "sensor.computer_room_temp",
            "heater": "input_boolean.computer_room_heater",
            "secondary_heater": "switch.computer_room_heater_switch",
            "cooler": "input_boolean.computer_room_cooler",
        },
        {
            "name": "First Floor",
            "sensor": "sensor.living_room_temp",
            "heater": "input_boolean.living_room_heat",
            "cooler": "switch.air_conditioner",
        },
    ]

    # Set up sensors (available) and switches/binary_sensors (unavailable)
    for t in thermostats:
        hass.states.async_set(t["sensor"], "70.0", {"unit_of_measurement": "°F"})
        hass.states.async_set(t["heater"], STATE_UNAVAILABLE)
        if "secondary_heater" in t:
            hass.states.async_set(t["secondary_heater"], STATE_UNAVAILABLE)
        hass.states.async_set(t["cooler"], STATE_UNAVAILABLE)

    _LOGGER.info("All heater/cooler entities set to UNAVAILABLE")

    # Configure all thermostats via YAML
    climate_configs = []
    for t in thermostats:
        config = {
            "platform": "dual_smart_thermostat",
            "name": f"{t['name']} Thermostat",
            "unique_id": f"{t['name'].lower().replace(' ', '_')}_yaml",
            "heater": t["heater"],
            "cooler": t["cooler"],
            "target_sensor": t["sensor"],
            "initial_hvac_mode": "heat_cool",
            "heat_cool_mode": True,
            "heat_tolerance": 1.0,
            "cool_tolerance": 1.0,
            "min_temp": 62,
            "max_temp": 80,
        }
        if "secondary_heater" in t:
            config["secondary_heater"] = t["secondary_heater"]
            config["secondary_heater_timeout"] = 600
            config["secondary_heater_dual_mode"] = False
        climate_configs.append(config)

    config = {CLIMATE_DOMAIN: climate_configs}

    # Set up all thermostats via YAML
    result = await async_setup_component(hass, CLIMATE_DOMAIN, config)
    assert result, "Climate platform should set up successfully"
    await hass.async_block_till_done()

    # Check all thermostats were created
    entity_ids = [
        "climate.master_bedroom_thermostat",
        "climate.computer_room_thermostat",
        "climate.first_floor_thermostat",
    ]

    _LOGGER.info("Checking thermostat states immediately after setup:")
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        if state:
            _LOGGER.info("  %s: %s", entity_id, state.state)
        else:
            _LOGGER.warning("  %s: NOT FOUND", entity_id)

    # Make all entities available
    _LOGGER.info("=== Making all entities available ===")
    for t in thermostats:
        hass.states.async_set(t["heater"], STATE_OFF)
        if "secondary_heater" in t:
            hass.states.async_set(t["secondary_heater"], STATE_OFF)
        hass.states.async_set(t["cooler"], STATE_OFF)
    await hass.async_block_till_done()

    # Check that no thermostats are unavailable
    _LOGGER.info("Checking thermostat states after entities available:")
    unavailable_thermostats = []
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        _LOGGER.info("  %s: %s", entity_id, state.state if state else "NOT FOUND")
        if state and state.state == STATE_UNAVAILABLE:
            unavailable_thermostats.append(entity_id)

    assert (
        len(unavailable_thermostats) == 0
    ), f"These thermostats became unavailable: {unavailable_thermostats}"
