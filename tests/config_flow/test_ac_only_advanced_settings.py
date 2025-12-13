"""Test that AC-only systems have consistent advanced settings in config and options flows."""

from unittest.mock import Mock

from homeassistant.config_entries import ConfigEntry
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HOT_TOLERANCE,
    CONF_KEEP_ALIVE,
    CONF_MIN_DUR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


class TestACOnlyAdvancedSettings:
    """Test AC-only advanced settings consistency between flows."""

    def test_config_flow_ac_only_has_advanced_section(self):
        """Test that config flow AC-only system has advanced settings section."""
        from custom_components.dual_smart_thermostat.schemas import get_basic_ac_schema

        schema = get_basic_ac_schema(defaults=None, include_name=True)
        schema_dict = schema.schema

        # Check that advanced_settings section exists
        advanced_field_found = False
        for key in schema_dict.keys():
            if hasattr(key, "schema") and "advanced_settings" in str(key.schema):
                advanced_field_found = True
                break

        assert (
            advanced_field_found
        ), "Advanced settings section not found in AC-only config schema"

    def test_options_flow_ac_only_has_advanced_section(self):
        """Test that options flow AC-only system has advanced settings section."""
        from custom_components.dual_smart_thermostat.schemas import get_basic_ac_schema

        mock_data = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "heater": "switch.ac",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_MIN_DUR: 300,
            CONF_KEEP_ALIVE: 300,
        }

        schema = get_basic_ac_schema(defaults=mock_data, include_name=False)
        schema_dict = schema.schema

        # Check that advanced_settings section exists
        advanced_field_found = False
        for key in schema_dict.keys():
            if hasattr(key, "schema") and "advanced_settings" in str(key.schema):
                advanced_field_found = True
                break

        assert (
            advanced_field_found
        ), "Advanced settings section not found in AC-only options schema"

    @pytest.mark.asyncio
    async def test_options_flow_init_step_ac_only(self):
        """Test that options flow init step correctly handles AC-only system.

        After moving keep_alive and min_cycle_duration out of advanced_settings,
        AC-only systems may not have an advanced_settings section since they don't
        have heat_tolerance/cool_tolerance fields (only for dual-mode systems).

        This test now verifies that keep_alive and min_cycle_duration are present
        in the main schema fields, not in an advanced section.
        """
        # Mock config entry
        mock_entry = Mock(spec=ConfigEntry)
        mock_entry.data = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "heater": "switch.ac",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            CONF_COLD_TOLERANCE: 0.3,
            CONF_HOT_TOLERANCE: 0.3,
            CONF_KEEP_ALIVE: 300,  # Should appear in main fields, not advanced section
        }
        mock_entry.options = {}

        flow = OptionsFlowHandler(mock_entry)
        flow.hass = Mock()
        flow.collected_config = {}

        # Mock the _get_entry method
        flow._get_entry = Mock(return_value=mock_entry)

        # Mock the _determine_options_next_step method
        async def mock_next_step():
            return {"type": "form", "step_id": "next"}

        flow._determine_options_next_step = mock_next_step

        # Test the init step with no user input (should show form)
        result = await flow.async_step_init(None)

        assert result["type"] == "form"
        assert result["step_id"] == "init"

        # Check that keep_alive and min_cycle_duration are in the main schema fields
        schema_dict = result["data_schema"].schema
        keep_alive_found = False
        min_dur_found = False

        for key in schema_dict.keys():
            if hasattr(key, "schema"):
                # Check if this is the keep_alive or min_cycle_duration field
                if "keep_alive" in str(key):
                    keep_alive_found = True
                if "min_cycle_duration" in str(key):
                    min_dur_found = True

        assert (
            keep_alive_found
        ), "keep_alive field not found in options flow AC-only init step main fields"
        assert (
            min_dur_found
        ), "min_cycle_duration field not found in options flow AC-only init step main fields"


if __name__ == "__main__":
    pytest.main([__file__])
