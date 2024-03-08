from homeassistant.core import DOMAIN, HomeAssistant
from homeassistant.setup import async_setup_component
from homeassistant.util.unit_system import METRIC_SYSTEM


async def setup_component(hass: HomeAssistant) -> None:
    """Initialize components."""
    hass.config.units = METRIC_SYSTEM
    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()
