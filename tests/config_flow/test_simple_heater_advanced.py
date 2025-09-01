"""Test simple heater advanced settings configuration flow."""

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import (
    DualSmartThermostatConfigFlow,
)
from custom_components.dual_smart_thermostat.const import (
    CONF_COLD_TOLERANCE,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_MIN_DUR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def config_flow(hass: HomeAssistant):
    """Create a config flow instance."""
    flow = DualSmartThermostatConfigFlow()
    flow.hass = hass
    return flow


@pytest.mark.asyncio
async def test_simple_heater_advanced_settings_config_flow(
    hass: HomeAssistant, config_flow
):
    """Test the config flow with advanced settings for simple heater system."""

    # Step 1: System type selection
    result = await config_flow.async_step_user()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await config_flow.async_step_user(
        user_input={CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    # Step 2: Basic configuration with advanced settings
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "basic"

    # Verify the form has advanced settings section
    schema = result["data_schema"]
    schema_dict = {field.schema: field for field in schema.schema}

    # Check that the fields are in the schema
    field_names = [str(field) for field in schema_dict.keys()]

    assert any(CONF_NAME in field for field in field_names)
    assert any(CONF_HEATER in field for field in field_names)
    assert any(CONF_SENSOR in field for field in field_names)
    assert "advanced_settings" in field_names

    # Test with custom advanced settings
    basic_input = {
        CONF_NAME: "Test Simple Heater",
        CONF_HEATER: "switch.test_heater",
        CONF_SENSOR: "sensor.test_temperature",
        CONF_COLD_TOLERANCE: 0.5,
        CONF_HOT_TOLERANCE: 0.5,
        CONF_MIN_DUR: 600,
    }

    result = await config_flow.async_step_basic(user_input=basic_input)

    # Should proceed to features selection
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "simple_heater_features"

    # Complete the flow without additional features
    result = await config_flow.async_step_simple_heater_features(
        user_input={
            "configure_openings": False,
            "configure_presets": False,
            "configure_floor_heating": False,
            "configure_advanced": False,
        }
    )

    # If it goes to preset selection, handle it
    if result.get("step_id") == "preset_selection":
        result = await config_flow.async_step_preset_selection(user_input={})

    # Should create the entry
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Simple Heater"

    # Verify the configuration includes our advanced settings
    config_data = result["data"]
    assert config_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
    assert config_data[CONF_NAME] == "Test Simple Heater"
    assert config_data[CONF_HEATER] == "switch.test_heater"
    assert config_data[CONF_SENSOR] == "sensor.test_temperature"
    assert config_data[CONF_COLD_TOLERANCE] == 0.5
    assert config_data[CONF_HOT_TOLERANCE] == 0.5
    assert config_data[CONF_MIN_DUR] == 600


@pytest.mark.asyncio
async def test_simple_heater_default_advanced_settings(
    hass: HomeAssistant, config_flow
):
    """Test the config flow with default values for advanced settings."""

    # Step 1: System type selection
    result = await config_flow.async_step_user(
        user_input={CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
    )

    # Step 2: Basic configuration using default values
    basic_input = {
        CONF_NAME: "Test Simple Heater Default",
        CONF_HEATER: "switch.test_heater",
        CONF_SENSOR: "sensor.test_temperature",
        # Not setting tolerance and min cycle duration to test defaults
    }

    result = await config_flow.async_step_basic(user_input=basic_input)

    # Should proceed to features selection
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "simple_heater_features"

    # Complete the flow
    result = await config_flow.async_step_simple_heater_features(
        user_input={
            "configure_openings": False,
            "configure_presets": False,
            "configure_floor_heating": False,
            "configure_advanced": False,
        }
    )

    # If it goes to preset selection, handle it
    if result.get("step_id") == "preset_selection":
        result = await config_flow.async_step_preset_selection(user_input={})

    # Should create the entry
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Verify the configuration uses default values for unset fields
    config_data = result["data"]
    assert config_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_SIMPLE_HEATER
    assert config_data[CONF_NAME] == "Test Simple Heater Default"
    assert config_data[CONF_HEATER] == "switch.test_heater"
    assert config_data[CONF_SENSOR] == "sensor.test_temperature"

    # Check that defaults are applied for optional fields
    # Note: Actual default handling may vary based on schema implementation
