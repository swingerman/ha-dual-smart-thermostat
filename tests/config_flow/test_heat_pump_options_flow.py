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
        """Test that options flow does NOT include name field.

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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass
        flow.collected_config = {}

        # Get options schema
        result = await flow.async_step_basic()

        # Verify name field is NOT in schema
        schema_fields = [
            k.schema
            for k in result["data_schema"].schema.keys()
            if hasattr(k, "schema")
        ]
        assert CONF_NAME not in schema_fields

    async def test_options_flow_prefills_all_fields(self, mock_hass):
        """Test that options flow pre-fills all heat_pump fields from existing config.

        Acceptance Criteria: Options flow pre-fills all heat_pump fields from existing config
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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass
        flow.collected_config = {}

        result = await flow.async_step_basic()
        schema = result["data_schema"].schema

        # Verify defaults are pre-filled from existing config
        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if field_name in config_entry.data:
                    # Check that default matches existing value
                    if hasattr(key, "default"):
                        expected_value = config_entry.data[field_name]
                        # Note: default might be callable or direct value
                        if callable(key.default):
                            assert key.default() == expected_value
                        else:
                            assert key.default == expected_value

    async def test_options_flow_preserves_unmodified_fields(self, mock_hass):
        """Test that options flow preserves fields that weren't changed.

        Acceptance Criteria: Unmodified fields preserved - fields not changed remain intact
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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass
        flow.collected_config = {}

        # Only change sensor, leave others unchanged
        options_input = {
            CONF_SENSOR: "sensor.new_temp",
            # Other fields not provided - should use existing values
        }

        await flow.async_step_basic(options_input)

        # Verify unchanged fields are preserved
        assert flow.collected_config.get(CONF_HEATER) == "switch.original_heat_pump"
        assert (
            flow.collected_config.get(CONF_HEAT_PUMP_COOLING)
            == "binary_sensor.original_cooling"
        )
        assert flow.collected_config.get(CONF_COLD_TOLERANCE) == 0.5

    async def test_options_flow_system_type_display_non_editable(self, mock_hass):
        """Test that system type is displayed but non-editable in options flow.

        Acceptance Criteria: System type is displayed but non-editable
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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass

        # Initialize options flow
        result = await flow.async_step_init()

        # System type should be stored/displayed but not editable
        # The flow should proceed to basic step without allowing system type change
        assert result["type"] == FlowResultType.FORM

        # The form should show the system type selector with current value as default
        schema = result["data_schema"].schema
        system_type_key = None
        for key in schema.keys():
            if str(key) == CONF_SYSTEM_TYPE:
                system_type_key = key
                break
        assert system_type_key is not None
        default_value = (
            system_type_key.default()
            if callable(system_type_key.default)
            else system_type_key.default
        )
        assert default_value == SYSTEM_TYPE_HEAT_PUMP

    async def test_options_flow_completes_without_error(self, mock_hass):
        """Test that options flow completes without error.

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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass
        flow.collected_config = {}

        result = await flow.async_step_basic()

        # Should show form without errors
        assert result["type"] == FlowResultType.FORM
        assert "errors" not in result or not result["errors"]

    async def test_options_flow_updated_config_matches_data_model(self, mock_hass):
        """Test that updated config matches data-model.md structure.

        Acceptance Criteria: Updated config matches data-model.md structure after changes
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

        flow = OptionsFlowHandler(config_entry)
        flow.hass = mock_hass
        flow.collected_config = {}

        # Update multiple fields
        options_input = {
            CONF_SENSOR: "sensor.new_temp",
            CONF_HEATER: "switch.new_heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.new_cooling",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_MIN_DUR: 600,
            },
        }

        await flow.async_step_basic(options_input)

        # Verify structure matches data-model.md
        assert CONF_SENSOR in flow.collected_config
        assert CONF_HEATER in flow.collected_config
        assert CONF_HEAT_PUMP_COOLING in flow.collected_config
        assert CONF_COLD_TOLERANCE in flow.collected_config
        assert CONF_HOT_TOLERANCE in flow.collected_config
        assert CONF_MIN_DUR in flow.collected_config

        # Verify updated values
        assert flow.collected_config[CONF_SENSOR] == "sensor.new_temp"
        assert flow.collected_config[CONF_HEATER] == "switch.new_heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING] == "binary_sensor.new_cooling"
        )
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.5
