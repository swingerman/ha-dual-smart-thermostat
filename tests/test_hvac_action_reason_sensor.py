"""Tests for the hvac_action_reason sensor entity (Phase 0)."""

import logging

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.entity import EntityCategory

from custom_components.dual_smart_thermostat.const import (
    SET_HVAC_ACTION_REASON_SENSOR_SIGNAL,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_auto import (
    HVACActionReasonAuto,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_external import (
    HVACActionReasonExternal,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
)
from custom_components.dual_smart_thermostat.sensor import HvacActionReasonSensor


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


def test_sensor_signal_constant_has_placeholder() -> None:
    """Signal template has one {} placeholder for the sensor_key."""
    assert "{}" in SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
    # Sanity — format with a sample key must produce a distinct, stable string.
    formatted = SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123")
    assert formatted.endswith("abc123")
    assert formatted != SET_HVAC_ACTION_REASON_SENSOR_SIGNAL


def test_sensor_entity_defaults() -> None:
    """The sensor entity exposes the correct ENUM contract and defaults."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")

    assert sensor.device_class == SensorDeviceClass.ENUM
    assert sensor.entity_category == EntityCategory.DIAGNOSTIC
    assert sensor.unique_id == "abc123_hvac_action_reason"
    assert sensor.translation_key == "hvac_action_reason"
    # Default native_value is the "none" string (empty enum value).
    assert sensor.native_value == HVACActionReason.NONE


def test_sensor_options_contains_all_reason_values() -> None:
    """options contains every Internal + External + Auto reason plus 'none'."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")

    options = set(sensor.options or [])
    # Every enum value from each sub-category must be present.
    for value in HVACActionReasonInternal:
        assert value.value in options, f"missing internal: {value.value}"
    for value in HVACActionReasonExternal:
        assert value.value in options, f"missing external: {value.value}"
    for value in HVACActionReasonAuto:
        assert value.value in options, f"missing auto: {value.value}"
    # NONE is the empty string — it must also be an allowed option.
    assert HVACActionReason.NONE in options


async def test_sensor_updates_state_on_valid_signal(hass: HomeAssistant) -> None:
    """A valid reason dispatched on the signal updates native_value."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")
    sensor.hass = hass
    # Simulate entity being added to hass (subscribes to the signal).
    await sensor.async_added_to_hass()

    async_dispatcher_send(
        hass,
        SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
        HVACActionReasonInternal.TARGET_TEMP_REACHED,
    )
    await hass.async_block_till_done()

    assert sensor.native_value == HVACActionReasonInternal.TARGET_TEMP_REACHED


async def test_sensor_ignores_invalid_signal_value(hass: HomeAssistant, caplog) -> None:
    """An invalid reason is logged as a warning and state is preserved."""
    sensor = HvacActionReasonSensor(sensor_key="abc123", name="Test")
    sensor.hass = hass
    await sensor.async_added_to_hass()

    # Prime the sensor with a known valid value.
    async_dispatcher_send(
        hass,
        SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
        HVACActionReasonInternal.TARGET_TEMP_REACHED,
    )
    await hass.async_block_till_done()

    caplog.clear()
    with caplog.at_level(logging.WARNING):
        async_dispatcher_send(
            hass,
            SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format("abc123"),
            "this_is_not_a_real_reason",
        )
        await hass.async_block_till_done()

    # State preserved.
    assert sensor.native_value == HVACActionReasonInternal.TARGET_TEMP_REACHED
    # A warning was logged.
    assert any("Invalid hvac_action_reason" in rec.message for rec in caplog.records)
