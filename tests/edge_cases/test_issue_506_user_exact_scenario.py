"""Test for issue #506 - User's EXACT scenario where hot_tolerance is ignored.

https://github.com/swingerman/ha-dual-smart-thermostat/issues/506

User's exact configuration from issue:
  - platform: dual_smart_thermostat
    unique_id: thermostat woonkamer achter
    name: Thermostat woonkamer achter
    heater: input_boolean.heater_living_room_back
    cooler: input_boolean.cooler_living_room_back
    target_sensor: sensor.temp_kamer_achter_temperature
    sensor_stale_duration: 24:00:00
    heat_cool_mode: true
    target_temp_step: 0.5

User states:
1. Without hot_tolerance set: shows 0 (should be 0.3)
2. WITH hot_tolerance set: still shows 0 (ignored!)

This test replicates the EXACT user scenario to find the bug.
"""

import datetime
import logging

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DEFAULT_TOLERANCE, DOMAIN

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_user_exact_config_with_hot_tolerance_set(hass: HomeAssistant):
    """Test user's EXACT scenario where hot_tolerance is explicitly set but ignored.

    This is the critical test - user says even when they SET hot_tolerance,
    it still shows as 0.
    """
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities - using exact entity names from user's config
    heater_entity = "input_boolean.heater_living_room_back"
    cooler_entity = "input_boolean.cooler_living_room_back"
    sensor_entity = "sensor.temp_kamer_achter_temperature"

    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # User's EXACT config with hot_tolerance EXPLICITLY SET
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "unique_id": "thermostat_woonkamer_achter",
            "name": "Thermostat woonkamer achter",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "heat_cool_mode": True,
            "target_temp_step": 0.5,
            # User says they SET this but it's still 0!
            "hot_tolerance": 0.3,
            "cold_tolerance": 0.3,
        }
    }

    # Setup component with YAML config
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.thermostat_woonkamer_achter":
            thermostat = entity
            break

    assert thermostat is not None, "Thermostat entity should be found"

    # Log the actual tolerance values for debugging
    _LOGGER.info(
        f"Environment manager tolerances: cold={thermostat.environment._cold_tolerance}, "
        f"hot={thermostat.environment._hot_tolerance}"
    )

    # This is what the user says is WRONG - they set hot_tolerance but it shows as 0
    assert thermostat.environment._hot_tolerance == 0.3, (
        f"User SET hot_tolerance=0.3 but got {thermostat.environment._hot_tolerance}. "
        f"This is the bug!"
    )
    assert (
        thermostat.environment._cold_tolerance == 0.3
    ), f"User SET cold_tolerance=0.3 but got {thermostat.environment._cold_tolerance}"


@pytest.mark.asyncio
async def test_user_exact_config_without_tolerances(hass: HomeAssistant):
    """Test user's config WITHOUT tolerances set (should default to 0.3)."""
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = "input_boolean.heater_living_room_back"
    cooler_entity = "input_boolean.cooler_living_room_back"
    sensor_entity = "sensor.temp_kamer_achter_temperature"

    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # User's config WITHOUT hot_tolerance/cold_tolerance
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "unique_id": "thermostat_woonkamer_achter",
            "name": "Thermostat woonkamer achter",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "heat_cool_mode": True,
            "target_temp_step": 0.5,
            # NOT setting hot_tolerance or cold_tolerance
        }
    }

    # Setup component
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.thermostat_woonkamer_achter":
            thermostat = entity
            break

    assert thermostat is not None, "Thermostat entity should be found"

    # User says this shows 0 instead of 0.3
    assert thermostat.environment._hot_tolerance == DEFAULT_TOLERANCE, (
        f"Without hot_tolerance set, should default to {DEFAULT_TOLERANCE} "
        f"but got {thermostat.environment._hot_tolerance}"
    )
    assert thermostat.environment._cold_tolerance == DEFAULT_TOLERANCE, (
        f"Without cold_tolerance set, should default to {DEFAULT_TOLERANCE} "
        f"but got {thermostat.environment._cold_tolerance}"
    )


@pytest.mark.asyncio
async def test_tolerance_actually_used_in_heat_cool_mode(hass: HomeAssistant):
    """Test that tolerance is actually USED when making heating/cooling decisions.

    This tests if the tolerance is stored correctly but perhaps not USED correctly
    when in heat_cool_mode.
    """
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = "input_boolean.heater_living_room_back"
    cooler_entity = "input_boolean.cooler_living_room_back"
    sensor_entity = "sensor.temp_kamer_achter_temperature"

    # Start with temp at 20°C
    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Config with explicit tolerances
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "unique_id": "thermostat_woonkamer_achter",
            "name": "Thermostat woonkamer achter",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "heat_cool_mode": True,
            "target_temp_step": 0.5,
            "hot_tolerance": 0.3,
            "cold_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.HEAT,
        }
    }

    # Setup component
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.thermostat_woonkamer_achter":
            thermostat = entity
            break

    assert thermostat is not None

    # Set target temperature to 22°C
    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Current: 20°C, Target: 22°C, cold_tolerance: 0.3
    # Should heat because: 20 < 22 - 0.3 = 21.7 (TRUE)
    # But if tolerance is being ignored (treated as 0), it would check:
    # 20 < 22 - 0 = 22 (TRUE, but different threshold)

    # Let's test the actual tolerance being used
    cold_tol, hot_tol = thermostat.environment._get_active_tolerance_for_mode()

    _LOGGER.info(f"Active tolerances in HEAT mode: cold={cold_tol}, hot={hot_tol}")

    # This is the REAL test - are the tolerances actually being used?
    assert cold_tol == 0.3, (
        f"Expected cold_tolerance of 0.3 to be used in HEAT mode, "
        f"but got {cold_tol}"
    )
    assert hot_tol == 0.3, (
        f"Expected hot_tolerance of 0.3 to be used in HEAT mode, " f"but got {hot_tol}"
    )

    # Now test in COOL mode
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    await thermostat.async_set_temperature(temperature=18.0)
    await hass.async_block_till_done()

    cold_tol, hot_tol = thermostat.environment._get_active_tolerance_for_mode()

    _LOGGER.info(f"Active tolerances in COOL mode: cold={cold_tol}, hot={hot_tol}")

    assert cold_tol == 0.3, (
        f"Expected cold_tolerance of 0.3 to be used in COOL mode, "
        f"but got {cold_tol}"
    )
    assert hot_tol == 0.3, (
        f"Expected hot_tolerance of 0.3 to be used in COOL mode, " f"but got {hot_tol}"
    )
