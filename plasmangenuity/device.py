"""HyperX Pulsefire Dart HID device communication."""

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

# HyperX Pulsefire Dart USB IDs (Kingston Technology)
VENDOR_ID = 0x0951
PRODUCT_ID_WIRELESS = 0x16E1
PRODUCT_ID_WIRED = 0x16E2

# HID Usage pages for the control interface
USAGE_PAGE_WIRELESS = 0xFF00
USAGE_PAGE_WIRED = 0xFF13

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

        # Response format:
        #   Byte 0x00: Command echo (0x51)
        #   Byte 0x04: Battery percentage (0-100)
        #   Byte 0x05: Charging status (0x00 = discharging, 0x01 = charging)
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

    Use this class when you need to send multiple commands efficiently.
    The connection stays open until close() is called.
    """

    def __init__(self):
        self._dev: Optional[hid.device] = None
        self._path: Optional[bytes] = None
        self._mode: Optional[str] = None

    @property
    def is_open(self) -> bool:
        """Check if device connection is open."""
        return self._dev is not None

    @property
    def mode(self) -> Optional[str]:
        """Connection mode: 'wireless' or 'wired'."""
        return self._mode

    def open(self) -> bool:
        """Open connection to the device.

        Returns:
            True if connection opened successfully, False otherwise.
        """
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
        """Close the device connection."""
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None
            self._path = None
            self._mode = None

    def _send(self, packet: bytes, expect_response: bool = True) -> Optional[bytes]:
        """Send a packet and optionally read response.

        Args:
            packet: 64-byte packet to send.
            expect_response: Whether to wait for a response.

        Returns:
            Response bytes or None if no response/error.
        """
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

    # =========================================================================
    # READ COMMANDS
    # =========================================================================

    def get_hw_info(self) -> Optional[HWInfo]:
        """Query hardware information.

        Returns:
            HWInfo named tuple or None on error.
        """
        response = self._send(build_hw_info_packet())
        if response:
            return parse_hw_info(response)
        return None

    def get_battery(self) -> Optional[BatteryStatus]:
        """Query battery status.

        Returns:
            BatteryStatus named tuple or None on error.
        """
        response = self._send(build_heartbeat_packet())
        if response:
            return parse_battery(response)
        return None

    def get_led_settings(self) -> Optional[LedSettings]:
        """Query LED settings from device memory.

        Note: This returns saved settings, not necessarily current
        direct-mode state.

        Returns:
            LedSettings named tuple or None on error.
        """
        response = self._send(build_led_query_packet())
        if response:
            return parse_led_settings(response)
        return None

    def get_dpi_settings(self) -> Optional[dict]:
        """Query DPI settings from device.

        Returns:
            Dict with 'active_profile' and 'dpi_values' or None on error.
        """
        response = self._send(build_dpi_query_packet())
        if response:
            return parse_dpi_settings(response)
        return None

    # =========================================================================
    # WRITE COMMANDS
    # =========================================================================

    def set_led(
        self,
        target: LedTarget,
        effect: LedEffect,
        red: int,
        green: int,
        blue: int,
        brightness: int = 100,
        speed: int = 0,
    ) -> bool:
        """Set LED color and effect (direct mode).

        Args:
            target: LED zone (logo, scroll, or both).
            effect: LED effect mode.
            red, green, blue: Color values (0-255).
            brightness: Brightness level (0-100).
            speed: Effect speed (0-100).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_led_packet(
            target, effect, red, green, blue, brightness, speed
        ))
        return response is not None

    def set_dpi_active(self, profile: int) -> bool:
        """Set active DPI profile.

        Args:
            profile: Profile index (0-4).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_dpi_select_packet(profile))
        return response is not None

    def set_dpi_enable_mask(self, mask: int) -> bool:
        """Set which DPI profiles are enabled.

        Args:
            mask: Bitmask of enabled profiles (bit 0 = profile 0, etc).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_dpi_enable_packet(mask))
        return response is not None

    def set_dpi_value(self, profile: int, dpi: int) -> bool:
        """Set DPI value for a profile.

        Args:
            profile: Profile index (0-4).
            dpi: DPI value (50-16000, step 50).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_dpi_value_packet(profile, dpi))
        return response is not None

    def set_dpi_color(self, profile: int, red: int, green: int, blue: int) -> bool:
        """Set DPI profile color.

        Args:
            profile: Profile index (0-4).
            red, green, blue: Color values (0-255).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_dpi_color_packet(profile, red, green, blue))
        return response is not None

    def set_button(self, button: int, button_type: ButtonType, code: int) -> bool:
        """Set button mapping.

        Args:
            button: Button index (0-5).
            button_type: Type of action (mouse, keyboard, media, DPI, macro).
            code: Action code (button code, scancode, media code, etc).

        Returns:
            True on success, False on error.
        """
        response = self._send(build_button_packet(button, button_type, code))
        return response is not None

    def upload_macro(self, button: int, events: List[MacroEvent]) -> bool:
        """Upload macro data to a button.

        Args:
            button: Button index (0-5).
            events: List of macro events.

        Returns:
            True on success, False on error.
        """
        packets = build_macro_packets(button, events)
        for packet in packets:
            response = self._send(packet)
            if response is None:
                return False
        return True

    def save_to_memory(self) -> bool:
        """Save current settings to device's persistent memory.

        Returns:
            True on success, False on error.
        """
        response = self._send(build_save_packet())
        return response is not None

    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
