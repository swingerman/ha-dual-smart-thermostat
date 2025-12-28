"""Behavioral threshold tests for heater mode.

Tests verify that cold_tolerance creates the correct threshold for heating activation.
These tests ensure the fix for issue #506 (inverted tolerance logic) stays fixed.

These tests are separate from test_heater_mode.py to keep them focused and easy to
maintain. They test the EXACT boundary behavior that wasn't covered before.
"""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import SERVICE_TURN_ON, STATE_OFF
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests.common import async_mock_service


@pytest.mark.asyncio
async def test_heater_threshold_boundary_with_default_tolerance(hass: HomeAssistant):
    """Test heater activation at exact threshold with default tolerance (0.3°C).

    With target=22°C and default cold_tolerance=0.3:
    - Threshold is 21.7°C
    - At 21.6°C: should heat (below threshold)
    - At 21.7°C: should heat (at threshold - inclusive)
    - At 21.8°C: should NOT heat (above threshold)
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    # Using default tolerance (0.3)
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "target_sensor": sensor_entity,
            "initial_hvac_mode": HVACMode.HEAT,
        }
    }

    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    # Get thermostat
    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 21.6°C (below threshold 21.7)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.7)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 21.7°C (at threshold - inclusive)"

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT activate at 21.8°C (above threshold)"


@pytest.mark.asyncio
async def test_heater_threshold_boundary_with_custom_tolerance(hass: HomeAssistant):
    """Test heater activation with custom cold_tolerance (1.0°C).

    With target=20°C and cold_tolerance=1.0:
    - Threshold is 19.0°C
    - At 18.9°C: should heat
    - At 19.0°C: should heat (inclusive)
    - At 19.1°C: should NOT heat
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 20.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "target_sensor": sensor_entity,
            "cold_tolerance": 1.0,
            "initial_hvac_mode": HVACMode.HEAT,
        }
    }

    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    await thermostat.async_set_temperature(temperature=20.0)
    await hass.async_block_till_done()

    # Test below threshold (18.9 < 19.0)
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 18.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 18.9°C (below threshold 19.0)"

    # Test at threshold (19.0 = 19.0)
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 19.0°C (at threshold)"

    # Test above threshold (19.1 > 19.0)
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT activate at 19.1°C (above threshold)"


@pytest.mark.asyncio
async def test_heater_zero_tolerance_exact_threshold(hass: HomeAssistant):
    """Test heater with zero tolerance - should activate only below target.

    With target=22°C and cold_tolerance=0:
    - Threshold is exactly 22°C
    - At 21.9°C: should heat
    - At 22.0°C: should heat (inclusive)
    - At 22.1°C: should NOT heat
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "target_sensor": sensor_entity,
            "cold_tolerance": 0.0,
            "initial_hvac_mode": HVACMode.HEAT,
        }
    }

    turn_on_calls = async_mock_service(hass, "homeassistant", SERVICE_TURN_ON)

    assert await async_setup_component(hass, CLIMATE, yaml_config)
    await hass.async_block_till_done()

    thermostat = None
    for entity in hass.data[CLIMATE].entities:
        if entity.entity_id == "climate.test":
            thermostat = entity
            break

    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Test below target
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "With zero tolerance, heater should activate at 21.9°C"

    # Test at target (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "With zero tolerance, heater should activate at exactly 22.0°C (inclusive)"

    # Test above target
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "With zero tolerance, heater should NOT activate at 22.1°C"
