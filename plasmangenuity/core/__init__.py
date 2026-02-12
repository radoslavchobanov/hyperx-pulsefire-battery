"""Core abstractions for unified multi-device battery monitoring."""

from plasmangenuity.core.types import (
    ConnectionType,
    ProviderType,
    DeviceId,
    BatteryReading,
    Capabilities,
    DeviceInfo,
)
from plasmangenuity.core.provider import BatteryProvider
from plasmangenuity.core.manager import DeviceManager

__all__ = [
    "ConnectionType",
    "ProviderType",
    "DeviceId",
    "BatteryReading",
    "Capabilities",
    "DeviceInfo",
    "BatteryProvider",
    "DeviceManager",
]
