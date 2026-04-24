"""Tests for FeatureManager.is_configured_for_auto_mode (Phase 1.1)."""

from unittest.mock import MagicMock

from custom_components.dual_smart_thermostat.const import CONF_HEATER, CONF_SENSOR
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)


def _make_feature_manager(config: dict) -> FeatureManager:
    """Build a FeatureManager from a raw config dict without hass dependencies."""
    hass = MagicMock()
    environment = MagicMock()
    return FeatureManager(hass, config, environment)


def test_feature_manager_stores_sensor_entity_id() -> None:
    """FeatureManager captures the temperature sensor entity from config."""
    config = {
        CONF_HEATER: "switch.heater",
        CONF_SENSOR: "sensor.indoor_temp",
    }

    fm = _make_feature_manager(config)

    assert fm._sensor_entity_id == "sensor.indoor_temp"


def test_feature_manager_sensor_entity_id_none_when_missing() -> None:
    """With no temperature sensor configured, the attribute is None."""
    config = {CONF_HEATER: "switch.heater"}

    fm = _make_feature_manager(config)

    assert fm._sensor_entity_id is None
