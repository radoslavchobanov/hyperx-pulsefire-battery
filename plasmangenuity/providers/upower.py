"""UPower battery provider — monitors wireless mouse battery via D-Bus.

Covers: Logitech (kernel hid-logitech-hidpp), BLE mice, and many others.
Priority: 10 (highest — preferred over direct HID).
"""

import logging
import re
import threading
from typing import List, Optional, Callable

from plasmangenuity.core.types import (
    DeviceInfo, DeviceId, BatteryReading, Capabilities,
    ConnectionType, ProviderType,
)
from plasmangenuity.core.provider import BatteryProvider

log = logging.getLogger(__name__)

# UPower device type constants
_UPOWER_TYPE_MOUSE = 8
_UPOWER_TYPE_KEYBOARD = 6

# UPower state constants
_UPOWER_STATE_CHARGING = 1
_UPOWER_STATE_FULLY_CHARGED = 4

_IFACE_DEVICE = "org.freedesktop.UPower.Device"
_IFACE_PROPS = "org.freedesktop.DBus.Properties"
_IFACE_UPOWER = "org.freedesktop.UPower"
_UPOWER_PATH = "/org/freedesktop/UPower"
_UPOWER_BUS = "org.freedesktop.UPower"


def _try_import_dbus():
    """Import dbus lazily so the module is loadable even without dbus-python."""
    try:
        import dbus
        return dbus
    except ImportError:
        return None


class UPowerProvider(BatteryProvider):
    """Battery provider using the UPower D-Bus daemon."""

    @property
    def name(self) -> str:
        return "UPower"

    @property
    def priority(self) -> int:
        return 10

    def __init__(self):
        self._bus = None
        self._watch_callback: Optional[Callable[[], None]] = None
        self._signal_matches = []

    def _get_bus(self):
        if self._bus is None:
            dbus = _try_import_dbus()
            if dbus is None:
                return None
            try:
                self._bus = dbus.SystemBus()
            except Exception:
                log.debug("Could not connect to system D-Bus")
                return None
        return self._bus

    def discover(self) -> List[DeviceInfo]:
        dbus = _try_import_dbus()
        if dbus is None:
            return []

        bus = self._get_bus()
        if bus is None:
            return []

        results = []
        try:
            upower_obj = bus.get_object(_UPOWER_BUS, _UPOWER_PATH)
            upower_iface = dbus.Interface(upower_obj, _IFACE_UPOWER)
            device_paths = upower_iface.EnumerateDevices()
        except Exception:
            log.debug("Failed to enumerate UPower devices")
            return []

        for dev_path in device_paths:
            try:
                info = self._read_device(bus, dbus, str(dev_path))
                if info:
                    results.append(info)
            except Exception:
                log.debug("Failed to read UPower device %s", dev_path)

        return results

    def _read_device(self, bus, dbus, dev_path: str) -> Optional[DeviceInfo]:
        """Read a single UPower device and return DeviceInfo if it's a mouse."""
        dev_obj = bus.get_object(_UPOWER_BUS, dev_path)
        props = dbus.Interface(dev_obj, _IFACE_PROPS)

        dev_type = int(props.Get(_IFACE_DEVICE, "Type"))
        if dev_type != _UPOWER_TYPE_MOUSE:
            return None

        # Read properties
        model = str(props.Get(_IFACE_DEVICE, "Model") or "")
        native_path = str(props.Get(_IFACE_DEVICE, "NativePath") or "")
        serial = str(props.Get(_IFACE_DEVICE, "Serial") or "")
        percentage = float(props.Get(_IFACE_DEVICE, "Percentage"))
        state = int(props.Get(_IFACE_DEVICE, "State"))
        is_present = bool(props.Get(_IFACE_DEVICE, "IsPresent"))

        if not is_present:
            return None

        # Try to extract VID/PID from native path or serial
        vid, pid = self._extract_vid_pid(native_path, serial)

        # Determine connection type
        conn = ConnectionType.UNKNOWN
        path_lower = dev_path.lower() + native_path.lower()
        if "bluetooth" in path_lower or "bt" in path_lower:
            conn = ConnectionType.BLUETOOTH_LE
        elif "usb" in path_lower or "hid" in path_lower:
            conn = ConnectionType.USB_DONGLE

        # Determine brand from model name
        brand = self._guess_brand(model)

        device_id = DeviceId(
            provider=ProviderType.UPOWER,
            path=dev_path,
            vendor_id=vid,
            product_id=pid,
            serial=serial or None,
        )

        is_charging = state in (_UPOWER_STATE_CHARGING, _UPOWER_STATE_FULLY_CHARGED)

        return DeviceInfo(
            device_id=device_id,
            name=model or "Wireless Mouse",
            brand=brand,
            model=model,
            connection=conn,
            capabilities=Capabilities(battery=True),
            battery=BatteryReading(
                percent=int(percentage),
                is_charging=is_charging,
                provider=ProviderType.UPOWER,
            ),
            vendor_id=vid,
            product_id=pid,
        )

    def read_battery(self, device_id: DeviceId) -> Optional[BatteryReading]:
        dbus = _try_import_dbus()
        if dbus is None:
            return None

        bus = self._get_bus()
        if bus is None:
            return None

        try:
            dev_obj = bus.get_object(_UPOWER_BUS, device_id.path)
            props = dbus.Interface(dev_obj, _IFACE_PROPS)

            percentage = float(props.Get(_IFACE_DEVICE, "Percentage"))
            state = int(props.Get(_IFACE_DEVICE, "State"))
            is_charging = state in (_UPOWER_STATE_CHARGING, _UPOWER_STATE_FULLY_CHARGED)

            return BatteryReading(
                percent=int(percentage),
                is_charging=is_charging,
                provider=ProviderType.UPOWER,
            )
        except Exception:
            log.debug("Failed to read battery from UPower device %s", device_id.path)
            return None

    def supports_hotplug(self) -> bool:
        return _try_import_dbus() is not None

    def start_watching(self, on_change: Callable[[], None]) -> None:
        dbus = _try_import_dbus()
        if dbus is None:
            return

        bus = self._get_bus()
        if bus is None:
            return

        self._watch_callback = on_change

        try:
            # Watch for device add/remove on UPower
            match_added = bus.add_signal_receiver(
                self._on_device_change,
                signal_name="DeviceAdded",
                dbus_interface=_IFACE_UPOWER,
                bus_name=_UPOWER_BUS,
            )
            match_removed = bus.add_signal_receiver(
                self._on_device_change,
                signal_name="DeviceRemoved",
                dbus_interface=_IFACE_UPOWER,
                bus_name=_UPOWER_BUS,
            )
            self._signal_matches = [match_added, match_removed]
        except Exception:
            log.debug("Failed to set up UPower D-Bus signal watchers")

    def stop_watching(self) -> None:
        self._watch_callback = None
        # dbus signal matches are cleaned up when the bus is closed
        self._signal_matches.clear()

    def close(self) -> None:
        self.stop_watching()
        self._bus = None

    def _on_device_change(self, *args):
        if self._watch_callback:
            self._watch_callback()

    @staticmethod
    def _extract_vid_pid(native_path: str, serial: str) -> tuple:
        """Try to extract vendor/product IDs from UPower metadata."""
        # Common patterns in native_path:
        #   /sys/devices/pci.../usb.../1234:5678:ABCD.0001
        #   hid-12:34:56:78:9a:bc  (Bluetooth MAC)
        for text in (native_path, serial):
            # Match VID:PID hex pattern (e.g., 046D:C548)
            m = re.search(r'([0-9a-fA-F]{4}):([0-9a-fA-F]{4})', text)
            if m:
                try:
                    vid = int(m.group(1), 16)
                    pid = int(m.group(2), 16)
                    # Sanity check — skip if it looks like a BT MAC fragment
                    if vid > 0 and pid > 0:
                        return vid, pid
                except ValueError:
                    pass
        return None, None

    @staticmethod
    def _guess_brand(model: str) -> str:
        """Guess mouse brand from model name."""
        model_lower = model.lower()
        brands = {
            "logitech": "Logitech",
            "logi": "Logitech",
            "razer": "Razer",
            "steelseries": "SteelSeries",
            "corsair": "Corsair",
            "hyperx": "HyperX",
            "glorious": "Glorious",
            "pulsar": "Pulsar",
            "endgame": "Endgame Gear",
            "zowie": "Zowie",
            "roccat": "Roccat",
            "microsoft": "Microsoft",
            "apple": "Apple",
        }
        for keyword, brand in brands.items():
            if keyword in model_lower:
                return brand
        return "Unknown"
