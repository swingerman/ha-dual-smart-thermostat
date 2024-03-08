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

from . import common, setup_boolean, setup_comp_1, setup_sensor  # noqa: F401

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

_LOGGER = logging.getLogger(__name__)


async def test_cooler_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_mode_change(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat switch state if HVAc mode changes."""
    cooler_switch = "input_boolean.test"
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF


async def test_cooler_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "cold_tolerance": COLD_TOLERANCE,
                "hot_tolerance": HOT_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.4)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 22)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.5)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.6)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 21.5)
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
async def test_cooler_mode_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode with cycle duration."""
    cooler_switch = "input_boolean.test"
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with patch(
        "homeassistant.helpers.condition.dt_util.utcnow", return_value=fake_changed
    ):
        await common.async_set_temperature(hass, 18)
        await hass.async_block_till_done()
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == result_state


async def test_cooler_mode_opening(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "opening_1": None, "opening_2": None}},
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "target_sensor": common.ENT_SENSOR,
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

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON

    # wait 10 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    await asyncio.sleep(13)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
