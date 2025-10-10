"""Test the set_hvac_action_reason service integration."""

from homeassistant.core import HomeAssistant

from custom_components.dual_smart_thermostat.const import ATTR_HVAC_ACTION_REASON
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason import (
    HVACActionReason,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_external import (
    HVACActionReasonExternal,
)

from . import common, setup_comp_heat, setup_sensor, setup_switch  # noqa: F401


async def test_service_set_hvac_action_reason_presence(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test setting HVAC action reason to PRESENCE."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.PRESENCE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.PRESENCE
    )


async def test_service_set_hvac_action_reason_schedule(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test setting HVAC action reason to SCHEDULE."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.SCHEDULE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.SCHEDULE
    )


async def test_service_set_hvac_action_reason_emergency(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test setting HVAC action reason to EMERGENCY."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.EMERGENCY
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.EMERGENCY
    )


async def test_service_set_hvac_action_reason_malfunction(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test setting HVAC action reason to MALFUNCTION."""
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == HVACActionReason.NONE

    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.MALFUNCTION
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.MALFUNCTION
    )


async def test_service_set_hvac_action_reason_invalid(
    hass: HomeAssistant, setup_comp_heat, caplog  # noqa: F811
) -> None:
    """Test setting HVAC action reason with invalid value logs error."""
    state = hass.states.get(common.ENTITY)
    initial_reason = state.attributes.get(ATTR_HVAC_ACTION_REASON)
    assert initial_reason == HVACActionReason.NONE

    # Try to set an invalid reason
    await common.async_set_hvac_action_reason(hass, common.ENTITY, "invalid_reason")
    await hass.async_block_till_done()

    # State should remain unchanged
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == initial_reason

    # Check that error was logged
    assert "Invalid HVACActionReasonExternal: invalid_reason" in caplog.text


async def test_service_set_hvac_action_reason_empty_string_rejected(
    hass: HomeAssistant, setup_comp_heat, caplog  # noqa: F811
) -> None:
    """Test that empty string is rejected as invalid external reason."""
    # First set a valid reason
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.SCHEDULE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.SCHEDULE
    )

    # Try to clear it with empty string - should be rejected
    await common.async_set_hvac_action_reason(hass, common.ENTITY, "")
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    # Empty string is not a valid external reason, so state should not change
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.SCHEDULE
    )
    # Check that error was logged
    assert "Invalid HVACActionReasonExternal:" in caplog.text


async def test_service_set_hvac_action_reason_no_entity_id(
    hass: HomeAssistant, setup_comp_heat, caplog  # noqa: F811
) -> None:
    """Test service call without entity_id parameter."""
    state = hass.states.get(common.ENTITY)
    initial_reason = state.attributes.get(ATTR_HVAC_ACTION_REASON)

    # Call service without entity_id - service should not crash
    # but also should not change state since no entity is targeted
    await common.async_set_hvac_action_reason(
        hass, None, HVACActionReasonExternal.SCHEDULE
    )
    await hass.async_block_till_done()

    # State should remain unchanged because no entity was targeted
    state = hass.states.get(common.ENTITY)
    assert state.attributes.get(ATTR_HVAC_ACTION_REASON) == initial_reason


async def test_service_set_hvac_action_reason_state_persistence(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that action reason persists across multiple reads."""
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.SCHEDULE
    )
    await hass.async_block_till_done()

    # Read state multiple times
    for _ in range(3):
        state = hass.states.get(common.ENTITY)
        assert (
            state.attributes.get(ATTR_HVAC_ACTION_REASON)
            == HVACActionReasonExternal.SCHEDULE
        )
        await hass.async_block_till_done()


async def test_service_set_hvac_action_reason_overwrite(
    hass: HomeAssistant, setup_comp_heat  # noqa: F811
) -> None:
    """Test that setting a new reason overwrites the previous one."""
    # Set initial reason
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.PRESENCE
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.PRESENCE
    )

    # Overwrite with different reason
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.EMERGENCY
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.EMERGENCY
    )

    # Overwrite again
    await common.async_set_hvac_action_reason(
        hass, common.ENTITY, HVACActionReasonExternal.MALFUNCTION
    )
    await hass.async_block_till_done()

    state = hass.states.get(common.ENTITY)
    assert (
        state.attributes.get(ATTR_HVAC_ACTION_REASON)
        == HVACActionReasonExternal.MALFUNCTION
    )
