"""Test for issue #506 - hot_tolerance ignored in heat_cool (range) mode.

https://github.com/swingerman/ha-dual-smart-thermostat/issues/506

Root cause: HeaterDevice.is_above_target_env_attr() bypasses hot_tolerance
when the heater is active in range mode, causing the heater to turn off at
exactly target_temp_low instead of target_temp_low + hot_tolerance.

Similarly, CoolerDevice.is_below_target_env_attr() bypasses cold_tolerance
when the cooler is active in range mode.

Correct behavior (standard thermostat hysteresis):
- Heater ON when temp <= target_low - cold_tolerance
- Heater OFF when temp >= target_low + hot_tolerance
- Cooler ON when temp >= target_high + hot_tolerance
- Cooler OFF when temp <= target_high - cold_tolerance
"""

import logging

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import HVACMode
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.const import ENTITY_MATCH_ALL, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.dual_smart_thermostat.const import DOMAIN
from tests import common, setup_comp_1, setup_sensor  # noqa: F401
from tests.common import async_set_temperature_range

_LOGGER = logging.getLogger(__name__)

COLD_TOLERANCE = 0.3
HOT_TOLERANCE = 0.3


async def test_heater_uses_hot_tolerance_in_range_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test that heater respects hot_tolerance when turning off in HEAT_COOL mode.

    Issue #506: Users report heater turns off at exactly target_temp_low
    instead of target_temp_low + hot_tolerance. This causes short cycling
    because there's no hysteresis on the turn-off side.

    With target_low=22, hot_tolerance=0.3:
    - Heater should turn OFF at 22.3 (22 + 0.3), not at 22.0
    """
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "test",
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "heat_cool_mode": True,
                "hot_tolerance": HOT_TOLERANCE,
                "cold_tolerance": COLD_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    # Set range: target_low=22, target_high=25
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # Both should be off in comfort zone
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # Drop temp to trigger heating: 21.7 <= 22 - 0.3
    setup_sensor(hass, 21.7)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
    ), "Heater should turn ON at 21.7 (target_low 22 - cold_tolerance 0.3)"

    # Temp rises to 22.0 - heater should STAY ON (below target_low + hot_tolerance)
    setup_sensor(hass, 22.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON, (
        "Heater should STAY ON at 22.0 because hot_tolerance=0.3 means "
        "it should turn off at 22.3, not 22.0"
    )

    # Temp rises to 22.2 - heater should STILL stay on
    setup_sensor(hass, 22.2)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
    ), "Heater should STAY ON at 22.2 (still below 22 + 0.3 = 22.3)"

    # Temp reaches 22.3 - heater should turn OFF (target_low + hot_tolerance)
    setup_sensor(hass, 22.3)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_OFF
    ), "Heater should turn OFF at 22.3 (target_low 22 + hot_tolerance 0.3)"


async def test_cooler_uses_cold_tolerance_in_range_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test that cooler respects cold_tolerance when turning off in HEAT_COOL mode.

    Symmetric to heater test: cooler should turn off at target_high - cold_tolerance,
    not at target_high.

    With target_high=25, cold_tolerance=0.3:
    - Cooler should turn OFF at 24.7 (25 - 0.3), not at 25.0
    """
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "test",
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "heat_cool_mode": True,
                "hot_tolerance": HOT_TOLERANCE,
                "cold_tolerance": COLD_TOLERANCE,
            }
        },
    )
    await hass.async_block_till_done()

    # Set range: target_low=22, target_high=25
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    await async_set_temperature_range(hass, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    # Raise temp to trigger cooling: 25.3 >= 25 + 0.3
    setup_sensor(hass, 25.3)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
    ), "Cooler should turn ON at 25.3 (target_high 25 + hot_tolerance 0.3)"

    # Temp drops to 25.0 - cooler should STAY ON (above target_high - cold_tolerance)
    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON, (
        "Cooler should STAY ON at 25.0 because cold_tolerance=0.3 means "
        "it should turn off at 24.7, not 25.0"
    )

    # Temp drops to 24.8 - cooler should STILL stay on
    setup_sensor(hass, 24.8)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
    ), "Cooler should STAY ON at 24.8 (still above 25 - 0.3 = 24.7)"

    # Temp reaches 24.7 - cooler should turn OFF (target_high - cold_tolerance)
    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    assert (
        hass.states.get(cooler_switch).state == STATE_OFF
    ), "Cooler should turn OFF at 24.7 (target_high 25 - cold_tolerance 0.3)"


async def test_heater_stays_on_between_target_and_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test the exact scenario from issue #506.

    User config: heat_cool_mode=true, hot_tolerance=0.3, setpoint=18
    User reports: heater turns off at 18.0 instead of 18.3

    This test reproduces the exact user scenario.
    """
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )
    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {
                    "name": "test",
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "heat_cool_mode": True,
                "hot_tolerance": 0.3,
                "cold_tolerance": 0.3,
            }
        },
    )
    await hass.async_block_till_done()

    # Set range: target_low=18, target_high=24
    setup_sensor(hass, 20)
    await hass.async_block_till_done()
    await async_set_temperature_range(hass, ENTITY_MATCH_ALL, 24, 18)
    await hass.async_block_till_done()

    # Drop temp to trigger heating
    setup_sensor(hass, 17.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON

    # Temp reaches setpoint (18.0) - heater should STAY ON per issue #506
    setup_sensor(hass, 18.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON, (
        "Issue #506: Heater should STAY ON at 18.0 with hot_tolerance=0.3. "
        "Should turn off at 18.3, not 18.0."
    )

    # Temp reaches 18.3 - NOW heater should turn off
    setup_sensor(hass, 18.3)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_OFF
    ), "Heater should turn OFF at 18.3 (18 + 0.3)"
