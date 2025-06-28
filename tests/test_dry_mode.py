"""The tests for the dual_smart_thermostat."""

import datetime
from datetime import timedelta
import logging

from freezegun import freeze_time
from freezegun.api import FrozenDateTimeFactory
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
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import DOMAIN as CLIMATE
from homeassistant.components.humidifier import ATTR_HUMIDITY
from homeassistant.const import (
    ATTR_TEMPERATURE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import DOMAIN as HASS_DOMAIN, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt, dt as dt_util
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest

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
    setup_comp_heat_ac_cool,
    setup_comp_heat_ac_cool_cycle,
    setup_comp_heat_ac_cool_cycle_kepp_alive,
    setup_comp_heat_ac_cool_fan_config,
    setup_comp_heat_ac_cool_presets,
    setup_comp_heat_ac_cool_safety_delay,
    setup_fan,
    setup_humidity_sensor,
    setup_sensor,
    setup_switch,
    setup_switch_dual,
)

COLD_TOLERANCE = 0.5
HOT_TOLERANCE = 0.5

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
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
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
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
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
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heater_switch,
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "ac_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).state == HVACMode.OFF


async def test_setup_gets_current_humidity_from_sensor(
    hass: HomeAssistant,
) -> None:  # noqa: F811
    """Test that current temperature is updated on entity addition."""
    hass.config.units = METRIC_SYSTEM
    setup_humidity_sensor(hass, 50)
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
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "ac_mode": "true",
            }
        },
    )
    await hass.async_block_till_done()
    assert hass.states.get(common.ENTITY).attributes["current_humidity"] == 50


###################
# CHANGE SETTINGS #
###################


@pytest.fixture
async def setup_comp_heat_ac_cool_dry(hass: HomeAssistant) -> None:
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
                "moist_tolerance": 5,
                "dry_tolerance": 6,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                PRESET_AWAY: {"temperature": 30, "humidity": 50},
            }
        },
    )
    await hass.async_block_till_done()


async def test_get_hvac_modes(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test that the operation list returns the correct modes."""
    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    assert set(modes) == set([HVACMode.COOL, HVACMode.DRY, HVACMode.OFF])


@pytest.fixture
async def setup_comp_heat_ac_cool_dry_presets(hass: HomeAssistant) -> None:
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
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                PRESET_AWAY: {"temperature": 16, "humidity": 60},
                PRESET_ACTIVITY: {"temperature": 21, "humidity": 50},
                PRESET_COMFORT: {"temperature": 20, "humidity": 55},
                PRESET_ECO: {"temperature": 18, "humidity": 65},
                PRESET_HOME: {"temperature": 19, "humidity": 60},
                PRESET_SLEEP: {"temperature": 17, "humidity": 50},
                PRESET_BOOST: {"temperature": 10, "humidity": 50},
                "anti_freeze": {"temperature": 5, "humidity": 70},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("preset", "temp", "humidity"),
    [
        (PRESET_NONE, 23, 50),
        (PRESET_AWAY, 16, 60),
        (PRESET_ACTIVITY, 21, 50),
        (PRESET_COMFORT, 20, 55),
        (PRESET_ECO, 18, 65),
        (PRESET_HOME, 19, 60),
        (PRESET_SLEEP, 17, 50),
        (PRESET_BOOST, 10, 50),
        (PRESET_ANTI_FREEZE, 5, 70),
    ],
)
async def test_set_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_dry_presets,
    preset,
    temp,
    humidity,  # noqa: F811
) -> None:
    """Test the setting preset mode."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_humidity(hass, 50)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp
    assert state.attributes.get(ATTR_HUMIDITY) == humidity


@pytest.mark.parametrize(
    ("preset", "temp", "humidity"),
    [
        (PRESET_NONE, 23, 45),
        (PRESET_AWAY, 16, 60),
        (PRESET_ACTIVITY, 21, 50),
        (PRESET_COMFORT, 20, 55),
        (PRESET_ECO, 18, 65),
        (PRESET_HOME, 19, 60),
        (PRESET_SLEEP, 17, 50),
        (PRESET_BOOST, 10, 50),
        (PRESET_ANTI_FREEZE, 5, 70),
    ],
)
async def test_set_preset_mode_and_restore_prev_humidity(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_dry_presets,
    preset,
    temp,
    humidity,  # noqa: F811
) -> None:
    """Test the setting preset mode.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_humidity(hass, 45)
    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == 23
    assert state.attributes.get(ATTR_HUMIDITY) == 45


@pytest.mark.parametrize(
    ("preset", "temp", "humidity"),
    [
        (PRESET_NONE, 23, 45),
        (PRESET_AWAY, 16, 60),
        (PRESET_ACTIVITY, 21, 50),
        (PRESET_COMFORT, 20, 55),
        (PRESET_ECO, 18, 65),
        (PRESET_HOME, 19, 60),
        (PRESET_SLEEP, 17, 50),
        (PRESET_BOOST, 10, 50),
        (PRESET_ANTI_FREEZE, 5, 70),
    ],
)
async def test_set_preset_modet_twice_and_restore_prev_humidity(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_dry_presets,
    preset,
    temp,
    humidity,  # noqa: F811
) -> None:
    """Test the setting preset mode twice in a row.

    Verify original temperature is restored.
    """
    await common.async_set_temperature(hass, 23)
    await common.async_set_humidity(hass, 45)
    await common.async_set_preset_mode(hass, preset)
    await common.async_set_preset_mode(hass, preset)

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp
    assert state.attributes.get(ATTR_HUMIDITY) == humidity

    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == 23
    assert state.attributes.get(ATTR_HUMIDITY) == 45


async def test_set_preset_mode_invalid(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_presets  # noqa: F811
) -> None:
    """Test an invalid mode raises an error and ignore case when checking modes."""
    await common.async_set_temperature(hass, 23)
    await common.async_set_humidity(hass, 50)
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
    ("preset", "temp", "humidity"),
    [
        (PRESET_NONE, 23, 45),
        (PRESET_AWAY, 16, 60),
        (PRESET_ACTIVITY, 21, 50),
        (PRESET_COMFORT, 20, 55),
        (PRESET_ECO, 18, 65),
        (PRESET_HOME, 19, 60),
        (PRESET_SLEEP, 17, 50),
        (PRESET_BOOST, 10, 50),
        (PRESET_ANTI_FREEZE, 5, 70),
    ],
)
async def test_set_preset_mode_set_temp_keeps_preset_mode(
    hass: HomeAssistant,
    setup_comp_heat_ac_cool_dry_presets,
    preset,
    temp,
    humidity,  # noqa: F811
) -> None:
    """Test the setting preset mode then set temperature and humidity.

    Verify preset mode preserved while temperature updated.
    """
    target_temp = 32
    target_humidity = 63
    await common.async_set_temperature(hass, 23)
    await common.async_set_humidity(hass, 45)

    await common.async_set_preset_mode(hass, preset)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == temp
    assert state.attributes.get(ATTR_HUMIDITY) == humidity
    await common.async_set_temperature(hass, target_temp)
    await common.async_set_humidity(hass, target_humidity)
    assert state.attributes.get("supported_features") == 405
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == target_temp
    assert state.attributes.get("preset_mode") == preset
    assert state.attributes.get("supported_features") == 405
    await common.async_set_preset_mode(hass, PRESET_NONE)
    state = hass.states.get(common.ENTITY)
    if preset == PRESET_NONE:
        assert state.attributes.get(ATTR_TEMPERATURE) == target_temp
        assert state.attributes.get(ATTR_HUMIDITY) == target_humidity
    else:
        assert state.attributes.get(ATTR_TEMPERATURE) == 23
        assert state.attributes.get(ATTR_HUMIDITY) == 45


async def test_set_target_temp_ac_dry_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if target temperature turn ac off."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    await common.async_set_humidity(hass, 65)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_turn_away_mode_on_drying(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test the setting away mode when cooling."""
    setup_switch_dual(hass, common.ENT_DRYER, False, True)
    setup_sensor(hass, 25)
    setup_humidity_sensor(hass, 40)
    await hass.async_block_till_done()
    state = hass.states.get(common.ENTITY)
    assert set(state.attributes.get("preset_modes")) == set([PRESET_NONE, PRESET_AWAY])
    await common.async_set_temperature(hass, 19)
    await common.async_set_humidity(hass, 60)
    await common.async_set_preset_mode(hass, PRESET_AWAY)
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TEMPERATURE) == 30
    assert state.attributes.get(ATTR_HUMIDITY) == 50


###################
# HVAC OPERATIONS #
###################


@pytest.mark.parametrize(
    ["from_hvac_mode", "to_hvac_mode"],
    [
        [HVACMode.OFF, HVACMode.DRY],
        [HVACMode.DRY, HVACMode.OFF],
    ],
)
async def test_toggle(
    hass: HomeAssistant,
    from_hvac_mode,
    to_hvac_mode,
    setup_comp_heat_ac_cool_dry,  # noqa: F811
) -> None:
    """Test change mode from from_hvac_mode to to_hvac_mode.
    And toggle resumes from to_hvac_mode
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


async def test_hvac_mode_cdry(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test change mode from OFF to DRY.

    Switch turns on when temp below setpoint and mode changes.
    """
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_hvac_mode(hass, HVACMode.DRY)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_sensor_chhange_dont_control_dryer_when_off(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test that the humidifier switch doesn't turn on when the thermostat is off."""
    # Given
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)

    # When
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()

    # Then
    assert len(calls) == 0


async def test_set_target_temp_ac_dryer_on(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if target temperature turn ac dryer on (needs initial hva cmode DRY)."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    setup_humidity_sensor(hass, 70)
    await common.async_set_humidity(hass, 65)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_temp_change_ac_dry_off_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if humidity change doesn't turn ac dryer off within tolerance."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 64.8)
    await hass.async_block_till_done()
    assert len(calls) == 0

    # still ON
    setup_humidity_sensor(hass, 63.3)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_set_temp_change_ac_dry_off_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if humidity change turn ac dryer off outside tolerance."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 59)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_temp_change_ac_dryer_on_within_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if humidity change doesn't turn ac dryer on within tolerance."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 67)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_on_outside_tolerance(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test if humidity change turn ac dryer on."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_running_when_operating_mode_is_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test that the humidifier switch turns off when enabled is set False."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_no_state_change_when_operation_mode_off_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry  # noqa: F811
) -> None:
    """Test that the switch doesn't turn on when enabled is False."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()
    assert len(calls) == 0


@pytest.fixture
async def setup_comp_heat_ac_cool_dry_cycle(hass: HomeAssistant) -> None:
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
                "moist_tolerance": 5,
                "dry_tolerance": 6,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                PRESET_AWAY: {"temperature": 30, "humidity": 50},
            }
        },
    )
    await hass.async_block_till_done()


async def test_temp_change_ac_dry_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn dryer on."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_dry_trigger_on_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_temp_change_ac_dry_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_dry_trigger_off_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if himidity change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_mode_change_ac_dry_trigger_off_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac off despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_mode_change_ac_dry_trigger_on_not_long_enough(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.DRY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_temp_change_ac_dry_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_dryer_trigger_on_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_temp_change_ac_dry_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    assert len(calls) == 0


async def test_temp_change_ac_dry_trigger_off_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if humidity change turn ac on."""
    fake_changed = datetime.datetime(1970, 11, 11, 11, 11, 11, tzinfo=dt_util.UTC)
    with freeze_time(fake_changed):
        calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_mode_change_ac_dry_trigger_off_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac off despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 50)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_OFF
    assert call.data["entity_id"] == common.ENT_DRYER


async def test_mode_change_ac_dry_trigger_on_not_long_enough_2(
    hass: HomeAssistant, setup_comp_heat_ac_cool_dry_cycle  # noqa: F811
) -> None:
    """Test if mode change turns ac on despite minimum cycle."""
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    await common.async_set_humidity(hass, 65)
    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()
    assert len(calls) == 0
    await common.async_set_hvac_mode(hass, HVACMode.DRY)
    assert len(calls) == 1
    call = calls[0]
    assert call.domain == "homeassistant"
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


@pytest.fixture
async def setup_comp_heat_ac_cool_dry_stale_duration(hass: HomeAssistant) -> None:
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
                "moist_tolerance": 5,
                "dry_tolerance": 6,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "dryer": common.ENT_DRYER,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "sensor_stale_duration": datetime.timedelta(minutes=2),
                PRESET_AWAY: {"temperature": 30, "humidity": 50},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.mark.parametrize(
    "sensor_state",
    [70, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_ac_dry_off_outside_stale_duration(
    hass: HomeAssistant,
    sensor_state,
    setup_comp_heat_ac_cool_dry_stale_duration,  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off AC."""
    setup_humidity_sensor(hass, 70)
    await common.async_set_humidity(hass, 65)
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, True)

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_HUMIDITY_SENSOR, sensor_state)
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
    assert call.data["entity_id"] == common.ENT_DRYER

    # Turns back on if sensor is restored
    calls = setup_switch_dual(hass, common.ENT_DRYER, False, False)
    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()

    assert len(calls) == 1
    call = calls[0]
    assert call.domain == HASS_DOMAIN
    assert call.service == SERVICE_TURN_ON
    assert call.data["entity_id"] == common.ENT_DRYER


@pytest.mark.parametrize(
    "sensor_state",
    [70, STATE_UNAVAILABLE, STATE_UNKNOWN],
)
@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_sensor_unknown_secure_ac_dry_off_outside_stale_duration_reason(
    hass: HomeAssistant,
    sensor_state,
    setup_comp_heat_ac_cool_dry_stale_duration,  # noqa: F811
) -> None:
    """Test if sensor unavailable for defined delay turns off AC."""

    setup_humidity_sensor(hass, 70)
    await common.async_set_humidity(hass, 65)
    setup_switch_dual(hass, common.ENT_DRYER, False, True)

    # set up sensor in th edesired state
    hass.states.async_set(common.ENT_HUMIDITY_SENSOR, sensor_state)
    await hass.async_block_till_done()

    # Wait 3 minutes
    common.async_fire_time_changed(
        hass, dt_util.utcnow() + datetime.timedelta(minutes=3)
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonInternal.HUMIDITY_SENSOR_STALLED
    )


async def test_dryer_mode(hass: HomeAssistant, setup_comp_1) -> None:  # noqa: F811
    """Test thermostat dryer switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 60)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_OFF


async def test_dryer_mode_change(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat dryer state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 60)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 68)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_ON


async def test_dryer_mode_from_off_to_idle(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat dryer switch state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    await common.async_set_hvac_mode(hass, HVACMode.DRY)

    assert hass.states.get(dryer_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.IDLE


async def test_dryer_mode_off_switch_change_keeps_off(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat dryer switch state if HVAC mode changes."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
            }
        },
    )
    await hass.async_block_till_done()

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF

    hass.states.async_set(dryer_switch, STATE_ON)

    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_ON
    assert hass.states.get(common.ENTITY).attributes["hvac_action"] == HVACAction.OFF


async def test_dryer_mode_tolerance(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat dryer switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "dry_tolerance": 2,
                "moist_tolerance": 3,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 72)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 75)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_humidity_sensor(hass, 71)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_humidity_sensor(hass, 67)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == STATE_OFF


@pytest.mark.parametrize(
    ["duration", "result_state"],
    [
        # (timedelta(seconds=10), STATE_ON),
        (timedelta(seconds=30), STATE_OFF),
    ],
)
@pytest.mark.asyncio
async def test_dryer_mode_cycle(
    hass: HomeAssistant, duration, result_state, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat dryer switch in cooling mode with cycle duration."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "min_cycle_duration": timedelta(seconds=15),
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    fake_changed = dt.utcnow() - duration
    common.async_fire_time_changed(hass, fake_changed)
    with freeze_time(fake_changed):
        await common.async_set_humidity(hass, 60)
        await hass.async_block_till_done()
        assert hass.states.get(dryer_switch).state == STATE_ON

    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()
    assert hass.states.get(dryer_switch).state == result_state


######################
# HVAC ACTION REASON #
######################


async def test_dryer_mode_opening_hvac_action_reason(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "test_dryer": None,
                "opening_1": None,
                "opening_2": None,
            }
        },
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 5}},
                ],
            }
        },
    )
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.NONE
    )

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    # wait openings
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 60)
    await hass.async_block_till_done()
    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_HUMIDITY_NOT_REACHED
    )

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_HUMIDITY_NOT_REACHED
    )

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_HUMIDITY_NOT_REACHED
    )

    # wait 5 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(minutes=10)
    # )
    # await asyncio.sleep(6)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.OPENING
    )

    # wait openings
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_HUMIDITY_NOT_REACHED
    )

    setup_humidity_sensor(hass, 60)
    await hass.async_block_till_done()

    assert (
        hass.states.get(common.ENTITY).attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReason.TARGET_HUMIDITY_REACHED
    )


############
# OPENINGS #
############


async def test_dryer_mode_opening(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, setup_comp_1  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    opening_1 = "input_boolean.opening_1"
    opening_2 = "input_boolean.opening_2"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {
            "input_boolean": {
                "test": None,
                "test_dryer": None,
                "opening_1": None,
                "opening_2": None,
            }
        },
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": HVACMode.DRY,
                "openings": [
                    opening_1,
                    {"entity_id": opening_2, "timeout": {"seconds": 5}},
                ],
            }
        },
    )

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    # wait openings
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 60)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_boolean(hass, opening_1, "open")
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_boolean(hass, opening_1, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_ON

    setup_boolean(hass, opening_2, "open")
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_ON

    # wait 5 seconds, actually 133 due to the other tests run time seems to affect this
    # needs to separate the tests
    # common.async_fire_time_changed(
    #     hass, dt_util.utcnow() + datetime.timedelta(minutes=10)
    # )
    # await asyncio.sleep(5)
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_boolean(hass, opening_2, "closed")
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    # wait openings
    freezer.tick(timedelta(seconds=6))
    common.async_fire_time_changed(hass)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_ON


@pytest.mark.parametrize(
    ["hvac_mode", "oepning_scope", "switch_state"],
    [
        ([HVACMode.DRY, ["all"], STATE_OFF]),
        ([HVACMode.DRY, [HVACMode.DRY], STATE_OFF]),
        ([HVACMode.DRY, [HVACMode.COOL], STATE_ON]),
    ],
)
async def test_cooler_mode_opening_scope(
    hass: HomeAssistant,
    hvac_mode,
    oepning_scope,
    switch_state,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test thermostat cooler switch in cooling mode."""
    cooler_switch = "input_boolean.test"
    dryer_switch = "input_boolean.test_dryer"
    opening_1 = "input_boolean.opening_1"

    assert await async_setup_component(
        hass,
        input_boolean.DOMAIN,
        {"input_boolean": {"test": None, "test_dryer": None, "opening_1": None}},
    )

    assert await async_setup_component(
        hass,
        input_number.DOMAIN,
        {
            "input_number": {
                "temp": {"name": "test", "initial": 10, "min": 0, "max": 40, "step": 1},
                "humidity": {
                    "name": "humididty",
                    "initial": 50,
                    "min": 20,
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
                "heater": cooler_switch,
                "ac_mode": "true",
                "dryer": dryer_switch,
                "target_sensor": common.ENT_SENSOR,
                "humidity_sensor": common.ENT_HUMIDITY_SENSOR,
                "initial_hvac_mode": hvac_mode,
                "openings": [
                    opening_1,
                ],
                "openings_scope": oepning_scope,
            }
        },
    )
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == STATE_OFF

    setup_humidity_sensor(hass, 70)
    await hass.async_block_till_done()

    await common.async_set_humidity(hass, 60)
    await hass.async_block_till_done()
    assert (
        hass.states.get(dryer_switch).state == STATE_ON
        if hvac_mode == HVACMode.DRY
        else STATE_OFF
    )

    setup_boolean(hass, opening_1, STATE_OPEN)
    await hass.async_block_till_done()

    assert hass.states.get(dryer_switch).state == switch_state

    setup_boolean(hass, opening_1, STATE_CLOSED)
    await hass.async_block_till_done()

    assert (
        hass.states.get(dryer_switch).state == STATE_ON
        if hvac_mode == HVACMode.DRY
        else STATE_OFF
    )
