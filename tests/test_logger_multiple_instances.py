"""Test logger behavior with multiple thermostat instances."""

import logging

from homeassistant.components.climate import HVACMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.climate import DOMAIN
from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_SENSOR,
    CONF_TARGET_TEMP,
)


@pytest.mark.asyncio
async def test_multiple_thermostats_logger_names(hass: HomeAssistant, caplog):
    """Test that multiple thermostat instances have correct logger names in logs.

    This test reproduces issue #511 where the logger name is incorrectly set
    to the last initialized thermostat's unique_id, causing confusion when
    troubleshooting logs for multiple thermostats.
    """
    # Mock the heater and sensor entities BEFORE creating config entries
    hass.states.async_set("switch.living_heater", "off")
    hass.states.async_set(
        "sensor.living_temp", "20", {"unit_of_measurement": UnitOfTemperature.CELSIUS}
    )
    hass.states.async_set("switch.master_heater", "off")
    hass.states.async_set(
        "sensor.master_temp", "20", {"unit_of_measurement": UnitOfTemperature.CELSIUS}
    )

    # Create and set up first thermostat - "living"
    living_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Living",
            CONF_HEATER: "switch.living_heater",
            CONF_SENSOR: "sensor.living_temp",
            CONF_TARGET_TEMP: 22,
        },
        unique_id="living",
        title="Living",
        entry_id="living_entry",
    )
    living_config.add_to_hass(hass)
    await hass.config_entries.async_setup(living_config.entry_id)
    await hass.async_block_till_done()

    # Create and set up second thermostat - "master"
    master_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Master",
            CONF_HEATER: "switch.master_heater",
            CONF_SENSOR: "sensor.master_temp",
            CONF_TARGET_TEMP: 22,
        },
        unique_id="master",
        title="Master",
        entry_id="master_entry",
    )
    master_config.add_to_hass(hass)
    await hass.config_entries.async_setup(master_config.entry_id)
    await hass.async_block_till_done()

    # Get the climate entities
    living_entity_id = "climate.living"
    master_entity_id = "climate.master"

    # Clear logs
    caplog.clear()

    # Trigger an action on the living thermostat
    with caplog.at_level(logging.INFO):
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": living_entity_id, "hvac_mode": HVACMode.HEAT},
            blocking=True,
        )
        await hass.async_block_till_done()

    # Check that logs for living thermostat include the entity_id in the message
    living_logs = [
        record for record in caplog.records if "Setting hvac mode" in record.message
    ]

    assert len(living_logs) > 0, "Expected to find log messages for setting HVAC mode"

    # Verify the log message includes the correct entity_id
    log_message = living_logs[0].message
    assert living_entity_id in log_message, (
        f"Log message should include entity_id '{living_entity_id}', "
        f"but got: {log_message}"
    )

    # Clear logs and test master thermostat
    caplog.clear()

    with caplog.at_level(logging.INFO):
        await hass.services.async_call(
            "climate",
            "set_hvac_mode",
            {"entity_id": master_entity_id, "hvac_mode": HVACMode.HEAT},
            blocking=True,
        )
        await hass.async_block_till_done()

    master_logs = [
        record for record in caplog.records if "Setting hvac mode" in record.message
    ]

    assert len(master_logs) > 0, "Expected to find log messages for master thermostat"

    # Verify the log message includes the correct entity_id for master
    log_message = master_logs[0].message
    assert master_entity_id in log_message, (
        f"Log message should include entity_id '{master_entity_id}', "
        f"but got: {log_message}"
    )


@pytest.mark.asyncio
async def test_logger_name_not_overridden(hass: HomeAssistant):
    """Test that logger name remains consistent across multiple thermostat instances.

    This test verifies the fix for issue #511 where the logger name was incorrectly
    overridden by the last initialized thermostat's unique_id.
    """
    from custom_components.dual_smart_thermostat import climate

    # Get the module-level logger
    original_logger_name = climate._LOGGER.name

    # Set up entities FIRST
    hass.states.async_set("switch.living_heater", "off")
    hass.states.async_set(
        "sensor.living_temp", "20", {"unit_of_measurement": UnitOfTemperature.CELSIUS}
    )
    hass.states.async_set("switch.master_heater", "off")
    hass.states.async_set(
        "sensor.master_temp", "20", {"unit_of_measurement": UnitOfTemperature.CELSIUS}
    )

    # Create and set up first thermostat
    living_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Living",
            CONF_HEATER: "switch.living_heater",
            CONF_SENSOR: "sensor.living_temp",
            CONF_TARGET_TEMP: 22,
        },
        unique_id="living",
        title="Living",
        entry_id="living_entry",
    )
    living_config.add_to_hass(hass)
    await hass.config_entries.async_setup(living_config.entry_id)
    await hass.async_block_till_done()

    # Check logger name after first thermostat - should remain unchanged
    logger_name_after_living = climate._LOGGER.name
    assert logger_name_after_living == original_logger_name

    # Create and set up second thermostat
    master_config = MockConfigEntry(
        domain=DOMAIN,
        data={
            "name": "Master",
            CONF_HEATER: "switch.master_heater",
            CONF_SENSOR: "sensor.master_temp",
            CONF_TARGET_TEMP: 22,
        },
        unique_id="master",
        title="Master",
        entry_id="master_entry",
    )
    master_config.add_to_hass(hass)
    await hass.config_entries.async_setup(master_config.entry_id)
    await hass.async_block_till_done()

    # FIX: Logger name should still be the original, not overridden
    logger_name_after_master = climate._LOGGER.name

    # Verify the logger name hasn't changed
    assert logger_name_after_master == original_logger_name
    assert logger_name_after_master == logger_name_after_living

    # Logger name should be the module name, not contain instance-specific IDs
    assert "living" not in logger_name_after_master
    assert "master" not in logger_name_after_master
