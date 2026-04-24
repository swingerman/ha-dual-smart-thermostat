"""Tests for FeatureManager.is_configured_for_auto_mode (Phase 1.1)."""

from unittest.mock import MagicMock

import pytest

from custom_components.dual_smart_thermostat.const import (
    CONF_AC_MODE,
    CONF_COOLER,
    CONF_DRYER,
    CONF_FAN,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HUMIDITY_SENSOR,
    CONF_SENSOR,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)


def _make_feature_manager(config: dict) -> FeatureManager:
    """Build a FeatureManager from a raw config dict without hass dependencies.

    The environment is a MagicMock whose ``sensor_entity_id`` mirrors the
    config's ``CONF_SENSOR`` value, so the predicate's sensor check
    behaves as it would in production.
    """
    hass = MagicMock()
    environment = MagicMock()
    environment.sensor_entity_id = config.get(CONF_SENSOR)
    return FeatureManager(hass, config, environment)


_BASE_SENSOR = {CONF_SENSOR: "sensor.indoor_temp"}


@pytest.mark.parametrize(
    "config",
    [
        # Heater + separate cooler (dual mode) → can_heat + can_cool
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            **_BASE_SENSOR,
        },
        # Heater as AC + dryer + humidity sensor → can_cool + can_dry
        {
            CONF_HEATER: "switch.hvac",
            CONF_AC_MODE: True,
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Heater + fan entity → can_heat + can_fan
        {
            CONF_HEATER: "switch.heater",
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # Heater + dryer + humidity sensor → can_heat + can_dry
        {
            CONF_HEATER: "switch.heater",
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Heat-pump only → can_heat + can_cool (heat pump provides both)
        {
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "sensor.heat_pump_mode",
            **_BASE_SENSOR,
        },
        # Heat pump + fan → can_heat + can_cool + can_fan
        {
            CONF_HEATER: "switch.heat_pump",
            CONF_HEAT_PUMP_COOLING: "sensor.heat_pump_mode",
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # All four capabilities → can_heat + can_cool + can_dry + can_fan
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
            CONF_DRYER: "switch.dryer",
            CONF_FAN: "switch.fan",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
    ],
    ids=[
        "heater+cooler_dual",
        "ac+dryer",
        "heater+fan",
        "heater+dryer",
        "heat_pump_only",
        "heat_pump+fan",
        "all_four",
    ],
)
def test_is_configured_for_auto_mode_true(config: dict) -> None:
    """Configurations with two or more capabilities plus a sensor qualify."""
    fm = _make_feature_manager(config)

    assert fm.is_configured_for_auto_mode is True


@pytest.mark.parametrize(
    "config",
    [
        # Heater-only → can_heat only.
        {
            CONF_HEATER: "switch.heater",
            **_BASE_SENSOR,
        },
        # AC-mode only (heater entity operating as a cooler) → can_cool only.
        {
            CONF_HEATER: "switch.hvac",
            CONF_AC_MODE: True,
            **_BASE_SENSOR,
        },
        # Fan-only → can_fan only (no heater/cooler/dryer).
        {
            CONF_FAN: "switch.fan",
            **_BASE_SENSOR,
        },
        # Dryer-only + humidity sensor → can_dry only.
        {
            CONF_DRYER: "switch.dryer",
            CONF_HUMIDITY_SENSOR: "sensor.humidity",
            **_BASE_SENSOR,
        },
        # Otherwise qualifying multi-capability config, but no temperature sensor.
        {
            CONF_HEATER: "switch.heater",
            CONF_COOLER: "switch.cooler",
        },
    ],
    ids=[
        "heater_only",
        "ac_only",
        "fan_only",
        "dryer_only",
        "no_temperature_sensor",
    ],
)
def test_is_configured_for_auto_mode_false(config: dict) -> None:
    """Configurations with zero or one capability, or no sensor, do not qualify."""
    fm = _make_feature_manager(config)

    assert fm.is_configured_for_auto_mode is False
