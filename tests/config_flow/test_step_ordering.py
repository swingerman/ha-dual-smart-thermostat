"""Test configuration step ordering to ensure openings configuration has all necessary data."""

from unittest.mock import Mock

import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_FAN,
    CONF_HEAT_COOL_MODE,
    CONF_HUMIDITY_SENSOR,
    CONF_SYSTEM_TYPE,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


class TestConfigStepOrdering:
    """Test that configuration steps are ordered correctly."""

    @pytest.mark.asyncio
    async def test_ac_only_system_step_ordering(self):
        """Test that AC-only system shows feature config before openings."""
        flow = ConfigFlowHandler()
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY,
            "heater": "switch.ac",
            "ac_mode": True,
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
        }

        # Mock the step methods to track call order
        called_steps = []

        async def mock_ac_only_features():
            called_steps.append("features")
            flow.collected_config.update(
                {
                    "configure_fan": True,
                    "configure_humidity": True,
                    "configure_openings": True,
                    "features_shown": True,
                }
            )
            return {"type": "form", "step_id": "features"}

        async def mock_fan():
            called_steps.append("fan")
            flow.collected_config[CONF_FAN] = "switch.fan"
            return {"type": "form", "step_id": "fan"}

        async def mock_humidity():
            called_steps.append("humidity")
            flow.collected_config[CONF_HUMIDITY_SENSOR] = "sensor.humidity"
            return {"type": "form", "step_id": "humidity"}

        async def mock_openings_selection():
            called_steps.append("openings_selection")
            flow.collected_config["selected_openings"] = ["binary_sensor.door"]
            return {"type": "form", "step_id": "openings_selection"}

        async def mock_preset_selection():
            called_steps.append("preset_selection")
            return {"type": "form", "step_id": "preset_selection"}

        flow.async_step_features = mock_ac_only_features
        flow.async_step_fan = mock_fan
        flow.async_step_humidity = mock_humidity
        flow.async_step_openings_selection = mock_openings_selection
        flow.async_step_preset_selection = mock_preset_selection

        # Simulate the flow progression
        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "features"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "fan"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "humidity"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "openings_selection"

        # Verify the order is correct
        expected_order = ["features", "fan", "humidity", "openings_selection"]
        assert called_steps == expected_order

    @pytest.mark.asyncio
    async def test_heat_pump_system_step_ordering(self):
        """Test that heat pump system shows all feature config before openings."""
        flow = ConfigFlowHandler()
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP,
            "heater": "switch.heat_pump",
            "heat_pump_cooling": "sensor.heat_pump_mode",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            # Add floor sensor to skip floor heating config
            "floor_sensor": "sensor.floor_temp",
        }

        # Mock the step methods to track call order
        called_steps = []

        async def mock_system_features():
            called_steps.append("features")
            flow.collected_config.update(
                {
                    "configure_fan": True,
                    "configure_humidity": True,
                    "configure_openings": True,
                    "features_shown": True,
                }
            )
            return {"type": "form", "step_id": "features"}

        async def mock_fan_toggle():
            called_steps.append("fan_toggle")
            flow.collected_config.update(
                {
                    "configure_fan": True,
                    "fan_toggle_shown": True,
                }
            )
            return {"type": "form", "step_id": "fan_toggle"}

        async def mock_humidity_toggle():
            called_steps.append("humidity_toggle")
            flow.collected_config.update(
                {
                    "configure_humidity": True,
                    "humidity_toggle_shown": True,
                }
            )
            return {"type": "form", "step_id": "humidity_toggle"}

        async def mock_heat_cool_mode():
            called_steps.append("heat_cool_mode")
            flow.collected_config[CONF_HEAT_COOL_MODE] = True
            return {"type": "form", "step_id": "heat_cool_mode"}

        async def mock_openings_toggle():
            called_steps.append("openings_toggle")
            flow.collected_config.update(
                {
                    "enable_openings": True,
                    "openings_toggle_shown": True,
                }
            )
            return {"type": "form", "step_id": "openings_toggle"}

        async def mock_openings_selection():
            called_steps.append("openings_selection")
            flow.collected_config["selected_openings"] = ["binary_sensor.door"]
            return {"type": "form", "step_id": "openings_selection"}

        async def mock_preset_selection():
            called_steps.append("preset_selection")
            return {"type": "form", "step_id": "preset_selection"}

        flow.async_step_features = mock_system_features
        flow.async_step_fan_toggle = mock_fan_toggle
        flow.async_step_humidity_toggle = mock_humidity_toggle
        flow.async_step_heat_cool_mode = mock_heat_cool_mode
        flow.async_step_openings_toggle = mock_openings_toggle
        flow.async_step_openings_selection = mock_openings_selection
        flow.async_step_preset_selection = mock_preset_selection

        # Mock the helper methods
        flow._has_both_heating_and_cooling = Mock(return_value=True)

        # Simulate the flow progression
        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "features"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "fan_toggle"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "humidity_toggle"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "heat_cool_mode"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "openings_toggle"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "openings_selection"

        # Verify the order is correct - openings comes AFTER all feature configuration
        expected_order = [
            "features",
            "fan_toggle",
            "humidity_toggle",
            "heat_cool_mode",
            "openings_toggle",
            "openings_selection",
        ]
        assert called_steps == expected_order

    @pytest.mark.asyncio
    async def test_openings_scope_has_all_feature_data(self):
        """Test that openings configuration has access to all configured features."""
        flow = ConfigFlowHandler()

        # Simulate a fully configured dual system with all features
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER,
            "heater": "switch.heater",
            "cooler": "switch.cooler",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
            # All feature configuration completed
            CONF_FAN: "switch.fan",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            CONF_HEAT_COOL_MODE: True,
            "dryer": "switch.dryer",
            "selected_openings": ["binary_sensor.door"],
        }

        # Call the openings configuration step
        result = await flow.openings_steps.async_step_config(
            flow, None, flow.collected_config, lambda: None
        )

        # Verify that the schema includes all expected scope options
        schema_dict = result["data_schema"].schema
        scope_field = None
        for key, value in schema_dict.items():
            if hasattr(key, "key") and key.key == "openings_scope":
                scope_field = value
                break
            elif hasattr(key, "schema") and "openings_scope" in str(key.schema):
                scope_field = value
                break

        assert scope_field is not None, "openings_scope field not found in schema"

        scope_options = scope_field.config.get("options", [])
        # With new translation format, scope_options is now a list of strings
        option_values = (
            scope_options
            if scope_options and isinstance(scope_options[0], str)
            else [opt["value"] for opt in scope_options]
        )

        # Should have all options because all features are configured
        expected_options = ["all", "heat", "cool", "heat_cool", "fan_only", "dry"]
        for expected in expected_options:
            assert (
                expected in option_values
            ), f"Expected scope option '{expected}' not found"

    @pytest.mark.asyncio
    async def test_simple_heater_openings_after_features(self):
        """Test that simple heater shows openings after feature configuration."""
        flow = ConfigFlowHandler()
        flow.collected_config = {
            CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER,
            "heater": "switch.heater",
            "sensor": "sensor.temp",
            "name": "Test Thermostat",
        }

        # Mock the step methods to track call order
        called_steps = []

        async def mock_simple_heater_features():
            called_steps.append("features")
            flow.collected_config.update(
                {
                    "configure_openings": True,
                    "configure_presets": True,
                    "features_shown": True,
                }
            )
            return {"type": "form", "step_id": "features"}

        async def mock_openings_selection():
            called_steps.append("openings_selection")
            flow.collected_config["selected_openings"] = ["binary_sensor.door"]
            return {"type": "form", "step_id": "openings_selection"}

        async def mock_preset_selection():
            called_steps.append("preset_selection")
            return {"type": "form", "step_id": "preset_selection"}

        flow.async_step_features = mock_simple_heater_features
        flow.async_step_openings_selection = mock_openings_selection
        flow.async_step_preset_selection = mock_preset_selection

        # Simulate the flow progression
        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "features"

        step_result = await flow._determine_next_step()
        assert step_result["step_id"] == "openings_selection"

        # Verify the order is correct
        expected_order = ["features", "openings_selection"]
        assert called_steps == expected_order


if __name__ == "__main__":
    pytest.main([__file__])
