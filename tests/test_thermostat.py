"""The tests for the dual_smart_thermostat."""
import asyncio
from datetime import timedelta
import logging
import time
from typing import Final
from unittest.mock import patch

import pytest

from homeassistant.components import input_boolean, input_number
from homeassistant.util import dt
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.dual_smart_thermostat.const import *
from custom_components.dual_smart_thermostat import (
    DOMAIN as DUAL_SMART_THERMOSTAT,
)

ENT_SWITCH = "switch.test"
HEAT_ENTITY = "climate.test_heat"
COOL_ENTITY = "climate.test_cool"
ATTR_AWAY_MODE = "away_mode"
MIN_TEMP = 3.0
MAX_TEMP = 65.0
TARGET_TEMP = 42.0
COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5
TARGET_TEMP_STEP = 0.5

SERVICE_SET_TEMPERATURE = "set_temperature"
SERVICE_SET_HVAC_MODE = "set_hvac_mode"
INPUT_SET_VALUE = "set_value"
ENTITY_MATCH_ALL: Final = "all"

ATTR_AUX_HEAT = "aux_heat"
ATTR_CURRENT_HUMIDITY = "current_humidity"
ATTR_CURRENT_TEMPERATURE = "current_temperature"
ATTR_FAN_MODES = "fan_modes"
ATTR_FAN_MODE = "fan_mode"
ATTR_PRESET_MODE = "preset_mode"
ATTR_PRESET_MODES = "preset_modes"
ATTR_HUMIDITY = "humidity"
ATTR_MAX_HUMIDITY = "max_humidity"
ATTR_MIN_HUMIDITY = "min_humidity"
ATTR_MAX_TEMP = "max_temp"
ATTR_MIN_TEMP = "min_temp"
ATTR_HVAC_ACTION = "hvac_action"
ATTR_HVAC_MODES = "hvac_modes"
ATTR_HVAC_MODE = "hvac_mode"
ATTR_SWING_MODES = "swing_modes"
ATTR_SWING_MODE = "swing_mode"
ATTR_TARGET_TEMP_HIGH = "target_temp_high"
ATTR_TARGET_TEMP_LOW = "target_temp_low"
ATTR_TARGET_TEMP_STEP = "target_temp_step"


_LOGGER = logging.getLogger(__name__)


async def test_valid_conf(hass):
    """Test set up dual_smart_thermostat with valid config values."""
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": CONF_HEATER,
                "target_sensor": CONF_SENSOR,
            }
        },
    )


@pytest.fixture
async def setup_comp_1(hass):
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, HASS_DOMAIN, {})
    await hass.async_block_till_done()


@pytest.mark.asyncio
async def test_heater_mode(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater switch in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 23)
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


@pytest.mark.asyncio
async def test_heater_mode_secondary_heater(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat secondary heater switch in heating mode."""

    secondaty_heater_timeout = 10
    heater_switch = "input_boolean.heater_switch"
    secondary_heater_switch = "input_boolean.secondary_heater_switch"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater_switch": None, "secondary_heater_switch": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "secondary_heater": secondary_heater_switch,
                "secondary_heater_timeout": {"seconds": secondaty_heater_timeout},
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 23)
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # until secondary heater timeout everything should be the same
    await asyncio.sleep(secondaty_heater_timeout - 4)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # after secondary heater timeout secondary heater should be on
    await asyncio.sleep(secondaty_heater_timeout + 3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON

    # triggers reaching target temp should turn off secondary heater
    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # if temp is below target temp secondary heater should be on again for the same day
    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON


@pytest.mark.asyncio
async def test_heater_mode_tolerance(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater switch in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18.6)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 19.4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 19.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


@pytest.mark.asyncio
async def test_heater_mode_floor_temp(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater switch with floor temp in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "temp", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    floor_temp_input = "input_number.floor_temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "floor_temp",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                }
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
                "floor_sensor": floor_temp_input,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18.6)
    _setup_sensor(hass, floor_temp_input, 10)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18)
    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, floor_temp_input, 28)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, floor_temp_input, 26)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, floor_temp_input, 4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, floor_temp_input, 3)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, floor_temp_input, 10)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_heater_mode_cycle(hass, duration, result_state, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater switch in heating mode with min_cycle_duration."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await async_climate_set_temperature(hass, 23)
        assert hass.states.get(heater_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state


@pytest.mark.asyncio
async def test_cooler_mode(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18)
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.asyncio
async def test_mode_change(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat switch state iif HVAc mode changes."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18)
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.asyncio
async def test_cooler_mode_tolerance(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 22.4)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 22)
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 21.5)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_cooler_mode_cycle(hass, duration, result_state, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    cooler_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await async_climate_set_temperature(hass, 18)
        assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.asyncio
async def test_cooler_mode_dual(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18)
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_cooler_mode_dual_cycle(hass, duration, result_state, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await async_climate_set_temperature(hass, 18)
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.asyncio
async def test_cooler_mode_opening(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "opening_1": None, "opening_2": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.COOL,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 10}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 23)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18)
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON


@pytest.mark.asyncio
async def test_heater_cooler_mode(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": temp_input,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get("climate.test").attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()

    await async_set_hvac_mode(hass, "all", HVACMode.HEAT_COOL)
    await async_climate_set_temperature(hass, 18, "all", 25, 22)
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # switch to heat only mode
    await async_set_hvac_mode(hass, "all", HVACMode.HEAT)
    await async_climate_set_temperature(hass, 25, "all", 25, 22)

    _setup_sensor(hass, temp_input, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # swith to cool only mode
    await async_set_hvac_mode(hass, "all", HVACMode.COOL)

    assert hass.states.get(heater_switch).state == STATE_OFF


@pytest.mark.asyncio
async def test_heater_cooler_mode_floor_temp(hass, setup_comp_1):
    await setup_comp_1
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "temp", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    floor_temp_input = "input_number.floor_temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "floor_temp",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                }
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": temp_input,
                "floor_sensor": floor_temp_input,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get("climate.test").attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    _setup_sensor(hass, floor_temp_input, 10)
    await hass.async_block_till_done()

    await async_set_hvac_mode(hass, "all", HVACMode.HEAT_COOL)
    await async_climate_set_temperature(hass, 18, "all", 25, 22)
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is below min_floor_temp, heater should be on"""
    _setup_sensor(hass, floor_temp_input, 4)
    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is above min_floor_temp, heater should be off"""
    _setup_sensor(hass, floor_temp_input, 10)
    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_heater_cooler_mode_cycle_heat(
    hass, duration, result_state, setup_comp_1
):
    """Test thermostat heater and cooler switch in heat mode with min_cycle_duration."""
    await setup_comp_1
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        assert await async_setup_component(
            hass,
            input_boolean.DOMAIN,
            {"input_boolean": {"heater": None, "cooler": None}},
        )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 20)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await async_climate_set_temperature(hass, None, "all", 25, 22)
        assert hass.states.get(heater_switch).state == STATE_ON
        assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state
    assert hass.states.get(cooler_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_heater_cooler_mode_cycle_cool(
    hass, duration, result_state, setup_comp_1
):
    """Test thermostat heater and cooler switch in cool mode with min_cycle_duration."""

    await setup_comp_1
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        assert await async_setup_component(
            hass,
            input_boolean.DOMAIN,
            {"input_boolean": {"heater": None, "cooler": None}},
        )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await async_climate_set_temperature(hass, None, "all", 25, 22)
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.asyncio
async def test_heater_cooler_switch_hvac_modes(hass, setup_comp_1):
    """Test thermostat heater and cooler switch to heater only mode."""

    await setup_comp_1
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 26)
    await hass.async_block_till_done()

    await async_set_hvac_mode(hass, "all", HVACMode.HEAT)
    assert hass.states.get("climate.test").state == HVAC_MODE_HEAT

    await async_set_hvac_mode(hass, "all", HVACMode.COOL)
    assert hass.states.get("climate.test").state == HVAC_MODE_COOL


@pytest.mark.asyncio
async def test_heater_cooler_mode_tolerances(hass, setup_comp_1):
    """Test thermostat heater and cooler mode tolerances."""

    await setup_comp_1
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    temp_input = "input_number.temp"
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DUAL_SMART_THERMOSTAT,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": temp_input,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "heat_cool_mode": True,
                "hot_tolerance": 0.3,
                "cold_tolerance": 0.3,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 24)
    await hass.async_block_till_done()

    await async_climate_set_temperature(hass, 18, "all", 25, 22)

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 21.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 22.1)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 22.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # since both heater and cooler are off, we expect the cooler not
    # to turn on until the temperature is 0.3 degrees above the target
    _setup_sensor(hass, temp_input, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    _setup_sensor(hass, temp_input, 25.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # since cooler is on we expect it keep on until reaches 0.3 degrees
    # below the target
    _setup_sensor(hass, temp_input, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    _setup_sensor(hass, temp_input, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


def _setup_sensor(hass, sensor, temp):
    """Set up the test sensor."""
    hass.states.async_set(sensor, temp)


def _setup_boolean(hass, entity, state):
    """Set up the test sensor."""
    hass.states.async_set(entity, state)


async def async_climate_set_temperature(
    hass,
    temperature=None,
    entity_id="all",
    target_temp_high=None,
    target_temp_low=None,
    hvac_mode=None,
):
    """Set new target temperature."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_TEMPERATURE, temperature),
            (ATTR_TARGET_TEMP_HIGH, target_temp_high),
            (ATTR_TARGET_TEMP_LOW, target_temp_low),
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("set_temperature start data=%s", kwargs)
    await hass.services.async_call(
        CLIMATE, SERVICE_SET_TEMPERATURE, kwargs, blocking=True
    )


async def async_set_hvac_mode(
    hass,
    entity_id="all",
    hvac_mode=HVACMode.OFF,
):
    """Set new HVAC mode."""
    kwargs = {
        key: value
        for key, value in [
            (ATTR_ENTITY_ID, entity_id),
            (ATTR_HVAC_MODE, hvac_mode),
        ]
        if value is not None
    }
    _LOGGER.debug("%s start data=%s", SERVICE_SET_HVAC_MODE, kwargs)
    await hass.services.async_call(
        CLIMATE, SERVICE_SET_HVAC_MODE, kwargs, blocking=True
    )
