"""Shared helpers for feature step handlers."""

from __future__ import annotations

import inspect
from typing import Any, Dict
from unittest.mock import AsyncMock


def build_schema_context_from_flow(
    flow_instance, collected_config: dict, current_config: dict | None = None
) -> Dict[str, Any]:
    """Return a lightweight schema context containing a hass states snapshot and merged configs.

    This avoids passing Home Assistant objects directly into schema factories (which may be
    test Mocks) and provides a consistent shape for both config and options flows.
    """
    ctx: dict[str, Any] = dict(collected_config or {})

    # Merge current_config for options flows so defaults and selectors can read persisted values
    if current_config:
        # Do not overwrite explicit collected flags
        for k, v in current_config.items():
            ctx.setdefault(k, v)

    # Build a minimal hass snapshot if available and iterable
    hass = getattr(flow_instance, "hass", None)
    if hass is not None:
        states = getattr(hass, "states", None)
        if states is not None:
            values_attr = getattr(states, "values", None)
            if values_attr is not None:
                try:
                    # If `values` is an AsyncMock or a coroutine function, don't call it
                    # (calling would create a coroutine that's not awaited in this
                    # synchronous helper). For normal dict-like `values()` methods,
                    # call and iterate the returned collection.
                    if callable(values_attr):
                        if isinstance(
                            values_attr, AsyncMock
                        ) or inspect.iscoroutinefunction(values_attr):
                            # Tests may supply AsyncMock for states.values — skip
                            # snapshot in that case to avoid creating un-awaited
                            # coroutine objects.
                            maybe_values = None
                        else:
                            maybe_values = values_attr()
                    else:
                        maybe_values = values_attr

                    if maybe_values is None:
                        # Skip snapshot when we can't synchronously obtain values.
                        pass
                    elif inspect.isawaitable(maybe_values):
                        # Safety: if calling produced an awaitable (unexpected), skip it
                        # rather than create a coroutine warning.
                        pass
                    else:
                        # Build a simple mapping of entity_id -> state object. Use
                        # getattr for entity_id in case test mocks omit it.
                        ctx["hass"] = {
                            "states": {
                                getattr(s, "entity_id", None): s for s in maybe_values
                            }
                        }
                except Exception:
                    # If snapshot fails, skip it (schema factories will handle missing hass)
                    pass

    return ctx
