#!/usr/bin/env python3
"""
PlasmaNGenuity - Plasma Widget Backend
Outputs comprehensive device status as JSON for the KDE Plasma applet
Supports both read and write operations.
"""

import json
import sys
import time
import argparse

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

# HID packet size
PACKET_SIZE = 64

# Command bytes (from protocol.py)
CMD_HW_INFO = 0x50
CMD_HEARTBEAT = 0x51
CMD_LED_QUERY = 0x52
CMD_DPI_QUERY = 0x53
CMD_LED_SET = 0xD2
CMD_DPI_SET = 0xD3


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


def send_command(dev, data, retries=3):
    """Send a command packet and read response with retries."""
    packet = [0x00] * PACKET_SIZE
    packet[0] = 0x00  # Report ID
    for i, byte in enumerate(data):
        if i + 1 < PACKET_SIZE:
            packet[i + 1] = byte

    for attempt in range(retries):
        try:
            dev.write(packet)
            response = dev.read(PACKET_SIZE, timeout_ms=1000)
            if response and len(response) > 0:
                return response
            time.sleep(0.05)
        except Exception:
            if attempt < retries - 1:
                time.sleep(0.1)
            continue
    return None


def get_battery_status(dev):
    """Query battery status from the mouse."""
    response = send_command(dev, [CMD_HEARTBEAT])
    if not response or len(response) < 6 or response[0] != CMD_HEARTBEAT:
        return None, None
    return response[4], response[5] == 0x01


def get_hw_info(dev):
    """Query hardware information."""
    response = send_command(dev, [CMD_HW_INFO])
    if not response or len(response) < 32 or response[0] != CMD_HW_INFO:
        return None

    product_id = response[4] | (response[5] << 8)
    vendor_id = response[6] | (response[7] << 8)

    name_bytes = response[12:44]
    try:
        null_idx = list(name_bytes).index(0)
    except ValueError:
        null_idx = len(name_bytes)
    device_name = bytes(name_bytes[:null_idx]).decode('ascii', errors='ignore')

    firmware_version = f"{response[3]}.0.0"

    return {
        "firmware": firmware_version,
        "device_name": device_name.strip() or "HyperX Pulsefire Dart",
        "vendor_id": f"0x{vendor_id:04X}",
        "product_id": f"0x{product_id:04X}"
    }


def get_dpi_settings(dev):
    """Query DPI settings."""
    response = send_command(dev, [CMD_DPI_QUERY])
    if not response or len(response) < 30 or response[0] != CMD_DPI_QUERY:
        return None

    active_profile = response[5]

    dpi_offsets = [10, 12, 14, 16, 18]
    dpi_values = []
    for offset in dpi_offsets:
        raw = response[offset] | (response[offset + 1] << 8)
        dpi_values.append(raw * 50)

    colors = []
    for i in range(5):
        offset = 22 + i * 3
        if offset + 2 < len(response):
            r, g, b = response[offset], response[offset + 1], response[offset + 2]
            colors.append(f"#{r:02X}{g:02X}{b:02X}")
        else:
            colors.append("#FFFFFF")

    profiles = []
    for i in range(5):
        profiles.append({
            "index": i + 1,
            "dpi": dpi_values[i] if i < len(dpi_values) else 800,
            "enabled": True,
            "active": i == active_profile,
            "color": colors[i] if i < len(colors) else "#FFFFFF"
        })

    return {
        "active_profile": active_profile + 1,
        "profiles": profiles
    }


def get_led_settings(dev):
    """Query LED settings."""
    response = send_command(dev, [CMD_LED_QUERY])
    if not response or len(response) < 21 or response[0] != CMD_LED_QUERY:
        return None

    brightness = response[17]
    r = response[18]
    g = response[19]
    b = response[20]

    return {
        "effect": "Static",
        "target": "Both",
        "color": f"#{r:02X}{g:02X}{b:02X}",
        "brightness": brightness,
        "speed": 0
    }


def set_dpi_profile(dev, profile):
    """Set active DPI profile (0-4)."""
    profile = max(0, min(4, profile))
    response = send_command(dev, [CMD_DPI_SET, 0x00, profile, 0x00])
    return response is not None


def set_led_color(dev, r, g, b, brightness=100):
    """Set LED color (static mode, both zones)."""
    brightness = max(0, min(100, brightness))
    # CMD_LED_SET, target=Both(0x20), effect=Static(0x00), length=8,
    # R, G, B, R2, G2, B2, brightness, speed
    response = send_command(dev, [
        CMD_LED_SET,
        0x20,  # Both zones
        0x00,  # Static effect
        0x08,  # Data length
        r, g, b,  # Primary color
        r, g, b,  # Secondary color
        brightness,
        0x00   # Speed (not used for static)
    ])
    return response is not None


def cmd_read():
    """Read all device data."""
    device_info, mode = find_device()

    if not device_info:
        return {"error": "Device not found", "connected": False}

    dev = None
    try:
        dev = hid.device()
        dev.open_path(device_info["path"])
        dev.set_nonblocking(False)

        result = {
            "connected": True,
            "mode": mode,
            "error": None
        }

        time.sleep(0.05)

        battery, charging = get_battery_status(dev)
        result["battery"] = battery
        result["charging"] = charging if battery is not None else False

        time.sleep(0.02)

        hw_info = get_hw_info(dev)
        if hw_info:
            result["hw_info"] = hw_info

        time.sleep(0.02)

        dpi_settings = get_dpi_settings(dev)
        if dpi_settings:
            result["dpi"] = dpi_settings

        time.sleep(0.02)

        led_settings = get_led_settings(dev)
        if led_settings:
            result["led"] = led_settings

        return result

    except IOError as e:
        return {"error": f"IO Error: {e}", "connected": False}
    except Exception as e:
        return {"error": str(e), "connected": False}
    finally:
        if dev:
            try:
                dev.close()
            except:
                pass


def cmd_set_dpi(profile):
    """Set DPI profile."""
    device_info, mode = find_device()
    if not device_info:
        return {"success": False, "error": "Device not found"}

    dev = None
    try:
        dev = hid.device()
        dev.open_path(device_info["path"])
        dev.set_nonblocking(False)
        time.sleep(0.05)

        success = set_dpi_profile(dev, profile)
        return {"success": success, "error": None if success else "Failed to set DPI"}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if dev:
            try:
                dev.close()
            except:
                pass


def cmd_set_led(r, g, b, brightness=100):
    """Set LED color."""
    device_info, mode = find_device()
    if not device_info:
        return {"success": False, "error": "Device not found"}

    dev = None
    try:
        dev = hid.device()
        dev.open_path(device_info["path"])
        dev.set_nonblocking(False)
        time.sleep(0.05)

        success = set_led_color(dev, r, g, b, brightness)
        return {"success": success, "error": None if success else "Failed to set LED"}

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if dev:
            try:
                dev.close()
            except:
                pass


def main():
    parser = argparse.ArgumentParser(description="PlasmaNGenuity Backend")
    parser.add_argument("--set-dpi", type=int, metavar="PROFILE",
                        help="Set active DPI profile (1-5)")
    parser.add_argument("--set-led", metavar="R,G,B",
                        help="Set LED color (e.g., 255,0,0 for red)")
    parser.add_argument("--brightness", type=int, default=100,
                        help="LED brightness (0-100, default 100)")

    args = parser.parse_args()

    if args.set_dpi is not None:
        profile = args.set_dpi - 1  # Convert to 0-indexed
        result = cmd_set_dpi(profile)
        print(json.dumps(result))
    elif args.set_led is not None:
        try:
            r, g, b = map(int, args.set_led.split(","))
            result = cmd_set_led(r, g, b, args.brightness)
            print(json.dumps(result))
        except ValueError:
            print(json.dumps({"success": False, "error": "Invalid color format. Use R,G,B"}))
    else:
        result = cmd_read()
        print(json.dumps(result))


if __name__ == "__main__":
    main()
