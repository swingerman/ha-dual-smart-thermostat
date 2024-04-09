from enum import StrEnum
from itertools import chain

from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_external import (
    HVACActionReasonExternal,
)
from custom_components.dual_smart_thermostat.hvac_action_reason.hvac_action_reason_internal import (
    HVACActionReasonInternal,
)

SET_HVAC_ACTION_REASON_SIGNAL = "set_hvac_action_reason_signal_{}"
SERVICE_SET_HVAC_ACTION_REASON = "set_hvac_action_reason"


class HVACActionReason(StrEnum):
    """HVAC Action Reason for climate devices."""

    _ignore_ = "member cls"
    cls = vars()
    for member in chain(list(HVACActionReasonInternal), list(HVACActionReasonExternal)):
        cls[member.name] = member.value

    NONE = ""
