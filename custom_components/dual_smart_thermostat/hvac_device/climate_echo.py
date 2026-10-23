"""Echo tracking for a shared climate entity.

Tells the thermostats' own commands (and the device's side effects of them)
from changes made on the device by someone else.
"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
from typing import Any, NamedTuple

from homeassistant.components.climate import ATTR_FAN_MODE
from homeassistant.const import ATTR_ASSUMED_STATE, ATTR_TEMPERATURE
from homeassistant.core import Context, State
from homeassistant.util import dt as dt_util

from .entity_port import is_unavailable

_MAX_PENDING = 4
# HA stamps a state write with the entity's last service context for this long
# (CONTEXT_RECENT_TIME_SECONDS): a device reacting to our command reports under it.
_OWN_CONTEXT_WINDOW = timedelta(seconds=5)


@dataclass
class ExternalReport:
    """What a state report of a child means for one thermostat."""

    changed: set[str] = field(default_factory=set)  # attributes changed from outside
    fan_dropped: bool = False  # the device dropped our fan: send it again, once


class _Expected(NamedTuple):
    """A value `origin` commanded and nobody has seen reported yet."""

    value: Any
    origin: Any
    at: datetime


def _enter(counts: dict, key: Any) -> bool:
    """Depth-counted bracket: True when this is the outermost entry."""
    counts[key] = counts.get(key, 0) + 1
    return counts[key] == 1


def _leave(counts: dict, key: Any) -> bool:
    """True when this closes the outermost entry."""
    counts[key] -= 1
    return counts[key] == 0


_TRACKED = (
    ("mode", lambda s: s.state),
    ("target", lambda s: s.attributes.get(ATTR_TEMPERATURE)),
    ("fan_mode", lambda s: s.attributes.get(ATTR_FAN_MODE)),
)


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, abs_tol=1e-6)
    return a == b


class ClimateEcho:
    """What each thermostat on one climate child commanded and has not yet seen back.

    Owned by a ClimateChild. `owners` names the thermostats currently on the child.
    """

    def __init__(self, owners: Callable[[], set[Any]]) -> None:
        self._owners = owners
        # Per owner (the thermostat): what it commanded and has not yet seen reported.
        self._pending: dict[Any, dict[str, list[_Expected]]] = {}
        self._sending: dict[Any, int] = {}
        self._fan_sent: set[Any] = set()  # owners whose sequence has sent its fan
        self._own_contexts: dict[str, datetime] = {}  # contexts of our recent commands
        self._last_fan: dict[Any, str] = {}  # owner -> the fan it commanded last
        self._fan_resent: set[Any] = set()  # ... and have, in this sequence
        self._adopting: dict[Any, int] = {}
        self._deferred: dict[Any, Callable[[], None]] = {}

    def is_adopting(self, owner: Any) -> bool:
        return bool(self._adopting.get(owner))

    def fan_commanded(self, owner: Any, fan_mode: str) -> None:
        self._fan_sent.add(owner)
        self._last_fan[owner] = fan_mode

    @contextmanager
    def sending(self, owner: Any):
        """DST sends a sequence: changes reported meanwhile are the device's side effects."""
        if _enter(self._sending, owner):
            self._fan_sent.discard(owner)
            self._fan_resent.discard(owner)
        try:
            yield
        finally:
            _leave(self._sending, owner)
            if not any(self._sending.values()):
                deferred, self._deferred = self._deferred, {}
                for run in deferred.values():
                    run()

    def defer_while_sending(self, owner: Any, run: Callable[[], None]) -> bool:
        """Run `run` once nobody is sending to the child any more.

        Another thermostat's turn-on is a sequence of events (mode, target, fan);
        adopting from the first one would read a half-finished child. Returns
        False (and does nothing) when the child is idle, so the caller runs now.
        """
        if not any(self._sending.values()):
            return False
        self._deferred[owner] = run
        return True

    @contextmanager
    def adopting(self, owner: Any):
        """This owner adopts the child's state: its commands to the child are dropped."""
        _enter(self._adopting, owner)
        try:
            yield
        finally:
            _leave(self._adopting, owner)

    def _observers(self, origin: Any) -> set[Any]:
        """Every thermostat on this child: a command of one is an echo for all."""
        return self._owners() | {origin}

    def own_context(self, parent: Context | None) -> Context:
        """A fresh context for one of our commands (logbook attribution only)."""
        context = Context(parent_id=parent.id if parent else None)
        now = dt_util.utcnow()
        self._own_contexts[context.id] = now
        for stale in [
            i for i, at in self._own_contexts.items() if now - at > _OWN_CONTEXT_WINDOW
        ]:
            del self._own_contexts[stale]
        return context

    def expect(self, origin: Any, expect: dict[str, Any]) -> None:
        """Record the values `origin` commanded and nobody has seen reported yet.

        Peers record them too, so a command of a thermostat (its own control, such
        as a safety stop, as much as the user's) is never taken for the user acting
        on the device by another thermostat sharing the child.
        """
        observers, now = self._observers(origin), dt_util.utcnow()
        for attr, value in expect.items():
            for observer in observers:
                pending = self._pending.setdefault(observer, {}).setdefault(attr, [])
                pending.append(_Expected(value, origin, now))
                del pending[:-_MAX_PENDING]

    def retract(self, origin: Any, attr: str, value: Any) -> None:
        for observer in self._observers(origin):
            pending = self._pending.get(observer, {}).get(attr, [])
            for index in range(len(pending) - 1, -1, -1):
                entry = pending[index]
                if entry.origin is origin and _same(entry.value, value):
                    del pending[index]
                    break

    def clear(self, origin: Any) -> None:
        """Forget what `origin` commanded (after its adoption, or when it goes away)."""
        for attrs in self._pending.values():
            for attr, pending in attrs.items():
                attrs[attr] = [e for e in pending if e.origin is not origin]

    def forget(self, owner: Any) -> None:
        """The thermostat is going away: no record of it may outlive it."""
        self.clear(owner)
        for record in (
            self._pending,
            self._sending,
            self._adopting,
            self._deferred,
            self._last_fan,
        ):
            record.pop(owner, None)
        self._fan_sent.discard(owner)
        self._fan_resent.discard(owner)

    def reset(self, observer: Any) -> None:
        """The child went away: nothing pending is meaningful any more."""
        self._pending.pop(observer, None)

    def external(
        self, owner: Any, old: State | None, new: State | None
    ) -> ExternalReport:
        """Consume this owner's echoes; the attributes that changed from outside.

        Judged by value against what this owner commanded and has not yet seen
        reported. Contexts and time play no part: HA stamps a write within 5 s of
        a service call with the caller's context, and a polled device reports
        late.
        """
        if is_unavailable(old) or is_unavailable(new):
            self.reset(owner)  # first sight and reconnect adopt nothing
            return ExternalReport()
        if old.attributes.get(ATTR_ASSUMED_STATE) or new.attributes.get(
            ATTR_ASSUMED_STATE
        ):
            return ExternalReport()  # an assumed child reports DST's own record
        external: set[str] = set()
        fan_dropped = False
        for attr, read in _TRACKED:
            before, after = read(old), read(new)
            if after is None or _same(before, after):
                continue
            pending = self._pending.get(owner, {}).get(attr, [])
            match = next(
                (i for i, entry in enumerate(pending) if _same(entry.value, after)),
                None,
            )
            if match is not None:
                del pending[match]  # an echo of ours; any order is fine
            else:
                external.add(attr)
                # The device moved on without reporting what was commanded: the
                # expectations recorded before this report are stale and must not
                # swallow a later press (a peer's command sent since is kept).
                pending[:] = [e for e in pending if e.at >= new.last_updated]
        if "fan_mode" in external and self._dropped_by_device(owner, new):
            # The device answered our own command with its default (a power-on
            # reset): not the user. Say it again once, adopt nothing.
            external.discard("fan_mode")
            if owner not in self._fan_resent:
                self._fan_resent.add(owner)
                fan_dropped = True
        if self._sending.get(owner):
            # Side effects of the sequence (a mode that resets the fan) are not the
            # user's; but the fan is the last thing sent, so a fan reported after
            # it was sent is someone else's last word.
            external = external & {ATTR_FAN_MODE} if owner in self._fan_sent else set()
        return ExternalReport(external, fan_dropped)

    def pending_mode(self, owner: Any) -> str | None:
        """The last mode `owner` commanded that the device has not reported yet."""
        pending = self._pending.get(owner, {}).get("mode", [])
        return next((e.value for e in reversed(pending) if e.origin is owner), None)

    def _dropped_by_device(self, owner: Any, new: State) -> bool:
        """A fan reported under the context of our own command, not what we sent.

        HA stamps a write with the entity's last service context while it is
        recent, so a device reacting to our command carries ours; an automation
        or the UI carries their own. (A remote press within seconds of our
        command would carry ours too: it is overridden once.)
        """
        sent = self._last_fan.get(owner)
        at = self._own_contexts.get(new.context.id)
        return (
            sent is not None
            and at is not None
            and dt_util.utcnow() - at <= _OWN_CONTEXT_WINDOW
            and not _same(new.attributes.get(ATTR_FAN_MODE), sent)
        )
