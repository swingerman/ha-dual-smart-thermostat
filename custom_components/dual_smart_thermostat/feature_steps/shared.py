"""Shared helpers for feature step handlers."""

from __future__ import annotations

from typing import Any, Dict


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
        if states is not None and hasattr(states, "values"):
            try:
                ctx["hass"] = {"states": {s.entity_id: s for s in states.values()}}
            except Exception:
                # If snapshot fails, skip it (schema factories will handle missing hass)
                pass

    return ctx
