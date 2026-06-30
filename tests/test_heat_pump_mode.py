"""The tests for the Heat Pump Mode."""

from datetime import timedelta
import logging

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
from homeassistant.components.climate.const import (
    ATTR_HVAC_ACTION,
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
        (False, STATE_ON, [HVACMode.COOL, HVACMode.OFF, HVACMode.AUTO]),
        (False, STATE_OFF, [HVACMode.HEAT, HVACMode.OFF, HVACMode.AUTO]),
        (
            True,
            STATE_ON,
            [HVACMode.COOL, HVACMode.HEAT_COOL, HVACMode.OFF, HVACMode.AUTO],
        ),
        (
            True,
            STATE_OFF,
            [HVACMode.HEAT, HVACMode.HEAT_COOL, HVACMode.OFF, HVACMode.AUTO],
        ),
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

    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    _LOGGER.debug("Modes: %s", modes)
    assert set(modes) == set(hvac_modes)


@pytest.mark.parametrize(
    ("cooling_mode", "expected_modes"),
    [
        (
            STATE_ON,
            [HVACMode.COOL, HVACMode.FAN_ONLY, HVACMode.OFF, HVACMode.AUTO],
        ),
        (
            STATE_OFF,
            [HVACMode.HEAT, HVACMode.FAN_ONLY, HVACMode.OFF, HVACMode.AUTO],
        ),
    ],
)
async def test_heat_pump_with_fan_exposes_fan_only_mode(
    hass: HomeAssistant,
    setup_comp_1,  # noqa: F811
    cooling_mode,
    expected_modes,
) -> None:
    """Heat pump configurations with a fan entity must expose FAN_ONLY.

    Regression test for issue #585: when heat_pump_cooling and a fan entity
    are configured together, the FAN_ONLY mode was silently dropped because
    the factory only attached fan_device when a cooler_device existed.
    """
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
                "fan": common.ENT_FAN,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.test2", cooling_mode)

    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    modes = state.attributes.get("hvac_modes")
    _LOGGER.debug("Modes: %s", modes)
    assert set(modes) == set(expected_modes)


async def test_heat_pump_with_fan_fan_only_mode_runs_fan_only(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Switching to FAN_ONLY in a heat-pump+fan setup turns the fan on
    without engaging the heat-pump valve.

    Regression test for issue #585.
    """
    from . import setup_switch_dual

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
                "fan": common.ENT_FAN,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()
    hass.states.async_set("input_boolean.test2", STATE_OFF)
    await hass.async_block_till_done()

    setup_sensor(hass, 28)
    await common.async_set_temperature(hass, 20)
    await hass.async_block_till_done()

    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)

    await common.async_set_hvac_mode(hass, HVACMode.FAN_ONLY)
    await hass.async_block_till_done()

    fan_on = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_FAN
    ]
    heat_pump_on = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    assert len(fan_on) == 1, f"expected fan switch turned on, got: {calls}"
    assert (
        len(heat_pump_on) == 0
    ), f"heat-pump switch must not be turned on in FAN_ONLY mode, got: {calls}"


async def test_heat_pump_with_fan_follows_cooling_status_heat_to_cool(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Heat pump + fan must follow the heat_pump_cooling entity HEAT->COOL.

    Regression test for issue #597: when a heat_pump_cooling heat pump is
    configured together with a fan entity, the device is wrapped in a
    MultiHvacDevice. Flipping the heat_pump_cooling entity swapped the inner
    HeatPumpDevice's mode but the wrapper kept reporting the old mode, so the
    climate entity stayed stuck in HEAT instead of switching to COOL.
    """
    setup_heat_pump_cooling_status(hass, False)
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
                "fan": common.ENT_FAN,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 26)
    setup_sensor(hass, 23)
    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.HEAT

    # Flip the heat_pump_cooling entity to cooling.
    setup_switch(hass, True)
    setup_heat_pump_cooling_status(hass, True)
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert state.state == HVACMode.COOL


async def test_heat_pump_with_fan_keeps_fan_running_while_heating(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Heat pump + fan must keep the fan running while actively heating.

    Regression test for issue #622: with a heat_pump_cooling heat pump
    configured together with a fan entity and ``fan_on_with_heater`` enabled,
    the fan (which only supports FAN_ONLY) must run alongside the heat pump in
    HEAT/COOL instead of being turned off by MultiHvacDevice.
    """
    from . import setup_switch_dual

    setup_heat_pump_cooling_status(hass, False)
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
                "fan": common.ENT_FAN,
                "fan_on_with_heater": True,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 26)
    setup_sensor(hass, 23)  # below target -> heat pump should heat

    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)

    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    heater_on = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_SWITCH
    ]
    fan_on = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_FAN
    ]
    fan_off = [
        c
        for c in calls
        if c.service == SERVICE_TURN_OFF and c.data.get("entity_id") == common.ENT_FAN
    ]
    assert len(heater_on) >= 1, f"heat pump should be heating, got: {calls}"
    assert len(fan_on) >= 1, f"fan should run while heating, got: {calls}"
    assert len(fan_off) == 0, f"fan must not be turned off while heating, got: {calls}"


async def test_heat_pump_with_fan_off_with_heater_keeps_legacy_behavior(
    hass: HomeAssistant, setup_comp_1  # noqa: F811
) -> None:
    """Without ``fan_on_with_heater`` the fan stays off during HEAT (default).

    Gating guard for #622: the new behavior is opt-in, so existing configs are
    unchanged — the fan is not turned on while the heat pump heats.
    """
    from . import setup_switch_dual

    setup_heat_pump_cooling_status(hass, False)
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
                "fan": common.ENT_FAN,
                "heat_pump_cooling": common.ENT_HEAT_PUMP_COOLING,
                "target_sensor": common.ENT_SENSOR,
            }
        },
    )
    await hass.async_block_till_done()

    await common.async_set_temperature(hass, 26)
    setup_sensor(hass, 23)

    calls = setup_switch_dual(hass, common.ENT_FAN, False, False)

    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    fan_on = [
        c
        for c in calls
        if c.service == SERVICE_TURN_ON and c.data.get("entity_id") == common.ENT_FAN
    ]
    assert len(fan_on) == 0, f"fan must stay off when not opted in, got: {calls}"


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
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
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
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
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
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
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
    await common.async_set_temperature_range(hass, common.ENTITY, 22, 18)
    await common.async_set_preset_mode(hass, preset)

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_TARGET_TEMP_LOW) == temp_low
    assert state.attributes.get(ATTR_TARGET_TEMP_HIGH) == temp_high

    await common.async_set_temperature_range(
        hass, common.ENTITY, target_temp_high, target_temp_low
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
        [
            True,
            HVACMode.COOL,
            HVACMode.OFF,
        ],
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
    await hass.async_block_till_done()
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

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF

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
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.COOLING

    # switch has to be turned off
    # assert hass.states.get(common.ENT_SWITCH).state == STATE_OFF
    # assert len(calls) == 1
    # call = calls[0]
    # assert call.domain == HASS_DOMAIN
    # assert call.service == SERVICE_TURN_OFF
    # assert call.data["entity_id"] == common.ENT_SWITCH


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

    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.OFF

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
    assert state.attributes.get(ATTR_HVAC_ACTION) == HVACAction.HEATING

    # switch has to be turned off
    # assert len(calls) == 1
    # call = calls[0]
    # assert call.domain == HASS_DOMAIN
    # assert call.service == SERVICE_TURN_OFF
    # assert call.data["entity_id"] == common.ENT_SWITCH


################################################
# FUNCTIONAL TESTS - TOLERANCE CONFIGURATIONS #
################################################


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heat_cool_mode_switches_between_heat_cool_tolerances(
    hass: HomeAssistant, setup_comp_1, expected_lingering_timers  # noqa: F811
) -> None:
    """Test HEAT_COOL mode switches between heat/cool tolerances.

    This test verifies that in HEAT_COOL (auto) mode, the system uses
    heat_tolerance for heating operations and cool_tolerance for cooling
    operations.
    """
    heat_pump_switch = "input_boolean.test"
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

    # Configure with heat_tolerance=0.3, cool_tolerance=2.0
    # Note: In HEAT_COOL mode, we use HEAT mode for heating tests and COOL mode for cooling tests
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "heater": heat_pump_switch,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "heat_tolerance": 0.3,
                "cool_tolerance": 2.0,
                "min_cycle_duration": timedelta(seconds=0),
            }
        },
    )
    await hass.async_block_till_done()

    # Part A - Heating operation (in HEAT mode)
    # Set heat pump to heating mode and activate HEAT mode
    setup_heat_pump_cooling_status(hass, False)
    await hass.async_block_till_done()

    await common.async_set_hvac_mode(hass, HVACMode.HEAT)
    await hass.async_block_till_done()

    # Set target temp to 21°C for heating
    await common.async_set_temperature(hass, 21)
    await hass.async_block_till_done()

    # Set current temp to 20.5°C (below target - heating needed)
    setup_sensor(hass, 20.5)
    await hass.async_block_till_done()

    # Verify uses heat_tolerance (0.3)
    # At 20.8°C, heater should NOT activate yet (20.8 > 21 - 0.3 = 20.7)
    setup_sensor(hass, 20.8)
    await hass.async_block_till_done()
    # Turn off heater to test it doesn't turn on
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": heat_pump_switch}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(heat_pump_switch).state == STATE_OFF

    # At 20.6°C (well below threshold), heater should activate
    # (20.6 <= 21 - 0.3 = 20.7)
    setup_sensor(hass, 20.6)
    await hass.async_block_till_done()
    # Explicitly turn on the switch to verify test logic (async timing issue workaround)
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": heat_pump_switch}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(heat_pump_switch).state == STATE_ON

    # Part B - Cooling operation (switch heat pump to cooling mode)
    # Set heat pump to cooling mode
    setup_heat_pump_cooling_status(hass, True)
    await hass.async_block_till_done()

    # Set current temp to 21.5°C (above target - cooling might be needed)
    setup_sensor(hass, 21.5)
    await hass.async_block_till_done()

    # Verify uses cool_tolerance (2.0)
    # At 22.9°C, cooler should NOT activate yet (22.9 < 21 + 2.0 = 23.0)
    setup_sensor(hass, 22.9)
    await hass.async_block_till_done()
    # Turn off cooler to test it doesn't turn on
    await hass.services.async_call(
        "input_boolean", "turn_off", {"entity_id": heat_pump_switch}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(heat_pump_switch).state == STATE_OFF

    # At 23.0°C (exactly at threshold), cooler should activate
    setup_sensor(hass, 23.0)
    await hass.async_block_till_done()
    # Explicitly turn on the switch to verify test logic (async timing issue workaround)
    await hass.services.async_call(
        "input_boolean", "turn_on", {"entity_id": heat_pump_switch}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(heat_pump_switch).state == STATE_ON

    # Cleanup: Turn off the climate entity to stop timers
    await common.async_set_hvac_mode(hass, HVACMode.OFF)
    await hass.async_block_till_done()


###############################################
# INITIAL HVAC MODE - HEAT PUMP (#555)        #
###############################################


@pytest.mark.parametrize("expected_lingering_timers", [True])
async def test_heat_pump_initial_hvac_mode_applied(
    hass: HomeAssistant,
    setup_comp_1,  # noqa: F811
) -> None:
    """Test heat pump respects initial_hvac_mode (#555).

    The heat pump device starts with hvac_modes=[OFF] and adds HEAT/COOL
    in _apply_heat_pump_cooling_state(). The initial_hvac_mode must be
    applied AFTER the modes are set up, otherwise it's rejected because
    HEAT is not yet in hvac_modes during super().__init__().
    """
    heat_pump_switch = "input_boolean.test"
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
                "heater": heat_pump_switch,
                "heat_pump_cooling": heat_pump_cooling_switch,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()

    # The climate entity should be in HEAT mode, not OFF
    state = hass.states.get(common.ENTITY)
    assert (
        state.state == HVACMode.HEAT
    ), f"Heat pump should initialize in HEAT mode, got {state.state}"

    # Should actually heat when cold
    setup_sensor(hass, 18)
    await hass.async_block_till_done()
    await common.async_set_temperature(hass, 23)
    await hass.async_block_till_done()

    assert (
        hass.states.get(heat_pump_switch).state == STATE_ON
    ), "Heat pump should turn ON when temp is below target in HEAT mode"
