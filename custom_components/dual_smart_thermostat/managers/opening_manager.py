"""Opening Manager for Dual Smart Thermostat."""

from calendar import c
import enum
from itertools import chain
import logging
from typing import List

from homeassistant.components.climate import HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers.typing import ConfigType

from custom_components.dual_smart_thermostat.const import (
    ATTR_TIMEOUT,
    CONF_OPENINGS,
    CONF_OPENINGS_SCOPE,
    TIMED_OPENING_SCHEMA,
)

_LOGGER = logging.getLogger(__name__)


class OpeningHvacModeScope(enum.StrEnum):
    """Opening Scope Options"""

    _ignore_ = "member cls"
    cls = vars()
    for member in chain(list(HVACMode)):
        cls[member.name] = member.value

    ALL = "all"


class OpeningManager:
    """Opening Manager for Dual Smart Thermostat."""

    def __init__(self, hass: HomeAssistant, config: ConfigType) -> None:
        self.hass = hass

        openings = config.get(CONF_OPENINGS)
        self.openings_scope: List[OpeningHvacModeScope] = config.get(
            CONF_OPENINGS_SCOPE
        ) or [OpeningHvacModeScope.ALL]

        self.openings = self.conform_openings_list(openings) if openings else []
        self.opening_entities = (
            self.conform_opnening_entities(self.openings) if openings else []
        )

    @staticmethod
    def conform_openings_list(openings: list) -> list:
        """Return a list of openings from a list of entities."""
        return [
            (
                entry
                if isinstance(entry, dict)
                else {ATTR_ENTITY_ID: entry, ATTR_TIMEOUT: None}
            )
            for entry in openings
        ]

    @staticmethod
    def conform_opnening_entities(openings: [TIMED_OPENING_SCHEMA]) -> list:  # type: ignore
        """Return a list of entities from a list of openings."""
        return [entry[ATTR_ENTITY_ID] for entry in openings]

    def _is_opening_available(self, opening: TIMED_OPENING_SCHEMA) -> bool:  # type: ignore
        """If the opening is available."""
        opening_entity = opening[ATTR_ENTITY_ID]
        opening_entity_state = self.hass.states.get(opening_entity)

        if opening_entity_state is None:
            _LOGGER.debug("Opening %s is not available.", opening)
            return False

        if opening_entity_state.state == STATE_UNAVAILABLE:
            _LOGGER.debug("Opening %s is unavailable.", opening)
            return False

        if opening_entity_state.state == STATE_UNKNOWN:
            _LOGGER.debug("Opening %s is unknown.", opening)
            return False

        return True

    def _has_timeout_mode(self, opening: TIMED_OPENING_SCHEMA) -> bool:  # type: ignore
        """If the opening has a timeout mode."""
        return opening[ATTR_TIMEOUT] is not None

    def _is_opening_open_state(self, opening: TIMED_OPENING_SCHEMA) -> bool:  # type: ignore
        """If the opening is currently open."""

        if not self._is_opening_available(opening):
            _LOGGER.debug("Opening %s is not available.", opening)
            return False

        opening_entity = opening[ATTR_ENTITY_ID]
        return self.hass.states.is_state(
            opening_entity, STATE_OPEN
        ) or self.hass.states.is_state(opening_entity, STATE_ON)

    def any_opening_open(
        self, hvac_mode_scope: OpeningHvacModeScope = OpeningHvacModeScope.ALL
    ) -> bool:
        """If any opening is currently open."""
        _LOGGER.debug("_any_opening_open")
        if not self.opening_entities:
            return False

        _is_open = False

        _LOGGER.debug("Checking openings: %s", self.opening_entities)
        _LOGGER.debug("hvac_mode_scope: %s", hvac_mode_scope)

        if (
            # the requester doesn't care about the scope or defaultt
            hvac_mode_scope == OpeningHvacModeScope.ALL
            # the requester sets it's scope and it's in the scope
            # in case of ALL, it's always in the scope
            or (
                self.openings_scope != [OpeningHvacModeScope.ALL]
                and hvac_mode_scope in self.openings_scope
            )
            # the scope is not restricted at all
            or OpeningHvacModeScope.ALL in self.openings_scope
        ):
            for opening in self.openings:
                if self._is_opening_open(opening):
                    _is_open = True
                    break

        return _is_open

    def _is_opening_open(self, opening: TIMED_OPENING_SCHEMA) -> bool:  # type: ignore
        """If the opening is currently open."""

        # the opening is closed or unavailable
        if not self._is_opening_available(opening):
            _LOGGER.debug("Opening %s is not available.", opening)
            return False

        is_open = self._is_opening_open_state(opening)
        # check timeout
        if self._has_timeout_mode(opening):
            _LOGGER.debug(
                "Have timeout mode for opening: %s, is open: %s",
                opening,
                is_open,
            )
            if self._is_opening_timed_out(opening, is_open):
                return is_open
            return not is_open

        _LOGGER.debug(
            "No timeout mode for opening %s, is open: %s.",
            opening,
            is_open,
        )
        return is_open

    def _is_opening_timed_out(self, opening: TIMED_OPENING_SCHEMA, check_open: True) -> bool:  # type: ignore
        opening_entity = opening[ATTR_ENTITY_ID]

        _LOGGER.debug(
            "Checking if opening %s is timed out, state: %s, timeout: %s, waiting state: %s",
            opening,
            self.hass.states.get(opening_entity),
            opening[ATTR_TIMEOUT],
            STATE_OPEN if check_open else STATE_CLOSED,
        )
        if condition.state(
            self.hass,
            opening_entity,
            STATE_OPEN if check_open else STATE_CLOSED,
            opening[ATTR_TIMEOUT],
        ) or condition.state(
            self.hass,
            opening_entity,
            STATE_ON if check_open else STATE_OFF,
            opening[ATTR_TIMEOUT],
        ):
            return True
        return False
