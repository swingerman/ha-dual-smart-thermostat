"""The tests for the Heat Pump Mode."""

import logging
from tkinter import FALSE

from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

from custom_components.dual_smart_thermostat.const import DOMAIN, PRESET_ANTI_FREEZE

from . import (  # noqa: F401
    common,
    setup_comp_1,
    setup_heat_pump_cooling_status,
    setup_sensor,
    setup_switch,
)

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_unique_id(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, setup_comp_1  # noqa: F811
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
    heater_switch = "input_boolean.test"
    heat_pump_cooling_switch = "input_boolean.test2"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test2": None}},
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
                "heat_pump_cooling": heat_pump_cooling_switch,
                "unique_id": unique_id,
            }
        },
    )
    await hass.async_block_till_done()

    entry = entity_registry.async_get(common.ENTITY)
    assert entry
    assert entry.unique_id == unique_id


async def test_setup_defaults_to_unknown(hass: HomeAssistant) -> None:  # noqa: F811
    """Test the setting of defaults to unknown."""
    heater_switch = "input_boolean.test"
    heat_pump_cooling_switch = "input_boolean.test2"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temperature_from_sensor(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 24)
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_HEATER,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 24


###################
# CHANGE SETTINGS #
###################


@pytest.fixture
async def setup_comp_heat_pump(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_SWITCH,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("dual_mode", "cooling_mode", "hvac_modes"),
    [
        (False, STATE_ON, [HVACMode.COOL, HVACMode.OFF]),
        (False, STATE_OFF, [HVACMode.HEAT, HVACMode.OFF]),
        (True, STATE_ON, [HVACMode.COOL, HVACMode.HEAT_COOL, HVACMode.OFF]),
        (True, STATE_OFF, [HVACMode.HEAT, HVACMode.HEAT_COOL, HVACMode.OFF]),
    ],
)
async def test_get_hvac_modes(
    hass: HomeAssistant,
    setup_comp_1,  # noqa: F811
    dual_mode,
    cooling_mode,
    hvac_modes,  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    # heater_switch = "input_boolean.test"
    heat_pump_cooling_switch = "input_boolean.test2"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_SWITCH,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": dual_mode,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.test2", cooling_mode)

    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(hvac_modes)


@pytest.fixture
async def setup_comp_heat_pump_presets(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_SWITCH,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
                PRESET_AWAY: {
                    "temperature": 16,
                },
                PRESET_COMFORT: {
                    "temperature": 20,
                },
                PRESET_ECO: {
                    "temperature": 18,
                },
                PRESET_HOME: {
                    "temperature": 19,
                },
                PRESET_SLEEP: {
                    "temperature": 17,
                },
                PRESET_ACTIVITY: {
                    "temperature": 21,
                },
                PRESET_BOOST: {
                    "temperature": 10,
                },
                "anti_freeze": {
                    "temperature": 5,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_pump_heat_cool_presets(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 2,
                "hot_tolerance": 4,
                "heater": common.ENT_SWITCH,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
                PRESET_AWAY: {
                    "temperature": 16,
                    "target_temp_low": 16,
                    "target_temp_high": 30,
                },
                PRESET_COMFORT: {
                    "temperature": 20,
                    "target_temp_low": 20,
                    "target_temp_high": 27,
                },
                PRESET_ECO: {
                    "temperature": 18,
                    "target_temp_low": 18,
                    "target_temp_high": 29,
                },
                PRESET_HOME: {
                    "temperature": 19,
                    "target_temp_low": 19,
                    "target_temp_high": 23,
                },
                PRESET_SLEEP: {
                    "temperature": 17,
                    "target_temp_low": 17,
                    "target_temp_high": 24,
                },
                PRESET_ACTIVITY: {
                    "temperature": 21,
                    "target_temp_low": 21,
                    "target_temp_high": 28,
                },
                PRESET_BOOST: {
                    "temperature": 10,
                    "target_temp_low": 10,
                    "target_temp_high": 21,
                },
                "anti_freeze": {
                    "temperature": 5,
                    "target_temp_low": 5,
                    "target_temp_high": 32,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_ACTIVITY, 21),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_pump_presets,
    preset,
    temp,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_BOOST, 10, 21),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_heat_cool(
    hass: HomeAssistant,
    setup_comp_heat_pump_heat_cool_presets,
    preset,
    temp_low,
    temp_high,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    setup_sensor(hass, 23)
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_ACTIVITY, 21),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_pump_presets,
    preset,
    temp,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp

    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == 23


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_BOOST, 10, 21),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_heat_cool_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_pump_heat_cool_presets,
    preset,
    temp_low,
    temp_high,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    setup_sensor(hass, 23)
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 18
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 22


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_ACTIVITY, 21),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_pump_presets,
    preset,
    temp,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp

    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == 23


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_BOOST, 10, 21),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_heat_cool_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_pump_heat_cool_presets,
    preset,
    temp_low,
    temp_high,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    setup_sensor(hass, 23)
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 18
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 22


async def test_set_preset_mode_invalid(
    hass: HomeAssistant,
    setup_comp_heat_pump_presets,  # noqa: F811
) -> None:
    """Test the setting invalid preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_AWAY
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_NONE
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == PRESET_NONE


@pytest.mark.parametrize(
    ("preset", "temp"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_ACTIVITY, 21),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_BOOST, 10),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_pump_presets,
    preset,
    temp,  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp

    await common.async_set_temperature(hass, target_temp)
    assert state.attributes.get("supported_features") == 401

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401
    await common.async_set_preset_mode(hass, PRESET_NONE)

    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get(ATTR_TEMPERATURE) == target_temp
    else:
        assert state.attributes.get(ATTR_TEMPERATURE) == 23


@pytest.mark.parametrize(
    ("preset", "temp_low", "temp_high"),
    [
        (PRESET_NONE, 18, 22),
        (PRESET_AWAY, 16, 30),
        (PRESET_COMFORT, 20, 27),
        (PRESET_ECO, 18, 29),
        (PRESET_HOME, 19, 23),
        (PRESET_SLEEP, 17, 24),
        (PRESET_ACTIVITY, 21, 28),
        (PRESET_BOOST, 10, 21),
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_preset_mode_heat_cool_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_pump_heat_cool_presets,
    preset,
    temp_low,
    temp_high,  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    target_temp_high = 32
    target_temp_low = 18
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    await common.async_set_temperature(
        hass, 18, common.ENTITY, target_temp_high, target_temp_low
    )
    assert state.attributes.get("supported_features") == 402

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == target_temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 402
    await common.async_set_preset_mode(hass, PRESET_NONE)

    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == target_temp_low
        assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == target_temp_high
    else:
        assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == 18
        assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == 22


# async def test_set_target_temp_off(
#     hass: HomeAssistant, setup_comp_heat_pump  # noqa: F811
# ) -> None:
#     """Test if target temperature turn heat pump off."""
#     # setup_sensor(hass, 23)

#     setup_heat_pump_cooling_status(hass, STATE_OFF)
#     await hass.async_block_till_done()
#     await common.async_set_hvac_mode(hass, HVACMode.HEAT)
#     calls = setup_switch(hass, True)
#     await hass.async_block_till_done()
#     await common.async_set_temperature(hass, 23)
#     assert len(calls) == 1
#     call = calls[0]
#     assert call.domain == HASS_DOMAIN
#     assert call.service == SERVICE_TURN_OFF
#     assert call.data["entity_id"] == common.ENT_SWITCH

###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["heat_pump_cooling", "from_hvac_mode", "to_hvac_mode"],
    [
        [True, HVACMode.OFF, HVACMode.COOL],
        [True, HVACMode.COOL, HVACMode.OFF],
        [False, HVACMode.OFF, HVACMode.HEAT],
        [False, HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_toggle(
    hass: HomeAssistant,
    heat_pump_cooling,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_pump,  # noqa: F811
) -> None:
    """Test change mode from from_hvac_mode to to_hvac_mode.
    And toggle resumes from to_hvac_mode
    """
    setup_heat_pump_cooling_status(hass, heat_pump_cooling)
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await hass.async_block_till_done()

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


async def test_hvac_mode_cool(
    hass: HomeAssistant, setup_comp_heat_pump  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    setup_heat_pump_cooling_status(hass, True)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 23)
    setup_sensor(hass, 28)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_hvac_mode_heat(
    hass: HomeAssistant, setup_comp_heat_pump  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    setup_heat_pump_cooling_status(hass, FALSE)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 26)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_hvac_mode_heat_switches_to_cool(
    hass: HomeAssistant, setup_comp_heat_pump  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    setup_heat_pump_cooling_status(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 26)
    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH

    calls = setup_switch(hass, True)
    setup_heat_pump_cooling_status(hass, True)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)

    # hvac mode should have changed to COOL
    assert state.state == HVACMode.COOL

    # switch has to be turned off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


async def test_hvac_mode_cool_switches_to_heat(
    hass: HomeAssistant, setup_comp_heat_pump  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    setup_heat_pump_cooling_status(hass, True)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_temperature(hass, 22)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()
    calls = setup_switch(hass, False)
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_SWITCH

    calls = setup_switch(hass, True)
    setup_heat_pump_cooling_status(hass, False)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)

    # hvac mode should have changed to COOL
    assert state.state == HVACMode.HEAT

    # switch has to be turned off
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH
