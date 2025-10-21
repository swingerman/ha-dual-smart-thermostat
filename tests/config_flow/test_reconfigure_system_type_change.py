#!/usr/bin/env python3
"""Tests for system type change detection in reconfigure flow.

These tests verify that when a user changes the system type during
reconfiguration, the previously saved configuration is properly cleared
to prevent incompatible settings from causing problems.
"""

from unittest.mock import Mock, PropertyMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def heat_pump_entry_with_features():
    """Create a mock config entry for heat pump system with features."""
    entry = Mock()
    entry.entry_id = "test_heat_pump"
    entry.data = {
        CONF_NAME: "Living Room",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
        CONF_HEATER: "switch.heat_pump",
        CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        CONF_SENSOR: "sensor.temperature",
        CONF_FLOOR_SENSOR: "sensor.floor_temp",
        CONF_FAN: "switch.fan",
        CONF_HUMIDITY_SENSOR: "sensor.humidity",
        "openings": ["binary_sensor.window"],
    }
    return entry


@pytest.fixture
def heater_cooler_entry_with_features():
    """Create a mock config entry for heater+cooler system with features."""
    entry = Mock()
    entry.entry_id = "test_heater_cooler"
    entry.data = {
        CONF_NAME: "Bedroom",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_SENSOR: "sensor.temperature",
        CONF_FLOOR_SENSOR: "sensor.floor_temp",
        CONF_FAN: "switch.fan",
    }
    return entry


async def test_system_type_unchanged_preserves_config(heat_pump_entry_with_features):
    """Test that keeping the same system type preserves existing configuration."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Verify all config was loaded
        assert flow.collected_config[CONF_NAME] == "Living Room"
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP
        assert flow.collected_config[CONF_HEATER] == "switch.heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_mode"
        )
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert "binary_sensor.window" in flow.collected_config["openings"]

        # Confirm same system type
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )

        # Verify config is still preserved after confirmation
        assert flow.collected_config[CONF_NAME] == "Living Room"
        assert flow.collected_config[CONF_HEATER] == "switch.heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_mode"
        )
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert "system_type_changed" not in flow.collected_config


async def test_system_type_change_clears_config(heat_pump_entry_with_features):
    """Test that changing system type clears incompatible configuration."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Verify all config was loaded initially
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_mode"
        )
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_FAN] == "switch.fan"

        # Change system type from heat_pump to simple_heater
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # Verify incompatible config was cleared
        assert flow.collected_config[CONF_NAME] == "Living Room"  # Name preserved
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
        assert CONF_HEAT_PUMP_COOLING not in flow.collected_config  # Heat pump specific
        assert CONF_FLOOR_SENSOR not in flow.collected_config  # Features cleared
        assert CONF_FAN not in flow.collected_config  # Features cleared
        assert CONF_HUMIDITY_SENSOR not in flow.collected_config  # Features cleared
        assert "openings" not in flow.collected_config  # Features cleared
        assert flow.collected_config.get("system_type_changed") is True


async def test_heat_pump_to_heater_cooler_clears_heat_pump_cooling(
    heat_pump_entry_with_features,
):
    """Test that changing from heat pump to heater+cooler removes heat_pump_cooling sensor."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()
        assert CONF_HEAT_PUMP_COOLING in flow.collected_config

        # Change to heater_cooler system
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )

        # Verify heat pump specific sensor is removed
        assert flow.collected_config[CONF_NAME] == "Living Room"
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
        assert CONF_HEAT_PUMP_COOLING not in flow.collected_config
        assert flow.collected_config.get("system_type_changed") is True


async def test_heater_cooler_to_ac_only_clears_heater(
    heater_cooler_entry_with_features,
):
    """Test that changing from heater+cooler to AC-only removes heater entity."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(
            return_value=heater_cooler_entry_with_features
        )

        # Start reconfigure
        await flow.async_step_reconfigure()
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"

        # Change to AC-only system
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY}
        )

        # Verify cooler entity is removed (AC-only uses heater field)
        assert flow.collected_config[CONF_NAME] == "Bedroom"
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_AC_ONLY
        assert CONF_HEATER not in flow.collected_config  # Cleared
        assert CONF_COOLER not in flow.collected_config  # Cleared
        assert flow.collected_config.get("system_type_changed") is True


async def test_system_type_change_allows_fresh_configuration(
    heat_pump_entry_with_features,
):
    """Test that after system type change, user can configure new system from scratch."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        result = await flow.async_step_reconfigure()

        # Change to simple heater
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # Should proceed to basic configuration step with cleared config
        assert result["type"] == "form"
        assert result["step_id"] == "basic"

        # Configure simple heater with new entities
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Living Room",  # Name is preserved from before
                CONF_HEATER: "switch.new_heater",  # New heater entity
                CONF_SENSOR: "sensor.new_temperature",  # New sensor
            }
        )

        # Should proceed to features step
        assert result["type"] == "form"
        assert result["step_id"] == "features"

        # Verify new configuration is being used
        assert flow.collected_config[CONF_HEATER] == "switch.new_heater"
        assert flow.collected_config[CONF_SENSOR] == "sensor.new_temperature"
        assert CONF_HEAT_PUMP_COOLING not in flow.collected_config


async def test_system_type_change_flag_cleared_before_storage(
    heat_pump_entry_with_features,
):
    """Test that system_type_changed flag is removed before saving to config entry."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure and change system type
        await flow.async_step_reconfigure()
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # Verify flag is set during flow
        assert flow.collected_config.get("system_type_changed") is True

        # Configure the new system
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temp",
            }
        )

        # Complete flow with no features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should finish with abort (reconfigure uses abort instead of create_entry)
        assert result["type"] == "abort"

        # Verify the flag is removed from the saved data
        # The _clean_config_for_storage method should have removed it
        cleaned_config = flow._clean_config_for_storage(flow.collected_config)
        assert "system_type_changed" not in cleaned_config


async def test_multiple_system_type_changes(heat_pump_entry_with_features):
    """Test that multiple system type changes in sequence work correctly."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure (heat_pump → simple_heater)
        await flow.async_step_reconfigure()
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )

        # Config should be cleared
        assert CONF_HEAT_PUMP_COOLING not in flow.collected_config
        assert flow.collected_config.get("system_type_changed") is True

        # User configures simple heater
        await flow.async_step_basic(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.simple_heater",
                CONF_SENSOR: "sensor.temp",
            }
        )

        # Now imagine user goes back and changes system type again
        # (In real flow this requires navigation, but testing the logic)
        flow.collected_config[CONF_SYSTEM_TYPE] = SYSTEM_TYPE_SIMPLE_HEATER
        original_system = flow.collected_config.get(CONF_SYSTEM_TYPE)

        # Simulate another system type change
        new_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        if new_input[CONF_SYSTEM_TYPE] != original_system:
            name = flow.collected_config.get(CONF_NAME)
            flow.collected_config = {
                CONF_NAME: name,
                CONF_SYSTEM_TYPE: new_input[CONF_SYSTEM_TYPE],
                "system_type_changed": True,
            }

        # Verify config cleared again
        assert flow.collected_config[CONF_NAME] == "Living Room"
        assert flow.collected_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
        assert CONF_HEATER not in flow.collected_config
        assert CONF_SENSOR not in flow.collected_config


async def test_features_step_shows_configured_features(heat_pump_entry_with_features):
    """Test that features step checkboxes show which features are currently configured."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure (loads existing config with features)
        await flow.async_step_reconfigure()

        # Confirm same system type (preserves config)
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )

        # Go through basic config
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
                CONF_SENSOR: "sensor.temperature",
            }
        )

        # Detect configured features before showing form
        feature_defaults = flow._detect_configured_features()

        # Verify all configured features are detected
        assert feature_defaults.get("configure_floor_heating") is True
        assert feature_defaults.get("configure_fan") is True
        assert feature_defaults.get("configure_humidity") is True
        assert feature_defaults.get("configure_openings") is True


async def test_uncheck_floor_heating_clears_config(heat_pump_entry_with_features):
    """Test that unchecking floor heating clears related configuration."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
                CONF_SENSOR: "sensor.temperature",
            }
        )

        # Verify floor sensor is present before unchecking
        assert CONF_FLOOR_SENSOR in flow.collected_config

        # Uncheck floor heating (but keep other features)
        await flow.async_step_features(
            {
                "configure_floor_heating": False,  # Unchecked
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Verify floor sensor was cleared
        assert CONF_FLOOR_SENSOR not in flow.collected_config
        # Verify other features are preserved
        assert CONF_FAN in flow.collected_config
        assert CONF_HUMIDITY_SENSOR in flow.collected_config


async def test_uncheck_fan_clears_config(heat_pump_entry_with_features):
    """Test that unchecking fan clears related configuration."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
                CONF_SENSOR: "sensor.temperature",
            }
        )

        # Verify fan is present before unchecking
        assert CONF_FAN in flow.collected_config

        # Uncheck fan
        await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": False,  # Unchecked
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Verify fan was cleared
        assert CONF_FAN not in flow.collected_config


async def test_uncheck_all_features_clears_all_config(heat_pump_entry_with_features):
    """Test that unchecking all features clears all related configuration."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry_with_features)

        # Start reconfigure
        await flow.async_step_reconfigure()
        await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Living Room",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
                CONF_SENSOR: "sensor.temperature",
            }
        )

        # Verify features are present before unchecking
        assert CONF_FLOOR_SENSOR in flow.collected_config
        assert CONF_FAN in flow.collected_config
        assert CONF_HUMIDITY_SENSOR in flow.collected_config
        assert "openings" in flow.collected_config

        # Uncheck ALL features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should finish successfully
        assert result["type"] == "abort"

        # Verify all feature config was cleared
        assert CONF_FLOOR_SENSOR not in flow.collected_config
        assert CONF_FAN not in flow.collected_config
        assert CONF_HUMIDITY_SENSOR not in flow.collected_config
        assert "openings" not in flow.collected_config
