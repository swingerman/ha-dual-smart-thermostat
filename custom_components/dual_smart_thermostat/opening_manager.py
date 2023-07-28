"""Opening Manager for Dual Smart Thermostat"""


import logging
from typing import List

from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ON,
    STATE_OPEN,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)

from homeassistant.core import HomeAssistant

from homeassistant.helpers import condition

from custom_components.dual_smart_thermostat.const import (
    ATTR_TIMEOUT,
    TIMED_OPENING_SCHEMA,
)


_LOGGER = logging.getLogger(__name__)


class OpeningManager:
    """Opening Manager for Dual Smart Thermostat"""

    def __init__(self, hass: HomeAssistant, openings):
        self.hass = hass
        self.openings = self.conform_openings_list(openings) if openings else []
        self.opening_entities = (
            self.conform_opnening_entities(self.openings) if openings else []
        )

    @staticmethod
    def conform_openings_list(openings: list) -> list:
        """Return a list of openings from a list of entities"""
        return list(
            map(
                lambda entry: entry
                if isinstance(entry, dict)
                else {ATTR_ENTITY_ID: entry, ATTR_TIMEOUT: None},
                openings,
            )
        )

    @staticmethod
    def conform_opnening_entities(openings: [TIMED_OPENING_SCHEMA]) -> List:
        """Return a list of entities from a list of openings"""
        return list(map(lambda entry: entry[ATTR_ENTITY_ID], openings))

    @property
    def any_opening_open(self) -> bool:
        """If any opening is currently open."""
        _LOGGER.debug("_any_opening_open")
        if not self.opening_entities:
            return False

        _is_open = False
        for opening in self.openings:
            if self._is_opening_open(opening):
                _is_open = True
                break

        return _is_open

    def _is_opening_open(self, opening: TIMED_OPENING_SCHEMA):
        """If the opening is currently open."""
        opening_entity = opening[ATTR_ENTITY_ID]
        opening_entity_state = self.hass.states.get(opening_entity)
        _is_open = False
        if (
            opening_entity_state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)
            and opening[ATTR_TIMEOUT] is not None
            and self._is_opening_timed_out(opening)
        ):
            _is_open = True
            _LOGGER.debug(
                "Have timeout mode for opening %s, is open: %s",
                opening,
                _is_open,
            )
        else:
            if self.hass.states.is_state(
                opening_entity, STATE_OPEN
            ) or self.hass.states.is_state(opening_entity, STATE_ON):
                _is_open = True
            _LOGGER.debug(
                "No timeout mode for opening %s, is open: %s.",
                opening_entity,
                _is_open,
            )
        return _is_open

    def _is_opening_timed_out(self, opening: TIMED_OPENING_SCHEMA) -> bool:
        opening_entity = opening[ATTR_ENTITY_ID]
        _is_open = False
        if condition.state(
            self.hass,
            opening_entity,
            STATE_OPEN,
            opening[ATTR_TIMEOUT],
        ) or condition.state(
            self.hass,
            opening_entity,
            STATE_ON,
            opening[ATTR_TIMEOUT],
        ):
            _is_open = True
        return _is_open
