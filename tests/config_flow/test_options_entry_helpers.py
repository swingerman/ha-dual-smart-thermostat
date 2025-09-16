from types import SimpleNamespace

from custom_components.dual_smart_thermostat.options_flow import (
    DualSmartThermostatOptionsFlow,
)


def test_get_entry_fallback_and_instance_attr():
    """Verify _get_entry and config_entry property fall back to initial entry.

    - When the instance has no `config_entry` attribute, both _get_entry()
      and the config_entry property should return the initially passed
      config entry object.
    - When an instance attribute `config_entry` is set (simulating Home
      Assistant runtime), both accessors should return that instance
      attribute.
    """
    initial = SimpleNamespace(data={"foo": "bar"}, options={})
    handler = DualSmartThermostatOptionsFlow(initial)

    # Before HA sets the instance attribute, _get_entry() should return the fallback
    assert handler._get_entry() is initial
    assert handler.config_entry is initial

    # Simulate Home Assistant setting the attribute on the handler
    runtime_entry = SimpleNamespace(data={"baz": "qux"}, options={})
    handler.__dict__["config_entry"] = runtime_entry

    # Now both should return the runtime instance attribute
    assert handler._get_entry() is runtime_entry
    assert handler.config_entry is runtime_entry
