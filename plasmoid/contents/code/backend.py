#!/usr/bin/env python3
"""
PlasmaNGenuity - Plasma Widget Backend
Outputs comprehensive device status as JSON for the KDE Plasma applet
"""

import json
import sys

try:
    import hid
except ImportError:
    print(json.dumps({
        "error": "hidapi not installed",
        "connected": False
    }))
    sys.exit(0)

# HyperX Pulsefire Dart USB IDs
VENDOR_ID = 0x0951
PRODUCT_ID_WIRELESS = 0x16E1
PRODUCT_ID_WIRED = 0x16E2
USAGE_PAGE_WIRELESS = 0xFF00
USAGE_PAGE_WIRED = 0xFF13

# HID packet size and commands
PACKET_SIZE = 64
CMD_HW_INFO = 0x50
CMD_HEARTBEAT = 0x51
CMD_LED_QUERY = 0xD2
CMD_DPI_QUERY = 0xD3


def find_device():
    """Find the HyperX Pulsefire Dart HID device."""
    try:
        devices = hid.enumerate(VENDOR_ID)
    except Exception:
        return None, None

    for dev in devices:
        if dev["product_id"] == PRODUCT_ID_WIRELESS:
            if dev["usage_page"] == USAGE_PAGE_WIRELESS or dev["interface_number"] == 2:
                return dev, "wireless"
        elif dev["product_id"] == PRODUCT_ID_WIRED:
            if dev["usage_page"] == USAGE_PAGE_WIRED or dev["interface_number"] == 1:
                return dev, "wired"

    return None, None


def send_command(dev, cmd, expect_response=True):
    """Send a command and optionally read response."""
    packet = [0x00] * PACKET_SIZE
    packet[0] = 0x00  # Report ID
    packet[1] = cmd
    dev.write(packet)

    if expect_response:
        response = dev.read(PACKET_SIZE, timeout_ms=1000)
        return response
    return None


def get_device_info(dev):
    """Query hardware information."""
    response = send_command(dev, CMD_HW_INFO)
    if not response or response[0] != CMD_HW_INFO:
        return None

    # Parse firmware version from bytes 4-7
    fw_bytes = response[4:8]
    firmware = ".".join(str(b) for b in fw_bytes if b != 0) or "Unknown"

    # Device name from bytes 8-39 (null-terminated string)
    name_bytes = response[8:40]
    try:
        name_end = name_bytes.index(0)
        device_name = bytes(name_bytes[:name_end]).decode('ascii', errors='ignore')
    except ValueError:
        device_name = bytes(name_bytes).decode('ascii', errors='ignore')

    return {
        "firmware": firmware,
        "device_name": device_name.strip() or "HyperX Pulsefire Dart",
        "vendor_id": f"0x{VENDOR_ID:04X}",
        "product_id": f"0x{response[2]:02X}{response[3]:02X}" if len(response) > 3 else "Unknown"
    }


def get_battery_status(dev):
    """Query battery status from the mouse."""
    response = send_command(dev, CMD_HEARTBEAT)
    if not response or response[0] != CMD_HEARTBEAT:
        return None, None

    return response[4], response[5] == 0x01


def get_dpi_settings(dev):
    """Query DPI settings."""
    response = send_command(dev, CMD_DPI_QUERY)
    if not response or response[0] != CMD_DPI_QUERY:
        return None

    active_profile = response[2]
    enabled_mask = response[3]

    profiles = []
    for i in range(5):
        # DPI value (2 bytes per profile, starting at offset 4)
        dpi_low = response[4 + i * 2]
        dpi_high = response[5 + i * 2]
        dpi = (dpi_high << 8) | dpi_low
        if dpi == 0:
            dpi = 800  # Default

        # Color (3 bytes per profile, starting at offset 14)
        r = response[14 + i * 3]
        g = response[15 + i * 3]
        b = response[16 + i * 3]

        profiles.append({
            "index": i + 1,
            "dpi": dpi,
            "enabled": bool(enabled_mask & (1 << i)),
            "active": i == active_profile,
            "color": f"#{r:02X}{g:02X}{b:02X}"
        })

    return {
        "active_profile": active_profile + 1,
        "profiles": profiles
    }


def get_led_settings(dev):
    """Query LED settings."""
    response = send_command(dev, CMD_LED_QUERY)
    if not response or response[0] != CMD_LED_QUERY:
        return None

    effects = ["Static", "Breathing", "Spectrum Cycle", "Trigger Fade"]
    targets = ["Logo", "Scroll Wheel", "Both"]

    effect_idx = min(response[2], len(effects) - 1)
    target_idx = min(response[3], len(targets) - 1)

    return {
        "effect": effects[effect_idx],
        "target": targets[target_idx],
        "color": f"#{response[4]:02X}{response[5]:02X}{response[6]:02X}",
        "brightness": response[7],
        "speed": response[8]
    }


def main():
    device_info, mode = find_device()

    if not device_info:
        print(json.dumps({
            "error": "Device not found",
            "connected": False
        }))
        return

    try:
        dev = hid.device()
        dev.open_path(device_info["path"])
        dev.set_nonblocking(False)

        result = {
            "connected": True,
            "mode": mode,
            "error": None
        }

        # Get battery
        battery, charging = get_battery_status(dev)
        if battery is not None:
            result["battery"] = battery
            result["charging"] = charging
        else:
            result["battery"] = None
            result["charging"] = False

        # Get hardware info
        hw_info = get_device_info(dev)
        if hw_info:
            result["hw_info"] = hw_info

        # Get DPI settings
        dpi_settings = get_dpi_settings(dev)
        if dpi_settings:
            result["dpi"] = dpi_settings

        # Get LED settings
        led_settings = get_led_settings(dev)
        if led_settings:
            result["led"] = led_settings

        dev.close()
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({
            "error": str(e),
            "connected": False
        }))


if __name__ == "__main__":
    main()
