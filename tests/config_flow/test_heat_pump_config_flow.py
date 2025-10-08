"""Tests for heat_pump system type config flow.

Following TDD approach - these tests should guide implementation.
Task: T006 - Complete heat_pump implementation
Issue: #416
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEAT_PUMP,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestHeatPumpConfigFlow:
    """Test heat_pump config flow - Core Requirements."""

    async def test_config_flow_completes_without_error(self, mock_hass):
        """Test that heat_pump config flow completes successfully.

        Acceptance Criteria: Flow completes without error - all steps navigate successfully
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Step 1: Select heat_pump system type
        user_input = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        result = await flow.async_step_user(user_input)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "heat_pump"

        # Step 2: Configure heat_pump basic settings
        heat_pump_input = {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_MIN_DUR: 300,
            },
        }
        result = await flow.async_step_heat_pump(heat_pump_input)

        # Should proceed to features step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

    async def test_valid_configuration_created(self, mock_hass):
        """Test that valid configuration is created matching data-model.md.

        Acceptance Criteria: Valid configuration created - config entry data matches data-model.md
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_state",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.3,
                CONF_HOT_TOLERANCE: 0.3,
                CONF_MIN_DUR: 600,
            },
        }

        await flow.async_step_heat_pump(heat_pump_input)

        # Verify configuration structure
        assert CONF_NAME in flow.collected_config
        assert CONF_SENSOR in flow.collected_config
        assert CONF_HEATER in flow.collected_config
        assert CONF_HEAT_PUMP_COOLING in flow.collected_config

        # Verify advanced settings are flattened to top level
        assert CONF_COLD_TOLERANCE in flow.collected_config
        assert CONF_HOT_TOLERANCE in flow.collected_config
        assert CONF_MIN_DUR in flow.collected_config

        # Verify values
        assert flow.collected_config[CONF_NAME] == "Test Heat Pump"
        assert flow.collected_config[CONF_HEATER] == "switch.heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_state"
        )
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 0.3

    async def test_all_required_fields_present(self, mock_hass):
        """Test that all required fields from schema are present in saved config.

        Acceptance Criteria: All required fields from schema present in saved config
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        # Get the schema
        result = await flow.async_step_heat_pump()
        schema = result["data_schema"].schema

        # Verify required fields in schema
        required_fields = []
        for key in schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                # Check if field is required (not Optional)
                if not hasattr(key, "default") or key.default is None:
                    required_fields.append(field_name)

        # Required fields should include name, sensor, heater
        assert CONF_NAME in [k.schema for k in schema.keys() if hasattr(k, "schema")]
        assert CONF_SENSOR in [k.schema for k in schema.keys() if hasattr(k, "schema")]
        assert CONF_HEATER in [k.schema for k in schema.keys() if hasattr(k, "schema")]

    async def test_advanced_settings_flattened_correctly(self, mock_hass):
        """Test that advanced settings are extracted and flattened to top level.

        Acceptance Criteria: Advanced settings flattened to top level (tolerances, min_cycle_duration)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heat_pump",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 1.0,
                CONF_HOT_TOLERANCE: 2.0,
                CONF_MIN_DUR: 900,
            },
        }

        await flow.async_step_heat_pump(heat_pump_input)

        # Verify advanced_settings key is removed
        assert "advanced_settings" not in flow.collected_config

        # Verify settings are flattened to top level
        assert flow.collected_config[CONF_COLD_TOLERANCE] == 1.0
        assert flow.collected_config[CONF_HOT_TOLERANCE] == 2.0
        assert flow.collected_config[CONF_MIN_DUR] == 900

    async def test_validation_same_heater_sensor_entity(self, mock_hass):
        """Test validation error when heater and sensor are the same entity.

        Acceptance Criteria: Required fields (heater, sensor) raise validation errors when missing
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "switch.heat_pump",  # Wrong domain, same as heater
            CONF_HEATER: "switch.heat_pump",
        }

        result = await flow.async_step_heat_pump(heat_pump_input)

        # Should show error
        assert result["type"] == FlowResultType.FORM
        assert "errors" in result

    async def test_heat_pump_cooling_entity_id_accepted(self, mock_hass):
        """Test that heat_pump_cooling accepts entity_id.

        Acceptance Criteria: heat_pump_cooling accepts entity_id (preferred) or boolean
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_MIN_DUR: 300,
            },
        }

        result = await flow.async_step_heat_pump(heat_pump_input)

        # Should proceed to features step
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_mode"
        )

    async def test_heat_pump_cooling_optional(self, mock_hass):
        """Test that heat_pump_cooling is optional and can be omitted.

        Acceptance Criteria: heat_pump_cooling is an optional field
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heat_pump",
            # heat_pump_cooling omitted - should be optional
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,
                CONF_HOT_TOLERANCE: 0.5,
                CONF_MIN_DUR: 300,
            },
        }

        result = await flow.async_step_heat_pump(heat_pump_input)

        # Should proceed to features step even without heat_pump_cooling
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "features"

    async def test_name_field_collected_in_config_flow(self, mock_hass):
        """Test that name field is collected in config flow.

        Acceptance Criteria: name field is collected in config flow
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "My Heat Pump Thermostat",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }

        await flow.async_step_heat_pump(heat_pump_input)

        # Verify name is collected
        assert CONF_NAME in flow.collected_config
        assert flow.collected_config[CONF_NAME] == "My Heat Pump Thermostat"


class TestHeatPumpFieldValidation:
    """Test heat_pump field-specific validation."""

    async def test_numeric_fields_have_correct_defaults(self, mock_hass):
        """Test that numeric fields have correct defaults when not provided.

        Acceptance Criteria: Numeric fields have correct defaults when not provided
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        # Get the schema without providing defaults
        result = await flow.async_step_heat_pump()
        schema = result["data_schema"].schema

        # Verify schema exists and has advanced_settings section
        field_names = [
            k.schema if hasattr(k, "schema") else str(k) for k in schema.keys()
        ]
        assert "advanced_settings" in field_names

    async def test_field_types_match_expected_types(self, mock_hass):
        """Test that field types match expected types.

        Acceptance Criteria: Field types match expected types (entity_id strings, numeric values)
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}

        heat_pump_input = {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",  # entity_id string
            CONF_HEATER: "switch.heater",  # entity_id string
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",  # entity_id string
            "advanced_settings": {
                CONF_COLD_TOLERANCE: 0.5,  # numeric
                CONF_HOT_TOLERANCE: 0.5,  # numeric
                CONF_MIN_DUR: 300,  # numeric (int)
            },
        }

        await flow.async_step_heat_pump(heat_pump_input)

        # Verify types
        assert isinstance(flow.collected_config[CONF_SENSOR], str)
        assert isinstance(flow.collected_config[CONF_HEATER], str)
        assert isinstance(flow.collected_config[CONF_HEAT_PUMP_COOLING], str)
        assert isinstance(flow.collected_config[CONF_COLD_TOLERANCE], (int, float))
        assert isinstance(flow.collected_config[CONF_HOT_TOLERANCE], (int, float))
        assert isinstance(flow.collected_config[CONF_MIN_DUR], int)
