"""Sensor platform for dual_smart_thermostat.

Phase 0 of the Auto Mode roadmap (#563): exposes each climate entity's
``hvac_action_reason`` value as a diagnostic enum sensor entity. The sensor
is dual-exposed alongside the existing (deprecated) climate state attribute.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import SET_HVAC_ACTION_REASON_SENSOR_SIGNAL  # noqa: F401  # used in Task 4
from .hvac_action_reason.hvac_action_reason import HVACActionReason
from .hvac_action_reason.hvac_action_reason_auto import HVACActionReasonAuto
from .hvac_action_reason.hvac_action_reason_external import HVACActionReasonExternal
from .hvac_action_reason.hvac_action_reason_internal import HVACActionReasonInternal

_LOGGER = logging.getLogger(__name__)


def _build_options() -> list[str]:
    """Return every valid sensor state value (sorted for stability)."""
    values: set[str] = {HVACActionReason.NONE}
    for enum_cls in (
        HVACActionReasonInternal,
        HVACActionReasonExternal,
        HVACActionReasonAuto,
    ):
        for member in enum_cls:
            values.add(member.value)
    return sorted(values)


_OPTIONS = _build_options()


class HvacActionReasonSensor(SensorEntity, RestoreEntity):
    """Diagnostic enum sensor that mirrors a climate's hvac_action_reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_translation_key = "hvac_action_reason"

    def __init__(self, sensor_key: str, name: str) -> None:
        """Initialise the sensor.

        Args:
            sensor_key: The climate's stable identifier (config entry id,
                unique_id, or name). Used to build unique_id and subscribe
                to the mirror signal.
            name: Human-readable base name, usually the climate's name.
        """
        self._sensor_key = sensor_key
        self._attr_name = f"{name} HVAC Action Reason"
        self._attr_unique_id = f"{sensor_key}_hvac_action_reason"
        self._attr_options = list(_OPTIONS)
        self._attr_native_value = HVACActionReason.NONE
        self._remove_signal: callable | None = None
