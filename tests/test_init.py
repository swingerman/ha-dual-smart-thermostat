import asyncio
import pytest

from homeassistant.core import HomeAssistant


async def setup_component(hass: HomeAssistant):
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, HASS_DOMAIN, {})
    await hass.async_block_till_done()
