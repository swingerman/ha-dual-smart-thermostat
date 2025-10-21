#!/usr/bin/env python3
"""End-to-end tests for heater+cooler reconfigure flow.

These tests verify that the heater+cooler reconfigure flow goes through
all the same steps as the config flow.
"""

from unittest.mock import Mock, PropertyMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_HEATER_COOLER,
)


@pytest.fixture
def heater_cooler_entry():
    """Create a mock config entry for heater+cooler system."""
    entry = Mock()
    entry.entry_id = "test_heater_cooler"
    entry.data = {
        CONF_NAME: "Heater Cooler",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
        CONF_HEATER: "switch.heater",
        CONF_COOLER: "switch.cooler",
        CONF_SENSOR: "sensor.temperature",
    }
    return entry


async def test_reconfigure_heater_cooler_minimal_flow(heater_cooler_entry):
    """Test heater+cooler reconfigure with minimal configuration (no features)."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Step 1: Start reconfigure
        result = await flow.async_step_reconfigure()
        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure_confirm"
        steps_visited.append("reconfigure_confirm")

        # Step 2: Confirm system type (keep heater_cooler)
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "heater_cooler"
        steps_visited.append("heater_cooler")

        # Step 3: Heater+cooler configuration
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Heater Cooler",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
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
                "configure_fan": False,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should finish
        assert result["type"] == "abort"
        steps_visited.append("finish")

    print(f"Steps visited: {steps_visited}")
    assert steps_visited == [
        "reconfigure_confirm",
        "heater_cooler",
        "features",
        "finish",
    ]


async def test_reconfigure_heater_cooler_with_floor_heating(heater_cooler_entry):
    """Test heater+cooler reconfigure with floor heating enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        steps_visited.append("heater_cooler")

        # Heater+cooler configuration
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Heater Cooler",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable floor heating
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": False,
                "configure_humidity": False,
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


async def test_reconfigure_heater_cooler_with_fan(heater_cooler_entry):
    """Test heater+cooler reconfigure with fan enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        steps_visited.append("heater_cooler")

        # Heater+cooler configuration
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Heater Cooler",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable fan
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": True,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to fan config
        assert result["type"] == "form"
        assert result["step_id"] == "fan"
        steps_visited.append("fan")

    print(f"Steps visited: {steps_visited}")
    assert "fan" in steps_visited


async def test_reconfigure_heater_cooler_with_humidity(heater_cooler_entry):
    """Test heater+cooler reconfigure with humidity enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        steps_visited.append("heater_cooler")

        # Heater+cooler configuration
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Heater Cooler",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable humidity
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Should go to humidity config
        assert result["type"] == "form"
        assert result["step_id"] == "humidity"
        steps_visited.append("humidity")

    print(f"Steps visited: {steps_visited}")
    assert "humidity" in steps_visited


async def test_reconfigure_heater_cooler_all_features(heater_cooler_entry):
    """Test heater+cooler reconfigure with ALL features enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER}
        )
        steps_visited.append("heater_cooler")

        # Heater+cooler configuration
        result = await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Heater Cooler",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
                CONF_SENSOR: "sensor.temperature",
            }
        )
        steps_visited.append("features")

        # Enable ALL features
        result = await flow.async_step_features(
            {
                "configure_floor_heating": True,
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": True,
                "configure_presets": True,
            }
        )

        # Should go to floor config first
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

        # Should go to fan
        assert result["type"] == "form"
        assert result["step_id"] == "fan"
        steps_visited.append("fan")

        # Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_mode": False,
            }
        )

        # Should go to humidity
        assert result["type"] == "form"
        assert result["step_id"] == "humidity"
        steps_visited.append("humidity")

        # Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                "target_humidity": 50,
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
            {"presets": [{"value": "away"}]}
        )

        # Should go to presets config
        assert result["type"] == "form"
        assert result["step_id"] == "presets"
        steps_visited.append("presets")

    print(f"Steps visited: {steps_visited}")

    # Verify all expected steps
    expected_steps = [
        "reconfigure_confirm",
        "heater_cooler",
        "features",
        "floor_config",
        "fan",
        "humidity",
        "openings_selection",
        "openings_config",
        "preset_selection",
        "presets",
    ]
    for step in expected_steps:
        assert step in steps_visited, f"Missing step: {step}"


async def test_reconfigure_heater_cooler_preserves_data(heater_cooler_entry):
    """Test that reconfigure preserves existing configuration data."""
    # Add existing features to entry
    heater_cooler_entry.data.update(
        {
            CONF_FLOOR_SENSOR: "sensor.floor_temp",
            CONF_FAN: "switch.fan",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            "openings": ["binary_sensor.window"],
        }
    )

    flow = ConfigFlowHandler()
    flow.hass = Mock()

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heater_cooler_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Verify existing config was loaded
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert "binary_sensor.window" in flow.collected_config["openings"]
        assert flow.collected_config[CONF_NAME] == "Heater Cooler"
        assert flow.collected_config[CONF_HEATER] == "switch.heater"
        assert flow.collected_config[CONF_COOLER] == "switch.cooler"
