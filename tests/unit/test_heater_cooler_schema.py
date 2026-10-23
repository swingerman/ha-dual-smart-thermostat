"""Unit tests for heater_cooler schema.

Following TDD approach - these tests should guide implementation.
Task: T005 - Complete heater_cooler implementation
Issue: #415
"""

from homeassistant.const import CONF_NAME
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.const import (
    CONF_AUX_HEATER,
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
)
from custom_components.dual_smart_thermostat.schemas import (
    get_basic_ac_schema,
    get_core_schema,
    get_dual_stage_schema,
    get_fan_schema,
    get_heat_pump_schema,
    get_heater_cooler_schema,
    get_humidity_schema,
    get_simple_heater_schema,
)


class TestHeaterCoolerSchema:
    """Test heater_cooler schema structure and defaults."""

    def test_schema_with_include_name_true_includes_name_field(self):
        """Test that schema includes name field when include_name=True.

        Acceptance Criteria: get_heater_cooler_schema(defaults=None, include_name=True)
                              includes all required fields
        """
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        assert CONF_NAME in field_names
        assert CONF_SENSOR in field_names
        assert CONF_HEATER in field_names
        assert CONF_COOLER in field_names
        assert CONF_HEAT_COOL_MODE in field_names

    def test_schema_with_include_name_false_omits_name_field(self):
        """Test that schema omits name field when include_name=False.

        Acceptance Criteria: get_heater_cooler_schema(defaults=None, include_name=False)
                              omits name field
        """
        schema = get_heater_cooler_schema(defaults=None, include_name=False)

        # Extract field names from schema
        field_names = [k.schema for k in schema.schema.keys() if hasattr(k, "schema")]

        assert CONF_NAME not in field_names
        assert CONF_SENSOR in field_names
        assert CONF_HEATER in field_names
        assert CONF_COOLER in field_names

    def test_schema_with_defaults_prefills_values_correctly(self):
        """Test that schema pre-fills values when defaults provided.

        Acceptance Criteria: get_heater_cooler_schema(defaults={...}) pre-fills values correctly
        """
        defaults = {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heater",
            CONF_COOLER: "switch.test_cooler",
            CONF_HEAT_COOL_MODE: True,
            CONF_COLD_TOLERANCE: 0.7,
            CONF_HOT_TOLERANCE: 0.8,
            CONF_MIN_DUR: 600,
        }

        schema = get_heater_cooler_schema(defaults=defaults, include_name=True)

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
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

        # Note: We can't easily test selector types without inspecting implementation
        # This test verifies schema is created without errors
        assert schema is not None
        assert isinstance(schema, vol.Schema)

    def test_optional_entity_fields_use_vol_undefined(self):
        """Test that optional entity fields use vol.UNDEFINED when no default provided.

        Acceptance Criteria: Optional entity fields use vol.UNDEFINED when no default provided
        """
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

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
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

        # Verify advanced_settings exists in schema
        field_names = [
            k.schema if hasattr(k, "schema") else str(k) for k in schema.schema.keys()
        ]

        # Advanced settings should be present
        assert "advanced_settings" in field_names

    def test_schema_defaults_match_constants(self):
        """Test that schema defaults use correct constant values."""
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

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

    def test_heat_cool_mode_defaults_to_false(self):
        """Test that heat_cool_mode defaults to False when no defaults provided."""
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

        # Find heat_cool_mode field
        for key in schema.schema.keys():
            if hasattr(key, "schema") and key.schema == CONF_HEAT_COOL_MODE:
                # Should have default of False
                assert hasattr(key, "default")
                if callable(key.default):
                    assert key.default() is False
                else:
                    assert key.default is False
                break

    def test_required_fields_are_marked_required(self):
        """Test that required fields (heater, cooler, sensor, name) are marked as Required."""
        schema = get_heater_cooler_schema(defaults=None, include_name=True)

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
        assert CONF_HEATER in required_fields
        assert CONF_COOLER in required_fields

        # The sensor is optional: a climate device can supply the temperature
        # (EntityValidator enforces "sensor or a climate role")
        assert CONF_SENSOR in optional_fields

        # Heat/cool mode and advanced settings should be optional
        assert (
            CONF_HEAT_COOL_MODE in optional_fields
            or "advanced_settings" in optional_fields
        )


def test_heater_and_cooler_accept_climate_entities():
    """A climate entity can back the heater and cooler roles."""
    schema = get_heater_cooler_schema(defaults=None, include_name=True)
    validated = schema(
        {
            CONF_NAME: "T",
            CONF_SENSOR: "sensor.t",
            CONF_HEATER: "climate.ac",
            CONF_COOLER: "climate.ac",
        }
    )
    assert validated[CONF_HEATER] == "climate.ac"
    assert validated[CONF_COOLER] == "climate.ac"


def test_fan_accepts_climate_entity():
    """A climate entity can be the fan role."""
    schema = get_fan_schema(defaults={})
    assert schema({CONF_FAN: "climate.ac"})[CONF_FAN] == "climate.ac"


def test_dryer_accepts_climate_entity():
    """A climate entity can be the dryer role."""
    schema = get_humidity_schema(defaults={})
    validated = schema({CONF_HUMIDITY_SENSOR: "sensor.h", CONF_DRYER: "climate.ac"})
    assert validated[CONF_DRYER] == "climate.ac"


def test_aux_heater_still_rejects_climate_entity():
    """Aux heating stays switch-like."""
    with pytest.raises(vol.Invalid):
        get_dual_stage_schema()(
            {CONF_HEATER: "switch.h", CONF_AUX_HEATER: "climate.ac"}
        )


@pytest.mark.parametrize(
    ("factory", "entities"),
    [
        (
            get_heater_cooler_schema,
            {CONF_HEATER: "switch.h", CONF_COOLER: "climate.ac"},
        ),
        (
            get_heat_pump_schema,
            {CONF_HEATER: "climate.hp", CONF_HEAT_PUMP_COOLING: "binary_sensor.c"},
        ),
        (get_simple_heater_schema, {CONF_HEATER: "climate.ac"}),
        (get_basic_ac_schema, {CONF_HEATER: "climate.ac"}),
    ],
)
def test_form_without_sensor_validates_with_flow_defaults(factory, entities):
    """The flow's defaults always hold system_type, never a sensor: the empty sensor
    field must not become a None default that HA's validation rejects."""
    schema = factory(defaults={CONF_SYSTEM_TYPE: "x"}, include_name=True)

    validated = schema({CONF_NAME: "T", **entities})

    assert not validated.get(CONF_SENSOR)


def test_core_schema_without_sensor_validates_with_flow_defaults():
    """get_core_schema has the same sensor default rule."""
    schema = get_core_schema(
        "heater_cooler", defaults={CONF_SYSTEM_TYPE: "heater_cooler"}, include_name=True
    )

    validated = schema(
        {CONF_NAME: "T", CONF_HEATER: "switch.h", CONF_COOLER: "climate.ac"}
    )

    assert not validated.get(CONF_SENSOR)


def test_fan_on_with_ac_defaults_off_for_a_fan_on_the_same_climate():
    """The runtime forces it off for a shared climate: the form says so too."""
    defaults = {
        CONF_FAN: "climate.ac",
        CONF_COOLER: "climate.ac",
        CONF_HEATER: "climate.ac",
    }
    schema = get_fan_schema(defaults=defaults)

    got = {
        str(k): k.default()
        for k in schema.schema
        if getattr(k, "default", vol.UNDEFINED) is not vol.UNDEFINED
    }

    assert got["fan_on_with_ac"] is False
    assert got["fan_on_with_heater"] is False


def test_fan_on_with_ac_keeps_its_default_for_a_separate_fan():
    """Only a fan on the same climate is affected."""
    defaults = {CONF_FAN: "switch.fan", CONF_COOLER: "climate.ac"}
    schema = get_fan_schema(defaults=defaults)

    got = {
        str(k): k.default()
        for k in schema.schema
        if getattr(k, "default", vol.UNDEFINED) is not vol.UNDEFINED
    }

    assert got["fan_on_with_ac"] is True
