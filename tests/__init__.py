"""dual_smart_thermostat tests."""

import datetime
import logging

from homeassistant.components.climate import (
    DOMAIN as CLIMATE,
    PRESET_ACTIVITY,
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_HOME,
    PRESET_SLEEP,
    STATE_OFF,
    STATE_ON,
    HVACMode,
)
from homeassistant.components.valve import ValveEntityFeature
from homeassistant.const import (
    SERVICE_CLOSE_VALVE,
    SERVICE_OPEN_VALVE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_CLOSED,
    STATE_OPEN,
    UnitOfTemperature,
)
import homeassistant.core as ha
from homeassistant.core import HomeAssistant, callback
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    DOMAIN,
)

from . import common

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def setup_comp_1(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_valve(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_VALVE,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_safety_delay(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "sensor_stale_duration": datetime.timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_floor_sensor(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_floor_opening_sensor(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "floor_sensor": common.ENT_FLOOR_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                "openings": [common.ENT_OPENING_SENSOR],
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cycle(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cycle_precision(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                "keep_alive": datetime.timedelta(minutes=10),
                "initial_hvac_mode": HVACMode.HEAT,
                "precision": 0.1,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_safety_delay(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "sensor_stale_duration": datetime.timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.COOL,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_fan_only_config(hass: HomeAssistant) -> None:
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
                "fan_mode": "true",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_fan_only_config_cycle(hass: HomeAssistant) -> None:
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
                "fan_mode": "true",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.FAN_ONLY,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_fan_only_config_presets(hass: HomeAssistant) -> None:
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
                "fan_mode": "true",
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.OFF,
                PRESET_AWAY: {"temperature": 16},
                PRESET_ACTIVITY: {"temperature": 21},
                PRESET_COMFORT: {"temperature": 20},
                PRESET_ECO: {"temperature": 18},
                PRESET_HOME: {"temperature": 19},
                PRESET_SLEEP: {"temperature": 17},
                PRESET_BOOST: {"temperature": 10},
                "anti_freeze": {"temperature": 5},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_fan_config(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "fan": common.ENT_FAN,
                "initial_hvac_mode": HVACMode.OFF,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_fan_config_tolerance(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "fan": common.ENT_FAN,
                "fan_hot_tolerance": 1,
                "initial_hvac_mode": HVACMode.OFF,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


# @pytest.fixture
async def setup_comp_heat_ac_cool_fan_config_tolerance_min_cycle(
    hass: HomeAssistant,
) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.2,
                "hot_tolerance": 0.2,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "fan": common.ENT_FAN,
                "fan_hot_tolerance": 0.5,
                "min_cycle_duration": datetime.timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.OFF,
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_fan_config_cycle(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "fan": common.ENT_FAN,
                "initial_hvac_mode": HVACMode.OFF,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_fan_config_presets(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "fan": common.ENT_FAN,
                "initial_hvac_mode": HVACMode.OFF,
                PRESET_AWAY: {"temperature": 16},
                PRESET_ACTIVITY: {"temperature": 21},
                PRESET_COMFORT: {"temperature": 20},
                PRESET_ECO: {"temperature": 18},
                PRESET_HOME: {"temperature": 19},
                PRESET_SLEEP: {"temperature": 17},
                PRESET_BOOST: {"temperature": 10},
                "anti_freeze": {"temperature": 5},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_presets(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                PRESET_AWAY: {"temperature": 16},
                PRESET_ACTIVITY: {"temperature": 21},
                PRESET_COMFORT: {"temperature": 20},
                PRESET_ECO: {"temperature": 18},
                PRESET_HOME: {"temperature": 19},
                PRESET_SLEEP: {"temperature": 17},
                PRESET_BOOST: {"temperature": 10},
                "anti_freeze": {"temperature": 5},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_presets_range(hass: HomeAssistant) -> None:
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
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
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
                    "target_temp_high": 32,
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


@pytest.fixture
async def setup_comp_heat_ac_cool_cycle(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    hass.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_ac_cool_cycle_kepp_alive(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    hass.config.temperature_unit = UnitOfTemperature.CELSIUS
    assert await async_setup_component(
        hass,
        CLIMATE,
        {
            "climate": {
                "platform": DOMAIN,
                "name": "test",
                "cold_tolerance": 0.3,
                "hot_tolerance": 0.3,
                "ac_mode": True,
                "heater": common.ENT_SWITCH,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
                "min_cycle_duration": datetime.timedelta(minutes=10),
                "keep_alive": datetime.timedelta(minutes=10),
                PRESET_AWAY: {"temperature": 30},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_presets(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                PRESET_AWAY: {"temperature": 16},
                PRESET_ACTIVITY: {"temperature": 21},
                PRESET_COMFORT: {"temperature": 20},
                PRESET_ECO: {"temperature": 18},
                PRESET_HOME: {"temperature": 19},
                PRESET_SLEEP: {"temperature": 17},
                PRESET_BOOST: {"temperature": 24},
                "anti_freeze": {"temperature": 5},
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_presets_floor(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
                PRESET_AWAY: {
                    "temperature": 16,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_ACTIVITY: {
                    "temperature": 21,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_COMFORT: {
                    "temperature": 20,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_ECO: {
                    "temperature": 18,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_HOME: {
                    "temperature": 19,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_SLEEP: {
                    "temperature": 17,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                PRESET_BOOST: {
                    "temperature": 24,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
                "anti_freeze": {
                    "temperature": 5,
                    CONF_MAX_FLOOR_TEMP: 30,
                    CONF_MIN_FLOOR_TEMP: 15,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_cool(hass: HomeAssistant) -> None:
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
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_dual(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_1(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_2(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "target_temp_low": 20,
                "target_temp_high": 25,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_3(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "target_temp": 21,
                "heat_cool_mode": False,
                PRESET_AWAY: {
                    "temperature": 16,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_dual_fan_config(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_fan_config(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_fan_config_tolerance(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "fan_hot_tolerance": 1,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_fan_config_2(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                "min_temp": 9,
                "max_temp": 32,
                "target_temp": 19.5,
                "target_temp_high": 20.5,
                "target_temp_low": 19.5,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_dual_presets(hass: HomeAssistant) -> None:
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
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
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
                "anti_freeze": {
                    "temperature": 5,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_presets(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
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
                "anti_freeze": {
                    "temperature": 5,
                    "target_temp_low": 5,
                    "target_temp_high": 32,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_presets_range_only(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                PRESET_AWAY: {
                    "target_temp_low": 16,
                    "target_temp_high": 30,
                },
                PRESET_COMFORT: {
                    "target_temp_low": 20,
                    "target_temp_high": 27,
                },
                PRESET_ECO: {
                    "target_temp_low": 18,
                    "target_temp_high": 29,
                },
                PRESET_HOME: {
                    "target_temp_low": 19,
                    "target_temp_high": 23,
                },
                PRESET_SLEEP: {
                    "target_temp_low": 17,
                    "target_temp_high": 24,
                },
                PRESET_ACTIVITY: {
                    "target_temp_low": 21,
                    "target_temp_high": 28,
                },
                "anti_freeze": {
                    "target_temp_low": 5,
                    "target_temp_high": 32,
                },
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_safety_delay(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_SWITCH,
                "cooler": common.ENT_COOLER,
                "target_sensor": common.ENT_SENSOR,
                "sensor_stale_duration": datetime.timedelta(minutes=2),
                "initial_hvac_mode": HVACMode.HEAT_COOL,
            }
        },
    )
    await hass.async_block_till_done()


@pytest.fixture
async def setup_comp_heat_cool_fan_presets(hass: HomeAssistant) -> None:
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
                "heat_cool_mode": True,
                "heater": common.ENT_HEATER,
                "cooler": common.ENT_COOLER,
                "fan": common.ENT_FAN,
                "target_sensor": common.ENT_SENSOR,
                "initial_hvac_mode": HVACMode.HEAT_COOL,
                PRESET_AWAY: {
                    # "temperature": 16,
                    "target_temp_low": 16,
                    "target_temp_high": 30,
                },
                PRESET_COMFORT: {
                    # "temperature": 20,
                    "target_temp_low": 20,
                    "target_temp_high": 27,
                },
                PRESET_ECO: {
                    # "temperature": 18,
                    "target_temp_low": 18,
                    "target_temp_high": 29,
                },
                PRESET_HOME: {
                    # "temperature": 19,
                    "target_temp_low": 19,
                    "target_temp_high": 23,
                },
                PRESET_SLEEP: {
                    # "temperature": 17,
                    "target_temp_low": 17,
                    "target_temp_high": 24,
                },
                PRESET_ACTIVITY: {
                    # "temperature": 21,
                    "target_temp_low": 21,
                    "target_temp_high": 28,
                },
                "anti_freeze": {
                    # "temperature": 5,
                    "target_temp_low": 5,
                    "target_temp_high": 32,
                },
            }
        },
    )
    await hass.async_block_till_done()


async def setup_component(hass: HomeAssistant, mock_config: dict) -> MockConfigEntry:
    """Initialize knmi for tests."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=mock_config, entry_id="test")
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass=hass, domain=DOMAIN, config=mock_config)
    await hass.async_block_till_done()

    return config_entry


def setup_sensor(hass: HomeAssistant, temp: float) -> None:
    """Set up the test sensor."""
    hass.states.async_set(common.ENT_SENSOR, temp)


def setup_floor_sensor(hass: HomeAssistant, temp: float) -> None:
    """Set up the test floor sensor."""
    hass.states.async_set(common.ENT_FLOOR_SENSOR, temp)


def setup_outside_sensor(hass: HomeAssistant, temp: float) -> None:
    """Set up the test outside sensor."""
    hass.states.async_set(common.ENT_OUTSIDE_SENSOR, temp)


def setup_humidity_sensor(hass: HomeAssistant, humidity: float) -> None:
    """Set up the test humidity sensor."""
    hass.states.async_set(common.ENT_HUMIDITY_SENSOR, humidity)


def setup_boolean(hass: HomeAssistant, entity, state) -> None:
    """Set up the test sensor."""
    hass.states.async_set(entity, state)


def setup_switch(
    hass: HomeAssistant, is_on: bool, entity_id: str = common.ENT_SWITCH
) -> None:
    """Set up the test switch."""
    hass.states.async_set(entity_id, STATE_ON if is_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


def setup_valve(hass: HomeAssistant, is_open: bool) -> None:
    """Set up the test switch."""
    hass.states.async_set(
        common.ENT_VALVE,
        STATE_OPEN if is_open else STATE_CLOSED,
        {"supported_features": ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE},
    )
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_OPEN_VALVE, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_CLOSE_VALVE, log_call)

    return calls


def setup_fan_heat_tolerance_toggle(hass: HomeAssistant, is_on: bool) -> None:
    """Set up the test switch."""
    hass.states.async_set(
        common.ENT_FAN_HOT_TOLERNACE_TOGGLE, STATE_ON if is_on else STATE_OFF
    )
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


def setup_heat_pump_cooling_status(hass: HomeAssistant, is_on: bool) -> None:
    """Set up the test switch."""
    hass.states.async_set(
        common.ENT_HEAT_PUMP_COOLING, STATE_ON if is_on else STATE_OFF
    )
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


def setup_switch_dual(
    hass: HomeAssistant, second_switch: str, is_on: bool, is_second_on: bool
) -> None:
    """Set up the test switch."""
    hass.states.async_set(common.ENT_SWITCH, STATE_ON if is_on else STATE_OFF)
    hass.states.async_set(second_switch, STATE_ON if is_second_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


def setup_switch_heat_cool_fan(
    hass: HomeAssistant, is_on: bool, is_cooler_on: bool, is_fan_on: bool
) -> None:
    """Set up the test switch."""
    hass.states.async_set(common.ENT_SWITCH, STATE_ON if is_on else STATE_OFF)
    hass.states.async_set(common.ENT_COOLER, STATE_ON if is_cooler_on else STATE_OFF)
    hass.states.async_set(common.ENT_FAN, STATE_ON if is_fan_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call) -> None:
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls


def setup_fan(hass: HomeAssistant, is_on: bool) -> None:
    """Set up the test switch."""
    hass.states.async_set(common.ENT_FAN, STATE_ON if is_on else STATE_OFF)
    calls = []

    @callback
    def log_call(call):
        """Log service calls."""
        calls.append(call)

    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_ON, log_call)
    hass.services.async_register(ha.DOMAIN, SERVICE_TURN_OFF, log_call)

    return calls
