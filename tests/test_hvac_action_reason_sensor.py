"""Tests for the hvac_action_reason sensor entity (Phase 0)."""

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_auto import (
    HVACActionReasonAuto,
)


def test_hvac_action_reason_auto_values_exist() -> None:
    """Auto-mode enum declares the three Phase 1 reserved values."""
    assert HVACActionReasonAuto.AUTO_PRIORITY_HUMIDITY == "auto_priority_humidity"
    assert HVACActionReasonAuto.AUTO_PRIORITY_TEMPERATURE == "auto_priority_temperature"
    assert HVACActionReasonAuto.AUTO_PRIORITY_COMFORT == "auto_priority_comfort"


def test_hvac_action_reason_aggregate_includes_auto_values() -> None:
    """The top-level HVACActionReason aggregates Auto values alongside Internal/External."""
    assert HVACActionReason.AUTO_PRIORITY_HUMIDITY == "auto_priority_humidity"
    assert HVACActionReason.AUTO_PRIORITY_TEMPERATURE == "auto_priority_temperature"
    assert HVACActionReason.AUTO_PRIORITY_COMFORT == "auto_priority_comfort"
