"""Tests for fan speed control feature."""

from datetime import timedelta
from unittest.mock import MagicMock

from homeassistant.components.climate import HVACMode
from homeassistant.core import HomeAssistant
import pytest

from custom_components.dual_smart_thermostat.const import (
    FAN_MODE_TO_PERCENTAGE,
    PERCENTAGE_TO_FAN_MODE,
)
from custom_components.dual_smart_thermostat.hvac_device.fan_device import FanDevice
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.hvac_power_manager import (
    HvacPowerManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)


def test_fan_mode_percentage_mappings_exist():
    """Test that fan mode to percentage mappings are defined."""
    assert "auto" in FAN_MODE_TO_PERCENTAGE
    assert "low" in FAN_MODE_TO_PERCENTAGE
    assert "medium" in FAN_MODE_TO_PERCENTAGE
    assert "high" in FAN_MODE_TO_PERCENTAGE

    assert FAN_MODE_TO_PERCENTAGE["low"] == 33
    assert FAN_MODE_TO_PERCENTAGE["medium"] == 66
    assert FAN_MODE_TO_PERCENTAGE["high"] == 100
    assert FAN_MODE_TO_PERCENTAGE["auto"] == 100


def test_percentage_to_fan_mode_mapping():
    """Test reverse mapping from percentage to fan mode."""
    assert 33 in PERCENTAGE_TO_FAN_MODE
    assert 66 in PERCENTAGE_TO_FAN_MODE
    assert 100 in PERCENTAGE_TO_FAN_MODE

    assert PERCENTAGE_TO_FAN_MODE[33] == "low"
    assert PERCENTAGE_TO_FAN_MODE[66] == "medium"
    assert PERCENTAGE_TO_FAN_MODE[100] == "high"


def test_auto_mode_uses_100_percent_same_as_high():
    """Test that auto mode uses 100% like high mode.

    This documents intentional behavior: auto and high both send 100% to the fan.
    When reading back a 100% state, it's interpreted as "high" mode.
    """
    # Both auto and high use 100%
    assert FAN_MODE_TO_PERCENTAGE["auto"] == 100
    assert FAN_MODE_TO_PERCENTAGE["high"] == 100

    # But reading 100% returns "high" as canonical
    assert PERCENTAGE_TO_FAN_MODE[100] == "high"


@pytest.mark.asyncio
async def test_fan_device_detects_preset_modes(hass: HomeAssistant):
    """Test that FanDevice detects preset_mode support."""
    # Setup mock fan entity with preset_modes
    hass.states.async_set(
        "fan.test_fan",
        "off",
        {
            "preset_modes": ["auto", "low", "medium", "high"],
            "preset_mode": "auto",
        },
    )

    # Create FanDevice
    environment = MagicMock(spec=EnvironmentManager)
    openings = MagicMock(spec=OpeningManager)
    features = MagicMock(spec=FeatureManager)
    hvac_power = MagicMock(spec=HvacPowerManager)

    fan_device = FanDevice(
        hass,
        "fan.test_fan",
        timedelta(seconds=5),
        HVACMode.FAN_ONLY,
        environment,
        openings,
        features,
        hvac_power,
    )

    # Check detection
    assert fan_device.supports_fan_mode is True
    assert fan_device.fan_modes == ["auto", "low", "medium", "high"]
    assert fan_device.uses_preset_modes is True
    assert fan_device.current_fan_mode == "auto"


@pytest.mark.asyncio
async def test_fan_device_detects_percentage_support(hass: HomeAssistant):
    """Test that FanDevice detects percentage support."""
    # Setup mock fan entity with percentage
    hass.states.async_set(
        "fan.test_fan",
        "off",
        {
            "percentage": 50,
        },
    )

    environment = MagicMock(spec=EnvironmentManager)
    openings = MagicMock(spec=OpeningManager)
    features = MagicMock(spec=FeatureManager)
    hvac_power = MagicMock(spec=HvacPowerManager)

    fan_device = FanDevice(
        hass,
        "fan.test_fan",
        timedelta(seconds=5),
        HVACMode.FAN_ONLY,
        environment,
        openings,
        features,
        hvac_power,
    )

    assert fan_device.supports_fan_mode is True
    assert fan_device.fan_modes == ["auto", "low", "medium", "high"]
    assert fan_device.uses_preset_modes is False


@pytest.mark.asyncio
async def test_fan_device_switch_no_speed_control(hass: HomeAssistant):
    """Test that switch entities don't support speed control."""
    # Setup mock switch entity
    hass.states.async_set("switch.test_fan", "off")

    environment = MagicMock(spec=EnvironmentManager)
    openings = MagicMock(spec=OpeningManager)
    features = MagicMock(spec=FeatureManager)
    hvac_power = MagicMock(spec=HvacPowerManager)

    fan_device = FanDevice(
        hass,
        "switch.test_fan",
        timedelta(seconds=5),
        HVACMode.FAN_ONLY,
        environment,
        openings,
        features,
        hvac_power,
    )

    assert fan_device.supports_fan_mode is False
    assert fan_device.fan_modes == []


@pytest.mark.asyncio
async def test_fan_device_missing_entity_no_speed_control(hass: HomeAssistant):
    """Test that missing entities gracefully fall back to no speed control."""
    # Don't create any entity - hass.states.get will return None
    environment = MagicMock(spec=EnvironmentManager)
    openings = MagicMock(spec=OpeningManager)
    features = MagicMock(spec=FeatureManager)
    hvac_power = MagicMock(spec=HvacPowerManager)

    fan_device = FanDevice(
        hass,
        "fan.nonexistent",
        timedelta(seconds=5),
        HVACMode.FAN_ONLY,
        environment,
        openings,
        features,
        hvac_power,
    )

    assert fan_device.supports_fan_mode is False
    assert fan_device.fan_modes == []
