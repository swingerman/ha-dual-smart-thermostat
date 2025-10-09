"""Test for openings scope/timeout bug fix.

Bug Report: In config flow, when configuring openings with a specific scope
(e.g., "heat") and timeout, these values were not being saved to collected_config.

Root Cause: feature_steps/openings.py async_step_config() was not calling
collected_config.update(user_input) before processing the openings list.

Fix: Added collected_config.update(user_input) at line 120 to ensure all
user input fields (opening_scope, timeout_openings_open) are saved.
"""

from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_HEATER,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.mark.asyncio
async def test_openings_scope_and_timeout_saved_to_config(hass):
    """Test that opening_scope and timeout_openings_open are saved to config.

    Bug: These values were being lost because async_step_config didn't
    update collected_config with user_input before processing.

    Expected: opening_scope="heat" and timeout_openings_open=300 should
    both be present in the final config.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    # Start config flow
    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    # Enable openings
    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    # Select openings
    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Configure openings with specific scope and timeout
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "heat",  # This was being lost
            "timeout_openings_open": 300,  # This was being lost
        }
    )

    # Flow should complete
    assert result["type"] == "create_entry"

    created_data = result["data"]

    # BUG FIX VERIFICATION: These should now be saved
    # Note: The form field is "opening_scope" (singular) but after clean_openings_scope
    # it gets normalized to "openings_scope" (plural) if not "all"
    # Actually, looking at the logs, it stays as "opening_scope" in collected_config
    assert (
        "opening_scope" in created_data
    ), "opening_scope should be saved when not 'all'"
    assert created_data["opening_scope"] == "heat"

    # Timeout should also be saved
    assert "timeout_openings_open" in created_data
    assert created_data["timeout_openings_open"] == 300


@pytest.mark.asyncio
async def test_openings_scope_all_is_cleaned(hass):
    """Test that opening_scope='all' is removed (existing behavior).

    The clean_openings_scope function removes scope="all" because
    "all" is the default behavior.
    """
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Configure with scope="all"
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "all",  # This should be removed
            "timeout_openings_open": 300,
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # "all" scope should be cleaned (removed)
    assert (
        "opening_scope" not in created_data
        or created_data.get("opening_scope") != "all"
    )

    # But timeout should still be saved
    assert "timeout_openings_open" in created_data
    assert created_data["timeout_openings_open"] == 300


@pytest.mark.asyncio
async def test_multiple_timeout_values_saved(hass):
    """Test that different timeout values are saved correctly."""
    from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler

    flow = ConfigFlowHandler()
    flow.hass = hass

    result = await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER})

    result = await flow.async_step_basic(
        {
            CONF_NAME: "Test Heater",
            CONF_SENSOR: "sensor.temperature",
            CONF_HEATER: "switch.heater",
        }
    )

    result = await flow.async_step_features(
        {
            "configure_floor_heating": False,
            "configure_openings": True,
            "configure_presets": False,
        }
    )

    result = await flow.async_step_openings_selection(
        {"selected_openings": ["binary_sensor.window_1"]}
    )

    # Test with a different timeout value
    result = await flow.async_step_openings_config(
        {
            "opening_scope": "heat",
            "timeout_openings_open": 600,  # 10 minutes
        }
    )

    assert result["type"] == "create_entry"

    created_data = result["data"]

    # Verify the specific timeout value is saved
    assert created_data["timeout_openings_open"] == 600
    assert created_data["opening_scope"] == "heat"
