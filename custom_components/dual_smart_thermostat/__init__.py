"""The dual_smart_thermostat component."""

import logging

from homeassistant.config_entries import ConfigEntry, SOURCE_IMPORT
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "dual_smart_thermostat"
PLATFORMS = [Platform.CLIMATE]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Dual Smart Thermostat component from YAML (one-time import)."""
    if DOMAIN not in config:
        return True

    _LOGGER.info(
        "YAML configuration detected for Dual Smart Thermostat. "
        "Starting automatic import to UI configuration..."
    )

    # Import each YAML configuration to config entry
    for platform_config in config[DOMAIN]:
        # Check if already imported (avoid duplicates)
        unique_id = platform_config.get(CONF_UNIQUE_ID)
        name = platform_config.get(CONF_NAME, "Dual Smart Thermostat")

        existing_entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if (unique_id and entry.unique_id == unique_id)
            or entry.title == name
        ]

        if existing_entries:
            _LOGGER.warning(
                "Skipping YAML import for '%s' - already exists as UI configuration entry",
                name,
            )
            continue

        # Trigger import flow
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=platform_config,
            )
        )

    # Show deprecation notice
    hass.components.persistent_notification.async_create(
        "YAML configuration for Dual Smart Thermostat has been automatically "
        "imported to UI configuration entries.\n\n"
        "You can now manage your thermostats from the UI (Settings → Devices & Services).\n\n"
        "Please remove the 'dual_smart_thermostat:' section from your configuration.yaml file.",
        title="Dual Smart Thermostat - YAML Import Complete",
        notification_id=f"{DOMAIN}_yaml_import_complete",
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update listener, called when the config entry options are changed."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
