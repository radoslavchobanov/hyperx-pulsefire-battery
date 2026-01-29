#!/usr/bin/env python3
"""Command-line interface for reading HyperX Pulsefire Dart battery status."""

import sys
import json
import time
import argparse

from hyperx_battery.device import find_device, get_battery_status, list_devices


def main():
    parser = argparse.ArgumentParser(
        description="HyperX Pulsefire Dart Battery Monitor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s              Show battery status
  %(prog)s --json       Output as JSON (for scripts/waybar)
  %(prog)s --list       List all HyperX devices
  %(prog)s --watch      Continuously monitor battery
""",
    )
    parser.add_argument("--list", "-l", action="store_true", help="List all HyperX devices")
    parser.add_argument("--json", "-j", action="store_true", help="Output as JSON")
    parser.add_argument("--watch", "-w", action="store_true", help="Continuously monitor battery")
    parser.add_argument(
        "--interval", "-i", type=int, default=30, help="Watch interval in seconds (default: 30)"
    )

    args = parser.parse_args()

    if args.list:
        devices = list_devices()
        if not devices:
            print("No HyperX devices found.")
            print("\nTroubleshooting:")
            print("  1. Make sure the mouse/dongle is connected")
            print("  2. Check udev rules are installed (see README)")
            print("  3. Try running with sudo")
            return 0

        print(f"Found {len(devices)} HyperX USB interface(s):\n")
        for dev in devices:
            for key, val in dev.items():
                print(f"  {key}: {val}")
            print()
        return 0

    device_info, mode = find_device()

    if not device_info:
        if args.json:
            print(json.dumps({"error": "Device not found"}))
        else:
            print("Error: HyperX Pulsefire Dart not found.")
            print("\nMake sure:")
            print("  - The wireless dongle is plugged in (for wireless mode)")
            print("  - Or the mouse is connected via USB cable (for wired mode)")
            print("  - udev rules are installed (see README)")
            print("\nRun with --list to see all HyperX devices.")
        return 1

    device_path = device_info["path"]

    def print_status():
        battery, charging, error = get_battery_status(device_path)

        if error:
            if args.json:
                print(json.dumps({"error": error}))
            else:
                print(f"Error: {error}")
            return False

        if args.json:
            print(json.dumps({"battery_percent": battery, "is_charging": charging, "mode": mode}))
        else:
            charging_str = " (charging)" if charging else ""
            print(f"Battery: {battery}%{charging_str}")
            print(f"Mode: {mode}")

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
