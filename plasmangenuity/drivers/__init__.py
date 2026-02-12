"""HID driver registry for brand-specific mouse protocols."""

from typing import List, Type
from plasmangenuity.drivers.base import HidMouseDriver

_registry: List[Type[HidMouseDriver]] = []


def register_driver(driver_cls: Type[HidMouseDriver]) -> None:
    """Register a HID mouse driver class."""
    if driver_cls not in _registry:
        _registry.append(driver_cls)


def get_registered_drivers() -> List[Type[HidMouseDriver]]:
    """Return all registered driver classes."""
    return list(_registry)


# Auto-register built-in drivers on import.
from plasmangenuity.drivers.hyperx import HyperXPulsefireDriver  # noqa: E402
register_driver(HyperXPulsefireDriver)
