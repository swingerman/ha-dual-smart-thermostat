"""Integration tests for config and options flow functionality.

This module contains integration tests that verify the complete behavior
of config and options flows, particularly focusing on:

1. Options Flow - Openings Management:
   - Schema creation with current values
   - Data processing and transformation
   - Removal of openings configuration

2. Transient Flags Handling:
   - Verification that transient flags (features_shown, configure_*, etc.)
     are properly filtered from saved configuration
   - Testing with real Home Assistant config entries
   - Both config flow and options flow scenarios

These tests use a mix of mock fixtures for isolated testing and real
Home Assistant fixtures for runtime behavior validation.
"""

from unittest.mock import AsyncMock, Mock, patch

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResult
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.dual_smart_thermostat.const import (
    ATTR_CLOSING_TIMEOUT,
    ATTR_OPENING_TIMEOUT,
    CONF_COOLER,
    CONF_FAN,
    CONF_HEATER,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_HEATER_COOLER,
)
from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def hass_mock():
    """Create a mock hass instance for isolated testing."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_update_entry = AsyncMock()
    return hass


@pytest.fixture
def config_entry_with_openings():
    """Create a mock config entry with existing openings configuration."""
    config_entry = Mock()
    config_entry.data = {
        "name": "Test Thermostat",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_OPENINGS: [
            {"entity_id": "binary_sensor.door", ATTR_OPENING_TIMEOUT: {"seconds": 30}},
            "binary_sensor.window",
        ],
        CONF_OPENINGS_SCOPE: ["heat", "cool"],
    }
    config_entry.options = {}
    config_entry.entry_id = "test_entry"
    return config_entry


# =============================================================================
# OPTIONS FLOW - OPENINGS MANAGEMENT TESTS
# =============================================================================


async def test_options_flow_openings_schema_creation(
    hass_mock, config_entry_with_openings
):
    """Test that openings options creates proper schema with current values."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass_mock
    options_handler.collected_config = {}

    # Mock the flow show form method to capture the schema
    with patch.object(options_handler, "async_show_form") as mock_show_form:
        mock_show_form.return_value = Mock()

        # Call openings options step
        await options_handler.async_step_openings_options()

        # Verify show_form was called
        assert mock_show_form.called
    call_args = mock_show_form.call_args

    # Check that step_id is correct
    assert call_args[1]["step_id"] == "openings_options"

    # Check that schema includes expected fields
    schema = call_args[1]["data_schema"]
    assert schema is not None

    print("Options flow creates proper openings schema")


async def test_options_flow_openings_data_processing(
    hass_mock, config_entry_with_openings
):
    """Test that openings options processes user input correctly."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass_mock
    options_handler.collected_config = {}

    # Mock _determine_options_next_step to return a mock result
    mock_result = FlowResult()
    mock_result["type"] = "form"

    with patch.object(
        options_handler, "_determine_options_next_step"
    ) as mock_next_step:
        mock_next_step.return_value = mock_result

        # Test user input with modified openings
        user_input = {
            "selected_openings": ["binary_sensor.door", "binary_sensor.new_window"],
            CONF_OPENINGS_SCOPE: ["heat"],
            "binary_sensor.door_opening_timeout": {"seconds": 45},
            "binary_sensor.new_window_closing_timeout": {"seconds": 15},
        }

        # Call openings options with user input
        await options_handler.async_step_openings_options(user_input)

        # Verify that _determine_options_next_step was called
        assert mock_next_step.called

        # Check that collected_config has the correct data
        assert "selected_openings" in options_handler.collected_config
        assert options_handler.collected_config["selected_openings"] == [
            "binary_sensor.door",
            "binary_sensor.new_window",
        ]
        assert options_handler.collected_config[CONF_OPENINGS_SCOPE] == ["heat"]

        # Check that openings list was properly formed
        openings_list = options_handler.collected_config[CONF_OPENINGS]
        assert len(openings_list) == 2

        # Find the door entry
        door_entry = next(
            (o for o in openings_list if o.get("entity_id") == "binary_sensor.door"),
            None,
        )
        assert door_entry is not None
        assert door_entry[ATTR_OPENING_TIMEOUT] == {"seconds": 45}

        # Find the window entry
        window_entry = next(
            (
                o
                for o in openings_list
                if o.get("entity_id") == "binary_sensor.new_window"
            ),
            None,
        )
        assert window_entry is not None
        assert window_entry[ATTR_CLOSING_TIMEOUT] == {"seconds": 15}

        # simple confirmation log
        print("Options flow processes openings user input correctly")


async def test_options_flow_openings_removal(hass_mock, config_entry_with_openings):
    """Test that openings can be completely removed via options flow."""
    # Create options flow handler
    options_handler = OptionsFlowHandler(config_entry_with_openings)
    options_handler.hass = hass_mock
    options_handler.collected_config = {}

    mock_result = FlowResult()
    mock_result["type"] = "form"

    with patch.object(
        options_handler, "_determine_options_next_step"
    ) as mock_next_step:
        mock_next_step.return_value = mock_result

        # Test user input with no selected openings (removal)
        user_input = {
            "selected_openings": [],  # Empty selection removes openings
        }

        # Call openings options with user input
        await options_handler.async_step_openings_options(user_input)

        # Verify that openings configuration was removed
        assert CONF_OPENINGS not in options_handler.collected_config
        assert CONF_OPENINGS_SCOPE not in options_handler.collected_config

        # simple confirmation log
        print("Options flow can remove openings configuration")


# =============================================================================
# TRANSIENT FLAGS HANDLING TESTS (Real Home Assistant Fixtures)
# =============================================================================


@pytest.mark.asyncio
async def test_options_flow_with_real_config_entry(hass):
    """Test that options flow works correctly with real ConfigEntry and transient flags.

    This test verifies that transient flags in storage are properly filtered out
    and don't affect the options flow. The simplified options flow shows runtime
    tuning parameters in init, then proceeds through feature option steps.
    """
    # Create a config entry with transient flags (simulating contaminated storage)
    config_data = {
        CONF_NAME: "Test HC",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_SENSOR: "sensor.room_temp",
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_FAN: "switch.fan",
        # These transient flags should NOT affect the options flow
        "features_shown": True,
        "configure_fan": True,
        "fan_options_shown": True,
    }

    entry = MockConfigEntry(
        domain=DOMAIN,
        data=config_data,
        title="Test HC",
    )
    entry.add_to_hass(hass)

    # Open the options flow using the correct Home Assistant API
    from custom_components.dual_smart_thermostat.options_flow import OptionsFlowHandler

    flow = OptionsFlowHandler(entry)
    flow.hass = hass

    # Simplified options flow shows runtime tuning parameters in init step
    result = await flow.async_step_init()

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    # Submit with runtime parameter changes
    result2 = await flow.async_step_init(
        user_input={"cold_tolerance": 0.5, "hot_tolerance": 0.5},
    )

    # Since fan is configured, should proceed to fan_options step
    assert result2["type"] == "form"
    assert result2["step_id"] == "fan_options"

    # Complete fan options step
    result3 = await flow.async_step_fan_options({})

    # Should now complete since no other features are configured
    assert result3["type"] == "create_entry"

    # Verify transient flags were filtered out from final data
    final_data = result3["data"]
    print(f"DEBUG: final_data keys = {list(final_data.keys())}")
    print(f"DEBUG: has features_shown = {'features_shown' in final_data}")
    print(f"DEBUG: has configure_fan = {'configure_fan' in final_data}")
    print(f"DEBUG: has fan_options_shown = {'fan_options_shown' in final_data}")

    assert (
        "features_shown" not in final_data
    ), f"features_shown still in data! Keys: {list(final_data.keys())}"
    assert (
        "configure_fan" not in final_data
    ), f"configure_fan still in data! Keys: {list(final_data.keys())}"
    assert (
        "fan_options_shown" not in final_data
    ), f"fan_options_shown still in data! Keys: {list(final_data.keys())}"

    # Verify real config is preserved
    assert final_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert final_data[CONF_HEATER] == "switch.heater"
    assert final_data[CONF_COOLER] == "switch.cooler"
    assert final_data[CONF_FAN] == "switch.fan"


@pytest.mark.asyncio
async def test_config_flow_does_not_save_transient_flags(hass):
    """Test that ConfigFlow strips transient flags before saving."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    # Start the config flow
    result = await flow.async_step_user(
        user_input={CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
    )

    # Fill in basic config
    result = await flow.async_step_heater_cooler(
        {
            CONF_NAME: "Test",
            CONF_SENSOR: "sensor.temp",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        }
    )

    # Skip features
    result = await flow.async_step_features({})

    # Should complete
    assert result["type"] == "create_entry"

    # Check that the saved data does NOT contain transient flags
    saved_data = result["data"]
    assert "features_shown" not in saved_data, "features_shown should not be saved!"
    assert "configure_fan" not in saved_data, "configure_fan should not be saved!"
    assert (
        "fan_options_shown" not in saved_data
    ), "fan_options_shown should not be saved!"
    assert (
        "system_type_changed" not in saved_data
    ), "system_type_changed should not be saved!"

    # But it should have the real config
    assert saved_data[CONF_SYSTEM_TYPE] == SYSTEM_TYPE_HEATER_COOLER
    assert saved_data[CONF_HEATER] == "switch.heater"
    assert saved_data[CONF_COOLER] == "switch.cooler"


# =============================================================================
# STANDALONE TEST RUNNER (for manual testing)
# =============================================================================


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        from unittest.mock import Mock

        # Create mock objects
        hass = Mock()
        hass.config_entries = Mock()
        hass.config_entries.async_update_entry = AsyncMock()

        config_entry = Mock()
        config_entry.data = {
            "name": "Test Thermostat",
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_OPENINGS: [
                {
                    "entity_id": "binary_sensor.door",
                    ATTR_OPENING_TIMEOUT: {"seconds": 30},
                },
                "binary_sensor.window",
            ],
            CONF_OPENINGS_SCOPE: ["heat", "cool"],
        }
        config_entry.entry_id = "test_entry"

        await test_options_flow_openings_schema_creation(hass, config_entry)
        await test_options_flow_openings_data_processing(hass, config_entry)
        await test_options_flow_openings_removal(hass, config_entry)

        print("All options flow integration tests passed!")

    asyncio.run(run_tests())
