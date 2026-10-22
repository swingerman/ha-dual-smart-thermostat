"""Which device roles are backed by a climate entity.

The one definition shared by YAML validation, the config flows and runtime, so
they cannot disagree about it. Aux (secondary) heater is deliberately absent:
it stays switch-like.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .const import CONF_COOLER, CONF_DRYER, CONF_FAN, CONF_HEATER

CLIMATE_DOMAIN = "climate"

# Priority order, also the order the temperature fallback picks a source in.
CLIMATE_ROLE_KEYS = (CONF_HEATER, CONF_COOLER, CONF_FAN, CONF_DRYER)


def is_climate_entity(entity_id: Any) -> bool:
    """True when the id belongs to the climate domain."""
    return isinstance(entity_id, str) and entity_id.startswith(f"{CLIMATE_DOMAIN}.")


def climate_role_ids(config: Mapping[str, Any]) -> dict[str, str]:
    """Role key -> entity id for every role that is a climate entity."""
    return {
        key: config[key]
        for key in CLIMATE_ROLE_KEYS
        if is_climate_entity(config.get(key))
    }


def has_climate_role(config: Mapping[str, Any]) -> bool:
    """True when at least one role is a climate entity."""
    return bool(climate_role_ids(config))


def first_climate_role(config: Mapping[str, Any]) -> str | None:
    """Entity id of the first climate role in priority order."""
    return next(iter(climate_role_ids(config).values()), None)
