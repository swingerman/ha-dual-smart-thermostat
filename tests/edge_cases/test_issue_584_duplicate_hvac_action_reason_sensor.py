"""Regression test for issue #584.

UI config entries forward setup to the sensor platform via
``async_forward_entry_setups`` in ``__init__.py``. If ``climate.py`` also
schedules a discovery load of the same sensor platform, the
``hvac_action_reason`` sensor gets registered twice with the same unique_id,
and the rejected duplicate ends up in the entity registry orphaned from its
config entry (no device, no area, "Delete" greyed out).
"""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_SENSOR,
    DOMAIN,
)
from tests import common, setup_sensor, setup_switch


async def test_ui_config_entry_registers_hvac_action_reason_sensor_once(
    hass: HomeAssistant,
):
    """UI config entry registers exactly one hvac_action_reason sensor,
    linked to its config entry (not orphaned).
    """
    setup_sensor(hass, 22.5)
    setup_switch(hass, False, common.ENT_HEATER)

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "test",
            CONF_HEATER: common.ENT_HEATER,
            CONF_SENSOR: common.ENT_SENSOR,
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
        },
    )
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "sensor", DOMAIN, f"{config_entry.entry_id}_hvac_action_reason"
    )
    assert entity_id is not None
    assert registry.async_get(entity_id).config_entry_id == config_entry.entry_id
