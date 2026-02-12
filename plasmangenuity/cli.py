#!/usr/bin/env python3
"""Command-line interface for PlasmaNGenuity wireless mouse battery monitor."""

import sys
import json
import time
import argparse

from plasmangenuity.config import load_config
from plasmangenuity.core.manager import _DeviceManagerCore
from plasmangenuity.providers.upower import UPowerProvider
from plasmangenuity.providers.sysfs import SysfsProvider
from plasmangenuity.providers.hid_driver import HidDriverProvider


def _create_manager() -> _DeviceManagerCore:
    """Create a DeviceManager with all enabled providers."""
    config = load_config()
    providers_cfg = config.get("providers", {})

    mgr = _DeviceManagerCore()
    if providers_cfg.get("upower", True):
        mgr.register_provider(UPowerProvider())
    if providers_cfg.get("sysfs", True):
        mgr.register_provider(SysfsProvider())
    if providers_cfg.get("hid", True):
        mgr.register_provider(HidDriverProvider())
    return mgr


def main():
    parser = argparse.ArgumentParser(
        description="PlasmaNGenuity — Wireless Mouse Battery Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s              Show battery status for all wireless mice
  %(prog)s --json       Output as JSON (for scripts/waybar)
  %(prog)s --list       List all detected devices with details
  %(prog)s --watch      Continuously monitor battery
  %(prog)s --device KEY Filter to a specific device by stable key
""",
    )
    parser.add_argument("--list", "-l", action="store_true", help="List all detected devices")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--watch", "-w", action="store_true", help="Continuously monitor battery")
    parser.add_argument("--device", "-d", type=str, default=None, help="Filter to a specific device key")
    parser.add_argument(
        "--interval", "-i", type=int, default=30, help="Watch interval in seconds (default: 30)"
    )

    args = parser.parse_args()
    mgr = _create_manager()

    if args.list:
        devices = mgr.scan_once()
        if not devices:
            print("No wireless mice found.")
            print("\nTroubleshooting:")
            print("  1. Make sure the mouse/dongle is connected")
            print("  2. For HyperX mice, check udev rules are installed (see README)")
            print("  3. For Logitech/BLE mice, ensure UPower daemon is running")
            return 0

        print(f"Found {len(devices)} device(s):\n")
        for dev in devices:
            batt = f"{dev.battery.percent}%" if dev.battery and dev.battery.percent is not None else "N/A"
            charging = " (charging)" if dev.battery and dev.battery.is_charging else ""
            caps = [k for k in ("dpi", "led", "buttons", "macros")
                    if getattr(dev.capabilities, k, False)]

            print(f"  {dev.name}")
            print(f"    Key:        {dev.device_id.stable_key}")
            print(f"    Brand:      {dev.brand}")
            print(f"    Battery:    {batt}{charging}")
            print(f"    Connection: {dev.connection.name.lower()}")
            print(f"    Source:     {dev.device_id.provider.name.lower()}")
            if dev.driver_name:
                print(f"    Driver:     {dev.driver_name}")
            if caps:
                print(f"    Config:     {', '.join(caps)}")
            print()
        return 0

    def get_devices():
        devices = mgr.scan_once()
        if args.device:
            devices = [d for d in devices if d.device_id.stable_key == args.device]
        return devices

    def print_status():
        devices = get_devices()

        if not devices:
            if args.json:
                print(json.dumps({"error": "No devices found"}))
            else:
                if args.device:
                    print(f"Error: Device '{args.device}' not found.")
                else:
                    print("Error: No wireless mice found.")
                    print("\nMake sure:")
                    print("  - The wireless dongle is plugged in (for USB dongle mice)")
                    print("  - Or Bluetooth is paired and connected")
                    print("  - For HyperX mice, udev rules are installed (see README)")
                    print("\nRun with --list to see all detected devices.")
            return False

        if args.json:
            result = []
            for dev in devices:
                entry = {
                    "name": dev.name,
                    "key": dev.device_id.stable_key,
                    "brand": dev.brand,
                    "connection": dev.connection.name.lower(),
                    "source": dev.device_id.provider.name.lower(),
                }
                if dev.battery:
                    entry["battery_percent"] = dev.battery.percent
                    entry["is_charging"] = dev.battery.is_charging
                if dev.driver_name:
                    entry["driver"] = dev.driver_name
                result.append(entry)
            # Single device: flat object for waybar compat; multi: array
            if len(result) == 1:
                print(json.dumps(result[0]))
            else:
                print(json.dumps(result))
        else:
            for dev in devices:
                batt = f"{dev.battery.percent}%" if dev.battery and dev.battery.percent is not None else "N/A"
                charging = " (charging)" if dev.battery and dev.battery.is_charging else ""
                print(f"{dev.name}: {batt}{charging}")

        return True

    if args.watch:
        print(f"Monitoring battery (every {args.interval}s, Ctrl+C to stop)...\n")
        try:
            while True:
                print_status()
                print()
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        if not print_status():
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
