from enum import StrEnum
from itertools import chain

SET_HVAC_ACTION_REASON_SIGNAL = "set_hvac_action_reason_signal_{}"
SERVICE_SET_HVAC_ACTION_REASON = "set_hvac_action_reason"


class HVACActionReasonExternal(StrEnum):
    """External HVAC Action Reason for climate devices."""

    PRESENCE = "presence"

    SCHEDULE = "schedule"

    EMERGENCY = "emergency"

    MALFUNCTION = "malfunction"


class HVACActionReasonInternal(StrEnum):
    """Internal HVAC Action Reason for climate devices."""

    TARGET_TEMP_NOT_REACHED = "target_temp_not_reached"

    TARGET_TEMP_REACHED = "target_temp_reached"

    MISCONFIGURATION = "misconfiguration"

    OPENING = "opening"

    LIMIT = "limit"

    OVERHEAT = "overheat"


class HVACActionReason(StrEnum):
    """HVAC Action Reason for climate devices."""

    _ignore_ = "member cls"
    cls = vars()
    for member in chain(list(HVACActionReasonInternal), list(HVACActionReasonExternal)):
        cls[member.name] = member.value

    NONE = ""
