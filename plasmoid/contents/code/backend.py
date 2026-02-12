#!/usr/bin/env python3
"""
PlasmaNGenuity - Plasma Widget Backend
Outputs comprehensive device status as JSON for the KDE Plasma applet.
Supports both read and write operations.

Uses the unified DeviceManager to discover all wireless mice (UPower,
sysfs, HID), and falls back to direct HID for write operations on
supported devices.
"""

import json
import sys
import time
import argparse


def cmd_read():
    """Read all device data via the unified DeviceManager."""
    try:
        from plasmangenuity.core.manager import _DeviceManagerCore
        from plasmangenuity.providers.upower import UPowerProvider
        from plasmangenuity.providers.sysfs import SysfsProvider
        from plasmangenuity.providers.hid_driver import HidDriverProvider
    except ImportError:
        return _cmd_read_legacy()

    mgr = _DeviceManagerCore()
    mgr.register_provider(UPowerProvider())
    mgr.register_provider(SysfsProvider())
    mgr.register_provider(HidDriverProvider())

    devices = mgr.scan_once()

    if not devices:
        return {"error": "Device not found", "connected": False}

    # Pick the primary device (first with HID driver, or first overall)
    primary = None
    for d in devices:
        if d.driver_name:
            primary = d
            break
    if not primary:
        primary = devices[0]

    result = {
        "connected": True,
        "mode": primary.connection.name.lower(),
        "error": None,
        "deviceName": primary.name,
        "brand": primary.brand,
    }

    if primary.battery:
        result["battery"] = primary.battery.percent
        result["charging"] = primary.battery.is_charging
    else:
        result["battery"] = None
        result["charging"] = False

    # If the primary device has an HID driver, get extra info
    driver = mgr.get_driver(primary.device_id.stable_key)
    if driver:
        try:
            hw_info = driver.get_hw_info()
            if hw_info:
                result["hw_info"] = {
                    "firmware": hw_info.firmware_version,
                    "device_name": hw_info.device_name or primary.name,
                    "vendor_id": f"0x{hw_info.vendor_id:04X}",
                    "product_id": f"0x{hw_info.product_id:04X}",
                }
        except Exception:
            pass

        try:
            dpi = driver.get_dpi_settings()
            if dpi:
                active_profile = dpi.get("active_profile", 0)
                dpi_values = dpi.get("dpi_values", [])
                colors = dpi.get("colors", [])
                profiles = []
                for i in range(5):
                    color = colors[i] if i < len(colors) else (255, 255, 255)
                    profiles.append({
                        "index": i + 1,
                        "dpi": dpi_values[i] if i < len(dpi_values) else 800,
                        "enabled": True,
                        "active": i == active_profile,
                        "color": f"#{color[0]:02X}{color[1]:02X}{color[2]:02X}",
                    })
                result["dpi"] = {
                    "active_profile": active_profile + 1,
                    "profiles": profiles,
                }
        except Exception:
            pass

        try:
            led = driver.get_led_settings()
            if led:
                result["led"] = {
                    "effect": "Static",
                    "target": "Both",
                    "color": f"#{led.red:02X}{led.green:02X}{led.blue:02X}",
                    "brightness": led.brightness,
                    "speed": led.speed,
                }
        except Exception:
            pass

    # Include all devices as a list for multi-device display
    all_devices = []
    for d in devices:
        entry = {
            "name": d.name,
            "brand": d.brand,
            "key": d.device_id.stable_key,
            "connection": d.connection.name.lower(),
        }
        if d.battery:
            entry["battery"] = d.battery.percent
            entry["charging"] = d.battery.is_charging
        all_devices.append(entry)
    result["devices"] = all_devices

    mgr.close()
    return result


def cmd_set_dpi(profile):
    """Set DPI profile via the HID driver."""
    try:
        from plasmangenuity.core.manager import _DeviceManagerCore
        from plasmangenuity.providers.hid_driver import HidDriverProvider
    except ImportError:
        return _cmd_set_dpi_legacy(profile)

    mgr = _DeviceManagerCore()
    mgr.register_provider(HidDriverProvider())
    devices = mgr.scan_once()

    for d in devices:
        driver = mgr.get_driver(d.device_id.stable_key)
        if driver:
            success = driver.set_dpi_active(profile)
            mgr.close()
            return {"success": success, "error": None if success else "Failed to set DPI"}

    mgr.close()
    return {"success": False, "error": "No configurable device found"}


def cmd_set_led(r, g, b, brightness=100):
    """Set LED color via the HID driver."""
    try:
        from plasmangenuity.core.manager import _DeviceManagerCore
        from plasmangenuity.providers.hid_driver import HidDriverProvider
    except ImportError:
        return _cmd_set_led_legacy(r, g, b, brightness)

    mgr = _DeviceManagerCore()
    mgr.register_provider(HidDriverProvider())
    devices = mgr.scan_once()

    for d in devices:
        driver = mgr.get_driver(d.device_id.stable_key)
        if driver:
            success = driver.set_led(
                red=r, green=g, blue=b, brightness=brightness
            )
            mgr.close()
            return {"success": success, "error": None if success else "Failed to set LED"}

    mgr.close()
    return {"success": False, "error": "No configurable device found"}


# === Legacy fallbacks (if plasmangenuity package not installed) ===

def _cmd_read_legacy():
    """Fallback: read via direct HID (original standalone code)."""
    try:
        import hid
    except ImportError:
        return {"error": "hidapi not installed", "connected": False}

    VENDOR_ID = 0x0951
    PRODUCT_ID_WIRELESS = 0x16E1
    PRODUCT_ID_WIRED = 0x16E2
    USAGE_PAGE_WIRELESS = 0xFF00
    USAGE_PAGE_WIRED = 0xFF13
    PACKET_SIZE = 64

    try:
        devices = hid.enumerate(VENDOR_ID)
    except Exception:
        return {"error": "HID enumeration failed", "connected": False}

    wireless = wired = None
    for d in devices:
        if d["product_id"] == PRODUCT_ID_WIRELESS:
            if d["usage_page"] == USAGE_PAGE_WIRELESS or d["interface_number"] == 2:
                wireless = d
        elif d["product_id"] == PRODUCT_ID_WIRED:
            if d["usage_page"] == USAGE_PAGE_WIRED or d["interface_number"] == 1:
                wired = d

    device_info = wired or wireless
    mode = "wired" if wired else ("wireless" if wireless else None)

    if not device_info:
        return {"error": "Device not found", "connected": False}

    dev = None
    try:
        dev = hid.device()
        dev.open_path(device_info["path"])
        dev.set_nonblocking(False)

        # Drain buffer
        dev.set_nonblocking(True)
        while dev.read(PACKET_SIZE, timeout_ms=50):
            pass
        dev.set_nonblocking(False)

        result = {"connected": True, "mode": mode, "error": None}

        # Battery
        packet = [0x00] * PACKET_SIZE
        packet[1] = 0x51
        dev.write(packet)
        time.sleep(0.05)
        resp = dev.read(PACKET_SIZE, timeout_ms=1000)
        if resp and resp[0] == 0x51:
            result["battery"] = resp[4]
            result["charging"] = resp[5] == 0x01

        return result
    except Exception as e:
        return {"error": str(e), "connected": False}
    finally:
        if dev:
            try:
                dev.close()
            except Exception:
                pass


def _cmd_set_dpi_legacy(profile):
    return {"success": False, "error": "plasmangenuity package not installed"}


def _cmd_set_led_legacy(r, g, b, brightness):
    return {"success": False, "error": "plasmangenuity package not installed"}


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
        profile = args.set_dpi - 1
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
