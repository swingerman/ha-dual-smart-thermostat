"""Test openings scope options generation based on system configuration."""

import pytest

from custom_components.dual_smart_thermostat.const import CONF_OPENINGS_SCOPE
from custom_components.dual_smart_thermostat.feature_steps.openings import OpeningsSteps


class MockFlowInstance:
    """Mock flow instance for testing."""

    def async_show_form(self, step_id, data_schema, description_placeholders=None):
        """Mock async_show_form method."""
        return {"type": "form", "step_id": step_id, "data_schema": data_schema}


def extract_scope_options_from_schema(schema_dict):
    """Helper function to extract scope options from schema."""
    for key, value in schema_dict.items():
        # Check if this is the openings_scope field
        if hasattr(key, "key") and key.key == CONF_OPENINGS_SCOPE:
            options = value.config.get("options", [])
            # Handle both old format (list of dicts) and new format (list of strings)
            if options and isinstance(options[0], str):
                # New format: list of strings (translated options)
                return options
            else:
                # Old format: list of dicts with value/label
                return options
        elif hasattr(key, "schema") and "openings_scope" in str(key.schema):
            options = value.config.get("options", [])
            # Handle both old format (list of dicts) and new format (list of strings)
            if options and isinstance(options[0], str):
                # New format: list of strings (translated options)
                return options
            else:
                # Old format: list of dicts with value/label
                return options

    raise AssertionError(
        f"Could not find openings_scope field in schema keys: {list(schema_dict.keys())}"
    )


class TestOpeningsScopeGeneration:
    """Test openings scope options generation."""

    @pytest.mark.asyncio
    async def test_ac_only_system_scope_options(self):
        """Test scope options for AC-only system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # AC-only system with fan and dryer
        collected_config = {
            "heater": "switch.ac",
            "ac_mode": True,
            "fan": "switch.fan",
            "dryer": "switch.dryer",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)

        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # AC-only system should have: all, cool, fan_only, dry
        expected_options = ["all", "cool", "fan_only", "dry"]
        assert all(opt in option_values for opt in expected_options)
        assert "heat" not in option_values  # No heating capability
        assert "heat_cool" not in option_values  # No heat_cool mode

    @pytest.mark.asyncio
    async def test_simple_heater_scope_options(self):
        """Test scope options for simple heater system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Simple heater system
        collected_config = {
            "heater": "switch.heater",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)

        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Simple heater should have: all, heat
        expected_options = ["all", "heat"]
        assert all(opt in option_values for opt in expected_options)
        assert "cool" not in option_values  # No cooling capability
        assert "fan_only" not in option_values  # No fan configured
        assert "dry" not in option_values  # No dryer configured
        assert "heat_cool" not in option_values  # No dual mode

    @pytest.mark.asyncio
    async def test_heat_pump_scope_options(self):
        """Test scope options for heat pump system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Heat pump system with heat_cool_mode enabled
        collected_config = {
            "heater": "switch.heat_pump",
            "heat_pump_cooling": "sensor.heat_pump_mode",
            "heat_cool_mode": True,
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Heat pump with heat_cool_mode should have: all, heat, cool, heat_cool
        expected_options = ["all", "heat", "cool", "heat_cool"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_dual_system_full_features_scope_options(self):
        """Test scope options for dual system with all features."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Dual system with all features
        collected_config = {
            "heater": "switch.heater",
            "cooler": "switch.cooler",
            "heat_cool_mode": True,
            "fan": "switch.fan",
            "dryer": "switch.dryer",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Dual system with all features should have all options
        expected_options = ["all", "heat", "cool", "heat_cool", "fan_only", "dry"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_fan_mode_only_scope_options(self):
        """Test scope options for fan-only system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Fan-only system
        collected_config = {
            "heater": "switch.fan",  # Heater entity used as fan in fan_mode
            "fan_mode": True,
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Fan-only system should have: all, heat (heater configured), fan_only
        expected_options = ["all", "heat", "fan_only"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_dual_system_without_heat_cool_mode(self):
        """Test scope options for dual system without heat_cool_mode."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Dual system without heat_cool_mode
        collected_config = {
            "heater": "switch.heater",
            "cooler": "switch.cooler",
            # heat_cool_mode not set or False
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_options = extract_scope_options_from_schema(schema_dict)
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Should have heat and cool but not heat_cool
        expected_options = ["all", "heat", "cool"]
        assert all(opt in option_values for opt in expected_options)
        assert "heat_cool" not in option_values  # heat_cool_mode not enabled


if __name__ == "__main__":
    pytest.main([__file__])

    @pytest.mark.asyncio
    async def test_ac_only_system_scope_options(self):
        """Test scope options for AC-only system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # AC-only system with fan and dryer
        collected_config = {
            "heater": "switch.ac",
            "ac_mode": True,
            "fan": "switch.fan",
            "dryer": "switch.dryer",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # AC-only system should have: all, cool, fan_only, dry
        expected_options = ["all", "cool", "fan_only", "dry"]
        assert all(opt in option_values for opt in expected_options)
        assert "heat" not in option_values  # No heating capability
        assert "heat_cool" not in option_values  # No heat_cool mode

    @pytest.mark.asyncio
    async def test_simple_heater_scope_options(self):
        """Test scope options for simple heater system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Simple heater system
        collected_config = {
            "heater": "switch.heater",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Simple heater should have: all, heat
        expected_options = ["all", "heat"]
        assert all(opt in option_values for opt in expected_options)
        assert "cool" not in option_values  # No cooling capability
        assert "fan_only" not in option_values  # No fan configured
        assert "dry" not in option_values  # No dryer configured
        assert "heat_cool" not in option_values  # No dual mode

    @pytest.mark.asyncio
    async def test_heat_pump_scope_options(self):
        """Test scope options for heat pump system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Heat pump system with heat_cool_mode enabled
        collected_config = {
            "heater": "switch.heat_pump",
            "heat_pump_cooling": "sensor.heat_pump_mode",
            "heat_cool_mode": True,
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Heat pump with heat_cool_mode should have: all, heat, cool, heat_cool
        expected_options = ["all", "heat", "cool", "heat_cool"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_dual_system_full_features_scope_options(self):
        """Test scope options for dual system with all features."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Dual system with all features
        collected_config = {
            "heater": "switch.heater",
            "cooler": "switch.cooler",
            "heat_cool_mode": True,
            "fan": "switch.fan",
            "dryer": "switch.dryer",
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Dual system with all features should have all options
        expected_options = ["all", "heat", "cool", "heat_cool", "fan_only", "dry"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_fan_mode_only_scope_options(self):
        """Test scope options for fan-only system."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Fan-only system
        collected_config = {
            "heater": "switch.fan",  # Heater entity used as fan in fan_mode
            "fan_mode": True,
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Fan-only system should have: all, heat (heater configured), fan_only
        expected_options = ["all", "heat", "fan_only"]
        assert all(opt in option_values for opt in expected_options)

    @pytest.mark.asyncio
    async def test_dual_system_without_heat_cool_mode(self):
        """Test scope options for dual system without heat_cool_mode."""
        openings_steps = OpeningsSteps()
        flow_instance = MockFlowInstance()

        # Dual system without heat_cool_mode
        collected_config = {
            "heater": "switch.heater",
            "cooler": "switch.cooler",
            # heat_cool_mode not set or False
            "selected_openings": ["binary_sensor.door"],
        }

        result = await openings_steps.async_step_config(
            flow_instance, None, collected_config, lambda: None
        )

        # Extract scope options from the schema
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None
        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Should have heat and cool but not heat_cool
        expected_options = ["all", "heat", "cool"]
        assert all(opt in option_values for opt in expected_options)
        assert "heat_cool" not in option_values  # heat_cool_mode not enabled


if __name__ == "__main__":
    pytest.main([__file__])
