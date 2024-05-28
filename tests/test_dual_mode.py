"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging

from freezegun import freeze_time
from homeassistant.components import input_boolean, input_number
from homeassistant.components.climate import (
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_NONE,
    PRESET_SLEEP,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    ATTR_PRESET_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    DOMAIN as CLIMATE,
)
from homeassistant.const import (
    ATTR_TEMPERATURE,
    ENTITY_MATCH_ALL,
    SERVICE_TURN_OFF,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, CoreState, HomeAssistant, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt, dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    ATTR_HVAC_ACTION_REASON,
    DOMAIN,
    PRESET_ANTI_FREEZE,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
)

from . import (  # noqa: F401
    common,
    setup_boolean,
    setup_comp_1,
    setup_comp_dual,
    setup_comp_dual_fan_config,
    setup_comp_dual_presets,
    setup_comp_heat_cool_1,
    setup_comp_heat_cool_2,
    setup_comp_heat_cool_fan_config,
    setup_comp_heat_cool_fan_config_2,
    setup_comp_heat_cool_fan_presets,
    setup_comp_heat_cool_presets,
    setup_comp_heat_cool_safety_delay,
    setup_floor_sensor,
    setup_humidity_sensor,
    setup_outside_sensor,
    setup_sensor,
    setup_switch_dual,
    setup_switch_heat_cool_fan,
)

COLD_TOLERANCE = 0.3
HOT_TOLERANCE = 0.3

ATTR_HVAC_MODES = "hvac_modes"

_LOGGER = logging.getLogger(__name__)

###################
# COMMON FEATURES #
###################


async def test_unique_id(
    hass: HomeAssistant, entity_registry: er.EntityRegistry, setup_comp_1  # noqa: F811
) -> None:
    """Test setting a unique ID."""
    unique_id = "some_unique_id"
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
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
    cooler_switvh = "input_boolean.test_cooler"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switvh,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_temp_from_sensor(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
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
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_temperature"] == 18


# issue 80
async def test_presets_use_case_80(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": timedelta(seconds=60),
                "precision": 0.5,
                "min_temp": 20,
                "max_temp": 25,
                "heat_cool_mode": True,
                PRESET_AWAY: {
                    "target_temp_low": 0,
                    "target_temp_high": 50,
                },
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 402
    assert state.attributes["preset_modes"] == [PRESET_NONE, PRESET_AWAY]

    await common.async_set_preset_mode(hass, PRESET_AWAY)

    state = hass.states.get(common.ENTITY)
    assert state.attributes[ATTR_PRESET_MODE] == PRESET_AWAY


# issue 150
async def test_presets_use_case_150(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_sensor(hass, 18)
    await hass.async_block_till_done()

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": timedelta(seconds=60),
                "precision": 1.0,
                "min_temp": 58,
                "max_temp": 80,
                "cold_tolerance": 1.0,
                "hot_tolerance": 1.0,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385


async def test_presets_use_case_150_2(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None}},
    )

    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "cooler": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                # "min_cycle_duration": min_cycle_duration,
                # "keep_alive": timedelta(seconds=3),
                "precision": 1.0,
                "min_temp": 16,
                "max_temp": 32,
                "target_temp": 26.5,
                "target_temp_low": 23,
                "target_temp_high": 26.5,
                "cold_tolerance": 0.5,
                "hot_tolerance": 0.5,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    setup_sensor(hass, 23)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 18, 16)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    assert (
        hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.COOLING
    )

    setup_sensor(hass, 1)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_dual_default_setup_params(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("temperature") == 35


async def test_heat_cool_default_setup_params(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test the setup with default parameters."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("min_temp") == 7
    assert state.attributes.get("max_temp") == 35
    assert state.attributes.get("target_temp_low") == 7
    assert state.attributes.get("target_temp_high") == 35
    assert state.attributes.get("target_temp_step") == 0.1


###################
# CHANGE SETTINGS #
###################


async def test_get_hvac_modes_dual(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set([HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL])


async def test_get_hvac_modes_heat_cool(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )


async def test_get_hvac_modes_heat_cool_2(
    hass: HomeAssistant, setup_comp_heat_cool_2  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.HEAT_COOL]
    )


async def test_dual_get_hvac_modes_fan_configured(
    hass: HomeAssistant, setup_comp_dual_fan_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.FAN_ONLY,
        ]
    )


async def test_heat_cool_get_hvac_modes_fan_configured(
    hass: HomeAssistant, setup_comp_heat_cool_fan_config  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set(
        [
            HVACMode.OFF,
            HVACMode.HEAT,
            HVACMode.COOL,
            HVACMode.HEAT_COOL,
            HVACMode.FAN_ONLY,
        ]
    )


async def test_set_target_temp_dual(
    hass: HomeAssistant, setup_comp_dual  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    await common.async_set_temperature(hass, 30)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 30


async def test_set_target_temp_heat_cool(
    hass: HomeAssistant, setup_comp_heat_cool_1  # noqa: F811
) -> None:
    """Test the setting of the target temperature."""
    await common.async_set_temperature(hass, 30, common.ENTITY, 25, 22)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0
    with pytest.raises(vol.Invalid):
        await common.async_set_temperature(hass, None)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_high") == 25.0
    assert state.attributes.get("target_temp_low") == 22.0


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_dual_presets,  # noqa: F811
    preset,
    temperature,
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_heat_cool_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_heat_cool_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_heat_cool_fan_preset_mode_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


@pytest.mark.parametrize(
    "preset",
    [PRESET_NONE, PRESET_AWAY],
)
async def test_set_heat_cool_fan_restore_state(
    hass: HomeAssistant, preset  # noqa: F811
) -> None:
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                HVACMode.HEAT_COOL,
                {
                    ATTR_TARGET_TEMP_HIGH: "20",
                    ATTR_TARGET_TEMP_LOW: "18",
                    ATTR_PRESET_MODE: preset,
                },
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                PRESET_AWAY: {
                    "temperature": 14,
                    "target_temp_high": 20,
                    "target_temp_low": 18,
                },
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 20
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 18
    assert state.attributes[ATTR_PRESET_MODE] == preset
    assert state.state == HVACMode.HEAT_COOL


@pytest.mark.parametrize(
    ["preset", "hvac_mode"],
    [
        [PRESET_NONE, HVACMode.HEAT],
        [PRESET_AWAY, HVACMode.HEAT],
        [PRESET_NONE, HVACMode.COOL],
        [PRESET_AWAY, HVACMode.COOL],
    ],
)
async def test_set_heat_cool_fan_restore_state_2(
    hass: HomeAssistant, preset, hvac_mode  # noqa: F811
) -> None:
    common.mock_restore_cache(
        hass,
        (
            State(
                "climate.test_thermostat",
                hvac_mode,
                {
                    ATTR_TEMPERATURE: "20",
                    ATTR_PRESET_MODE: preset,
                },
            ),
        ),
    )

    hass.set_state(CoreState.starting)

    await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test_thermostat",
                "heater": common.ENT_SWITCH,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                PRESET_AWAY: {
                    "temperature": 14,
                    "target_temp_high": 20,
                    "target_temp_low": 18,
                },
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("climate.test_thermostat")
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_PRESET_MODE] == preset
    assert state.state == hvac_mode


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_set_dual_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 23


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_set_heat_cool_preset_mode_twice_and_restore_prev_temp(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == 18
    assert state.attributes.get("target_temp_high") == 22


async def test_set_dual_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_dual_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, "away")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"
    await common.async_set_preset_mode(hass, "none")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


async def test_set_heat_cool_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_cool_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, "away")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "away"
    await common.async_set_preset_mode(hass, "none")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"
    with pytest.raises(ServiceValidationError):
        await common.async_set_preset_mode(hass, "Sleep")
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == "none"


@pytest.mark.parametrize(
    "sensor_state",
    [STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_cooler(
    hass: HomeAssistant, sensor_state, setup_comp_heat_cool_safety_delay  # noqa: F811
) -> None:

    setup_sensor(hass, 28)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 30, common.ENTITY, 25, 22)
    calls = setup_switch_dual(hass, common.ENT_COOLER, False, True)

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_COOLER


@pytest.mark.parametrize(
    "sensor_state",
    [STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_heater(
    hass: HomeAssistant, sensor_state, setup_comp_heat_cool_safety_delay  # noqa: F811
) -> None:

    setup_sensor(hass, 18)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 30, common.ENTITY, 25, 22)
    calls = setup_switch_dual(hass, common.ENT_COOLER, True, False)
    await hass.async_block_till_done()

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_SWITCH


@pytest.mark.parametrize(
    ["sensor_state", "sensor_value", "affected_switch"],
    [
        (STATE_UNAVAILABLE, 28, common.ENT_COOLER),
        (STATE_UNKNOWN, 28, common.ENT_COOLER),
        (28, 28, common.ENT_COOLER),
        (STATE_UNKNOWN, 18, common.ENT_SWITCH),
        (STATE_UNKNOWN, 18, common.ENT_SWITCH),
        (18, 18, common.ENT_SWITCH),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration(
    hass: HomeAssistant,
    sensor_state,
    sensor_value,
    affected_switch,
    setup_comp_heat_cool_safety_delay,  # noqa: F811
) -> None:
    temp_high = 25
    temp_low = 22

    setup_sensor(hass, sensor_value)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 30, common.ENTITY, temp_high, temp_low)
    calls = setup_switch_dual(
        hass, common.ENT_COOLER, sensor_value < temp_low, sensor_value > temp_high
    )
    await hass.async_block_till_done()

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == affected_switch


@pytest.mark.parametrize(
    ["sensor_state", "sensor_value"],
    [
        (STATE_UNAVAILABLE, 28),
        (STATE_UNKNOWN, 28),
        (28, 28),
        (STATE_UNKNOWN, 18),
        (STATE_UNKNOWN, 18),
        (18, 18),
    ],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_heat_cool_off_outside_stale_duration_reason(
    hass: HomeAssistant,
    sensor_state,
    sensor_value,
    setup_comp_heat_cool_safety_delay,  # noqa: F811
) -> None:
    temp_high = 25
    temp_low = 22

    setup_sensor(hass, sensor_value)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 30, common.ENTITY, temp_high, temp_low)
    calls = setup_switch_dual(  # noqa: F841
        hass, common.ENT_COOLER, sensor_value < temp_low, sensor_value > temp_high
    )
    await hass.async_block_till_done()

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.TEMPERATURE_SENSOR_STALLED
    )


@pytest.mark.parametrize(
    ("preset", "temperature"),
    [
        (PRESET_NONE, 23),
        (PRESET_AWAY, 16),
        (PRESET_COMFORT, 20),
        (PRESET_ECO, 18),
        (PRESET_HOME, 19),
        (PRESET_SLEEP, 17),
        (PRESET_ACTIVITY, 21),
        (PRESET_ANTI_FREEZE, 5),
    ],
)
async def test_dual_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant, setup_comp_dual_presets, preset, temperature  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    test_target_temp = 33
    await common.async_set_temperature(hass, 23)
    await common.async_set_preset_mode(hass, preset)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == temperature
    await common.async_set_temperature(
        hass,
        test_target_temp,
    )
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == test_target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 401
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("temperature") == test_target_temp
    else:
        assert state.attributes.get("temperature") == 23


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_heat_cool_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    test_target_temp_low = 3
    test_target_temp_high = 33
    await common.async_set_temperature(hass, 18, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_temperature(
        hass,
        test_target_temp_low,
        common.ENTITY,
        test_target_temp_high,
        test_target_temp_low,
    )
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == test_target_temp_low
    assert state.attributes.get("target_temp_high") == test_target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 402
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("target_temp_low") == test_target_temp_low
        assert state.attributes.get("target_temp_high") == test_target_temp_high
    else:
        assert state.attributes.get("target_temp_low") == 18
        assert state.attributes.get("target_temp_high") == 22


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_heat_cool_fan_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    test_target_temp_low = 3
    test_target_temp_high = 33
    await common.async_set_temperature(hass, 18, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high
    await common.async_set_temperature(
        hass,
        test_target_temp_low,
        common.ENTITY,
        test_target_temp_high,
        test_target_temp_low,
    )
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == test_target_temp_low
    assert state.attributes.get("target_temp_high") == test_target_temp_high
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 402
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get("target_temp_low") == test_target_temp_low
        assert state.attributes.get("target_temp_high") == test_target_temp_high
    else:
        assert state.attributes.get("target_temp_low") == 18
        assert state.attributes.get("target_temp_high") == 22


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
        (PRESET_ANTI_FREEZE, 5, 32),
    ],
)
async def test_heat_cool_fan_set_preset_mode_change_hvac_mode(
    hass: HomeAssistant,
    setup_comp_heat_cool_fan_presets,  # noqa: F811
    preset,
    temp_low,
    temp_high,
) -> None:
    """Test the setting preset mode then set temperature.

    Verify preset mode preserved while temperature updated.
    """
    await common.async_set_temperature(hass, 18, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") == temp_low
    assert state.attributes.get("target_temp_high") == temp_high

    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("temperature") == 18
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None

    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("temperature") == 18
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("temperature") == 18
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_dual_toggle(
    hass: HomeAssistant, from_hvac_mode, to_hvac_mode, setup_comp_dual  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT_COOL],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_heat_cool_toggle(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_cool_1,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.COOL],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.FAN_ONLY, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_dual_toggle_with_fan(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_dual_fan_config,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.HEAT_COOL],
        [HVACMode.HEAT_COOL, HVACMode.OFF],
        [HVACMode.COOL, HVACMode.OFF],
        [HVACMode.FAN_ONLY, HVACMode.OFF],
        [HVACMode.HEAT, HVACMode.OFF],
    ],
)
async def test_heat_cool_toggle_with_fan(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_cool_fan_config,  # noqa: F811
) -> None:
    """Test change mode from OFF to COOL.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, from_hvac_mode)
    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == to_hvac_mode

    await common.async_toggle(hass)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == from_hvac_mode


async def test_hvac_mode_mode_heat_cool(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # switch to heat only mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 25, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # switch to cool only mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 385

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # switch to COOL mode and test the fan hot tolerance
    # after the hot tolerance first the fan should turn on
    # and outside the fan_hot_tolerance the AC

    await common.async_set_hvac_mode(hass, hvac_mode)
    await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL, 20, 18)
    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_ignore_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "outside_temp": {
                    "name": "test",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "fan_air_outside": True,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "outside_sensor": common.ENT_OUTSIDE_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # switch to COOL mode and test the fan hot tolerance
    # after the hot tolerance first the fan should turn on
    # and outside the fan_hot_tolerance the AC

    await common.async_set_hvac_mode(hass, hvac_mode)
    await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL, 20, 18)

    # below hot_tolerance
    setup_sensor(hass, 20)
    setup_outside_sensor(hass, 21)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # outside fan_hot_tolerance, within hot_tolerance
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_dont_ignore_fan_tolerance(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "outside_temp": {
                    "name": "test",
                    "initial": 10,
                    "min": 0,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "fan_air_outside": True,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "outside_sensor": common.ENT_OUTSIDE_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    # switch to COOL mode and test the fan hot tolerance
    # after the hot tolerance first the fan should turn on
    # and outside the fan_hot_tolerance the AC

    await common.async_set_hvac_mode(hass, hvac_mode)
    await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL, 20, 18)

    # below hot_tolerance
    setup_sensor(hass, 20)
    setup_outside_sensor(hass, 18)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # within hot_tolerance and fan_hot_tolerance
    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    # outside fan_hot_tolerance, within hot_tolerance
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


@pytest.mark.parametrize(
    "hvac_mode",
    [
        HVACMode.HEAT_COOL,
        HVACMode.COOL,
    ],
)
async def test_hvac_mode_mode_heat_cool_fan_tolerance_with_floor_sensor(
    hass: HomeAssistant, hvac_mode, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fan_switch = "input_boolean.fan"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "fan": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "floor_temp": {
                    "name": "floor_temp",
                    "initial": 10,
                    "min": 10,
                    "max": 40,
                    "step": 1,
                },
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
                "fan": fan_switch,
                "hot_tolerance": 0.2,
                "cold_tolerance": 0.2,
                "fan_hot_tolerance": 0.5,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "max_floor_temp": 26,
                "min_floor_temp": 10,
            }
        },
    )
    await hass.async_block_till_done()

    # switch to COOL mode and test the fan hot tolerance
    # after the hot tolerance first the fan should turn on
    # and outside the fan_hot_tolerance the AC

    await common.async_set_hvac_mode(hass, hvac_mode)
    await common.async_set_temperature(hass, 20, ENTITY_MATCH_ALL, 20, 18)
    setup_sensor(hass, 20)
    setup_floor_sensor(hass, 27)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF

    setup_sensor(hass, 20.2)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.7)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_ON

    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()

    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(fan_switch).state == STATE_OFF


async def test_hvac_mode_mode_heat_cool_hvac_modes_temps(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 22
    assert state.attributes["target_temp_high"] == 25
    assert state.attributes.get("temperature") is None

    # switch to heat only mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 24)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None
    assert state.attributes.get("temperature") == 24

    # switch to cool only mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 26)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("target_temp_low") is None
    assert state.attributes.get("target_temp_high") is None
    assert state.attributes.get("temperature") == 26

    # switch back to heet cool mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # check if target temperatures are kept from previous steps
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 24
    assert state.attributes["target_temp_high"] == 26
    assert state.attributes.get("temperature") is None


async def test_hvac_mode_mode_heat_cool_hvac_modes_temps_avoid_unrealism(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode."""

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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["supported_features"] == 386

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 22
    assert state.attributes["target_temp_high"] == 25
    assert state.attributes.get("temperature") is None

    # switch to heat only mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await common.async_set_temperature(hass, 26)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 26

    # switch to cool only mode
    await common.async_set_hvac_mode(hass, HVACMode.COOL)
    await common.async_set_temperature(hass, 21)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get("temperature") == 21

    # switch back to heet cool mode
    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    # check if target temperatures are kept from previous steps
    state = hass.states.get(common.ENTITY)
    assert state.attributes["target_temp_low"] == 20  # temp_high - precision
    assert state.attributes["target_temp_high"] == 21  # temp_low + precision


async def test_hvac_mode_heat_cool_floor_temp(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": floor_temp_input,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
            }
        },
    )
    await hass.async_block_till_done()

    # check if all hvac modes are available
    hvac_modes = hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_MODES)
    assert HVACMode.HEAT in hvac_modes
    assert HVACMode.COOL in hvac_modes
    assert HVACMode.HEAT_COOL in hvac_modes
    assert HVACMode.OFF in hvac_modes

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is below min_floor_temp, heater should be on"""
    setup_floor_sensor(hass, 4)
    # setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    """If floor temp is above min_floor_temp, heater should be off"""
    setup_floor_sensor(hass, 10)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


# TODO: test handling setting only target temp without low and high


async def test_hvac_mode_cool(hass: HomeAssistant, setup_comp_1):  # noqa: F811
    """Test thermostat cooler switch in cooling mode."""
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
                "cooler": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_hvac_mode_cool_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat cooler switch in cooling mode with cycle duration."""
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
                "cooler": cooler_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": timedelta(seconds=15),
                "heat_cool_mode": True,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
        await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 18, 16)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
async def test_hvac_mode_heat_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat mode with min_cycle_duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 20)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
        await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_ON
        assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 24)
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
async def test_hvac_mode_heat_cool_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in cool mode with min_cycle_duration."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 26)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    with freeze_time(fake_changed):
        await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
        await hass.async_block_till_done()
        assert hass.states.get(heater_switch).state == STATE_OFF
        assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == result_state


async def test_hvac_mode_heat_cool_switch_preset_modes(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch to heater only mode."""
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
                "cooler": cooler_switch,
                "heater": heater_switch,
                "target_sensor": common.ENT_SENSOR,
                "heat_cool_mode": True,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                PRESET_AWAY: {},
                PRESET_HOME: {},
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # setup_sensor(hass, 26)
    # await hass.async_block_till_done()

    # await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    # await hass.async_block_till_done()
    # assert hass.states.get("climate.test").state == HVAC_MODE_HEAT

    # await common.async_set_hvac_mode(hass, HVACMode.COOL)
    # await hass.async_block_till_done()
    # assert hass.states.get("climate.test").state == HVAC_MODE_COOL


async def test_hvac_mode_heat_cool_dry_mode(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heatre, cooler and dryer mode"""

    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    dryer_switch = "input_boolean.dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {"heater": None, "cooler": None, "dryer": None},
        },
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "test_humidity",
                    "initial": 50,
                    "min": 10,
                    "max": 99,
                    "step": 1,
                },
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
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "heat_cool_mode": True,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 18)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 17)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()
    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(dryer_switch).state == STATE_OFF

    await common.async_set_hvac_mode(hass, HVACMode.DRY)
    await common.async_set_humidity(hass, 55)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF
    assert hass.states.get(dryer_switch).state == STATE_ON
    assert (
        hass.states.get(common.ENTITY).attributes.get("hvac_action")
        == HVACAction.DRYING
    )

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON
    assert hass.states.get(dryer_switch).state == STATE_OFF


async def test_hvac_mode_heat_cool_tolerances(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler mode tolerances."""
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

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 18, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 21.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.1)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_ON
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 22.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    # since both heater and cooler are off, we expect the cooler not
    # to turn on until the temperature is 0.3 degrees above the target
    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 25.3)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    # since cooler is on we expect it keep on until reaches 0.3 degrees
    # below the target
    setup_sensor(hass, 25.0)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_ON

    setup_sensor(hass, 24.7)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF


######################
# HVAC ACTION REASON #
######################


async def test_hvac_mode_heat_cool_floor_temp_hvac_action_reason(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
):
    """Test thermostat heater and cooler switch in heat/cool mode. with floor temp caps"""

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
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": floor_temp_input,
                "min_floor_temp": 5,
                "max_floor_temp": 28,
            }
        },
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_sensor(hass, 26)
    setup_floor_sensor(hass, 10)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT_COOL)
    await common.async_set_temperature(hass, None, ENTITY_MATCH_ALL, 25, 22)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )

    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )

    # Case floor temp is below min_floor_temp
    setup_floor_sensor(hass, 4)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.LIMIT
    )

    # Case floor temp is above min_floor_temp
    setup_floor_sensor(hass, 10)
    setup_sensor(hass, 24)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_REACHED
    )

    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_TEMP_NOT_REACHED
    )


############
# OPENINGS #
############


@pytest.mark.parametrize(
    ["hvac_mode", "taget_temp", "oepning_scope", "switch_state", "cooler_state"],
    [
        ([HVACMode.HEAT, 24, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.HEAT, 24, [HVACMode.HEAT], STATE_OFF, STATE_OFF]),
        ([HVACMode.HEAT, 24, [HVACMode.COOL], STATE_ON, STATE_OFF]),
        ([HVACMode.COOL, 18, ["all"], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, 18, [HVACMode.COOL], STATE_OFF, STATE_OFF]),
        ([HVACMode.COOL, 18, [HVACMode.HEAT], STATE_OFF, STATE_ON]),
    ],
)
async def test_heat_cool_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    taget_temp,
    oepning_scope,
    switch_state,
    cooler_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    heater_switch = "input_boolean.heater"
    cooler_switch = "input_boolean.cooler"
    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"heater": None, "cooler": None, "opening_1": None}},
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
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cooler": cooler_switch,
                "heater": heater_switch,
                "heat_cool_mode": True,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                ],
                "openings_scope": oepning_scope,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == STATE_OFF
    assert hass.states.get(cooler_switch).state == STATE_OFF

    setup_sensor(hass, 23)
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, taget_temp)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert hass.states.get(heater_switch).state == switch_state
    assert hass.states.get(cooler_switch).state == cooler_state

    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heater_switch).state == STATE_ON
        if hvac_mode == HVACMode.HEAT
        else STATE_OFF
    )

    assert (
        hass.states.get(cooler_switch).state == STATE_ON
        if hvac_mode == HVACMode.COOL
        else STATE_OFF
    )
