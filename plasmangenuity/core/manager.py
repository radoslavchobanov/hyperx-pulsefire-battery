"""Device manager - central orchestrator for multi-device battery monitoring."""

import logging
from typing import Dict, List, Optional

from plasmangenuity.core.types import DeviceInfo, BatteryReading
from plasmangenuity.core.provider import BatteryProvider

log = logging.getLogger(__name__)

# Try Qt imports — the manager works without them for CLI/plasmoid use.
try:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


class _DeviceManagerCore:
    """Pure-Python manager core without Qt dependency.

    Tracks providers, devices, and deduplication logic. Used directly
    by the CLI (scan_once) and wrapped by the Qt-aware DeviceManager.
    """

    def __init__(self):
        self._providers: List[BatteryProvider] = []
        self._devices: Dict[str, DeviceInfo] = {}  # stable_key -> DeviceInfo
        self._device_provider: Dict[str, BatteryProvider] = {}  # stable_key -> provider

    def register_provider(self, provider: BatteryProvider) -> None:
        """Register a battery provider, maintaining priority order."""
        self._providers.append(provider)
        self._providers.sort(key=lambda p: p.priority)

    def get_device(self, stable_key: str) -> Optional[DeviceInfo]:
        return self._devices.get(stable_key)

    def get_all_devices(self) -> List[DeviceInfo]:
        return list(self._devices.values())

    def get_driver(self, stable_key: str):
        """Get the HID driver for a device, if any.

        Returns the HidMouseDriver instance for configuration features,
        or None if this device uses a non-HID provider.
        """
        provider = self._device_provider.get(stable_key)
        if provider and hasattr(provider, 'get_driver_for'):
            device = self._devices.get(stable_key)
            if device:
                return provider.get_driver_for(device.device_id)
        return None

    def run_discovery(self):
        """Scan all providers and reconcile device list.

        Returns (added_keys, removed_keys) for the caller to act on.
        """
        seen_keys: Dict[str, DeviceInfo] = {}
        seen_providers: Dict[str, BatteryProvider] = {}

        for provider in self._providers:
            try:
                found = provider.discover()
            except Exception:
                log.exception("Discovery failed for provider %s", provider.name)
                continue

            for device_info in found:
                key = device_info.device_id.stable_key
                if key not in seen_keys:
                    seen_keys[key] = device_info
                    seen_providers[key] = provider

        added = set(seen_keys) - set(self._devices)
        removed = set(self._devices) - set(seen_keys)

        # Update internal state
        self._devices = seen_keys
        self._device_provider = seen_providers

        return added, removed

    def poll_all_batteries(self) -> Dict[str, BatteryReading]:
        """Read battery for all tracked devices. Returns {stable_key: reading}."""
        results = {}
        for key, device in list(self._devices.items()):
            provider = self._device_provider.get(key)
            if not provider:
                continue
            try:
                reading = provider.read_battery(device.device_id)
                if reading:
                    device.battery = reading
                    results[key] = reading
            except Exception:
                log.debug("Battery read failed for %s via %s", key, provider.name)
        return results

    def refresh_battery(self, stable_key: str) -> Optional[BatteryReading]:
        """Force-refresh battery for a specific device."""
        provider = self._device_provider.get(stable_key)
        device = self._devices.get(stable_key)
        if provider and device:
            try:
                reading = provider.read_battery(device.device_id)
                if reading:
                    device.battery = reading
                return reading
            except Exception:
                log.debug("Battery refresh failed for %s", stable_key)
        return None

    def scan_once(self) -> List[DeviceInfo]:
        """Synchronous one-shot: discover devices and read all batteries.

        Useful for CLI and plasmoid where there is no event loop.
        """
        self.run_discovery()
        self.poll_all_batteries()
        return self.get_all_devices()

    def close(self) -> None:
        """Stop watching and clean up all providers."""
        for provider in self._providers:
            try:
                provider.stop_watching()
            except Exception:
                pass
            try:
                provider.close()
            except Exception:
                pass


if _HAS_QT:

    class DeviceManager(QObject):
        """Qt-aware device manager with signals and timers.

        Signals:
            device_added(DeviceInfo): A new device was discovered.
            device_removed(str): A device disappeared (emits stable_key).
            battery_updated(str, BatteryReading): Battery reading for device.
        """

        device_added = pyqtSignal(object)
        device_removed = pyqtSignal(str)
        battery_updated = pyqtSignal(str, object)

        def __init__(self, poll_interval_ms: int = 60000, parent=None):
            super().__init__(parent)
            self._core = _DeviceManagerCore()
            self._poll_interval = poll_interval_ms

            self._discovery_timer = QTimer(self)
            self._discovery_timer.timeout.connect(self._run_discovery)

            self._battery_timer = QTimer(self)
            self._battery_timer.timeout.connect(self._poll_all_batteries)

        # --- Delegate to core ---

        def register_provider(self, provider: BatteryProvider) -> None:
            self._core.register_provider(provider)
            if provider.supports_hotplug():
                provider.start_watching(self._on_hotplug_event)

        def get_device(self, stable_key: str) -> Optional[DeviceInfo]:
            return self._core.get_device(stable_key)

        def get_all_devices(self) -> List[DeviceInfo]:
            return self._core.get_all_devices()

        def get_driver(self, stable_key: str):
            return self._core.get_driver(stable_key)

        def scan_once(self) -> List[DeviceInfo]:
            return self._core.scan_once()

        # --- Qt lifecycle ---

        def start(self) -> None:
            """Begin discovery and polling."""
            self._run_discovery()
            self._discovery_timer.start(self._poll_interval * 2)
            self._battery_timer.start(self._poll_interval)

        def stop(self) -> None:
            """Stop all timers and clean up."""
            self._discovery_timer.stop()
            self._battery_timer.stop()
            self._core.close()

        def refresh_battery(self, stable_key: str) -> Optional[BatteryReading]:
            reading = self._core.refresh_battery(stable_key)
            if reading:
                self.battery_updated.emit(stable_key, reading)
            return reading

        # --- Internal ---

        def _on_hotplug_event(self) -> None:
            QTimer.singleShot(2000, self._run_discovery)

        def _run_discovery(self) -> None:
            added, removed = self._core.run_discovery()
            for key in removed:
                self.device_removed.emit(key)
            for key in added:
                device = self._core.get_device(key)
                if device:
                    self.device_added.emit(device)

        def _poll_all_batteries(self) -> None:
            results = self._core.poll_all_batteries()
            for key, reading in results.items():
                self.battery_updated.emit(key, reading)

else:

    # When Qt is not available, DeviceManager is just the core.
    DeviceManager = _DeviceManagerCore
