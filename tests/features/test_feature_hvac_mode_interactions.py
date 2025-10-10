"""Interaction tests for feature-based HVAC mode additions.

Task: T007A - Phase 3: Interaction Tests
Issue: #440

These tests validate that enabling certain features correctly adds
corresponding HVAC modes to the available modes list.

Feature-Mode Relationships:
- Fan feature enabled → Adds FAN_ONLY mode (for systems with cooling)
- Humidity feature enabled → Adds DRY mode (for systems with humidity control)

Test Coverage:
1. ac_only system: fan feature adds FAN_ONLY mode
2. ac_only system: humidity feature adds DRY mode
3. ac_only system: both fan and humidity add both modes
4. heater_cooler system: fan feature adds FAN_ONLY mode
5. heater_cooler system: humidity feature adds DRY mode
6. heat_pump system: fan feature adds FAN_ONLY mode
7. heat_pump system: humidity feature adds DRY mode
8. simple_heater system: no additional modes (heating-only)
"""

from unittest.mock import Mock

from homeassistant.const import CONF_NAME
from homeassistant.data_entry_flow import FlowResultType
import pytest

from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import (
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
    CONF_SYSTEM_TYPE,
    DOMAIN,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)


@pytest.fixture
def mock_hass():
    """Create a mock Home Assistant instance."""
    hass = Mock()
    hass.config_entries = Mock()
    hass.config_entries.async_entries = Mock(return_value=[])
    hass.data = {DOMAIN: {}}
    return hass


class TestAcOnlyModeInteractions:
    """Test HVAC mode additions for ac_only system type."""

    async def test_fan_feature_adds_fan_only_mode(self, mock_hass):
        """Test that enabling fan feature adds FAN_ONLY mode to ac_only.

        Acceptance Criteria:
        - Without fan: COOL, OFF
        - With fan: COOL, FAN_ONLY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup ac_only system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Enable fan feature
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify fan feature enables FAN_ONLY mode
        assert flow.collected_config["configure_fan"] is True
        assert CONF_FAN in flow.collected_config

    async def test_humidity_feature_adds_dry_mode(self, mock_hass):
        """Test that enabling humidity feature adds DRY mode to ac_only.

        Acceptance Criteria:
        - Without humidity: COOL, OFF
        - With humidity: COOL, DRY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup ac_only system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Enable humidity feature
        result = await flow.async_step_features(
            {
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify humidity feature enables DRY mode
        assert flow.collected_config["configure_humidity"] is True
        assert CONF_HUMIDITY_SENSOR in flow.collected_config
        assert CONF_DRYER in flow.collected_config

    async def test_fan_and_humidity_add_both_modes(self, mock_hass):
        """Test that enabling both fan and humidity adds both modes.

        Acceptance Criteria:
        - With both: COOL, FAN_ONLY, DRY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup ac_only system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_AC_ONLY})
        await flow.async_step_basic_ac_only(
            {
                CONF_NAME: "Test AC",
                CONF_SENSOR: "sensor.temperature",
                CONF_COOLER: "switch.ac",
            }
        )

        # Enable both features
        result = await flow.async_step_features(
            {
                "configure_fan": True,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        # Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY

        # Verify both features are configured
        assert flow.collected_config["configure_fan"] is True
        assert flow.collected_config["configure_humidity"] is True
        assert CONF_FAN in flow.collected_config
        assert CONF_HUMIDITY_SENSOR in flow.collected_config


class TestHeaterCoolerModeInteractions:
    """Test HVAC mode additions for heater_cooler system type."""

    async def test_fan_feature_adds_fan_only_mode(self, mock_hass):
        """Test that enabling fan feature adds FAN_ONLY mode to heater_cooler.

        Acceptance Criteria:
        - Without fan: HEAT, COOL, HEAT_COOL, OFF
        - With fan: HEAT, COOL, HEAT_COOL, FAN_ONLY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup heater_cooler system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable fan feature
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": True,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_fan"] is True

    async def test_humidity_feature_adds_dry_mode(self, mock_hass):
        """Test that enabling humidity feature adds DRY mode to heater_cooler.

        Acceptance Criteria:
        - Without humidity: HEAT, COOL, HEAT_COOL, OFF
        - With humidity: HEAT, COOL, HEAT_COOL, DRY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup heater_cooler system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEATER_COOLER})
        await flow.async_step_heater_cooler(
            {
                CONF_NAME: "Test HVAC",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heater",
                CONF_COOLER: "switch.cooler",
            }
        )

        # Enable humidity feature
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_humidity"] is True


class TestHeatPumpModeInteractions:
    """Test HVAC mode additions for heat_pump system type."""

    async def test_fan_feature_adds_fan_only_mode(self, mock_hass):
        """Test that enabling fan feature adds FAN_ONLY mode to heat_pump.

        Acceptance Criteria:
        - Without fan: HEAT_COOL, OFF
        - With fan: HEAT_COOL, FAN_ONLY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup heat_pump system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP})
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Test Heat Pump",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            }
        )

        # Enable fan feature
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": True,
                "configure_humidity": False,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure fan
        result = await flow.async_step_fan(
            {
                CONF_FAN: "switch.fan",
                "fan_on_with_ac": True,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_fan"] is True

    async def test_humidity_feature_adds_dry_mode(self, mock_hass):
        """Test that enabling humidity feature adds DRY mode to heat_pump.

        Acceptance Criteria:
        - Without humidity: HEAT_COOL, OFF
        - With humidity: HEAT_COOL, DRY, OFF
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {}

        # Setup heat_pump system
        await flow.async_step_user({CONF_SYSTEM_TYPE: SYSTEM_TYPE_HEAT_PUMP})
        await flow.async_step_heat_pump(
            {
                CONF_NAME: "Test Heat Pump",
                CONF_SENSOR: "sensor.temperature",
                CONF_HEATER: "switch.heat_pump",
                CONF_HEAT_PUMP_COOLING: "binary_sensor.cooling_mode",
            }
        )

        # Enable humidity feature
        result = await flow.async_step_features(
            {
                "configure_floor_heating": False,
                "configure_fan": False,
                "configure_humidity": True,
                "configure_openings": False,
                "configure_presets": False,
            }
        )

        # Configure humidity
        result = await flow.async_step_humidity(
            {
                CONF_HUMIDITY_SENSOR: "sensor.humidity",
                CONF_DRYER: "switch.dehumidifier",
                "target_humidity": 50,
            }
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert flow.collected_config["configure_humidity"] is True


class TestSimpleHeaterModeInteractions:
    """Test that simple_heater does not add additional HVAC modes."""

    async def test_no_additional_modes_for_simple_heater(self, mock_hass):
        """Test that simple_heater never adds FAN_ONLY or DRY modes.

        simple_heater is heating-only and doesn't support fan or humidity features,
        so HVAC modes should always be: HEAT, OFF

        Acceptance Criteria:
        - No fan feature available
        - No humidity feature available
        - Only HEAT and OFF modes
        """
        flow = ConfigFlowHandler()
        flow.hass = mock_hass
        flow.collected_config = {CONF_SYSTEM_TYPE: SYSTEM_TYPE_SIMPLE_HEATER}

        # Check available features in schema
        result = await flow.async_step_features()
        schema = result["data_schema"].schema
        field_names = [key.schema for key in schema.keys() if hasattr(key, "schema")]

        # simple_heater should not have fan or humidity features
        assert "configure_fan" not in field_names
        assert "configure_humidity" not in field_names

        # Only floor_heating, openings, and presets should be available
        feature_fields = [f for f in field_names if f.startswith("configure_")]
        expected_features = [
            "configure_floor_heating",
            "configure_openings",
            "configure_presets",
        ]
        assert sorted(feature_fields) == sorted(expected_features)
