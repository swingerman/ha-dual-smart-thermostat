"""Sensor platform for dual_smart_thermostat.

Phase 0 of the Auto Mode roadmap (#563): exposes each climate entity's
``hvac_action_reason`` value as a diagnostic enum sensor entity. The sensor
is dual-exposed alongside the existing (deprecated) climate state attribute.
"""

from __future__ import annotations

from collections.abc import Callable
import logging

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import SET_HVAC_ACTION_REASON_SENSOR_SIGNAL
from .hvac_action_reason.hvac_action_reason import HVACActionReason

_LOGGER = logging.getLogger(__name__)


_OPTIONS: tuple[str, ...] = tuple(sorted(m.value for m in HVACActionReason))
_OPTIONS_SET: frozenset[str] = frozenset(_OPTIONS)


class HvacActionReasonSensor(SensorEntity, RestoreEntity):
    """Diagnostic enum sensor that mirrors a climate's hvac_action_reason."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = False
    _attr_has_entity_name = False
    _attr_translation_key = "hvac_action_reason"

    def __init__(self, sensor_key: str, name: str) -> None:
        """Initialise the sensor."""
        self._sensor_key = sensor_key
        self._attr_name = f"{name} HVAC Action Reason"
        self._attr_unique_id = f"{sensor_key}_hvac_action_reason"
        self._attr_options = _OPTIONS
        self._attr_native_value = HVACActionReason.NONE
        self._remove_signal: Callable[[], None] | None = None

    async def async_added_to_hass(self) -> None:
        """Restore previous state (if any) and subscribe to the mirror signal."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state is not None and last_state.state in _OPTIONS_SET:
            self._attr_native_value = last_state.state
        else:
            if last_state is not None:
                _LOGGER.debug(
                    "Ignoring unknown restored state %s for %s; defaulting to none",
                    last_state.state,
                    self.entity_id,
                )
            self._attr_native_value = HVACActionReason.NONE

        self._remove_signal = async_dispatcher_connect(
            self.hass,
            SET_HVAC_ACTION_REASON_SENSOR_SIGNAL.format(self._sensor_key),
            self._handle_reason_update,
        )

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe from the mirror signal."""
        if self._remove_signal is not None:
            self._remove_signal()
            self._remove_signal = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_reason_update(self, reason) -> None:
        """Update native_value from a dispatched reason; ignore invalid values."""
        value = str(reason) if reason is not None else HVACActionReason.NONE

        if value not in _OPTIONS_SET:
            _LOGGER.warning(
                "Invalid hvac_action_reason %s for %s; ignoring",
                value,
                self.entity_id,
            )
            return

        if value == self._attr_native_value:
            return

        self._attr_native_value = value
        self.async_write_ha_state()


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the companion action-reason sensor for a config entry."""
    config = {**config_entry.data, **config_entry.options}
    name = config.get(CONF_NAME, "dual_smart_thermostat")
    sensor_key = config_entry.entry_id

    async_add_entities([HvacActionReasonSensor(sensor_key=sensor_key, name=name)])


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Create the companion action-reason sensor for a YAML-discovered climate."""
    if discovery_info is None:
        # This platform is only instantiated via discovery from climate.py.
        return

    name = discovery_info["name"]
    sensor_key = discovery_info["sensor_key"]

    async_add_entities([HvacActionReasonSensor(sensor_key=sensor_key, name=name)])
