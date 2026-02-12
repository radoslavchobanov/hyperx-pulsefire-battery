"""Abstract base class for battery providers."""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable

from plasmangenuity.core.types import DeviceInfo, DeviceId, BatteryReading


class BatteryProvider(ABC):
    """A source of battery data for wireless mice.

    Implementations:
    - UPowerProvider: D-Bus UPower daemon
    - SysfsProvider: /sys/class/power_supply/
    - HidDriverProvider: Proprietary HID protocols via brand-specific drivers
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name (e.g., 'UPower')."""
        ...

    @property
    @abstractmethod
    def priority(self) -> int:
        """Lower = preferred. UPower=10, sysfs=20, HID=30."""
        ...

    @abstractmethod
    def discover(self) -> List[DeviceInfo]:
        """Scan for wireless mice and return found devices.

        Called periodically by the DeviceManager. Should be reasonably fast.
        """
        ...

    @abstractmethod
    def read_battery(self, device_id: DeviceId) -> Optional[BatteryReading]:
        """Read current battery level for a specific device.

        Returns BatteryReading or None if device is no longer available.
        """
        ...

    def supports_hotplug(self) -> bool:
        """Whether this provider can emit hotplug callbacks."""
        return False

    def start_watching(self, on_change: Callable[[], None]) -> None:
        """Start monitoring for device add/remove events.

        Args:
            on_change: Callback when devices change (debounced by manager).
        """
        pass

    def stop_watching(self) -> None:
        """Stop monitoring for device events."""
        pass

    def close(self) -> None:
        """Clean up resources."""
        pass
