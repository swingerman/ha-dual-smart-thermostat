"""Configuration validation using data models."""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    CONF_AC_MODE,
    CONF_COLD_TOLERANCE,
    CONF_COOLER,
    CONF_FLOOR_SENSOR,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HOT_TOLERANCE,
    CONF_HUMIDITY_SENSOR,
    CONF_MIN_DUR,
    CONF_SENSOR,
    SYSTEM_TYPE_AC_ONLY,
    SYSTEM_TYPE_HEAT_PUMP,
    SYSTEM_TYPE_HEATER_COOLER,
    SYSTEM_TYPE_SIMPLE_HEATER,
)
from .models import (
    ACOnlyCoreSettings,
    HeaterCoolerCoreSettings,
    HeatPumpCoreSettings,
    SimpleHeaterCoreSettings,
    ThermostatConfig,
)

_LOGGER = logging.getLogger(__name__)


def validate_config_with_models(config: dict[str, Any]) -> bool:
    """Validate configuration using data models.

    Args:
        config: Configuration dictionary to validate

    Returns:
        True if configuration is valid, False otherwise
    """
    try:
        _config_dict_to_model(config)
        return True
    except (ValueError, KeyError, TypeError) as err:
        _LOGGER.error("Configuration validation failed: %s", err)
        return False


def _config_dict_to_model(config: dict[str, Any]) -> ThermostatConfig:
    """Convert configuration dictionary to ThermostatConfig model.

    Args:
        config: Configuration dictionary

    Returns:
        ThermostatConfig instance

    Raises:
        ValueError: If system type is unknown or configuration is invalid
        KeyError: If required fields are missing
    """
    system_type = config.get("system_type", SYSTEM_TYPE_SIMPLE_HEATER)
    name = config.get("name", "Dual Smart Thermostat")

    # Build core settings based on system type
    if system_type == SYSTEM_TYPE_SIMPLE_HEATER:
        core_settings = SimpleHeaterCoreSettings(
            target_sensor=config[CONF_SENSOR],
            heater=config.get(CONF_HEATER),
            cold_tolerance=config.get(CONF_COLD_TOLERANCE, 0.3),
            hot_tolerance=config.get(CONF_HOT_TOLERANCE, 0.3),
            min_cycle_duration=config.get(CONF_MIN_DUR, 300),
        )
    elif system_type == SYSTEM_TYPE_AC_ONLY:
        core_settings = ACOnlyCoreSettings(
            target_sensor=config[CONF_SENSOR],
            heater=config.get(CONF_HEATER),  # AC switch reuses heater field
            ac_mode=config.get(CONF_AC_MODE, True),
            cold_tolerance=config.get(CONF_COLD_TOLERANCE, 0.3),
            hot_tolerance=config.get(CONF_HOT_TOLERANCE, 0.3),
            min_cycle_duration=config.get(CONF_MIN_DUR, 300),
        )
    elif system_type == SYSTEM_TYPE_HEATER_COOLER:
        core_settings = HeaterCoolerCoreSettings(
            target_sensor=config[CONF_SENSOR],
            heater=config.get(CONF_HEATER),
            cooler=config.get(CONF_COOLER),
            heat_cool_mode=config.get(CONF_HEAT_COOL_MODE, False),
            cold_tolerance=config.get(CONF_COLD_TOLERANCE, 0.3),
            hot_tolerance=config.get(CONF_HOT_TOLERANCE, 0.3),
            min_cycle_duration=config.get(CONF_MIN_DUR, 300),
        )
    elif system_type == SYSTEM_TYPE_HEAT_PUMP:
        core_settings = HeatPumpCoreSettings(
            target_sensor=config[CONF_SENSOR],
            heater=config.get(CONF_HEATER),
            heat_pump_cooling=config.get(CONF_HEAT_PUMP_COOLING),
            cold_tolerance=config.get(CONF_COLD_TOLERANCE, 0.3),
            hot_tolerance=config.get(CONF_HOT_TOLERANCE, 0.3),
            min_cycle_duration=config.get(CONF_MIN_DUR, 300),
        )
    else:
        raise ValueError(f"Unknown system type: {system_type}")

    # Parse optional feature settings (simplified - full implementation would parse all features)
    # For now, just validate that the config can be constructed
    thermostat_config = ThermostatConfig(
        name=name,
        system_type=system_type,
        core_settings=core_settings,
    )

    return thermostat_config


def get_system_type(config: dict[str, Any]) -> str:
    """Get system type from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        System type string
    """
    return config.get("system_type", SYSTEM_TYPE_SIMPLE_HEATER)


def has_feature(config: dict[str, Any], feature_key: str) -> bool:
    """Check if a feature is enabled in configuration.

    Args:
        config: Configuration dictionary
        feature_key: Feature key to check (e.g., 'humidity_sensor', 'floor_sensor')

    Returns:
        True if feature is configured, False otherwise
    """
    if feature_key == "humidity":
        return config.get(CONF_HUMIDITY_SENSOR) is not None
    if feature_key == "floor_heating":
        return config.get(CONF_FLOOR_SENSOR) is not None

    # Check if the key exists and is not None
    return config.get(feature_key) is not None
