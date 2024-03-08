"""dual_smart_thermostat tests."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import DOMAIN

from . import common

_LOGGER = logging.getLogger(__name__)


@pytest.fixture
async def setup_comp_1(hass: HomeAssistant):
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, "homeassistant", {})
    await hass.async_block_till_done()


async def setup_component(hass: HomeAssistant, mock_config: dict) -> MockConfigEntry:
    """Initialize knmi for tests."""
    config_entry = MockConfigEntry(domain=DOMAIN, data=mock_config, entry_id="test")
    config_entry.add_to_hass(hass)

    assert await async_setup_component(hass=hass, domain=DOMAIN, config=mock_config)
    await hass.async_block_till_done()

    return config_entry


def setup_sensor(hass: HomeAssistant, temp):
    """Set up the test sensor."""
    hass.states.async_set(common.ENT_SENSOR, temp)


def setup_floor_sensor(hass: HomeAssistant, temp):
    """Set up the test sensor."""
    hass.states.async_set(common.ENT_FLOOR_SENSOR, temp)


def setup_boolean(hass: HomeAssistant, entity, state):
    """Set up the test sensor."""
    hass.states.async_set(entity, state)
