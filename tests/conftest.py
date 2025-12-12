"""Global fixtures for knmi integration."""

# Fixtures allow you to replace functions with a Mock object. You can perform
# many options via the Mock to reflect a particular behavior from the original
# function that you want to see without going through the function's actual logic.
# Fixtures can either be passed into tests as parameters, or if autouse=True, they
# will automatically be used across all tests.
#
# Fixtures that are defined in conftest.py are available across all tests. You can also
# define fixtures within a particular test file to scope them locally.
#
# pytest_homeassistant_custom_component provides some fixtures that are provided by
# Home Assistant core. You can find those fixture definitions here:
# https://github.com/MatthewFlamm/pytest-homeassistant-custom-component/blob/master/pytest_homeassistant_custom_component/common.py
#
# See here for more info: https://docs.pytest.org/en/latest/fixture.html (note that
# pytest includes fixtures OOB which you can use as defined on this page)

from homeassistant.core import HomeAssistant
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
async def setup_template_test_entities(hass: HomeAssistant):
    """Set up helper entities for template testing."""
    # Helper entity for simple template tests
    hass.states.async_set("input_number.away_temp", "18", {"unit_of_measurement": "°C"})
    hass.states.async_set("input_number.eco_temp", "20", {"unit_of_measurement": "°C"})
    hass.states.async_set(
        "input_number.comfort_temp", "22", {"unit_of_measurement": "°C"}
    )

    # Season sensor for conditional template tests
    hass.states.async_set("sensor.season", "winter")

    # Outdoor temperature for calculated template tests
    hass.states.async_set("sensor.outdoor_temp", "20", {"unit_of_measurement": "°C"})

    # Binary sensor for presence-based templates
    hass.states.async_set("binary_sensor.someone_home", "on")

    await hass.async_block_till_done()
    return hass
