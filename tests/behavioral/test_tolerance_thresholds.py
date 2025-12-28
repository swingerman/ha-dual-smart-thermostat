"""Behavioral tests for tolerance threshold logic.

These tests verify that tolerance values correctly affect the EXACT temperature
thresholds at which heating/cooling turns on and off.

This test suite was created after discovering issue #506, where the tolerance
logic was completely inverted but existing tests didn't catch it because they
used values that happened to give correct results even with buggy logic.

Key principle: Test temperatures at and around the threshold boundaries:
- target - tolerance - 0.1 (should activate)
- target - tolerance (boundary - WILL activate, inclusive with <=)
- target - tolerance + 0.1 (should NOT activate)

Note: The threshold is INCLUSIVE (uses <= and >= operators), meaning:
- For heating: activates when current <= target - cold_tolerance
- For cooling: activates when current >= target + hot_tolerance
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
async def test_heater_cold_tolerance_threshold_heating_mode(hass: HomeAssistant):
    """Test that cold_tolerance creates correct heating threshold in HEAT mode.

    With target=20°C and cold_tolerance=0.3:
    - Threshold is 19.7°C (20 - 0.3)
    - At or below 19.7: should heat (inclusive threshold with <=)
    - Above 19.7: should NOT heat
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
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
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

    await thermostat.async_set_temperature(temperature=20.0)
    await hass.async_block_till_done()

    # Test 1: Below threshold (19.6 < 19.7) - should heat
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should turn ON at 19.6°C (below threshold 19.7)"

    # Test 2: At threshold (19.7 = 19.7) - WILL heat (threshold is inclusive with <=)
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)  # Reset heater state
    hass.states.async_set(sensor_entity, 19.7)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater SHOULD turn ON at 19.7°C (at threshold - inclusive boundary)"

    # Test 3: Above threshold (19.8 > 19.7) - should NOT heat
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT turn ON at 19.8°C (above threshold)"


@pytest.mark.asyncio
async def test_cooler_hot_tolerance_threshold_cooling_mode(hass: HomeAssistant):
    """Test that hot_tolerance creates correct cooling threshold in COOL mode.

    With target=24°C and hot_tolerance=0.3:
    - Threshold is 24.3°C (24 + 0.3)
    - At or above 24.3: should cool (inclusive threshold with >=)
    - Below 24.3: should NOT cool
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"  # Required even for AC-only mode
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,  # Required field
            "ac_mode": True,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
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

    # Test 1: Below threshold (24.2 < 24.3) - should NOT cool
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT turn ON at 24.2°C (below threshold 24.3)"

    # Test 2: At threshold (24.3 = 24.3) - WILL cool (inclusive threshold with >=)
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)  # Reset
    hass.states.async_set(sensor_entity, 24.3)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler SHOULD turn ON at 24.3°C (at threshold - inclusive boundary)"

    # Test 3: Above threshold (24.4 > 24.3) - should cool
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)  # Reset
    hass.states.async_set(sensor_entity, 24.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should turn ON at 24.4°C (above threshold 24.3)"


@pytest.mark.asyncio
async def test_heat_cool_mode_dual_thresholds(hass: HomeAssistant):
    """Test tolerance thresholds in HEAT_COOL mode with both heating and cooling.

    With target_low=20°C, target_high=24°C, tolerance=0.3:
    - Heat threshold: 19.7°C (20 - 0.3)
    - Cool threshold: 24.3°C (24 + 0.3)
    - Dead band: 19.7 to 24.3 (no heating or cooling)
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
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.HEAT_COOL,
            "target_temp_low": 20.0,
            "target_temp_high": 24.0,
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

    # Test heating threshold
    # At 19.6°C (below 19.7) - should heat
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should turn ON at 19.6°C (below heat threshold 19.7)"

    # At 19.8°C (above 19.7) - should NOT heat
    turn_on_calls.clear()
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 19.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should NOT turn ON at 19.8°C (above heat threshold)"

    # Test cooling threshold
    # At 24.4°C (above 24.3) - should cool
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 24.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should turn ON at 24.4°C (above cool threshold 24.3)"

    # At 24.2°C (below 24.3) - should NOT cool
    turn_on_calls.clear()
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 24.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should NOT turn ON at 24.2°C (below cool threshold)"


@pytest.mark.asyncio
async def test_zero_tolerance_immediate_response(hass: HomeAssistant):
    """Test that zero tolerance means immediate response at target temperature.

    With target=22°C and cold_tolerance=0:
    - Threshold is exactly 22°C
    - Below 22: should heat
    - At or above 22: should NOT heat
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
            "hot_tolerance": 0.0,
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

    # Test: Even 0.1° below target should activate with zero tolerance
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "With zero tolerance, heater should turn ON even at 21.9°C (0.1° below target)"


@pytest.mark.asyncio
async def test_large_tolerance_wide_dead_band(hass: HomeAssistant):
    """Test that large tolerance creates appropriately wide dead band.

    With target=22°C and cold_tolerance=2.0:
    - Threshold is 20.0°C (22 - 2.0)
    - This creates a 2°C dead band where heating won't activate
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
            "cold_tolerance": 2.0,
            "hot_tolerance": 2.0,
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

    # Test: At 21°C (1° below target but within 2° tolerance) - should NOT heat
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 21.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "With 2.0° tolerance, heater should NOT turn ON at 21.0°C (within tolerance)"

    # Test: At 19.9°C (just below threshold 20.0) - should heat
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 19.9)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should turn ON at 19.9°C (below threshold 20.0)"
