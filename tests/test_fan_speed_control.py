"""Tests for fan speed control feature."""

from custom_components.dual_smart_thermostat.const import (
    FAN_MODE_TO_PERCENTAGE,
    PERCENTAGE_TO_FAN_MODE,
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
