"""HyperX Pulsefire Dart HID driver.

Refactored from the original device.py — same protocol logic,
now implementing the HidMouseDriver interface.
"""

from typing import Optional, List, Dict, Any

import hid

from plasmangenuity.core.types import BatteryReading, Capabilities, ProviderType
from plasmangenuity.drivers.base import HidMouseDriver
from plasmangenuity.drivers.hyperx.protocol import (
    PACKET_SIZE,
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


class HyperXPulsefireDriver(HidMouseDriver):
    """Driver for HyperX Pulsefire Dart wireless mouse."""

    def __init__(self):
        self._dev: Optional[hid.device] = None
        self._path: Optional[bytes] = None
        self._mode_str: Optional[str] = None

    # --- HidMouseDriver interface ---

    @property
    def name(self) -> str:
        return "hyperx_pulsefire_dart"

    @property
    def brand(self) -> str:
        return "HyperX"

    @staticmethod
    def match(vendor_id: int, product_id: int,
              usage_page: int, interface_number: int) -> bool:
        if vendor_id != VENDOR_ID:
            return False
        if product_id == PRODUCT_ID_WIRELESS:
            return usage_page == USAGE_PAGE_WIRELESS or interface_number == 2
        if product_id == PRODUCT_ID_WIRED:
            return usage_page == USAGE_PAGE_WIRED or interface_number == 1
        return False

    def get_capabilities(self) -> Capabilities:
        return Capabilities(
            battery=True,
            dpi=True,
            led=True,
            buttons=True,
            macros=True,
            polling_rate=True,
            firmware_query=True,
        )

    def open(self, device_path: bytes) -> bool:
        if self._dev is not None:
            return True
        try:
            self._dev = hid.device()
            self._dev.open_path(device_path)
            self._dev.set_nonblocking(False)
            self._path = device_path
            return True
        except Exception:
            self._dev = None
            self._path = None
            return False

    def close(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:
                pass
            self._dev = None
            self._path = None
            self._mode_str = None

    @property
    def is_open(self) -> bool:
        return self._dev is not None

    @property
    def mode(self) -> Optional[str]:
        return self._mode_str

    @mode.setter
    def mode(self, value: Optional[str]):
        self._mode_str = value

    def read_battery(self) -> Optional[BatteryReading]:
        response = self._send(build_heartbeat_packet())
        if response:
            parsed = parse_battery(response)
            if parsed:
                return BatteryReading(
                    percent=parsed.percent,
                    is_charging=parsed.is_charging,
                    provider=ProviderType.HID_PROPRIETARY,
                )
        return None

    # --- Config methods ---

    def get_hw_info(self) -> Optional[HWInfo]:
        response = self._send(build_hw_info_packet())
        if response:
            return parse_hw_info(response)
        return None

    def get_dpi_settings(self) -> Optional[dict]:
        response = self._send(build_dpi_query_packet())
        if response:
            return parse_dpi_settings(response)
        return None

    def set_dpi_active(self, profile: int) -> bool:
        return self._send(build_dpi_select_packet(profile)) is not None

    def set_dpi_enable_mask(self, mask: int) -> bool:
        return self._send(build_dpi_enable_packet(mask)) is not None

    def set_dpi_value(self, profile: int, dpi: int) -> bool:
        return self._send(build_dpi_value_packet(profile, dpi)) is not None

    def set_dpi_color(self, profile: int, r: int, g: int, b: int) -> bool:
        return self._send(build_dpi_color_packet(profile, r, g, b)) is not None

    def get_led_settings(self):
        response = self._send(build_led_query_packet())
        if response:
            return parse_led_settings(response)
        return None

    def set_led(self, target=LedTarget.BOTH, effect=LedEffect.STATIC,
                red=0, green=0, blue=0, brightness=100, speed=0, **kwargs) -> bool:
        return self._send(build_led_packet(
            target, effect, red, green, blue, brightness, speed
        )) is not None

    def set_button(self, button: int, button_type: int, code: int) -> bool:
        return self._send(build_button_packet(button, ButtonType(button_type), code)) is not None

    def upload_macro(self, button: int, events: list) -> bool:
        packets = build_macro_packets(button, events)
        for packet in packets:
            if self._send(packet) is None:
                return False
        return True

    def save_to_memory(self) -> bool:
        return self._send(build_save_packet()) is not None

    # --- Internal ---

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
