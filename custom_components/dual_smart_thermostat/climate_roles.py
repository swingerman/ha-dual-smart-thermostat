"""Which device roles may be backed by a climate entity.

The one definition shared by YAML validation, the config flows and runtime, so
they cannot disagree about it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from .const import (
    CONF_AC_MODE,
    CONF_AUX_HEATER,
    CONF_CONTROL_STYLE,
    CONF_COOLER,
    CONF_COOLER_SETPOINT_OFFSET,
    CONF_DRYER,
    CONF_FAN,
    CONF_FAN_ON_WITH_AC,
    CONF_FAN_ON_WITH_HEATER,
    CONF_HEAT_COOL_MODE,
    CONF_HEAT_PUMP_COOLING,
    CONF_HEATER,
    CONF_HEATER_SETPOINT_OFFSET,
    CONF_SENSOR,
    CONF_TARGET_TEMP_HIGH,
    CONF_TARGET_TEMP_LOW,
    ControlStyle,
)

CLIMATE_DOMAIN = "climate"

# Priority order, also the order the temperature fallback picks a source in.
CLIMATE_ROLE_KEYS = (CONF_HEATER, CONF_COOLER, CONF_FAN, CONF_DRYER)


def is_climate_entity(entity_id: Any) -> bool:
    """True when the id belongs to the climate domain."""
    return isinstance(entity_id, str) and entity_id.startswith(f"{CLIMATE_DOMAIN}.")


def first_climate_role(config: Mapping[str, Any]) -> str | None:
    """Entity id of the first climate role in priority order."""
    return next(
        (
            config[key]
            for key in CLIMATE_ROLE_KEYS
            if is_climate_entity(config.get(key))
        ),
        None,
    )


def unsupported_climate_roles(config: Mapping[str, Any]) -> list[str]:
    """Roles configured with a climate entity that cannot be climate-backed."""
    return [key for key in (CONF_AUX_HEATER,) if is_climate_entity(config.get(key))]


def applicable_offset_keys(config: Mapping[str, Any]) -> list[str]:
    """Which per-role offsets mean something for these roles.

    Only roles that push a temperature have one. A climate `heater` that only
    serves as the cooler (`ac_mode`, no `cooler`) uses the cooler offset; a heat
    pump uses the heater offset while heating and the cooler offset while cooling.
    """
    heater_is_climate = is_climate_entity(config.get(CONF_HEATER))
    ac_only = bool(config.get(CONF_AC_MODE)) and not config.get(CONF_COOLER)
    heat_pump = bool(config.get(CONF_HEAT_PUMP_COOLING))

    keys = []
    if heater_is_climate and (not ac_only or heat_pump):
        keys.append(CONF_HEATER_SETPOINT_OFFSET)
    if is_climate_entity(config.get(CONF_COOLER)) or (
        heater_is_climate and (ac_only or heat_pump)
    ):
        keys.append(CONF_COOLER_SETPOINT_OFFSET)
    return keys


def setpoint_unsupported(config: Mapping[str, Any]) -> bool:
    """control_style: setpoint cannot drive a climate heat pump (spec OQ2)."""
    return bool(
        config.get(CONF_CONTROL_STYLE) == ControlStyle.SETPOINT
        and config.get(CONF_HEAT_PUMP_COOLING)
        and is_climate_entity(config.get(CONF_HEATER))
    )


def setpoint_shared_heat_cool(config: Mapping[str, Any]) -> bool:
    """Setpoint style cannot serve heat_cool from one climate in both roles.

    Heater and cooler would both stay engaged ("goal never reached") and keep
    flipping the one child between its heat and cool modes.
    """
    heat_cool = config.get(CONF_HEAT_COOL_MODE) or (
        config.get(CONF_TARGET_TEMP_LOW) is not None
        and config.get(CONF_TARGET_TEMP_HIGH) is not None
    )
    return bool(
        config.get(CONF_CONTROL_STYLE) == ControlStyle.SETPOINT
        and heat_cool
        and is_climate_entity(config.get(CONF_HEATER))
        and config.get(CONF_HEATER) == config.get(CONF_COOLER)
    )


def normalize_climate_roles(config: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve what climate roles imply, once, before anything reads the config.

    - No target_sensor: the first climate role is the temperature source.
    - A fan on the same climate as the cooler or heater cannot run alongside it
      (one entity holds one mode), so the concurrent options are forced off.
    """
    config = dict(config)

    if not config.get(CONF_SENSOR):
        if source := first_climate_role(config):
            config[CONF_SENSOR] = source

    fan = config.get(CONF_FAN)
    if is_climate_entity(fan):
        heater = config.get(CONF_HEATER)
        cooler = config.get(CONF_COOLER) or (
            heater if config.get(CONF_AC_MODE) else None
        )
        if fan == cooler and config.get(CONF_FAN_ON_WITH_AC):
            config[CONF_FAN_ON_WITH_AC] = False
        if fan == heater and config.get(CONF_FAN_ON_WITH_HEATER):
            config[CONF_FAN_ON_WITH_HEATER] = False

    return config


def validate_climate_roles(config: dict[str, Any]) -> dict[str, Any]:
    """Voluptuous validator: cross-field rules for climate-backed roles."""
    if setpoint_unsupported(config):
        raise vol.Invalid(
            "control_style: setpoint is not supported for a climate heat pump"
        )
    if setpoint_shared_heat_cool(config):
        raise vol.Invalid(
            "control_style: setpoint cannot do heat_cool with one climate as both "
            "heater and cooler"
        )
    if bad := unsupported_climate_roles(config):
        raise vol.Invalid(f"{', '.join(bad)} cannot be a climate entity")
    has_role = any(is_climate_entity(config.get(key)) for key in CLIMATE_ROLE_KEYS)
    if not config.get(CONF_SENSOR) and not has_role:
        raise vol.Invalid(
            "target_sensor is required unless heater, cooler, fan or dryer is a "
            "climate entity"
        )
    if CONF_CONTROL_STYLE in config and not has_role:
        raise vol.Invalid(
            "control_style needs heater, cooler, fan or dryer to be a climate entity"
        )
    applicable = applicable_offset_keys(config)
    for key in (CONF_HEATER_SETPOINT_OFFSET, CONF_COOLER_SETPOINT_OFFSET):
        if key in config and key not in applicable:
            raise vol.Invalid(
                f"{key} needs the matching role to be a climate entity (climate)"
            )
    return config
