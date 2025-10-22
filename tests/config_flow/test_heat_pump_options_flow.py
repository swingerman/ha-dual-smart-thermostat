"""Tests for heat_pump system type options flow.

Following TDD approach - these tests should guide implementation.
Task: T006 - Complete heat_pump implementation
Issue: #416
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_HEAT_PUMP,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    return hass


class TestHeatPumpOptionsFlow:
    """Test heat_pump options flow - Core Requirements."""

    async def test_options_flow_omits_name_field(self, mock_hass):
        """Test that simplified options flow does NOT include name field.

        Acceptance Criteria: name field is omitted in options flow
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        # Create a mock config entry
        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Existing Name",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Get options schema from simplified init step
        result = await flow.async_step_init()

        # Verify name field is NOT in schema
        schema_fields = [
            k.schema
            for k in result["data_schema"].schema.keys()
            if hasattr(k, "schema")
        ]
        assert CONF_NAME not in schema_fields

    async def test_options_flow_prefills_all_fields(self, mock_hass):
        """Test that simplified options flow pre-fills runtime tuning parameters from existing config.

        Acceptance Criteria: Options flow pre-fills runtime tuning parameters from existing config
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Existing",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.existing_temp",
            CONF_HEATER: "switch.existing_heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.existing_cooling",
            CONF_COLD_TOLERANCE: 0.7,
            CONF_HOT_TOLERANCE: 0.8,
            CONF_MIN_DUR: 450,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Get simplified init step showing runtime tuning
        result = await flow.async_step_init()
        schema = result["data_schema"].schema

        # Verify runtime parameter defaults are pre-filled from existing config
        runtime_params = [CONF_COLD_TOLERANCE, CONF_HOT_TOLERANCE]
        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if field_name in runtime_params and field_name in config_entry.data:
                    # Check that default matches existing value
                    if hasattr(key, "default"):
                        expected_value = config_entry.data[field_name]
                        # Note: default might be callable or direct value
                        if callable(key.default):
                            assert key.default() == expected_value
                        else:
                            assert key.default == expected_value

    async def test_options_flow_preserves_unmodified_fields(self, mock_hass):
        """Test that simplified options flow preserves fields from existing config.

        Acceptance Criteria: All existing config fields are preserved when updating runtime parameters
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Original Name",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.original",
            CONF_HEATER: "switch.original_heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.original_cooling",
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
            CONF_MIN_DUR: 300,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Only change tolerance, leave others unchanged
        options_input = {
            CONF_COLD_TOLERANCE: 0.7,
            # Other fields not provided - should use existing values
        }

        await flow.async_step_init(options_input)

        # Verify all existing fields are in collected config (merged from entry.data)
        assert flow.collected_config.get(CONF_HEATER) == "switch.original_heat_pump"
        assert (
            flow.collected_config.get(CONF_HEAT_PUMP_COOLING)
            == "binary_sensor.original_cooling"
        )
        assert flow.collected_config.get(CONF_SENSOR) == "sensor.original"
        # Updated field should have new value
        assert flow.collected_config.get(CONF_COLD_TOLERANCE) == 0.7

    async def test_options_flow_system_type_display_non_editable(self, mock_hass):
        """Test that system type is preserved but not shown in simplified options flow.

        Acceptance Criteria: System type is preserved in the config entry (not editable in options flow)
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Initialize simplified options flow
        result = await flow.async_step_init()

        # System type should NOT be in the form (not editable)
        assert result["type"] == FlowResultType.FORM

        # The simplified form shows runtime tuning only, not system type
        schema = result["data_schema"].schema
        schema_field_names = [str(k) for k in schema.keys()]

        # Verify system type is NOT in schema (use reconfigure flow to change it)
        assert not any(CONF_SYSTEM_TYPE in name for name in schema_field_names)

        # But it should be preserved in the config
        current_config = flow._get_current_config()
        assert current_config[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEAT_PUMP

    async def test_options_flow_completes_without_error(self, mock_hass):
        """Test that simplified options flow completes without error.

        Acceptance Criteria: Flow completes without error - all steps navigate successfully
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Start simplified flow
        result = await flow.async_step_init()

        # Should show form without errors
        assert result["type"] == FlowResultType.FORM
        assert "errors" not in result or not result["errors"]

    async def test_options_flow_updated_config_matches_data_model(self, mock_hass):
        """Test that updated runtime tuning parameters are collected correctly.

        Acceptance Criteria: Updated runtime tuning parameters are collected correctly
        """
        from custom_components.dual_smart_thermostat.options_flow import (
            OptionsFlowHandler,
        )

        config_entry = Mock()
        config_entry.data = {
            CONF_NAME: "Test",
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            CONF_SENSOR: "sensor.old_temp",
            CONF_HEATER: "switch.old_heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.old_cooling",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_MIN_DUR: 300,
        }
        config_entry.options = {}

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Update runtime tuning parameters only (entities are in reconfigure flow)
        options_input = {
            CONF_COLD_TOLERANCE: 0.5,
            CONF_HOT_TOLERANCE: 0.5,
        }

        await flow.async_step_init(options_input)

        # Verify all existing config is preserved
        assert CONF_SENSOR in flow.collected_config
        assert CONF_HEATER in flow.collected_config
        assert CONF_HEAT_PUMP_COOLING in flow.collected_config
        assert CONF_COLD_TOLERANCE in flow.collected_config
        assert CONF_HOT_TOLERANCE in flow.collected_config

        # Verify existing values are preserved
        assert flow.collected_config[CONF_SENSOR] == "sensor.old_temp"
        assert flow.collected_config[CONF_HEATER] == "switch.old_heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING] == "binary_sensor.old_cooling"
        )

        # Verify updated runtime parameters
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.5
        assert flow.collected_config[CONF_HOT_TOLERANCE] == 0.5
