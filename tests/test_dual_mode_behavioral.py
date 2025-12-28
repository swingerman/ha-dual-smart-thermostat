"""Behavioral threshold tests for dual mode (heater + cooler).

Tests verify that both cold_tolerance and hot_tolerance create correct thresholds
for heating and cooling activation in systems with separate heater and cooler switches.
These tests ensure the fix for issue #506 (inverted tolerance logic) stays fixed.

These tests are separate from test_dual_mode.py to keep them focused and easy to
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
async def test_dual_mode_heating_threshold_with_default_tolerance(hass: HomeAssistant):
    """Test heating threshold in HEAT mode with heater+cooler system.

    With target=22°C and default cold_tolerance=0.3:
    - Threshold is 21.7°C
    - At 21.6°C: should heat (below threshold)
    - At 21.7°C: should heat (at threshold - inclusive)
    - At 21.8°C: should NOT heat (above threshold)
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
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
async def test_dual_mode_cooling_threshold_with_default_tolerance(hass: HomeAssistant):
    """Test cooling threshold in COOL mode with heater+cooler system.

    With target=24°C and default hot_tolerance=0.3:
    - Threshold is 24.3°C
    - At 24.4°C: should cool (above threshold)
    - At 24.3°C: should cool (at threshold - inclusive)
    - At 24.2°C: should NOT cool (below threshold)
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
            "cooler": cooler_entity,
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
async def test_dual_mode_heat_cool_dual_thresholds(hass: HomeAssistant):
    """Test both thresholds in HEAT_COOL mode with default tolerance.

    With target_low=20°C, target_high=24°C, tolerance=0.3:
    - Heat threshold: 19.7°C (20 - 0.3)
    - Cool threshold: 24.3°C (24 + 0.3)
    - Dead band: 19.7 to 24.3
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "heat_cool_mode": True,
            "initial_hvac_mode": HVACMode.HEAT_COOL,
            "target_temp_low": 20.0,
            "target_temp_high": 24.0,
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

    # Test heating threshold - below 19.7
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 19.6°C (below heat threshold 19.7)"

    # Test heating threshold - at threshold (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.7)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 19.7°C (at heat threshold - inclusive)"

    # Test dead band - above heat threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT activate at 19.8°C (in dead band)"

    # Test cooling threshold - above 24.3
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 24.4°C (above cool threshold 24.3)"

    # Test cooling threshold - at threshold (inclusive)
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.3)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 24.3°C (at cool threshold - inclusive)"

    # Test dead band - below cool threshold
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT activate at 24.2°C (in dead band)"


@pytest.mark.asyncio
async def test_dual_mode_custom_tolerance_values(hass: HomeAssistant):
    """Test dual mode with custom tolerance values.

    With target=22°C, cold_tolerance=0.5, hot_tolerance=1.0:
    - Heat threshold: 21.5°C (22 - 0.5)
    - Cool threshold: 23.0°C (22 + 1.0)
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "cold_tolerance": 0.5,
            "hot_tolerance": 1.0,
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

    # Test heating with custom cold_tolerance
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should activate at 21.4°C (below threshold 21.5)"

    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 21.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT activate at 21.6°C (above threshold 21.5)"

    # Switch to cooling mode and test hot_tolerance
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    await hass.async_block_till_done()

    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 23.1)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should activate at 23.1°C (above threshold 23.0)"

    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 22.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT activate at 22.9°C (below threshold 23.0)"
