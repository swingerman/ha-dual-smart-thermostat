"""Test for issue #499 - Multiple thermostats unavailable after restart.

Issue: After HA restart, several thermostats become unavailable.
Only thermostats that control both heating and cooling are affected.

Key configurations from issue:
1. Master Bedroom: heater (binary_sensor) + secondary_heater (switch) + cooler (switch)
2. Computer Room: heater (input_boolean) + secondary_heater (switch) + cooler (input_boolean)
3. First Floor: heater (input_boolean) + cooler (switch)

Hypothesis: Entity availability issues during startup/restore, particularly with
heater_cooler systems and secondary heaters.
"""

import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
def master_bedroom_config():
    """Configuration matching Master Bedroom thermostat from issue #499."""
    return {
        "name": "Master Bedroom Thermostat",
        "heater": "binary_sensor.master_bedroom_vent",
        "secondary_heater": "switch.master_bedroom_heater_local",
        "secondary_heater_timeout": 600,  # 10 minutes in seconds
        "secondary_heater_dual_mode": False,
        "cooler": "switch.master_bedroom_air_conditioner",
        "target_sensor": "sensor.master_bedroom_temperature",
        "initial_hvac_mode": "heat_cool",
        "heat_cool_mode": True,
        "min_cycle_duration": 180,  # 3 minutes in seconds
        "keep_alive": 300,  # 5 minutes in seconds
        "heat_tolerance": 1.0,
        "cool_tolerance": 1.0,
        "min_temp": 62,
        "max_temp": 80,
        "precision": 0.1,
        "target_temp_step": 1,
    }


@pytest.fixture
def computer_room_config():
    """Configuration matching Computer Room thermostat from issue #499."""
    return {
        "name": "Computer Room Thermostat",
        "heater": "input_boolean.computer_room_heater",
        "secondary_heater": "switch.computer_room_heater",
        "secondary_heater_timeout": 600,  # 10 minutes in seconds
        "secondary_heater_dual_mode": False,
        "cooler": "input_boolean.computer_room_cooler",
        "target_sensor": "sensor.computer_room_temperature",
        "initial_hvac_mode": "heat_cool",
        "heat_cool_mode": True,
        "min_cycle_duration": 180,  # 3 minutes in seconds
        "keep_alive": 300,  # 5 minutes in seconds
        "heat_tolerance": 0.3,
        "cool_tolerance": 0.3,
        "openings": [
            {
                "entity_id": "input_boolean.microwave_power_lockout",
                "timeout": 5,  # 5 seconds
                "closing_timeout": 180,  # 3 minutes
            }
        ],
        "openings_scope": ["cool"],
        "min_temp": 62,
        "max_temp": 80,
        "precision": 0.1,
        "target_temp_step": 1,
    }


@pytest.fixture
def first_floor_config():
    """Configuration matching First Floor thermostat from issue #499."""
    return {
        "name": "First Floor Thermostat",
        "heater": "input_boolean.living_room_heat",
        "cooler": "switch.air_conditioner",
        "target_sensor": "sensor.living_room_temperature",
        "openings": [
            {
                "entity_id": "binary_sensor.dining_room_window",
                "timeout": 15,
                "closing_timeout": 15,
            },
            {
                "entity_id": "binary_sensor.kitchen_window",
                "timeout": 15,
                "closing_timeout": 15,
            },
        ],
        "initial_hvac_mode": "heat_cool",
        "heat_cool_mode": True,
        "min_cycle_duration": 180,  # 3 minutes in seconds
        "keep_alive": 180,  # 3 minutes in seconds
        "heat_tolerance": 1.0,
        "cool_tolerance": 1.3,
        "min_temp": 62,
        "max_temp": 80,
        "precision": 0.1,
        "target_temp_step": 1,
    }


async def setup_entities_for_config(hass: HomeAssistant, config: dict):
    """Set up mock entities required for a thermostat configuration."""
    # Set up target sensor (always required) - use Fahrenheit to match config range (62-80°F)
    hass.states.async_set(
        config["target_sensor"], "70.0", {"unit_of_measurement": "°F"}
    )

    # Set up heater entity
    if config.get("heater"):
        heater_entity = config["heater"]
        if heater_entity.startswith("binary_sensor."):
            hass.states.async_set(heater_entity, STATE_OFF)
        else:  # input_boolean or switch
            hass.states.async_set(heater_entity, STATE_OFF)

    # Set up secondary heater if present
    if config.get("secondary_heater"):
        hass.states.async_set(config["secondary_heater"], STATE_OFF)

    # Set up cooler entity
    if config.get("cooler"):
        hass.states.async_set(config["cooler"], STATE_OFF)

    # Set up openings if present
    if config.get("openings"):
        for opening in config["openings"]:
            hass.states.async_set(opening["entity_id"], STATE_OFF)


async def setup_thermostat_with_config(
    hass: HomeAssistant, config: dict, unique_id: str
) -> MockConfigEntry:
    """Set up a thermostat with the given configuration."""
    # Set up required entities first
    await setup_entities_for_config(hass, config)

    # Create config entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config,
        unique_id=unique_id,
        entry_id=unique_id,
    )
    entry.add_to_hass(hass)

    # Set up the integration
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    return entry


@pytest.mark.asyncio
async def test_master_bedroom_thermostat_availability_on_restart(
    hass: HomeAssistant, master_bedroom_config
):
    """Test Master Bedroom thermostat (binary_sensor heater + secondary heater + cooler) remains available after restart.

    This test replicates the configuration from issue #499 where the Master Bedroom
    thermostat becomes unavailable after Home Assistant restart.

    Configuration:
    - heater: binary_sensor (not a switch)
    - secondary_heater: switch
    - cooler: switch
    - heat_cool_mode: True
    """
    _LOGGER.info("=== Testing Master Bedroom thermostat availability on restart ===")

    # Set up the thermostat
    entry = await setup_thermostat_with_config(
        hass, master_bedroom_config, "master_bedroom_thermostat"
    )

    # Verify entity was created
    entity_id = "climate.master_bedroom_thermostat"
    state = hass.states.get(entity_id)
    assert state is not None, "Thermostat entity should be created"
    assert state.state != STATE_UNAVAILABLE, "Initial state should not be unavailable"
    assert state.state != STATE_UNKNOWN, "Initial state should not be unknown"

    _LOGGER.info("Initial state: %s", state.state)
    _LOGGER.info("Initial attributes: %s", state.attributes)

    # Set thermostat to heat_cool mode with targets
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.HEAT_COOL},
        blocking=True,
    )
    await hass.async_block_till_done()

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

    # Get state before restart
    state_before = hass.states.get(entity_id)
    _LOGGER.info("State before restart: %s", state_before.state)
    _LOGGER.info("Attributes before restart: %s", state_before.attributes)

    # Simulate Home Assistant restart by reloading the entry
    _LOGGER.info("=== Simulating Home Assistant restart ===")

    # First unload
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Simulate restart - ensure entities still exist
    await setup_entities_for_config(hass, master_bedroom_config)

    # Reload
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity is still available after restart
    state_after = hass.states.get(entity_id)
    assert state_after is not None, "Thermostat entity should exist after restart"

    _LOGGER.info("State after restart: %s", state_after.state)
    _LOGGER.info("Attributes after restart: %s", state_after.attributes)

    # THIS IS THE BUG: The thermostat should NOT be unavailable after restart
    assert (
        state_after.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable after restart. State: {state_after.state}, Attributes: {state_after.attributes}"
    assert (
        state_after.state != STATE_UNKNOWN
    ), f"Thermostat should not be unknown after restart. State: {state_after.state}"

    # Verify state was restored correctly
    assert state_after.state in [
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
    ], f"Expected valid HVAC mode, got: {state_after.state}"


@pytest.mark.asyncio
async def test_computer_room_thermostat_availability_on_restart(
    hass: HomeAssistant, computer_room_config
):
    """Test Computer Room thermostat (input_boolean heater + secondary heater + input_boolean cooler) remains available after restart.

    This test replicates the configuration from issue #499 where the Computer Room
    thermostat becomes unavailable after Home Assistant restart.

    Configuration:
    - heater: input_boolean
    - secondary_heater: switch
    - cooler: input_boolean
    - heat_cool_mode: True
    - openings with scope limited to cooling
    """
    _LOGGER.info("=== Testing Computer Room thermostat availability on restart ===")

    # Set up the thermostat
    entry = await setup_thermostat_with_config(
        hass, computer_room_config, "computer_room_thermostat"
    )

    # Verify entity was created
    entity_id = "climate.computer_room_thermostat"
    state = hass.states.get(entity_id)
    assert state is not None, "Thermostat entity should be created"
    assert state.state != STATE_UNAVAILABLE, "Initial state should not be unavailable"
    assert state.state != STATE_UNKNOWN, "Initial state should not be unknown"

    _LOGGER.info("Initial state: %s", state.state)

    # Set thermostat to heat_cool mode
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.HEAT_COOL},
        blocking=True,
    )
    await hass.async_block_till_done()

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

    state_before = hass.states.get(entity_id)
    _LOGGER.info("State before restart: %s", state_before.state)

    # Simulate Home Assistant restart
    _LOGGER.info("=== Simulating Home Assistant restart ===")

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await setup_entities_for_config(hass, computer_room_config)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity is still available after restart
    state_after = hass.states.get(entity_id)
    assert state_after is not None, "Thermostat entity should exist after restart"

    _LOGGER.info("State after restart: %s", state_after.state)
    _LOGGER.info("Attributes after restart: %s", state_after.attributes)

    # THIS IS THE BUG: The thermostat should NOT be unavailable after restart
    assert (
        state_after.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable after restart. State: {state_after.state}"
    assert (
        state_after.state != STATE_UNKNOWN
    ), f"Thermostat should not be unknown after restart. State: {state_after.state}"

    assert state_after.state in [
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
    ], f"Expected valid HVAC mode, got: {state_after.state}"


@pytest.mark.asyncio
async def test_first_floor_thermostat_availability_on_restart(
    hass: HomeAssistant, first_floor_config
):
    """Test First Floor thermostat (input_boolean heater + cooler) remains available after restart.

    This test replicates the configuration from issue #499 where the First Floor
    thermostat becomes unavailable after Home Assistant restart.

    Configuration:
    - heater: input_boolean
    - cooler: switch (no secondary heater)
    - heat_cool_mode: True
    - multiple window openings
    """
    _LOGGER.info("=== Testing First Floor thermostat availability on restart ===")

    # Set up the thermostat
    entry = await setup_thermostat_with_config(
        hass, first_floor_config, "first_floor_thermostat"
    )

    # Verify entity was created
    entity_id = "climate.first_floor_thermostat"
    state = hass.states.get(entity_id)
    assert state is not None, "Thermostat entity should be created"
    assert state.state != STATE_UNAVAILABLE, "Initial state should not be unavailable"
    assert state.state != STATE_UNKNOWN, "Initial state should not be unknown"

    _LOGGER.info("Initial state: %s", state.state)

    # Set thermostat to heat_cool mode
    await hass.services.async_call(
        "climate",
        "set_hvac_mode",
        {"entity_id": entity_id, "hvac_mode": HVACMode.HEAT_COOL},
        blocking=True,
    )
    await hass.async_block_till_done()

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

    state_before = hass.states.get(entity_id)
    _LOGGER.info("State before restart: %s", state_before.state)

    # Simulate Home Assistant restart
    _LOGGER.info("=== Simulating Home Assistant restart ===")

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await setup_entities_for_config(hass, first_floor_config)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify entity is still available after restart
    state_after = hass.states.get(entity_id)
    assert state_after is not None, "Thermostat entity should exist after restart"

    _LOGGER.info("State after restart: %s", state_after.state)
    _LOGGER.info("Attributes after restart: %s", state_after.attributes)

    # THIS IS THE BUG: The thermostat should NOT be unavailable after restart
    assert (
        state_after.state != STATE_UNAVAILABLE
    ), f"Thermostat should not be unavailable after restart. State: {state_after.state}"
    assert (
        state_after.state != STATE_UNKNOWN
    ), f"Thermostat should not be unknown after restart. State: {state_after.state}"

    assert state_after.state in [
        HVACMode.HEAT_COOL,
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
    ], f"Expected valid HVAC mode, got: {state_after.state}"


@pytest.mark.asyncio
async def test_all_thermostats_together_with_restart(
    hass: HomeAssistant,
    master_bedroom_config,
    computer_room_config,
    first_floor_config,
):
    """Test multiple thermostats together, simulating the actual issue #499 scenario.

    This test sets up all three affected thermostats simultaneously and tests
    their availability after a Home Assistant restart, which is when the issue occurs.
    """
    _LOGGER.info(
        "=== Testing multiple heater_cooler thermostats together with restart ==="
    )

    # Set up all three thermostats
    entry1 = await setup_thermostat_with_config(
        hass, master_bedroom_config, "master_bedroom_thermostat"
    )
    entry2 = await setup_thermostat_with_config(
        hass, computer_room_config, "computer_room_thermostat"
    )
    entry3 = await setup_thermostat_with_config(
        hass, first_floor_config, "first_floor_thermostat"
    )

    entity_ids = [
        "climate.master_bedroom_thermostat",
        "climate.computer_room_thermostat",
        "climate.first_floor_thermostat",
    ]

    # Verify all entities were created
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        assert state is not None, f"{entity_id} should be created"
        assert (
            state.state != STATE_UNAVAILABLE
        ), f"{entity_id} initial state should not be unavailable"
        _LOGGER.info("%s initial state: %s", entity_id, state.state)

    # Set all to heat_cool mode
    for entity_id in entity_ids:
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": entity_id, "hvac_mode": HVACMode.HEAT_COOL},
            blocking=True,
        )
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

    # Simulate Home Assistant restart for all
    _LOGGER.info("=== Simulating Home Assistant restart for all thermostats ===")

    for entry in [entry1, entry2, entry3]:
        await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    # Recreate entities
    await setup_entities_for_config(hass, master_bedroom_config)
    await setup_entities_for_config(hass, computer_room_config)
    await setup_entities_for_config(hass, first_floor_config)

    # Reload all entries
    for entry in [entry1, entry2, entry3]:
        await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify all entities are still available after restart
    unavailable_entities = []
    for entity_id in entity_ids:
        state_after = hass.states.get(entity_id)
        assert state_after is not None, f"{entity_id} should exist after restart"

        _LOGGER.info("%s state after restart: %s", entity_id, state_after.state)
        _LOGGER.info(
            "%s attributes after restart: %s", entity_id, state_after.attributes
        )

        if state_after.state == STATE_UNAVAILABLE:
            unavailable_entities.append(entity_id)

    # THIS IS THE BUG: None of the thermostats should be unavailable after restart
    assert (
        len(unavailable_entities) == 0
    ), f"The following thermostats became unavailable after restart: {unavailable_entities}"
