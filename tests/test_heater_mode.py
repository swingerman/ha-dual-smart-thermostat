"""The tests for the dual_smart_thermostat."""

import asyncio
from datetime import timedelta
import logging
from unittest.mock import patch

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common, setup_comp_1, setup_floor_sensor, setup_sensor  # noqa: F401

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

_LOGGER = logging.getLogger(__name__)


async def test_heater_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
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


async def test_heater_mode_secondary_heater(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
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


async def test_heater_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
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
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
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


async def test_heater_mode_floor_temp(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
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
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
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
async def test_heater_mode_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
) -> None:
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
