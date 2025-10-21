#!/usr/bin/env python3
"""End-to-end tests for heat pump reconfigure flow.

These tests verify that the heat pump reconfigure flow goes through
all the same steps as the config flow.
"""

from unittest.mock import Mock, PropertyMock, patch

from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.const import CONF_NAME
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_FAN,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_MAX_FLOOR_TEMP,
    CONF_MIN_FLOOR_TEMP,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_HEAT_PUMP,
)


@pytest.fixture
def heat_pump_entry():
    """Create a mock config entry for heat pump system."""
    entry = Mock()
    entry.entry_id = "test_heat_pump"
    entry.data = {
        CONF_NAME: "Heat Pump",
        CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
        CONF_HEATER: "switch.heat_pump",
        CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
        CONF_SENSOR: "sensor.temperature",
    }
    return entry


async def test_reconfigure_heat_pump_minimal_flow(heat_pump_entry):
    """Test heat pump reconfigure with minimal configuration (no features)."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Step 1: Start reconfigure
        result = await flow.async_step_reconfigure()
        assert result["type"] == "form"
        assert result["step_id"] == "reconfigure_confirm"
        steps_visited.append("reconfigure_confirm")

        # Step 2: Confirm system type (keep heat_pump)
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        assert result["type"] == "form"
        assert result["step_id"] == "heat_pump"
        steps_visited.append("heat_pump")

        # Step 3: Heat pump configuration
        result = await flow.async_step_heat_pump(
            {
                CONF_NAME: "Heat Pump",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
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
    assert steps_visited == ["reconfigure_confirm", "heat_pump", "features", "finish"]


async def test_reconfigure_heat_pump_with_floor_heating(heat_pump_entry):
    """Test heat pump reconfigure with floor heating enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        steps_visited.append("heat_pump")

        # Heat pump configuration
        result = await flow.async_step_heat_pump(
            {
                CONF_NAME: "Heat Pump",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
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


async def test_reconfigure_heat_pump_with_fan(heat_pump_entry):
    """Test heat pump reconfigure with fan enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        steps_visited.append("heat_pump")

        # Heat pump configuration
        result = await flow.async_step_heat_pump(
            {
                CONF_NAME: "Heat Pump",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
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


async def test_reconfigure_heat_pump_with_humidity(heat_pump_entry):
    """Test heat pump reconfigure with humidity enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        steps_visited.append("heat_pump")

        # Heat pump configuration
        result = await flow.async_step_heat_pump(
            {
                CONF_NAME: "Heat Pump",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
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


async def test_reconfigure_heat_pump_all_features(heat_pump_entry):
    """Test heat pump reconfigure with ALL features enabled."""
    flow = ConfigFlowHandler()
    flow.hass = Mock()

    steps_visited = []

    with patch.object(
        type(flow), "source", new_callable=PropertyMock, return_value=SOURCE_RECONFIGURE
    ):
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Start reconfigure
        result = await flow.async_step_reconfigure()
        steps_visited.append("reconfigure_confirm")

        # Confirm system type
        result = await flow.async_step_reconfigure_confirm(
            {CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP}
        )
        steps_visited.append("heat_pump")

        # Heat pump configuration
        result = await flow.async_step_heat_pump(
            {
                CONF_NAME: "Heat Pump",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
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
        "heat_pump",
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


async def test_reconfigure_heat_pump_preserves_data(heat_pump_entry):
    """Test that reconfigure preserves existing configuration data."""
    # Add existing features to entry
    heat_pump_entry.data.update(
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
        flow._get_reconfigure_entry = Mock(return_value=heat_pump_entry)

        # Start reconfigure
        await flow.async_step_reconfigure()

        # Verify existing config was loaded
        assert flow.collected_config[CONF_FLOOR_SENSOR] == "sensor.floor_temp"
        assert flow.collected_config[CONF_FAN] == "switch.fan"
        assert flow.collected_config[CONF_HUMIDITY_SENSOR] == "sensor.humidity"
        assert "binary_sensor.window" in flow.collected_config["openings"]
        assert flow.collected_config[CONF_NAME] == "Heat Pump"
        assert flow.collected_config[CONF_HEATER] == "switch.heat_pump"
        assert (
            flow.collected_config[CONF_HEAT_PUMP_COOLING]
            == "binary_sensor.cooling_mode"
        )
