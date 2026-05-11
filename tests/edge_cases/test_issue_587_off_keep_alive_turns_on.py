"""Regression test for issue #587.

When the thermostat is in HVACMode.OFF and ``keep_alive`` is configured,
the keep-alive timer used to call into the controller and trigger the
goal-based ``turn_on`` branch in ``generic_controller`` — even though
the climate is supposed to be off. This caused heaters/coolers to
switch on by themselves whenever the temperature happened to be away
from target.

Issue: https://github.com/swingerman/ha-dual-smart-thermostat/issues/587
"""

import datetime

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.dual_smart_thermostat.const import DOMAIN

from .. import common, setup_sensor, setup_switch


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_off_mode_keep_alive_does_not_turn_heater_on(
    hass: HomeAssistant,
) -> None:
    """Keep-alive timer must not turn the heater on while thermostat is OFF.

    Reproduces the symptom reported in #587: thermostat shows OFF but the
    heater entity gets switched on after every keep_alive interval because
    the controller's "turn on because goal not reached" path lacks an
    HVACMode.OFF guard.
    """
    heater_switch = common.ENT_SWITCH
    assert await async_setup_component(
        hass,
        "climate",
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.1,
                "target_temp": 22.0,
                "keep_alive": datetime.timedelta(minutes=3),
            }
        },
    )
    await hass.async_block_till_done()

    # Heater switch off, current temperature well below target (heating goal
    # not reached). Thermostat itself is OFF.
    calls = setup_switch(hass, False)
    setup_sensor(hass, 18.0)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    calls.clear()

    now = dt_util.utcnow()
    for i in range(1, 4):
        async_fire_time_changed(hass, now + datetime.timedelta(minutes=3 * i))
        await hass.async_block_till_done()

    turn_on_calls = [c for c in calls if c.service == "turn_on"]
    assert turn_on_calls == [], (
        f"Heater must not be turned on by keep-alive while thermostat is OFF, "
        f"but got {len(turn_on_calls)} turn_on call(s): {turn_on_calls}"
    )


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_off_mode_keep_alive_turns_externally_on_heater_off(
    hass: HomeAssistant,
) -> None:
    """Keep-alive should still enforce OFF: if the switch is externally on
    while the thermostat is OFF, keep-alive must turn it off.

    This guards the intended behaviour that the OFF-bypass in
    ``needs_control`` was designed to preserve.
    """
    heater_switch = common.ENT_SWITCH
    assert await async_setup_component(
        hass,
        "climate",
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.1,
                "target_temp": 22.0,
                "keep_alive": datetime.timedelta(minutes=3),
            }
        },
    )
    await hass.async_block_till_done()

    # Heater switch externally ON, thermostat OFF.
    calls = setup_switch(hass, True)
    setup_sensor(hass, 18.0)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()
    calls.clear()

    now = dt_util.utcnow()
    async_fire_time_changed(hass, now + datetime.timedelta(minutes=3))
    await hass.async_block_till_done()

    turn_off_calls = [c for c in calls if c.service == "turn_off"]
    assert len(turn_off_calls) >= 1, (
        "Keep-alive should turn the externally-on heater off while thermostat "
        f"is OFF, but got {turn_off_calls}"
    )
