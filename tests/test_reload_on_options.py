"""Reloads on config change go through HA helpers, not an update listener."""

from homeassistant.config_entries import OptionsFlowWithReload
from homeassistant.const import CONF_NAME
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


def test_options_flow_reloads_via_ha_helper():
    assert issubclass(OptionsFlowHandler, OptionsFlowWithReload)


@pytest.mark.asyncio
async def test_setup_registers_no_update_listener(hass):
    """HA 2026.12 drops reloads scheduled from update listeners."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            CONF_SENSOR: "sensor.room_temp",
            CONF_HEATER: "switch.heater",
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.update_listeners == []
