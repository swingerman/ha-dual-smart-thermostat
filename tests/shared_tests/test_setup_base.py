"""Consolidated setup and initialization tests across all HVAC modes.

This module consolidates duplicate setup tests from mode-specific test files:
- test_unique_id (6+ duplicates → 1 parametrized test)
- test_setup_defaults_to_unknown (6 duplicates → 1 parametrized test)
- test_setup_gets_current_temp_from_sensor (6 duplicates → 1 parametrized test)

All tests follow the Given/When/Then pattern.
"""

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests import common


@pytest.mark.parametrize(
    "mode_config",
    ["heater", "cooler", "heat_pump", "fan"],
    indirect=True,
)
async def test_unique_id(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mode_config,
) -> None:
    """Test that unique ID is correctly set for climate entity across all HVAC modes.

    This test consolidates 6+ duplicate unique_id tests from mode-specific files.
    """
    # GIVEN - System with input helpers and unique ID configured
    unique_id = "some_unique_id"
    hass.config.units = METRIC_SYSTEM

    # Setup input_boolean for device switches
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    # Setup input_number for temperature sensor
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    # Build climate configuration based on mode
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 2,
        "hot_tolerance": 4,
        "heater": mode_config["device_entity"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
        "unique_id": unique_id,
    }

    # Add mode-specific configuration
    climate_config.update(mode_config["config_extra"])

    # WHEN - Climate component is set up with unique ID
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    # THEN - Entity is registered with correct unique ID
    entry = entity_registry.async_get(common.ENTITY)
    assert entry is not None
    assert entry.unique_id == unique_id


@pytest.mark.parametrize(
    "mode_config",
    ["heater", "cooler", "heat_pump", "fan"],
    indirect=True,
)
async def test_setup_defaults_to_unknown(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that climate entity defaults to OFF when no initial_hvac_mode specified.

    This test consolidates 6 duplicate tests from mode-specific files.
    """
    # GIVEN - System configured without initial_hvac_mode parameter
    hass.config.units = METRIC_SYSTEM

    # Build climate configuration without initial_hvac_mode
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 2,
        "hot_tolerance": 4,
        "heater": mode_config["device_entity"],
        "target_sensor": common.ENT_SENSOR,
        # Note: initial_hvac_mode intentionally NOT set
    }

    # Add mode-specific configuration
    climate_config.update(mode_config["config_extra"])

    # WHEN - Climate component is set up
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    # THEN - Entity defaults to OFF state
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.state == HVACMode.OFF


@pytest.mark.parametrize(
    "mode_config",
    ["heater", "cooler", "heat_pump", "fan"],
    indirect=True,
)
async def test_setup_gets_current_temp_from_sensor(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that climate entity reads current temperature from sensor on setup.

    This test consolidates 6 duplicate tests from mode-specific files.
    """
    # GIVEN - System with temperature sensor already set
    hass.config.units = METRIC_SYSTEM

    # Set up temperature sensor BEFORE climate setup
    from tests import setup_sensor

    sensor_value = 18
    setup_sensor(hass, sensor_value)
    await hass.async_block_till_done()

    # Build climate configuration
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 2,
        "hot_tolerance": 4,
        "heater": mode_config["device_entity"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
    }

    # Add mode-specific configuration
    climate_config.update(mode_config["config_extra"])

    # WHEN - Climate component is set up
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    # THEN - Current temperature matches sensor value
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes.get("current_temperature") == sensor_value


@pytest.mark.parametrize(
    "mode_config",
    ["heater", "cooler", "heat_pump", "fan"],
    indirect=True,
)
async def test_sensor_state_unknown_on_startup(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that climate entity handles unknown sensor state on startup.

    This test verifies that when the temperature sensor has an unknown state
    during setup, the climate entity still initializes correctly.
    """
    # GIVEN - System with sensor in unknown state
    hass.config.units = METRIC_SYSTEM

    # Set up sensor with unknown state BEFORE climate setup
    hass.states.async_set(common.ENT_SENSOR, STATE_UNKNOWN)
    await hass.async_block_till_done()

    # Build climate configuration
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 2,
        "hot_tolerance": 4,
        "heater": mode_config["device_entity"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
    }

    # Add mode-specific configuration
    climate_config.update(mode_config["config_extra"])

    # WHEN - Climate component is set up with unknown sensor
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    # THEN - Entity initializes with no current temperature
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes.get("current_temperature") is None


@pytest.mark.parametrize(
    "mode_config",
    ["heater", "cooler", "heat_pump", "fan"],
    indirect=True,
)
async def test_sensor_state_unavailable_on_startup(
    hass: HomeAssistant,
    mode_config,
) -> None:
    """Test that climate entity handles unavailable sensor state on startup.

    This test verifies that when the temperature sensor is unavailable
    during setup, the climate entity still initializes correctly.
    """
    # GIVEN - System with sensor in unavailable state
    hass.config.units = METRIC_SYSTEM

    # Set up sensor with unavailable state BEFORE climate setup
    hass.states.async_set(common.ENT_SENSOR, STATE_UNAVAILABLE)
    await hass.async_block_till_done()

    # Build climate configuration
    climate_config = {
        "platform": DOMAIN,
        "name": "test",
        "cold_tolerance": 2,
        "hot_tolerance": 4,
        "heater": mode_config["device_entity"],
        "target_sensor": common.ENT_SENSOR,
        "initial_hvac_mode": mode_config["hvac_mode"],
    }

    # Add mode-specific configuration
    climate_config.update(mode_config["config_extra"])

    # WHEN - Climate component is set up with unavailable sensor
    assert await async_setup_component(
        hass,
        CLIMATE,
        {"climate": climate_config},
    )
    await hass.async_block_till_done()

    # THEN - Entity initializes with no current temperature
    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert state.attributes.get("current_temperature") is None
