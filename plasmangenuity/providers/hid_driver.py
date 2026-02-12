"""HID driver provider - battery via brand-specific proprietary HID protocols."""

import logging
import threading
from typing import List, Optional, Dict, Callable

import hid

from plasmangenuity.core.types import (
    DeviceInfo, DeviceId, BatteryReading, Capabilities,
    ConnectionType, ProviderType,
)
from plasmangenuity.core.provider import BatteryProvider
from plasmangenuity.drivers import get_registered_drivers
from plasmangenuity.drivers.base import HidMouseDriver

log = logging.getLogger(__name__)


class HidDriverProvider(BatteryProvider):
    """Battery provider that uses proprietary HID protocols via driver plugins.

    Enumerates HID devices and matches them against registered drivers.
    Manages driver instances and delegates battery reads.
    """

    @property
    def name(self) -> str:
        return "HID"

    @property
    def priority(self) -> int:
        return 30

    def __init__(self):
        # stable_key -> (driver_instance, hid_device_info_dict)
        self._active: Dict[str, HidMouseDriver] = {}
        self._device_infos: Dict[str, dict] = {}  # stable_key -> raw HID enum dict
        self._watch_callback: Optional[Callable[[], None]] = None
        self._watch_thread: Optional[threading.Thread] = None
        self._watching = False

    def discover(self) -> List[DeviceInfo]:
        drivers = get_registered_drivers()
        if not drivers:
            return []

        results = []
        seen_keys = set()

        # Gather all vendor IDs from registered drivers to narrow enumeration.
        # For now, enumerate everything and let drivers match.
        try:
            all_hid = hid.enumerate()
        except Exception:
            log.debug("HID enumeration failed")
            return []

        for hid_info in all_hid:
            vid = hid_info.get("vendor_id", 0)
            pid = hid_info.get("product_id", 0)
            usage = hid_info.get("usage_page", 0)
            iface = hid_info.get("interface_number", -1)

            for driver_cls in drivers:
                if not driver_cls.match(vid, pid, usage, iface):
                    continue

                device_id = DeviceId(
                    provider=ProviderType.HID_PROPRIETARY,
                    path=hid_info["path"].decode()
                        if isinstance(hid_info["path"], bytes)
                        else hid_info["path"],
                    vendor_id=vid,
                    product_id=pid,
                    serial=hid_info.get("serial_number"),
                )
                key = device_id.stable_key
                if key in seen_keys:
                    break
                seen_keys.add(key)

                # Determine connection type from product ID heuristics
                product_str = hid_info.get("product_string", "") or ""
                conn = ConnectionType.UNKNOWN
                # HyperX-specific: wired vs wireless by PID
                if pid in (0x16E2,):
                    conn = ConnectionType.WIRED
                elif pid in (0x16E1,):
                    conn = ConnectionType.USB_DONGLE

                driver_instance = driver_cls()
                caps = driver_instance.get_capabilities()

                info = DeviceInfo(
                    device_id=device_id,
                    name=product_str or f"{driver_instance.brand} Mouse",
                    brand=driver_instance.brand,
                    model=product_str,
                    connection=conn,
                    capabilities=caps,
                    vendor_id=vid,
                    product_id=pid,
                    driver_name=driver_instance.name,
                )

                # Store for later use
                self._device_infos[key] = hid_info
                if key not in self._active:
                    self._active[key] = driver_instance

                results.append(info)
                break  # Only one driver per device

        # Clean up drivers for devices no longer present
        gone = set(self._active.keys()) - seen_keys
        for key in gone:
            driver = self._active.pop(key, None)
            if driver and driver.is_open:
                driver.close()
            self._device_infos.pop(key, None)

        return results

    def read_battery(self, device_id: DeviceId) -> Optional[BatteryReading]:
        key = device_id.stable_key
        driver = self._active.get(key)
        hid_info = self._device_infos.get(key)
        if not driver or not hid_info:
            return None

        # Open if not already open
        if not driver.is_open:
            path = hid_info["path"]
            if isinstance(path, str):
                path = path.encode()
            if not driver.open(path):
                return None

        return driver.read_battery()

    def get_driver_for(self, device_id: DeviceId) -> Optional[HidMouseDriver]:
        """Get the driver instance for a device (for config features)."""
        key = device_id.stable_key
        driver = self._active.get(key)
        hid_info = self._device_infos.get(key)
        if not driver:
            return None
        # Ensure it's open
        if not driver.is_open and hid_info:
            path = hid_info["path"]
            if isinstance(path, str):
                path = path.encode()
            driver.open(path)
        return driver

    def supports_hotplug(self) -> bool:
        try:
            import pyudev  # noqa: F401
            return True
        except ImportError:
            return False

    def start_watching(self, on_change: Callable[[], None]) -> None:
        try:
            import pyudev
        except ImportError:
            return

        self._watch_callback = on_change
        self._watching = True

        def _watch():
            context = pyudev.Context()
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem="usb")
            for _ in iter(monitor.poll, None):
                if not self._watching:
                    break
                if self._watch_callback:
                    self._watch_callback()

        self._watch_thread = threading.Thread(target=_watch, daemon=True)
        self._watch_thread.start()

    def stop_watching(self) -> None:
        self._watching = False
        self._watch_callback = None

    def close(self) -> None:
        self.stop_watching()
        for driver in self._active.values():
            if driver.is_open:
                try:
                    driver.close()
                except Exception:
                    pass
        self._active.clear()
        self._device_infos.clear()
