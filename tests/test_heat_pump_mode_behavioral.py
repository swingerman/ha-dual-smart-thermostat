"""Behavioral threshold tests for heat pump mode.

Tests verify that tolerance creates correct thresholds for heating and cooling
activation in heat pump systems (single switch that handles both heating and cooling).
These tests ensure the fix for issue #506 (inverted tolerance logic) stays fixed.

These tests are separate from test_heat_pump_mode.py to keep them focused and easy to
maintain. They test the EXACT boundary behavior that wasn't covered before.
"""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests.common import async_mock_service


@pytest.mark.asyncio
async def test_heat_pump_heating_threshold_with_default_tolerance(hass: HomeAssistant):
    """Test heat pump heating threshold with default tolerance.

    With target=22°C and default cold_tolerance=0.3:
    - Threshold is 21.7°C
    - At 21.6°C: should heat (below threshold)
    - At 21.7°C: should heat (at threshold - inclusive)
    - At 21.8°C: should NOT heat (above threshold)
    """
    hass.config.units = METRIC_SYSTEM

    heat_pump_entity = "input_boolean.heat_pump"
    heat_pump_cooling_sensor = "input_boolean.heat_pump_cooling"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_OFF)  # Not in cooling mode
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heat_pump_entity,
            "heat_pump_cooling": heat_pump_cooling_sensor,
            "target_sensor": sensor_entity,
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

    # Ensure thermostat is in HEAT mode
    await thermostat.async_set_hvac_mode(HVACMode.HEAT)
    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate at 21.6°C (below threshold 21.7)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.7)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate at 21.7°C (at threshold - inclusive)"

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should NOT activate at 21.8°C (above threshold)"


@pytest.mark.asyncio
async def test_heat_pump_cooling_threshold_with_default_tolerance(hass: HomeAssistant):
    """Test heat pump cooling threshold with default tolerance.

    With target=24°C and default hot_tolerance=0.3:
    - Threshold is 24.3°C
    - At 24.4°C: should cool (above threshold)
    - At 24.3°C: should cool (at threshold - inclusive)
    - At 24.2°C: should NOT cool (below threshold)
    """
    hass.config.units = METRIC_SYSTEM

    heat_pump_entity = "input_boolean.heat_pump"
    heat_pump_cooling_sensor = "input_boolean.heat_pump_cooling"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_ON)  # In cooling mode
    hass.states.async_set(sensor_entity, 24.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heat_pump_entity,
            "heat_pump_cooling": heat_pump_cooling_sensor,
            "target_sensor": sensor_entity,
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

    # Ensure thermostat is in COOL mode
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    await thermostat.async_set_temperature(temperature=24.0)
    await hass.async_block_till_done()

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate for cooling at 24.4°C (above threshold 24.3)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.3)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate for cooling at 24.3°C (at threshold - inclusive)"

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should NOT activate for cooling at 24.2°C (below threshold)"


@pytest.mark.asyncio
async def test_heat_pump_custom_tolerance_heating(hass: HomeAssistant):
    """Test heat pump with custom cold_tolerance in heating mode.

    With target=20°C and cold_tolerance=1.0:
    - Threshold is 19.0°C
    - At 18.9°C: should heat
    - At 19.0°C: should heat (inclusive)
    - At 19.1°C: should NOT heat
    """
    hass.config.units = METRIC_SYSTEM

    heat_pump_entity = "input_boolean.heat_pump"
    heat_pump_cooling_sensor = "input_boolean.heat_pump_cooling"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_OFF)
    hass.states.async_set(sensor_entity, 20.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heat_pump_entity,
            "heat_pump_cooling": heat_pump_cooling_sensor,
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

    # Ensure thermostat is in HEAT mode
    await thermostat.async_set_hvac_mode(HVACMode.HEAT)
    await thermostat.async_set_temperature(temperature=20.0)
    await hass.async_block_till_done()

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 18.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate at 18.9°C (below threshold 19.0)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate at 19.0°C (at threshold)"

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should NOT activate at 19.1°C (above threshold)"


@pytest.mark.asyncio
async def test_heat_pump_custom_tolerance_cooling(hass: HomeAssistant):
    """Test heat pump with custom hot_tolerance in cooling mode.

    With target=20°C and hot_tolerance=1.0:
    - Threshold is 21.0°C
    - At 21.1°C: should cool
    - At 21.0°C: should cool (inclusive)
    - At 20.9°C: should NOT cool
    """
    hass.config.units = METRIC_SYSTEM

    heat_pump_entity = "input_boolean.heat_pump"
    heat_pump_cooling_sensor = "input_boolean.heat_pump_cooling"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_ON)
    hass.states.async_set(sensor_entity, 20.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heat_pump_entity,
            "heat_pump_cooling": heat_pump_cooling_sensor,
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

    # Ensure thermostat is in COOL mode
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    await thermostat.async_set_temperature(temperature=20.0)
    await hass.async_block_till_done()

    # Test above threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate for cooling at 21.1°C (above threshold 21.0)"

    # Test at threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should activate for cooling at 21.0°C (at threshold)"

    # Test below threshold
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 20.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "Heat pump should NOT activate for cooling at 20.9°C (below threshold)"


@pytest.mark.asyncio
async def test_heat_pump_zero_tolerance(hass: HomeAssistant):
    """Test heat pump with zero tolerance in both modes.

    With target=22°C and tolerance=0:
    - In heating: threshold is exactly 22°C
    - In cooling: threshold is exactly 22°C
    """
    hass.config.units = METRIC_SYSTEM

    heat_pump_entity = "input_boolean.heat_pump"
    heat_pump_cooling_sensor = "input_boolean.heat_pump_cooling"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heat_pump_entity,
            "heat_pump_cooling": heat_pump_cooling_sensor,
            "target_sensor": sensor_entity,
            "cold_tolerance": 0.0,
            "hot_tolerance": 0.0,
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

    # Ensure thermostat is in HEAT mode
    await thermostat.async_set_hvac_mode(HVACMode.HEAT)
    await thermostat.async_set_temperature(temperature=22.0)
    await hass.async_block_till_done()

    # Test heating at exactly target (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 22.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "With zero tolerance, heat pump should activate at exactly 22.0°C (inclusive)"

    # Test heating below target
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "With zero tolerance, heat pump should activate at 21.9°C"

    # Switch to cooling mode
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    hass.states.async_set(heat_pump_cooling_sensor, STATE_ON)
    await hass.async_block_till_done()

    # Test cooling at exactly target (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "With zero tolerance, heat pump should activate for cooling at exactly 22.0°C (inclusive)"

    # Test cooling above target
    turn_on_calls.clear()
    hass.states.async_set(heat_pump_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heat_pump_entity for c in turn_on_calls
    ), "With zero tolerance, heat pump should activate for cooling at 22.1°C"
