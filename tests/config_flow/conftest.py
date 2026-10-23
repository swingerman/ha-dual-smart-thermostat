"""Config flow test fixtures."""

from unittest.mock import patch

import pytest

from custom_components.dual_smart_thermostat.flow_utils import ExcludeOwnEntity


@pytest.fixture
def real_entity_registry():
    """Opt in to the real entity registry lookup of the entry's own entity."""


@pytest.fixture(autouse=True)
def _flows_have_no_own_entity(request):
    """Most flow tests run on a Mock hass and entry: no entity registry to look in."""
    if "real_entity_registry" in request.fixturenames:
        yield
        return
    with patch.object(ExcludeOwnEntity, "_own_entity_ids", return_value=[]):
        yield
