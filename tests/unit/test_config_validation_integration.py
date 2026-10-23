"""Tests for config validation integration with config_flow and options_flow."""

from unittest.mock import MagicMock, patch

from homeassistant.const import CONF_NAME
import pytest
import voluptuous as vol

from custom_components.dual_smart_thermostat.climate import PLATFORM_SCHEMA
from custom_components.dual_smart_thermostat.climate_roles import (
    applicable_offset_keys,
    normalize_climate_roles,
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
    [{"heater": "switch.heater", "secondary_heater": "climate.aux"}],
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


def test_platform_schema_accepts_a_climate_heat_pump() -> None:
    """A climate heat pump is supported (only setpoint style is not)."""
    PLATFORM_SCHEMA(
        {
            "platform": "dual_smart_thermostat",
            "name": "t",
            "target_sensor": "sensor.t",
            "heater": "climate.hp",
            "heat_pump_cooling": "binary_sensor.cooling",
        }
    )


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


@pytest.mark.parametrize(
    "heat_cool",
    [{"heat_cool_mode": True}, {"target_temp_low": 19, "target_temp_high": 24}],
)
def test_setpoint_with_one_climate_as_heater_and_cooler_cannot_heat_cool(
    heat_cool,
) -> None:
    """Both roles would stay engaged in heat_cool and flip the one child's mode."""
    with pytest.raises(vol.Invalid, match="heat_cool"):
        PLATFORM_SCHEMA(
            _yaml(
                heater="climate.ac",
                cooler="climate.ac",
                control_style="setpoint",
                **heat_cool,
            )
        )


def test_setpoint_heat_cool_is_fine_with_separate_climates_or_without_heat_cool() -> (
    None
):
    """Only the shared child cannot serve heat_cool in setpoint style."""
    PLATFORM_SCHEMA(
        _yaml(
            heater="climate.heat",
            cooler="climate.cool",
            control_style="setpoint",
            heat_cool_mode=True,
        )
    )
    PLATFORM_SCHEMA(
        _yaml(heater="climate.ac", cooler="climate.ac", control_style="setpoint")
    )


def test_missing_target_sensor_falls_back_to_first_climate_role() -> None:
    """The first climate role (heater, cooler, fan, dryer) is the temperature source."""
    cfg = normalize_climate_roles({"heater": "switch.h", "cooler": "climate.ac"})
    assert cfg["target_sensor"] == "climate.ac"
    cfg = normalize_climate_roles({"dryer": "climate.b", "cooler": "climate.a"})
    assert cfg["target_sensor"] == "climate.a"


def test_explicit_target_sensor_is_kept() -> None:
    """A configured sensor always wins."""
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "target_sensor": "sensor.room"}
    )
    assert cfg["target_sensor"] == "sensor.room"


def test_normalisation_does_not_mutate_the_input() -> None:
    """The caller's config is left alone."""
    original = {"cooler": "climate.ac"}
    normalize_climate_roles(original)
    assert "target_sensor" not in original


def test_fan_sharing_a_climate_with_the_cooler_cannot_run_alongside_it() -> None:
    """One entity holds one mode: fan_on_with_ac is forced off."""
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "fan": "climate.ac", "fan_on_with_ac": True}
    )
    assert cfg["fan_on_with_ac"] is False


def test_fan_sharing_a_climate_with_the_heater_cannot_run_alongside_it() -> None:
    """Same for fan_on_with_heater."""
    cfg = normalize_climate_roles(
        {"heater": "climate.ac", "fan": "climate.ac", "fan_on_with_heater": True}
    )
    assert cfg["fan_on_with_heater"] is False


def test_separate_fan_keeps_its_flags() -> None:
    """Only a fan on the same climate is affected."""
    cfg = normalize_climate_roles(
        {"cooler": "climate.ac", "fan": "switch.fan", "fan_on_with_ac": True}
    )
    assert cfg["fan_on_with_ac"] is True


def test_ac_mode_heater_is_the_cooler_for_fan_sharing() -> None:
    """An ac_mode climate heater serves as the cooler."""
    cfg = normalize_climate_roles(
        {
            "heater": "climate.ac",
            "ac_mode": True,
            "fan": "climate.ac",
            "fan_on_with_ac": True,
        }
    )
    assert cfg["fan_on_with_ac"] is False


def test_target_sensor_required_without_climate_role() -> None:
    """Without a climate role there is no other temperature source."""
    with pytest.raises(vol.Invalid, match="target_sensor"):
        PLATFORM_SCHEMA(
            {"platform": "dual_smart_thermostat", "name": "t", "heater": "switch.h"}
        )


def test_target_sensor_optional_with_climate_role() -> None:
    """Normalised at setup, not at validation."""
    cfg = PLATFORM_SCHEMA(
        {"platform": "dual_smart_thermostat", "name": "t", "heater": "climate.ac"}
    )
    assert "target_sensor" not in cfg


def test_setpoint_heat_cool_error_names_the_target_limits() -> None:
    """The limits count as heat_cool too: the message must say so."""
    with pytest.raises(vol.Invalid, match="target_temp_low/high"):
        PLATFORM_SCHEMA(
            _yaml(
                heater="climate.ac",
                cooler="climate.ac",
                control_style="setpoint",
                target_temp_low=19,
                target_temp_high=24,
            )
        )


def test_models_accept_a_config_without_sensor_when_a_climate_is_a_role() -> None:
    """A flow-created entry may omit target_sensor: the climate's own is used."""
    from custom_components.dual_smart_thermostat.config_validation import (
        validate_config_with_models,
    )

    config = {
        "name": "T",
        "system_type": "heater_cooler",
        "heater": "switch.h",
        "cooler": "climate.ac",
    }
    assert validate_config_with_models(config) is True
    assert "target_sensor" not in config  # the caller's config is not changed


_PARITY_CONFIGS = [
    {"heater": "switch.h", "target_sensor": "sensor.t"},
    {"heater": "switch.h"},
    {"heater": "climate.ac"},
    {"heater": "climate.ac", "cooler": "climate.ac"},
    {"heater": "switch.h", "control_style": "setpoint", "target_sensor": "sensor.t"},
    {"heater": "climate.ac", "control_style": "setpoint"},
    {
        "heater": "switch.h",
        "follow_device_changes": False,
        "target_sensor": "sensor.t",
    },
    {"heater": "climate.ac", "follow_device_changes": False},
    {"heater": "switch.h", "cooler": "climate.ac", "heater_setpoint_offset": 1},
    {"heater": "switch.h", "cooler": "climate.ac", "cooler_setpoint_offset": 1},
    {"heater": "climate.ac", "ac_mode": True, "cooler_setpoint_offset": 1},
    {"heater": "climate.ac", "ac_mode": True, "heater_setpoint_offset": 1},
    {
        "heater": "climate.hp",
        "heat_pump_cooling": "binary_sensor.c",
        "heater_setpoint_offset": 1,
        "cooler_setpoint_offset": 1,
    },
    {
        "heater": "climate.hp",
        "heat_pump_cooling": "binary_sensor.c",
        "control_style": "setpoint",
    },
    {
        "heater": "switch.h",
        "secondary_heater": "climate.aux",
        "target_sensor": "sensor.t",
    },
    {
        "heater": "climate.ac",
        "cooler": "climate.ac",
        "control_style": "setpoint",
        "heat_cool_mode": True,
    },
    {
        "heater": "switch.h",
        "target_sensor": "sensor.t",
        "fan": "climate.f",
        "control_style": "setpoint",
    },
    {
        "heater": "switch.h",
        "target_sensor": "sensor.t",
        "fan": "climate.f",
        "control_style": "on_off",
    },
]


@pytest.mark.parametrize("config", _PARITY_CONFIGS)
def test_tools_validator_agrees_with_yaml_validation(config) -> None:
    """tools/config_validator.py cannot import the integration (it needs HA), so
    this keeps its climate rules in step with climate_roles on a table of configs."""
    import importlib.util
    import pathlib

    spec = importlib.util.spec_from_file_location(
        "config_validator",
        pathlib.Path(__file__).parents[2] / "tools" / "config_validator.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    tool_valid, _, _ = module.ConfigValidator().validate_config(dict(config))

    try:
        PLATFORM_SCHEMA({"platform": "dual_smart_thermostat", "name": "t", **config})
        yaml_valid = True
    except vol.Invalid:
        yaml_valid = False

    assert tool_valid == yaml_valid


def test_a_climate_only_option_error_is_one_clean_line(hass) -> None:
    """HA's check_config output: no empty path and no dump of the whole config."""
    from homeassistant.config import format_schema_error

    config = {
        "platform": "dual_smart_thermostat",
        "name": "t",
        "heater": "switch.heater",
        "target_sensor": "sensor.t",
        "control_style": "setpoint",
    }
    with pytest.raises(vol.Invalid) as err:
        PLATFORM_SCHEMA(config)
    assert format_schema_error(hass, err.value, "climate", config) == (
        "Invalid config for 'climate': needs heater, cooler, fan or dryer to be a "
        "climate entity 'control_style', got 'setpoint'"
    )
