"""Test for issue #518 - Heater turns off prematurely ignoring hot_tolerance.

This test reproduces the bug where the heater turns off as soon as temperature
reaches the target, instead of waiting until target + hot_tolerance.

User scenario from issue #518:
- Heater is ON
- Setpoint: 18°C
- hot_tolerance: 0.3
- Current temperature: 18.2°C
- Expected: Heater should REMAIN ON (should only turn off at >= 18.3°C)
- Actual bug: Heater turns OFF prematurely

This is a regression that appeared in v0.11.0, with v0.9.12 working correctly.
"""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests.common import async_mock_service


@pytest.mark.asyncio
async def test_heater_stays_on_until_target_plus_hot_tolerance(hass: HomeAssistant):
    """Test that heater stays on until temperature reaches target + hot_tolerance.

    Scenario from issue #518:
    - Setpoint: 18°C
    - hot_tolerance: 0.3°C
    - Heater should turn OFF at: 18.3°C
    - At 18.2°C: Heater should REMAIN ON (bug: it turns off)
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"
    sensor_entity = "sensor.temp"

    # Start with heater OFF, temperature below threshold
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 17.5)

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

    # Set HEAT mode and target temperature
    await thermostat.async_set_hvac_mode(HVACMode.HEAT)
    await thermostat.async_set_temperature(temperature=18.0)
    await hass.async_block_till_done()

    # Temperature is 17.5°C - below threshold (18 - 0.3 = 17.7)
    # Heater should turn ON
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 17.5)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_on_calls
    ), "Heater should turn ON at 17.5°C (below threshold 17.7°C)"

    # Manually set heater to ON to simulate it being active
    hass.states.async_set(heater_entity, STATE_ON)
    await hass.async_block_till_done()

    # Temperature rises to 18.0°C (exactly at target)
    # Heater should REMAIN ON (should only turn off at 18.3°C)
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 18.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_off_calls
    ), "Heater should REMAIN ON at 18.0°C (target, below 18.3°C threshold)"

    # Temperature rises to 18.2°C (the exact scenario from issue #518)
    # Heater should STILL REMAIN ON (should only turn off at 18.3°C)
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 18.2)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == heater_entity for c in turn_off_calls
    ), "BUG #518: Heater should REMAIN ON at 18.2°C (below 18.3°C threshold)"

    # Temperature reaches 18.3°C (target + hot_tolerance)
    # NOW the heater should turn OFF
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 18.3)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_off_calls
    ), "Heater should turn OFF at 18.3°C (at threshold)"

    # Temperature goes above 18.3°C
    # Heater should definitely be OFF
    turn_off_calls.clear()
    hass.states.async_set(heater_entity, STATE_ON)  # Reset to ON
    hass.states.async_set(sensor_entity, 18.4)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == heater_entity for c in turn_off_calls
    ), "Heater should turn OFF at 18.4°C (above threshold)"


@pytest.mark.asyncio
async def test_cooler_stays_on_until_target_minus_cold_tolerance(hass: HomeAssistant):
    """Test that cooler stays on until temperature reaches target - cold_tolerance.

    Mirror scenario for cooling:
    - Setpoint: 24°C
    - cold_tolerance: 0.3°C
    - Cooler should turn OFF at: 23.7°C
    - At 23.8°C: Cooler should REMAIN ON
    """
    hass.config.units = METRIC_SYSTEM

    heater_entity = "input_boolean.heater"  # Required even for AC-only
    cooler_entity = "input_boolean.cooler"
    sensor_entity = "sensor.temp"

    # Start with cooler OFF, temperature above threshold
    hass.states.async_set(heater_entity, STATE_OFF)
    hass.states.async_set(cooler_entity, STATE_OFF)
    hass.states.async_set(sensor_entity, 25.0)

    yaml_config = {
        CLIMATE: {
            "platform": DOMAIN,
            "name": "test",
            "heater": heater_entity,
            "ac_mode": True,
            "cooler": cooler_entity,
            "target_sensor": sensor_entity,
            "cold_tolerance": 0.3,
            "hot_tolerance": 0.3,
            "initial_hvac_mode": HVACMode.COOL,
        }
    }

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

    # Set COOL mode and target temperature
    await thermostat.async_set_hvac_mode(HVACMode.COOL)
    await thermostat.async_set_temperature(temperature=24.0)
    await hass.async_block_till_done()

    # Temperature is 25.0°C - above threshold (24 + 0.3 = 24.3)
    # Cooler should turn ON
    turn_on_calls.clear()
    hass.states.async_set(sensor_entity, 25.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_on_calls
    ), "Cooler should turn ON at 25.0°C (above threshold 24.3°C)"

    # Manually set cooler to ON to simulate it being active
    hass.states.async_set(cooler_entity, STATE_ON)
    await hass.async_block_till_done()

    # Temperature drops to 24.0°C (exactly at target)
    # Cooler should REMAIN ON (should only turn off at 23.7°C)
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 24.0)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_off_calls
    ), "Cooler should REMAIN ON at 24.0°C (target, above 23.7°C threshold)"

    # Temperature drops to 23.8°C (mirror of heating scenario)
    # Cooler should STILL REMAIN ON (should only turn off at 23.7°C)
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 23.8)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert not any(
        c.data.get("entity_id") == cooler_entity for c in turn_off_calls
    ), "Cooler should REMAIN ON at 23.8°C (above 23.7°C threshold)"

    # Temperature reaches 23.7°C (target - cold_tolerance)
    # NOW the cooler should turn OFF
    turn_off_calls.clear()
    hass.states.async_set(sensor_entity, 23.7)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_off_calls
    ), "Cooler should turn OFF at 23.7°C (at threshold)"

    # Temperature goes below 23.7°C
    # Cooler should definitely be OFF
    turn_off_calls.clear()
    hass.states.async_set(cooler_entity, STATE_ON)  # Reset to ON
    hass.states.async_set(sensor_entity, 23.6)
    await hass.async_block_till_done()
    await thermostat._async_control_climate(force=True)
    await hass.async_block_till_done()

    assert any(
        c.data.get("entity_id") == cooler_entity for c in turn_off_calls
    ), "Cooler should turn OFF at 23.6°C (below threshold)"
