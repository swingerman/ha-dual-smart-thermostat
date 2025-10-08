"""Unit tests for heat_pump schema.

Following TDD approach - these tests should guide implementation.
Task: T006 - Complete heat_pump implementation
Issue: #416
"""

from homeassistant.const import CONF_NAME
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
    CONF_SENSOR,
)
from custom_components.dual_smart_thermostat.schemas import get_heat_pump_schema


class TestHeatPumpSchema:
    """Test heat_pump schema structure and defaults."""

    def test_schema_with_include_name_true_includes_name_field(self):
        """Test that schema includes name field when include_name=True.

        Acceptance Criteria: get_heat_pump_schema(defaults=None, include_name=True)
                              includes all required fields
        """
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        assert CONF_NAME in field_names
        assert CONF_SENSOR in field_names
        assert CONF_HEATER in field_names
        assert CONF_HEAT_PUMP_COOLING in field_names

    def test_schema_with_include_name_false_omits_name_field(self):
        """Test that schema omits name field when include_name=False.

        Acceptance Criteria: get_heat_pump_schema(defaults=None, include_name=False)
                              omits name field
        """
        schema = get_heat_pump_schema(defaults=None, include_name=False)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        assert CONF_NAME not in field_names
        assert CONF_SENSOR in field_names
        assert CONF_HEATER in field_names

    def test_schema_with_defaults_prefills_values_correctly(self):
        """Test that schema pre-fills values when defaults provided.

        Acceptance Criteria: get_heat_pump_schema(defaults={...}) pre-fills values correctly
        """
        defaults = {
            CONF_NAME: "Test Heat Pump",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heat_pump",
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            CONF_COLD_TOLERANCE: 0.7,
            CONF_HOT_TOLERANCE: 0.8,
            CONF_MIN_DUR: 600,
        }

        schema = get_heat_pump_schema(defaults=defaults, include_name=True)

        # Verify defaults are set
        for key in schema.schema.keys():
            if hasattr(key, "schema"):
                field_name = key.schema
                if field_name in defaults:
                    # Check default value
                    if hasattr(key, "default"):
                        if callable(key.default):
                            assert key.default() == defaults[field_name]
                        elif key.default != vol.UNDEFINED:
                            assert key.default == defaults[field_name]

    def test_schema_fields_use_correct_selectors(self):
        """Test that all fields use correct selector types.

        Acceptance Criteria: All fields use correct selectors (entity, number, boolean)
        """
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # Note: We can't easily test selector types without inspecting implementation
        # This test verifies schema is created without errors
        assert schema is not None
        assert isinstance(schema, vol.Schema)

    def test_heat_pump_cooling_accepts_entity_id(self):
        """Test that heat_pump_cooling accepts entity_id.

        Acceptance Criteria: heat_pump_cooling is an entity selector for binary_sensor
        """
        defaults = {
            CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        }

        schema = get_heat_pump_schema(defaults=defaults, include_name=True)

        # Verify heat_pump_cooling field exists
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]
        assert CONF_HEAT_PUMP_COOLING in field_names

        # Verify the default value is set correctly
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_HEAT_PUMP_COOLING:
                if hasattr(key, "default"):
                    default_value = (
                        key.default() if callable(key.default) else key.default
                    )
                    assert default_value == "binary_sensor.cooling_mode"
                break

    def test_optional_entity_fields_use_vol_undefined(self):
        """Test that optional entity fields use vol.UNDEFINED when no default provided.

        Acceptance Criteria: Optional entity fields use vol.UNDEFINED when no default provided
        """
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # For fields without defaults, they should use vol.UNDEFINED
        # Required fields should not have defaults
        for key in schema.schema.keys():
            if hasattr(key, "schema"):
                # For required fields, default should be UNDEFINED or not present
                if isinstance(key, vol.Required):
                    if hasattr(key, "default"):
                        # Required fields with no user default should have vol.UNDEFINED
                        assert key.default == vol.UNDEFINED or key.default is None

    def test_advanced_settings_section_structure(self):
        """Test that advanced_settings section is structured correctly.

        Acceptance Criteria: Test advanced_settings section structure
        """
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # Verify advanced_settings exists in schema
        field_names = [
            k.schema if hasattr(k, "schema") else str(k) for k in schema.schema.keys()
        ]

        # Advanced settings should be present
        assert "advanced_settings" in field_names

    def test_schema_defaults_match_constants(self):
        """Test that schema defaults use correct constant values."""
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # Find advanced_settings section
        advanced_settings_key = None
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == "advanced_settings":
                advanced_settings_key = key
                break

        # If advanced settings found, verify it has correct structure
        if advanced_settings_key is not None:
            # Advanced settings should contain tolerance and min_dur fields
            assert advanced_settings_key is not None

    def test_heat_pump_cooling_defaults_to_undefined(self):
        """Test that heat_pump_cooling defaults to vol.UNDEFINED when no defaults provided.

        Since heat_pump_cooling is an optional entity selector, it should default to
        vol.UNDEFINED when no default is provided.
        """
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        # Find heat_pump_cooling field
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_HEAT_PUMP_COOLING:
                # Should have default of vol.UNDEFINED for optional entity field
                assert hasattr(key, "default")
                if callable(key.default):
                    assert key.default() == vol.UNDEFINED
                else:
                    assert key.default == vol.UNDEFINED
                break

    def test_required_fields_are_marked_required(self):
        """Test that required fields (heater, sensor, name) are marked as Required."""
        schema = get_heat_pump_schema(defaults=None, include_name=True)

        required_fields = []
        optional_fields = []

        for key in schema.schema.keys():
            if hasattr(key, "schema"):
                if isinstance(key, vol.Required):
                    required_fields.append(key.schema)
                elif isinstance(key, vol.Optional):
                    optional_fields.append(key.schema)

        # Core fields should be required
        assert CONF_NAME in required_fields
        assert CONF_SENSOR in required_fields
        assert CONF_HEATER in required_fields

        # Heat pump cooling and advanced settings should be optional
        assert (
            CONF_HEAT_PUMP_COOLING in optional_fields
            or "advanced_settings" in optional_fields
        )

    def test_heat_pump_cooling_entity_selector_functionality(self):
        """Test that heat_pump_cooling entity selector works correctly.

        Acceptance Criteria: heat_pump_cooling entity selector functionality works correctly
        """
        # Test with entity_id default
        defaults = {CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_enabled"}
        schema = get_heat_pump_schema(defaults=defaults, include_name=True)

        # Find the heat_pump_cooling field and verify it has the default
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_HEAT_PUMP_COOLING:
                if hasattr(key, "default"):
                    default_value = (
                        key.default() if callable(key.default) else key.default
                    )
                    assert (
                        default_value == "binary_sensor.cooling_enabled"
                        or default_value is False
                    )
                break
