"""Multi-switch HVAC device that controls multiple entities as one unit."""

from datetime import timedelta
import logging
from typing import List

from homeassistant.components.climate import HVACAction, HVACMode
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import DOMAIN as HA_DOMAIN, Context, HomeAssistant

from custom_components.dual_smart_thermostat.hvac_device.generic_hvac_device import (
    GenericHVACDevice,
)
from custom_components.dual_smart_thermostat.hvac_controller.hvac_controller import (
    HvacGoal,
)
from custom_components.dual_smart_thermostat.managers.environment_manager import (
    EnvironmentManager,
)
from custom_components.dual_smart_thermostat.managers.feature_manager import (
    FeatureManager,
)
from custom_components.dual_smart_thermostat.managers.hvac_power_manager import (
    HvacPowerManager,
)
from custom_components.dual_smart_thermostat.managers.opening_manager import (
    OpeningManager,
)

_LOGGER = logging.getLogger(__name__)


class MultiSwitchDevice(GenericHVACDevice):
    """A generic HVAC device that controls multiple switch entities as one unit."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_ids: List[str],
        min_cycle_duration: timedelta,
        initial_hvac_mode: HVACMode,
        environment: EnvironmentManager,
        openings: OpeningManager,
        features: FeatureManager,
        hvac_power: HvacPowerManager,
        hvac_goal: HvacGoal,
    ) -> None:
        # Use the first entity ID as the primary for compatibility
        primary_entity_id = entity_ids[0] if entity_ids else None
        super().__init__(
            hass,
            primary_entity_id,
            min_cycle_duration,
            initial_hvac_mode,
            environment,
            openings,
            features,
            hvac_power,
            hvac_goal,
        )
        
        self._entity_ids = entity_ids
        self._device_type = f"{self.__class__.__name__}({len(entity_ids)} switches)"

    def get_device_ids(self) -> List[str]:
        """Return all controlled entity IDs."""
        return self._entity_ids.copy()

    @property
    def is_on(self) -> bool:
        """Return True if any of the switches is on."""
        for entity_id in self._entity_ids:
            state = self.hass.states.get(entity_id)
            if state and state.state == STATE_ON:
                return True
        return False

    async def async_turn_on(self):
        """Turn on all switches."""
        _LOGGER.info(
            "%s. Turning on entities %s",
            self.__class__.__name__,
            self._entity_ids,
        )

        if not self._entity_ids:
            return

        for entity_id in self._entity_ids:
            if entity_id and self.hass.states.is_state(entity_id, STATE_OFF):
                _LOGGER.debug("Turning on entity %s", entity_id)
                try:
                    await self.hass.services.async_call(
                        HA_DOMAIN,
                        SERVICE_TURN_ON,
                        {ATTR_ENTITY_ID: entity_id},
                        context=self._context,
                        blocking=True,
                    )
                except Exception as e:
                    _LOGGER.error(
                        "Error turning on entity %s. Error: %s", entity_id, e
                    )

    async def async_turn_off(self):
        """Turn off all switches."""
        _LOGGER.info(
            "%s. Turning off entities %s",
            self.__class__.__name__,
            self._entity_ids,
        )

        if not self._entity_ids:
            return

        for entity_id in self._entity_ids:
            if entity_id and self.hass.states.is_state(entity_id, STATE_ON):
                _LOGGER.debug("Turning off entity %s", entity_id)
                try:
                    await self.hass.services.async_call(
                        HA_DOMAIN,
                        SERVICE_TURN_OFF,
                        {ATTR_ENTITY_ID: entity_id},
                        context=self._context,
                        blocking=True,
                    )
                except Exception as e:
                    _LOGGER.error(
                        "Error turning off entity %s. Error: %s", entity_id, e
                    )

        self.hvac_power.update_hvac_power(
            self.strategy, self.target_env_attr, HVACAction.OFF
        )

    async def _async_turn_on_entity(self) -> None:
        """Turn on all entities (override from parent)."""
        await self.async_turn_on()

    async def _async_turn_off_entity(self) -> None:
        """Turn off all entities (override from parent)."""
        await self.async_turn_off()