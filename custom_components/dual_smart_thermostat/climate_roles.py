"""Which device roles may be backed by a climate entity.

The one definition shared by YAML validation, the config flows and runtime, so
they cannot disagree about it.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from .const import CONF_AUX_HEATER, CONF_HEAT_PUMP_COOLING, CONF_HEATER

CLIMATE_DOMAIN = "climate"


def is_climate_entity(entity_id: Any) -> bool:
    """True when the id belongs to the climate domain."""
    return isinstance(entity_id, str) and entity_id.startswith(f"{CLIMATE_DOMAIN}.")


def unsupported_climate_roles(config: Mapping[str, Any]) -> list[str]:
    """Roles configured with a climate entity that cannot be climate-backed yet."""
    roles = [CONF_AUX_HEATER]
    if config.get(CONF_HEAT_PUMP_COOLING):
        roles.append(CONF_HEATER)
    return [key for key in roles if is_climate_entity(config.get(key))]


def validate_climate_roles(config: dict[str, Any]) -> dict[str, Any]:
    """Voluptuous validator: reject climate entities in unsupported roles."""
    if bad := unsupported_climate_roles(config):
        raise vol.Invalid(f"{', '.join(bad)} cannot be a climate entity")
    return config
