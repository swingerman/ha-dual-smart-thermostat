#!/usr/bin/env python3
"""End-to-end tests for simple heater reconfigure flow.

These tests verify that the simple heater reconfigure flow goes through
all the same steps as the config flow.
"""

from unittest.mock import Mock, PropertyMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def simple_heater_entry():
    """Create a mock config entry for simple heater system."""
    entry = Mock()
    entry.entry_id = "test_simple_heater"
    entry.data = {
        CONF_NAME: "Simple Heater",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.temperature",
    }
    return entry


async def test_reconfigure_simple_heater_minimal_flow(simple_heater_entry):
    """Test simple heater reconfigure with minimal configuration (no features)."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Step 1: Start reconfigure
        result = await flow.async_step_reconfigure()
        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure_confirm"
        steps_visited.append("reconfigure_confirm")

        # Step 2: Confirm system type (keep simple_heater)
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "basic"
        steps_visited.append("basic")

        # Step 3: Basic configuration
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Simple Heater",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        assert result["type"] == "form"
        assert result["step_id"] == "features"
        steps_visited.append("features")

        # Step 4: Features (don't enable any)
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should finish (reconfigure uses abort)
        assert result["type"] == "abort"
        steps_visited.append("finish")

    print(f"Steps visited: {steps_visited}")
    assert steps_visited == ["reconfigure_confirm", "basic", "features", "finish"]


async def test_reconfigure_simple_heater_with_floor_heating(simple_heater_entry):
    """Test simple heater reconfigure with floor heating enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        steps_visited.append("basic")

        # Basic configuration
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Simple Heater",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable floor heating
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to floor config
        assert result["type"] == "form"
        assert result["step_id"] == "floor_config"
        steps_visited.append("floor_config")

        # Configure floor heating
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temp",
                CONF_MAX_FLOOR_TEMP: 28,
                CONF_MIN_FLOOR_TEMP: 5,
            }
        )

        # Should finish
        assert result["type"] == "abort"
        steps_visited.append("finish")

    print(f"Steps visited: {steps_visited}")
    assert "floor_config" in steps_visited


async def test_reconfigure_simple_heater_with_openings(simple_heater_entry):
    """Test simple heater reconfigure with openings enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        steps_visited.append("basic")

        # Basic configuration
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Simple Heater",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable openings
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": True,
                "configure_presets": False,
            }
        )

        # Should go to openings selection
        assert result["type"] == "form"
        assert result["step_id"] == "openings_selection"
        steps_visited.append("openings_selection")

        # Select openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window", "binary_sensor.door"]}
        )

        # Should go to openings config
        assert result["type"] == "form"
        assert result["step_id"] == "openings_config"
        steps_visited.append("openings_config")

    print(f"Steps visited: {steps_visited}")
    assert "openings_selection" in steps_visited
    assert "openings_config" in steps_visited


async def test_reconfigure_simple_heater_with_presets(simple_heater_entry):
    """Test simple heater reconfigure with presets enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        steps_visited.append("basic")

        # Basic configuration
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Simple Heater",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable presets
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_openings": False,
                "configure_presets": True,
            }
        )

        # Should go to preset selection
        assert result["type"] == "form"
        assert result["step_id"] == "preset_selection"
        steps_visited.append("preset_selection")

        # Select presets
        result = await flow.async_step_preset_selection(
            {"presets": [{"value": "away"}, {"value": "eco"}]}
        )

        # Should go to presets config
        assert result["type"] == "form"
        assert result["step_id"] == "presets"
        steps_visited.append("presets")

    print(f"Steps visited: {steps_visited}")
    assert "preset_selection" in steps_visited
    assert "presets" in steps_visited


async def test_reconfigure_simple_heater_all_features(simple_heater_entry):
    """Test simple heater reconfigure with ALL features enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}
        )
        steps_visited.append("basic")

        # Basic configuration
        result = await flow.async_step_basic(
            {
                CONF_NAME: "Simple Heater",
                CONF_HEATER: "switch.heater",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable ALL features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Should go to floor config
        assert result["type"] == "form"
        assert result["step_id"] == "floor_config"
        steps_visited.append("floor_config")

        # Configure floor heating
        result = await flow.async_step_floor_config(
            {
                CONF_FLOOR_SENSOR: "sensor.floor_temp",
                CONF_MAX_FLOOR_TEMP: 28,
                CONF_MIN_FLOOR_TEMP: 5,
            }
        )

        # Should go to openings selection
        assert result["type"] == "form"
        assert result["step_id"] == "openings_selection"
        steps_visited.append("openings_selection")

        # Select openings
        result = await flow.async_step_openings_selection(
            {"selected_openings": ["binary_sensor.window"]}
        )

        # Should go to openings config
        assert result["type"] == "form"
        assert result["step_id"] == "openings_config"
        steps_visited.append("openings_config")

        # Configure openings
        result = await flow.async_step_openings_config(
            {"binary_sensor.window": {"timeout_open": 30, "timeout_close": 30}}
        )

        # Should go to preset selection
        assert result["type"] == "form"
        assert result["step_id"] == "preset_selection"
        steps_visited.append("preset_selection")

        # Select presets
        result = await flow.async_step_preset_selection(
            {"presets": [{"value": "away"}, {"value": "eco"}]}
        )

        # Should go to presets config
        assert result["type"] == "form"
        assert result["step_id"] == "presets"
        steps_visited.append("presets")

    print(f"Steps visited: {steps_visited}")

    # Verify all expected steps
    expected_steps = [
        "reconfigure_confirm",
        "basic",
        "features",
        "floor_config",
        "openings_selection",
        "openings_config",
        "preset_selection",
        "presets",
    ]
    for step in expected_steps:
        assert step in steps_visited, f"Missing step: {step}"


async def test_reconfigure_simple_heater_preserves_data(simple_heater_entry):
    """Test that reconfigure preserves existing configuration data."""
    # Add existing features to entry
    simple_heater_entry.data.update(
        {
            CONF_FLOOR_SENSOR: "sensor.floor_temp",
            CONF_MAX_FLOOR_TEMP: 28,
            "openings": ["binary_sensor.window"],
        }
    )

    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=simple_heater_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Verify existing config was loaded
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_MAX_FLOOR_TEMP] == 28
        assert "binary_sensor.window" in flow.collected_config["openings"]
        assert flow.collected_config[CONF_NAME] == "Simple Heater"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
