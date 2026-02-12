"""HyperX Pulsefire Dart HID device communication.

This module preserves backward compatibility for existing consumers
(tray, panel, cli, widgets). The canonical driver is now
plasmangenuity.drivers.hyperx.driver.HyperXPulsefireDriver.
"""

from typing import Optional, Tuple, List, Dict, Any
import hid

from plasmangenuity.protocol import (
    PACKET_SIZE,
    CMD_HEARTBEAT,
    build_heartbeat_packet,
    build_hw_info_packet,
    build_led_query_packet,
    build_dpi_query_packet,
    build_led_packet,
    build_dpi_select_packet,
    build_dpi_enable_packet,
    build_dpi_value_packet,
    build_dpi_color_packet,
    build_button_packet,
    build_macro_packets,
    build_save_packet,
    parse_hw_info,
    parse_battery,
    parse_led_settings,
    parse_dpi_settings,
    HWInfo,
    BatteryStatus,
    LedSettings,
    LedTarget,
    LedEffect,
    ButtonType,
    MacroEvent,
)

# Re-export driver constants for backward compatibility.
from plasmangenuity.drivers.hyperx.driver import (  # noqa: F401
    VENDOR_ID,
    PRODUCT_ID_WIRELESS,
    PRODUCT_ID_WIRED,
    USAGE_PAGE_WIRELESS,
    USAGE_PAGE_WIRED,
)

# Vendor ID string used in udev events
VENDOR_ID_STR = "0951"


def find_device() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Find the HyperX Pulsefire Dart HID device.

    Prefers wired over wireless when both are present, since a wired
    connection means the USB cable is plugged in (charging) and the
    wired interface provides accurate battery/charging status.

    Returns:
        tuple: (device_info_dict, mode_string) or (None, None) if not found.
    """
    devices = hid.enumerate(VENDOR_ID)

    wireless = None
    wired = None

    for dev in devices:
        if dev["product_id"] == PRODUCT_ID_WIRELESS:
            if dev["usage_page"] == USAGE_PAGE_WIRELESS or dev["interface_number"] == 2:
                wireless = dev
        elif dev["product_id"] == PRODUCT_ID_WIRED:
            if dev["usage_page"] == USAGE_PAGE_WIRED or dev["interface_number"] == 1:
                wired = dev

    if wired:
        return wired, "wired"
    if wireless:
        return wireless, "wireless"

    return None, None


def get_battery_status(device_path) -> Tuple[Optional[int], Optional[bool], Optional[str]]:
    """Query battery status from the mouse.

    Args:
        device_path: HID device path (bytes or str).

    Returns:
        tuple: (battery_percent, is_charging, error_string).
            On success error_string is None.
            On failure battery_percent and is_charging are None.
    """
    try:
        dev = hid.device()
        dev.open_path(device_path)
        dev.set_nonblocking(False)

        packet = [0x00] * PACKET_SIZE
        packet[0] = 0x00  # Report ID
        packet[1] = CMD_HEARTBEAT
        dev.write(packet)

        response = dev.read(PACKET_SIZE, timeout_ms=1000)
        dev.close()

        if not response:
            return None, None, "No response from device"

        if response[0] == CMD_HEARTBEAT:
            return response[4], response[5] == 0x01, None

        return None, None, f"Unexpected response: 0x{response[0]:02X}"
    except IOError as e:
        return None, None, f"IO Error: {e}"
    except Exception as e:
        return None, None, f"Error: {e}"


def list_devices() -> List[Dict[str, Any]]:
    """Return a list of dicts describing all HyperX HID interfaces found."""
    devices = hid.enumerate(VENDOR_ID)
    result = []
    for dev in devices:
        result.append({
            "product_id": f"{dev['product_id']:04X}",
            "path": dev["path"].decode() if isinstance(dev["path"], bytes) else dev["path"],
            "interface": dev["interface_number"],
            "usage_page": f"0x{dev['usage_page']:04X}",
            "manufacturer": dev["manufacturer_string"],
            "product": dev["product_string"],
        })
    return result


class HyperXDevice:
    """Persistent HID connection to HyperX Pulsefire Dart mouse.

    This is the legacy wrapper class. New code should use
    plasmangenuity.drivers.hyperx.HyperXPulsefireDriver directly
    or go through the DeviceManager.
    """

    def __init__(self):
        self._dev: Optional[hid.device] = None
        self._path: Optional[bytes] = None
        self._mode: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    @property
    def mode(self) -> Optional[str]:
        return self._mode

    def open(self) -> bool:
        if self._dev is not None:
            return True

        device_info, mode = find_device()
        if not device_info:
            return False

        try:
            self._dev = hid.device()
            self._dev.open_path(device_info["path"])
            self._dev.set_nonblocking(False)
            self._path = device_info["path"]
            self._mode = mode
            return True
        except Exception:
            self._dev = None
            self._path = None
            self._mode = None
            return False

    def close(self):
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None
            self._path = None
            self._mode = None

    def _send(self, packet: bytes, expect_response: bool = True) -> Optional[bytes]:
        if self._dev is None:
            return None
        try:
            self._dev.write(packet)
            if expect_response:
                response = self._dev.read(PACKET_SIZE, timeout_ms=1000)
                return bytes(response) if response else None
            return b''
        except Exception:
            return None

    def get_hw_info(self) -> Optional[HWInfo]:
        response = self._send(build_hw_info_packet())
        if response:
            return parse_hw_info(response)
        return None

    def get_battery(self) -> Optional[BatteryStatus]:
        response = self._send(build_heartbeat_packet())
        if response:
            return parse_battery(response)
        return None

    def get_led_settings(self) -> Optional[LedSettings]:
        response = self._send(build_led_query_packet())
        if response:
            return parse_led_settings(response)
        return None

    def get_dpi_settings(self) -> Optional[dict]:
        response = self._send(build_dpi_query_packet())
        if response:
            return parse_dpi_settings(response)
        return None

    def set_led(self, target: LedTarget, effect: LedEffect,
                red: int, green: int, blue: int,
                brightness: int = 100, speed: int = 0) -> bool:
        response = self._send(build_led_packet(
            target, effect, red, green, blue, brightness, speed
        ))
        return response is not None

    def set_dpi_active(self, profile: int) -> bool:
        return self._send(build_dpi_select_packet(profile)) is not None

    def set_dpi_enable_mask(self, mask: int) -> bool:
        return self._send(build_dpi_enable_packet(mask)) is not None

    def set_dpi_value(self, profile: int, dpi: int) -> bool:
        return self._send(build_dpi_value_packet(profile, dpi)) is not None

    def set_dpi_color(self, profile: int, red: int, green: int, blue: int) -> bool:
        return self._send(build_dpi_color_packet(profile, red, green, blue)) is not None

    def set_button(self, button: int, button_type: ButtonType, code: int) -> bool:
        return self._send(build_button_packet(button, button_type, code)) is not None

    def upload_macro(self, button: int, events: List[MacroEvent]) -> bool:
        packets = build_macro_packets(button, events)
        for packet in packets:
            if self._send(packet) is None:
                return False
        return True

    def save_to_memory(self) -> bool:
        return self._send(build_save_packet()) is not None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
