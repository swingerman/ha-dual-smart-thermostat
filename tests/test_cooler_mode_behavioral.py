"""Behavioral threshold tests for cooler mode.

Tests verify that hot_tolerance creates the correct threshold for cooling activation.
These tests ensure the fix for issue #506 (inverted tolerance logic) stays fixed.

These tests are separate from test_cooler_mode.py to keep them focused and easy to
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
async def test_cooler_threshold_boundary_with_default_tolerance(hass: HomeAssistant):
    """Test cooler activation at exact threshold with default tolerance (0.3°C).

    With target=24°C and default hot_tolerance=0.3:
    - Threshold is 24.3°C
    - At 24.4°C: should cool (above threshold)
    - At 24.3°C: should cool (at threshold - inclusive)
    - At 24.2°C: should NOT cool (below threshold)
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"  # Required even for AC-only
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.0)

    # Using default tolerance (0.3)
    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "ac_mode": True,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "initial_hvac_mode": HVACMode.COOL,
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

    await thermostat.async_set_temperature(temperature=24.0)
    await hass.async_block_till_done()

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 24.4°C (above threshold 24.3)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.3)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 24.3°C (at threshold - inclusive)"

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT activate at 24.2°C (below threshold)"


@pytest.mark.asyncio
async def test_cooler_threshold_boundary_with_custom_tolerance(hass: HomeAssistant):
    """Test cooler activation with custom hot_tolerance (1.0°C).

    With target=20°C and hot_tolerance=1.0:
    - Threshold is 21.0°C
    - At 21.1°C: should cool
    - At 21.0°C: should cool (inclusive)
    - At 20.9°C: should NOT cool
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 20.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "ac_mode": True,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "hot_tolerance": 1.0,
            "initial_hvac_mode": HVACMode.COOL,
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

    # Test above threshold (21.1 > 21.0)
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 21.1°C (above threshold 21.0)"

    # Test at threshold (21.0 = 21.0)
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 21.0°C (at threshold)"

    # Test below threshold (20.9 < 21.0)
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 20.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT activate at 20.9°C (below threshold)"


@pytest.mark.asyncio
async def test_cooler_zero_tolerance_exact_threshold(hass: HomeAssistant):
    """Test cooler with zero tolerance - should activate only above target.

    With target=24°C and hot_tolerance=0:
    - Threshold is exactly 24°C
    - At 24.1°C: should cool
    - At 24.0°C: should cool (inclusive)
    - At 23.9°C: should NOT cool
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "ac_mode": True,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "hot_tolerance": 0.0,
            "initial_hvac_mode": HVACMode.COOL,
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

    await thermostat.async_set_temperature(temperature=24.0)
    await hass.async_block_till_done()

    # Test above target
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "With zero tolerance, cooler should activate at 24.1°C"

    # Test at target (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "With zero tolerance, cooler should activate at exactly 24.0°C (inclusive)"

    # Test below target
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 23.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "With zero tolerance, cooler should NOT activate at 23.9°C"
