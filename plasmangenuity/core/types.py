"""Core data types for the unified battery monitoring system."""

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Any


class ConnectionType(Enum):
    """How the mouse is connected."""
    USB_DONGLE = auto()
    BLUETOOTH_LE = auto()
    WIRED = auto()
    UNKNOWN = auto()


class ProviderType(Enum):
    """How the battery data was obtained."""
    UPOWER = auto()
    SYSFS = auto()
    HID_PROPRIETARY = auto()


@dataclass(frozen=True)
class DeviceId:
    """Unique identifier for a device across providers.

    Uses (vendor_id, product_id) when available from HID/UPower,
    or the provider-specific path as a stable identifier.
    """
    provider: ProviderType
    path: str

    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    serial: Optional[str] = None

    @property
    def stable_key(self) -> str:
        """Key for deduplication across providers.

        If we have VID:PID:serial, use that so the same physical device
        is recognized regardless of which provider found it first.
        Falls back to provider-specific path.
        """
        if self.vendor_id and self.product_id and self.serial:
            return f"{self.vendor_id:04x}:{self.product_id:04x}:{self.serial}"
        if self.vendor_id and self.product_id:
            return f"{self.vendor_id:04x}:{self.product_id:04x}"
        return self.path


@dataclass
class BatteryReading:
    """A single battery status reading."""
    percent: Optional[int] = None
    is_charging: bool = False
    provider: ProviderType = ProviderType.UPOWER
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class Capabilities:
    """What features a device supports beyond battery reading."""
    battery: bool = True
    dpi: bool = False
    led: bool = False
    buttons: bool = False
    macros: bool = False
    polling_rate: bool = False
    firmware_query: bool = False


@dataclass
class DeviceInfo:
    """Complete information about a discovered device."""
    device_id: DeviceId
    name: str
    brand: str = "Unknown"
    model: str = ""
    connection: ConnectionType = ConnectionType.UNKNOWN
    capabilities: Capabilities = field(default_factory=Capabilities)
    battery: Optional[BatteryReading] = None
    firmware: Optional[str] = None
    vendor_id: Optional[int] = None
    product_id: Optional[int] = None
    driver_name: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
