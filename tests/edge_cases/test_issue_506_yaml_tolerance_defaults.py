"""Test for issue #506 - hot_tolerance defaults to 0 for YAML configs.

https://github.com/swingerman/ha-dual-smart-thermostat/issues/506

User reports that hot_tolerance defaults to 0 instead of 0.3 when using
YAML configuration with heat_cool_mode:true on a heater+cooler system.

The schema has default=DEFAULT_TOLERANCE (0.3) but user sees 0.

YAML config from issue:
  - platform: dual_smart_thermostat
    name: Thermostat woonkamer achter
    heater: input_boolean.heater_living_room_back
    cooler: input_boolean.cooler_living_room_back
    target_sensor: sensor.temp_kamer_achter_temperature
    sensor_stale_duration: 24:00:00
    heat_cool_mode: true
    # cold_tolerance: 0.1  (commented out - should default to 0.3)
    # hot_tolerance: 0     (commented out - should default to 0.3)
    target_temp_step: 0.5

Expected behavior: hot_tolerance and cold_tolerance should default to 0.3
Actual behavior: Values appear to be 0
"""

import datetime

from homeassistant.components.climate import DOMAIN as CLIMATE
from homeassistant.const import STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DEFAULT_TOLERANCE, DOMAIN
from tests import common


@pytest.mark.asyncio
async def test_yaml_config_tolerance_defaults_applied(hass: HomeAssistant):
    """Test that tolerance defaults are applied for YAML configs without explicit values.

    This reproduces issue #506 where user's YAML config without explicit
    hot_tolerance/cold_tolerance values showed 0 instead of the default 0.3.
    """
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities using state.async_set like existing tests
    heater_entity = common.ENT_HEATER
    cooler_entity = common.ENT_COOLER
    sensor_entity = common.ENT_SENSOR

    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Create minimal YAML-style config matching user's setup
    # Intentionally NOT including cold_tolerance or hot_tolerance
    # to test that defaults are applied
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "target_temp_step": 0.5,
            # NOTE: cold_tolerance and hot_tolerance are NOT set
            # They should default to DEFAULT_TOLERANCE (0.3) via schema
        }
    }

    # Setup component with YAML config (schema defaults should be applied)
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    state = hass.states.get("climate.test")
    assert state is not None, "Thermostat entity should be created"

    # Access the thermostat entity directly to check internal tolerance values
    # The entity should be registered in hass.data
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None, "Thermostat entity should be found in hass.data"

    # Verify tolerances are set correctly in environment manager
    assert thermostat.environment._cold_tolerance == DEFAULT_TOLERANCE, (
        f"Environment manager cold_tolerance should be {DEFAULT_TOLERANCE}, "
        f"got {thermostat.environment._cold_tolerance}"
    )
    assert thermostat.environment._hot_tolerance == DEFAULT_TOLERANCE, (
        f"Environment manager hot_tolerance should be {DEFAULT_TOLERANCE}, "
        f"got {thermostat.environment._hot_tolerance}"
    )


@pytest.mark.asyncio
async def test_yaml_config_explicit_tolerance_values_respected(hass: HomeAssistant):
    """Test that explicitly set tolerance values in YAML are respected.

    This tests the second part of issue #506 where user reported that
    even when they SET hot_tolerance, it was ignored.
    """
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = common.ENT_HEATER
    cooler_entity = common.ENT_COOLER
    sensor_entity = common.ENT_SENSOR

    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Create YAML-style config with explicit tolerance values
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "target_temp_step": 0.5,
            "cold_tolerance": 0.1,  # Explicit value
            "hot_tolerance": 0.2,  # Explicit value
        }
    }

    # Setup component with YAML config
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None, "Thermostat entity should be found"

    # Verify tolerances are set correctly in environment manager
    assert (
        thermostat.environment._cold_tolerance == 0.1
    ), f"Environment manager cold_tolerance should be 0.1, got {thermostat.environment._cold_tolerance}"
    assert (
        thermostat.environment._hot_tolerance == 0.2
    ), f"Environment manager hot_tolerance should be 0.2, got {thermostat.environment._hot_tolerance}"


@pytest.mark.asyncio
async def test_yaml_config_zero_tolerance_values_respected(hass: HomeAssistant):
    """Test that explicit 0 tolerance values in YAML are respected.

    Edge case: User explicitly sets tolerance to 0, which should be allowed.
    """
    # Initialize Home Assistant
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = common.ENT_HEATER
    cooler_entity = common.ENT_COOLER
    sensor_entity = common.ENT_SENSOR

    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Create YAML-style config with explicit 0 tolerance
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "sensor_stale_duration": datetime.timedelta(hours=24),
            "target_temp_step": 0.5,
            "cold_tolerance": 0.0,  # Explicit zero
            "hot_tolerance": 0.0,  # Explicit zero
        }
    }

    # Setup component with YAML config
    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get the thermostat entity
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None, "Thermostat entity should be found"

    # Verify tolerances are set correctly in environment manager
    assert (
        thermostat.environment._cold_tolerance == 0.0
    ), f"Environment manager cold_tolerance should be 0.0, got {thermostat.environment._cold_tolerance}"
    assert (
        thermostat.environment._hot_tolerance == 0.0
    ), f"Environment manager hot_tolerance should be 0.0, got {thermostat.environment._hot_tolerance}"
