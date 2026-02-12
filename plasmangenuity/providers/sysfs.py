"""sysfs battery provider — reads /sys/class/power_supply/ for device batteries.

Catches devices that expose battery to the kernel but aren't picked up by UPower.
Priority: 20 (between UPower and HID).
"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Callable

from plasmangenuity.core.types import (
    DeviceInfo, DeviceId, BatteryReading, Capabilities,
    ConnectionType, ProviderType,
)
from plasmangenuity.core.provider import BatteryProvider

log = logging.getLogger(__name__)

_POWER_SUPPLY_DIR = Path("/sys/class/power_supply")


def _read_sysfs(path: Path) -> Optional[str]:
    """Read a sysfs attribute file, returning stripped content or None."""
    try:
        return path.read_text().strip()
    except (OSError, IOError):
        return None


class SysfsProvider(BatteryProvider):
    """Battery provider reading /sys/class/power_supply/*/ for device batteries."""

    @property
    def name(self) -> str:
        return "sysfs"

    @property
    def priority(self) -> int:
        return 20

    def discover(self) -> List[DeviceInfo]:
        if not _POWER_SUPPLY_DIR.is_dir():
            return []

        results = []
        for entry in _POWER_SUPPLY_DIR.iterdir():
            if not entry.is_dir():
                continue
            info = self._read_device(entry)
            if info:
                results.append(info)

        return results

    def _read_device(self, ps_dir: Path) -> Optional[DeviceInfo]:
        """Read a single power_supply entry and return DeviceInfo if it's a mouse battery."""
        # Must be a battery
        ps_type = _read_sysfs(ps_dir / "type")
        if ps_type != "Battery":
            return None

        # Must be a device battery (not the laptop's own battery)
        scope = _read_sysfs(ps_dir / "scope")
        if scope != "Device":
            return None

        # Read battery level
        capacity_str = _read_sysfs(ps_dir / "capacity")
        if capacity_str is None:
            return None
        try:
            capacity = int(capacity_str)
        except ValueError:
            return None

        # Read status (Charging, Discharging, Full, Not charging)
        status = _read_sysfs(ps_dir / "status") or "Unknown"
        is_charging = status.lower() in ("charging", "full")

        # Read device identity
        model = _read_sysfs(ps_dir / "model_name") or ""
        manufacturer = _read_sysfs(ps_dir / "manufacturer") or ""
        device_name = model or manufacturer or ps_dir.name

        # Try to determine if this is a mouse.
        # Heuristic: check symlink target for "mouse" or "input" in the path,
        # or check the device tree for HID descriptors.
        if not self._is_likely_mouse(ps_dir, model, manufacturer):
            return None

        # Try to extract VID/PID from device path
        vid, pid = self._extract_vid_pid(ps_dir)

        path_str = str(ps_dir)
        conn = ConnectionType.UNKNOWN
        if "bluetooth" in path_str.lower():
            conn = ConnectionType.BLUETOOTH_LE
        elif "usb" in path_str.lower():
            conn = ConnectionType.USB_DONGLE

        brand = "Unknown"
        if manufacturer:
            brand = manufacturer

        device_id = DeviceId(
            provider=ProviderType.SYSFS,
            path=path_str,
            vendor_id=vid,
            product_id=pid,
        )

        return DeviceInfo(
            device_id=device_id,
            name=device_name,
            brand=brand,
            model=model,
            connection=conn,
            capabilities=Capabilities(battery=True),
            battery=BatteryReading(
                percent=capacity,
                is_charging=is_charging,
                provider=ProviderType.SYSFS,
            ),
            vendor_id=vid,
            product_id=pid,
        )

    def read_battery(self, device_id: DeviceId) -> Optional[BatteryReading]:
        ps_dir = Path(device_id.path)
        if not ps_dir.is_dir():
            return None

        capacity_str = _read_sysfs(ps_dir / "capacity")
        if capacity_str is None:
            return None

        try:
            capacity = int(capacity_str)
        except ValueError:
            return None

        status = _read_sysfs(ps_dir / "status") or "Unknown"
        is_charging = status.lower() in ("charging", "full")

        return BatteryReading(
            percent=capacity,
            is_charging=is_charging,
            provider=ProviderType.SYSFS,
        )

    @staticmethod
    def _is_likely_mouse(ps_dir: Path, model: str, manufacturer: str) -> bool:
        """Heuristic check whether this power supply belongs to a mouse."""
        combined = (model + " " + manufacturer + " " + str(ps_dir)).lower()

        # Positive signals
        mouse_keywords = ("mouse", "mice", "pulsefire", "deathadder",
                          "viper", "basilisk", "g pro", "g502", "g703",
                          "g305", "superlight", "orochi", "naga",
                          "aerox", "rival", "prime", "haste")
        for kw in mouse_keywords:
            if kw in combined:
                return True

        # If the device path includes an input device with "mouse" capability
        # we'd need to walk the device tree, which is complex. For now, accept
        # any device-scoped battery that doesn't match known non-mouse types.
        non_mouse = ("keyboard", "kbd", "headset", "headphone", "earbuds",
                     "controller", "gamepad", "joystick", "tablet", "pen",
                     "stylus", "touchpad", "trackpad")
        for kw in non_mouse:
            if kw in combined:
                return False

        # Uncertain — include it (user can filter later)
        return True

    @staticmethod
    def _extract_vid_pid(ps_dir: Path) -> tuple:
        """Try to extract VID/PID from the sysfs device path symlinks."""
        try:
            real_path = str(ps_dir.resolve())
        except OSError:
            return None, None

        # Look for USB VID/PID pattern in the path: .../046D:C548/...
        m = re.search(r'/([0-9a-fA-F]{4}):([0-9a-fA-F]{4})(?:[./]|$)', real_path)
        if m:
            try:
                return int(m.group(1), 16), int(m.group(2), 16)
            except ValueError:
                pass
        return None, None
