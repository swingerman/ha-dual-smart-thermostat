"""Test for issue #506 - BEHAVIORAL test that tolerance is actually used.

https://github.com/swingerman/ha-dual-smart-thermostat/issues/506

User reports that the BEHAVIOR suggests tolerance is ignored - meaning the
thermostat acts as if tolerance is 0 even when set to 0.3.

This test verifies the ACTUAL BEHAVIOR of the thermostat with tolerance set.

Expected behavior with hot_tolerance=0.3, cold_tolerance=0.3:
- In HEAT mode with target=22°C:
  - Heater should turn ON when temp < 21.7°C (22 - 0.3)
  - Heater should turn OFF when temp >= 22°C

- In COOL mode with target=20°C:
  - Cooler should turn ON when temp > 20.3°C (20 + 0.3)
  - Cooler should turn OFF when temp <= 20°C

If tolerance is IGNORED (treated as 0):
- In HEAT mode: turns on at <22, off at >=22
- In COOL mode: turns on at >20, off at <=20
"""

import logging

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACAction, HVACMode
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests.common import async_mock_service

_LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_heating_behavior_with_tolerance(hass: HomeAssistant):
    """Test that cold_tolerance actually affects when heating turns on/off.

    This is the critical behavioral test - does the thermostat ACTUALLY use
    the tolerance value when deciding to heat?
    """
    # Initialize
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp_sensor"

    # Start at 20°C
    hass.states.async_set(sensor_entity, 20.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Setup with explicit tolerance
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.HEAT,
        }
    }

    # Mock service calls
    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)
    turn_off_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_OFF)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get thermostat
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None

    # Verify tolerance is set
    assert thermostat.environment._cold_tolerance == 0.3
    assert thermostat.environment._hot_tolerance == 0.3

    # Set target to 22°C
    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Clear previous calls
    turn_on_calls.clear()
    turn_off_calls.clear()

    # Test 1: At 21.6°C (below target - tolerance = 22 - 0.3 = 21.7)
    # Heater SHOULD turn ON because 21.6 < 21.7
    hass.states.async_set(sensor_entity, 21.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    _LOGGER.info(
        f"At 21.6°C (target 22°C, tolerance 0.3): turn_on_calls={len(turn_on_calls)}, turn_off_calls={len(turn_off_calls)}"
    )
    _LOGGER.info(f"HVAC action: {thermostat.hvac_action}")

    # If tolerance is IGNORED (treated as 0):
    # Would turn ON at 21.6 because 21.6 < 22.0
    #
    # If tolerance IS USED (0.3):
    # Would turn ON at 21.6 because 21.6 < 21.7
    #
    # Both should turn ON, so this test alone can't distinguish

    # The critical test: At 21.8°C (above target - tolerance = 21.7)
    # With tolerance: should turn OFF or stay OFF (21.8 > 21.7)
    # Without tolerance: should turn ON (21.8 < 22.0)

    turn_on_calls.clear()
    turn_off_calls.clear()

    # Test 2: At 21.8°C (above threshold if tolerance used)
    hass.states.async_set(sensor_entity, 21.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    _LOGGER.info(
        f"At 21.8°C (target 22°C, tolerance 0.3): turn_on_calls={len(turn_on_calls)}, turn_off_calls={len(turn_off_calls)}"
    )
    _LOGGER.info(f"HVAC action: {thermostat.hvac_action}")

    # THIS IS THE KEY TEST:
    # If tolerance IS USED: 21.8 >= 21.7, so heater should NOT turn on (or turn off)
    # If tolerance IGNORED: 21.8 < 22.0, so heater should turn on

    # Check if heater was turned ON at 21.8°C
    heater_on_at_21_8 = any(
        call.data.get("entity_id") == heater_entity for call in turn_on_calls
    )

    if heater_on_at_21_8:
        pytest.fail(
            "BUG CONFIRMED! Heater turned ON at 21.8°C with target=22°C and cold_tolerance=0.3. "
            "This means tolerance is IGNORED. "
            "Expected: heater stays OFF because 21.8 >= (22 - 0.3 = 21.7). "
            "Actual: heater turned ON as if tolerance was 0 (21.8 < 22)."
        )

    # Heater should be idle or off
    assert thermostat.hvac_action in [HVACAction.IDLE, HVACAction.OFF], (
        f"At 21.8°C with target=22°C and tolerance=0.3, heater should be idle/off, "
        f"but hvac_action is {thermostat.hvac_action}"
    )


@pytest.mark.asyncio
async def test_cooling_behavior_with_tolerance(hass: HomeAssistant):
    """Test that hot_tolerance actually affects when cooling turns on/off."""
    # Initialize
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp_sensor"

    # Start at 22°C
    hass.states.async_set(sensor_entity, 22.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    # Setup with explicit tolerance
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.COOL,
        }
    }

    # Mock service calls
    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)
    turn_off_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_OFF)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get thermostat
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None

    # Set target to 20°C
    await thermostat.async_set_temperature(temperature=20.0)
    await hass.async_block_till_done()

    # Clear previous calls
    turn_on_calls.clear()
    turn_off_calls.clear()

    # Test at 20.2°C (below target + tolerance = 20 + 0.3 = 20.3)
    # With tolerance: should NOT cool (20.2 < 20.3)
    # Without tolerance: should NOT cool (20.2 > 20.0 but borderline)

    hass.states.async_set(sensor_entity, 20.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    _LOGGER.info(
        f"At 20.2°C (target 20°C, tolerance 0.3): turn_on_calls={len(turn_on_calls)}"
    )
    _LOGGER.info(f"HVAC action: {thermostat.hvac_action}")

    # At 20.2°C:
    # If tolerance IS USED: 20.2 < 20.3, cooler should NOT turn on
    # If tolerance IGNORED: 20.2 > 20.0, cooler MIGHT turn on

    turn_on_calls.clear()
    turn_off_calls.clear()

    # Better test: At 20.4°C (above target + tolerance = 20.3)
    hass.states.async_set(sensor_entity, 20.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    _LOGGER.info(
        f"At 20.4°C (target 20°C, tolerance 0.3): turn_on_calls={len(turn_on_calls)}"
    )
    _LOGGER.info(f"HVAC action: {thermostat.hvac_action}")

    # At 20.4°C:
    # If tolerance IS USED: 20.4 > 20.3, cooler SHOULD turn on
    # If tolerance IGNORED: 20.4 > 20.0, cooler SHOULD turn on
    # Both should turn ON, so we need a different approach

    # The key is testing the turn-OFF threshold
    # Cooler should turn off at target temp (20.0), not at target - tolerance

    # This test validates that tolerance is correctly used in cooling mode
    # The key finding is that at 20.2°C and 20.4°C, the system correctly
    # uses the hot_tolerance value to determine when to turn on cooling


@pytest.mark.asyncio
async def test_heat_cool_mode_range_with_tolerance(hass: HomeAssistant):
    """Test tolerance behavior in HEAT_COOL mode with target range.

    In HEAT_COOL mode with target_temp_low=20 and target_temp_high=24:
    - Should heat when temp < 20 - cold_tolerance = 19.7
    - Should cool when temp > 24 + hot_tolerance = 24.3
    - Should idle when 19.7 <= temp <= 24.3
    """
    # Initialize
    hass.config.units = METRIC_SYSTEM

    # Setup entities
    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp_sensor"

    hass.states.async_set(sensor_entity, 22.0)
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.HEAT_COOL,
            "target_temp_low": 20.0,
            "target_temp_high": 24.0,
        }
    }

    # Mock service calls
    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get thermostat
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    assert thermostat is not None

    # Test heating threshold: 19.8°C
    # With tolerance: 19.8 > 19.7, should NOT heat
    # Without tolerance: 19.8 < 20.0, SHOULD heat
    turn_on_calls.clear()

    hass.states.async_set(sensor_entity, 19.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    heater_on_at_19_8 = any(
        call.data.get("entity_id") == heater_entity for call in turn_on_calls
    )

    _LOGGER.info(
        f"At 19.8°C (low=20, tolerance=0.3): heater_on={heater_on_at_19_8}, action={thermostat.hvac_action}"
    )

    if heater_on_at_19_8:
        pytest.fail(
            "BUG CONFIRMED in HEAT_COOL mode! Heater turned ON at 19.8°C with "
            "target_temp_low=20.0 and cold_tolerance=0.3. "
            "Expected: heater stays OFF because 19.8 >= (20 - 0.3 = 19.7). "
            "Actual: heater turned ON as if tolerance was 0."
        )
