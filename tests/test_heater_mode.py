"""The tests for the dual_smart_thermostat."""

import asyncio
from datetime import timedelta
import logging
from typing import Final
from unittest.mock import patch

from tests.const import MOCK_CONFIG_HEATER, MOCK_TARGET_SENSOR
from . import setup_component, setup_floor_sensor, setup_sensor, setup_comp_1
from . import common

from homeassistant.core import HomeAssistant

import pytest

from homeassistant.util import dt
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
)
from homeassistant.components import input_boolean, input_number

from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import (
    DOMAIN as CLIMATE,
)

from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM

from custom_components.dual_smart_thermostat.const import *
from custom_components.dual_smart_thermostat import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

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

PRESET_ANTI_FREEZE = "anti_freeze"

INPUT_SET_VALUE = "set_value"

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

ATTR_SWING_MODES = "swing_modes"
ATTR_SWING_MODE = "swing_mode"
ATTR_TARGET_TEMP_STEP = "target_temp_step"

_LOGGER = logging.getLogger(__name__)


async def test_heater_mode(hass, setup_comp_1) -> None:
    """Test thermostat heater switch in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


async def test_heater_mode_secondary_heater(hass, setup_comp_1):
    """Test thermostat secondary heater switch in heating mode."""

    secondaty_heater_timeout = 10
    heater_switch = "input_boolean.heater_switch"
    secondary_heater_switch = "input_boolean.secondary_heater_switch"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater_switch": None, "secondary_heater_switch": None}},
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "secondary_heater": secondary_heater_switch,
                "secondary_heater_timeout": {"seconds": secondaty_heater_timeout},
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()

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
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_OFF

    # if temp is below target temp secondary heater should be on again for the same day
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(secondary_heater_switch).state == STATE_ON


async def test_heater_mode_tolerance(hass, setup_comp_1):
    """Test thermostat heater switch in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.6)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19.4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 19.5)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


async def test_heater_mode_floor_temp(hass, setup_comp_1):
    """Test thermostat heater switch with floor temp in heating mode."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "temp", "initial": 10, "min": 0, "max": 40, "step": 1}
            }
        },
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18.6)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 28)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_floor_sensor(hass, 26)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 3)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON

    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_heater_mode_cycle(hass, duration, result_state, setup_comp_1):
    """Test thermostat heater switch in heating mode with min_cycle_duration."""
    heater_switch = "input_boolean.test"
    assert await async_setup_component(
        hass, input_boolean.DOMAIN, {"input_boolean": {"test": None}}
    )

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
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await common.async_set_temperature(hass, 23)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == result_state
