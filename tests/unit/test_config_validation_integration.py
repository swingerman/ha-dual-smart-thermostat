"""Tests for config validation integration with config_flow and options_flow."""

from unittest.mock import MagicMock, patch

from homeassistant.const import CONF_NAME
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.climate import PLATFORM_SCHEMA
from custom_components.dual_smart_thermostat.climate_roles import (
    applicable_offset_keys,
    setpoint_unsupported,
)
from custom_components.dual_smart_thermostat.config_flow import ConfigFlowHandler
from custom_components.dual_smart_thermostat.const import CONF_HEATER, CONF_SENSOR


@pytest.fixture
def mock_hass():
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.config_entries = MagicMock()
    return hass


class TestConfigFlowValidation:
    """Test config flow validation using models."""

    @pytest.mark.asyncio
    async def test_config_flow_validates_on_create_entry(self, mock_hass):
        """Test that config flow validates configuration before creating entry."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        # Setup minimal valid configuration
        flow.collected_config = {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heater",
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            mock_validate.return_value = True

            # Simulate finishing preset selection without presets
            await flow.async_step_preset_selection(user_input={})

            # Validation should have been called
            mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_flow_logs_warning_on_invalid_config(self, mock_hass):
        """Test that config flow logs warning when validation fails."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        # Setup invalid configuration (missing required fields)
        flow.collected_config = {
            CONF_NAME: "Test Thermostat",
            # Missing CONF_SENSOR - invalid
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            with patch(
                "custom_components.dual_smart_thermostat.config_flow._LOGGER"
            ) as mock_logger:
                mock_validate.return_value = False

                # Simulate finishing preset selection without presets
                await flow.async_step_preset_selection(user_input={})

                # Validation should have failed and logged warning
                mock_validate.assert_called_once()
                mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_config_flow_import_validates_config(self, mock_hass):
        """Test that config import step validates configuration."""
        flow = ConfigFlowHandler()
        flow.hass = mock_hass

        import_config = {
            CONF_NAME: "Imported Thermostat",
            CONF_SENSOR: "sensor.imported_temp",
            CONF_HEATER: "switch.imported_heater",
            "system_type": "simple_heater",
        }

        with patch(
            "custom_components.dual_smart_thermostat.config_flow.validate_config_with_models"
        ) as mock_validate:
            mock_validate.return_value = True

            await flow.async_step_import(import_config)

            # Validation should have been called
            mock_validate.assert_called_once_with(import_config)


class TestOptionsFlowValidation:
    """Test options flow validation using models."""

    @pytest.mark.asyncio
    async def test_options_flow_validates_config(self):
        """Test that options flow validation is called when needed."""
        # Simple test to verify validate_config_with_models can be called
        from custom_components.dual_smart_thermostat.config_validation import (
            validate_config_with_models,
        )

        valid_config = {
            CONF_NAME: "Test Thermostat",
            CONF_SENSOR: "sensor.test_temp",
            CONF_HEATER: "switch.test_heater",
            "system_type": "simple_heater",
        }

        # Should validate successfully
        assert validate_config_with_models(valid_config) is True

        # Missing required field should fail
        invalid_config = {
            CONF_NAME: "Test Thermostat",
            # Missing CONF_SENSOR
            "system_type": "simple_heater",
        }

        assert validate_config_with_models(invalid_config) is False


@pytest.mark.parametrize(
    "extra",
    [
        {"heater": "climate.hp", "heat_pump_cooling": "binary_sensor.cooling"},
        {"heater": "switch.heater", "secondary_heater": "climate.aux"},
    ],
)
def test_platform_schema_rejects_climate_where_roles_cannot_be_climate(extra) -> None:
    """YAML fails validation, with a clear message, instead of crashing at setup."""
    config = {
        "platform": "dual_smart_thermostat",
        "name": "t",
        "target_sensor": "sensor.t",
        **extra,
    }
    with pytest.raises(vol.Invalid, match="cannot be a climate entity"):
        PLATFORM_SCHEMA(config)


def test_platform_schema_accepts_climate_cooler() -> None:
    """Supported roles still validate."""
    PLATFORM_SCHEMA(
        {
            "platform": "dual_smart_thermostat",
            "name": "t",
            "target_sensor": "sensor.t",
            "heater": "switch.heater",
            "cooler": "climate.ac",
        }
    )


def _yaml(**extra):
    return {
        "platform": "dual_smart_thermostat",
        "name": "t",
        "target_sensor": "sensor.t",
        "heater": "switch.h",
        **extra,
    }


def test_control_style_and_cooler_offset_accepted_with_climate_cooler() -> None:
    """Climate cooler takes the style and its own offset."""
    cfg = PLATFORM_SCHEMA(
        _yaml(cooler="climate.ac", control_style="setpoint", cooler_setpoint_offset=-3)
    )
    assert cfg["control_style"] == "setpoint"
    assert cfg["cooler_setpoint_offset"] == -3.0


def test_each_offset_needs_its_own_climate_role() -> None:
    """An offset for a role that is not a climate entity has nothing to apply to."""
    with pytest.raises(vol.Invalid, match="heater_setpoint_offset"):
        PLATFORM_SCHEMA(_yaml(cooler="climate.ac", heater_setpoint_offset=2))
    with pytest.raises(vol.Invalid, match="cooler_setpoint_offset"):
        PLATFORM_SCHEMA(
            _yaml(heater="climate.ac", cooler="switch.c", cooler_setpoint_offset=2)
        )


def test_ac_mode_climate_heater_serves_as_the_cooler() -> None:
    """An ac_mode climate heater uses the cooler offset only."""
    cfg = PLATFORM_SCHEMA(
        _yaml(heater="climate.ac", ac_mode=True, cooler_setpoint_offset=-2)
    )
    assert cfg["cooler_setpoint_offset"] == -2.0
    with pytest.raises(vol.Invalid, match="heater_setpoint_offset"):
        PLATFORM_SCHEMA(
            _yaml(heater="climate.ac", ac_mode=True, heater_setpoint_offset=2)
        )


def test_applicable_offset_keys_follow_the_roles() -> None:
    """Offsets exist only for roles that push a temperature."""
    assert applicable_offset_keys({"heater": "switch.h", "cooler": "climate.ac"}) == [
        "cooler_setpoint_offset"
    ]
    assert applicable_offset_keys({"heater": "climate.h", "cooler": "climate.c"}) == [
        "heater_setpoint_offset",
        "cooler_setpoint_offset",
    ]
    assert applicable_offset_keys({"heater": "climate.h", "fan": "climate.h"}) == [
        "heater_setpoint_offset"
    ]
    assert applicable_offset_keys({"heater": "switch.h"}) == []
    # a heat pump uses the heater offset while heating, the cooler one while cooling
    assert applicable_offset_keys(
        {"heater": "climate.hp", "heat_pump_cooling": "binary_sensor.c"}
    ) == ["heater_setpoint_offset", "cooler_setpoint_offset"]


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("control_style", "on_off"),
        ("heater_setpoint_offset", 1),
        ("cooler_setpoint_offset", 1),
    ],
)
def test_climate_only_options_rejected_without_a_climate_role(key, value) -> None:
    """These options mean nothing when no role is a climate entity."""
    with pytest.raises(vol.Invalid, match="climate"):
        PLATFORM_SCHEMA(_yaml(**{key: value}))


def test_unknown_control_style_rejected() -> None:
    """Only on_off and setpoint exist."""
    with pytest.raises(vol.Invalid):
        PLATFORM_SCHEMA(_yaml(cooler="climate.ac", control_style="auto"))


def test_setpoint_with_climate_heat_pump_rejected() -> None:
    """Spec OQ2: reported as a setpoint problem, not just a heat pump one."""
    config = _yaml(
        heater="climate.hp",
        heat_pump_cooling="binary_sensor.cooling",
        control_style="setpoint",
    )
    assert setpoint_unsupported(config)
    with pytest.raises(vol.Invalid, match="setpoint is not supported"):
        PLATFORM_SCHEMA(config)
