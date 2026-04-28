"""Integration tests for AUTO mode end-to-end through the climate entity."""

from homeassistant.components.climate import DOMAIN as CLIMATE, HVACMode
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON, STATE_OFF
import homeassistant.core as ha
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common, setup_sensor

ENT_COOLER = "switch.cooler_test"


def _setup_switches_and_capture_calls(hass: HomeAssistant) -> list:
    """Pre-create heater + cooler switch states and capture turn_on/turn_off calls.

    Single registration so both switches' service calls land in one ``calls`` list.
    """
    hass.states.async_set(common.ENT_SWITCH, STATE_OFF)
    hass.states.async_set(ENT_COOLER, STATE_OFF)
    calls: list = []

    def log_call(call) -> None:
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)
    return calls


def _heater_cooler_climate_config(initial_mode: HVACMode = HVACMode.OFF) -> dict:
    return {
        "climate": {
            "platform": DOMAIN,
            "name": "test",
            "cold_tolerance": 0.5,
            "hot_tolerance": 0.5,
            "heater": common.ENT_SWITCH,
            "cooler": ENT_COOLER,
            "target_sensor": common.ENT_SENSOR,
            "initial_hvac_mode": initial_mode,
            "target_temp": 21.0,
        }
    }


@pytest.mark.asyncio
async def test_auto_in_hvac_modes_when_two_capabilities(hass: HomeAssistant) -> None:
    """AUTO appears in hvac_modes when heater + cooler are both configured."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, CLIMATE, _heater_cooler_climate_config())
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO in state.attributes["hvac_modes"]


@pytest.mark.asyncio
async def test_auto_absent_from_hvac_modes_for_heater_only(
    hass: HomeAssistant,
) -> None:
    """AUTO is NOT in hvac_modes for a heater-only setup (1 capability)."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state is not None
    assert HVACMode.AUTO not in state.attributes["hvac_modes"]


@pytest.mark.asyncio
async def test_auto_picks_heat_when_too_cold(hass: HomeAssistant) -> None:
    """Selecting AUTO with cur_temp << target → heater turn_on service fires."""
    hass.config.units = METRIC_SYSTEM
    calls = _setup_switches_and_capture_calls(hass)
    setup_sensor(hass, 18.0)  # well below target − 2x tolerance

    assert await async_setup_component(hass, CLIMATE, _heater_cooler_climate_config())
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO

    turn_on_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    assert turn_on_calls, "Heater should have been turned on by AUTO HEAT priority"


@pytest.mark.asyncio
async def test_auto_picks_cool_when_too_hot(hass: HomeAssistant) -> None:
    """Selecting AUTO with cur_temp >> target → cooler turn_on service fires."""
    hass.config.units = METRIC_SYSTEM
    calls = _setup_switches_and_capture_calls(hass)
    setup_sensor(hass, 25.0)  # well above target + 2x tolerance

    assert await async_setup_component(hass, CLIMATE, _heater_cooler_climate_config())
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO

    cooler_on_calls = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == ENT_COOLER
    ]
    assert cooler_on_calls, "Cooler should have been turned on by AUTO COOL priority"


@pytest.mark.asyncio
async def test_auto_idle_when_at_target(hass: HomeAssistant) -> None:
    """At target → AUTO reports idle, no actuator turn_on call."""
    hass.config.units = METRIC_SYSTEM
    calls = _setup_switches_and_capture_calls(hass)
    setup_sensor(hass, 21.0)

    assert await async_setup_component(hass, CLIMATE, _heater_cooler_climate_config())
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.AUTO, common.ENTITY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.AUTO

    turn_on_calls = [c for c in calls if c.service == SERVICE_TURN_ON]
    assert (
        not turn_on_calls
    ), f"Expected no turn_on calls at target, got {turn_on_calls!r}"
