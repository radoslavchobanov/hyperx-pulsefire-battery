#!/usr/bin/env python3
"""System tray widget showing wireless mouse battery levels."""

import sys
import math

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import (
    QIcon, QPainter, QColor, QFont, QPixmap, QPainterPath, QPen,
)
from PyQt5.QtCore import QTimer, Qt, QRectF

from plasmangenuity.core.manager import DeviceManager
from plasmangenuity.core.types import DeviceInfo, BatteryReading
from plasmangenuity.providers.upower import UPowerProvider
from plasmangenuity.providers.sysfs import SysfsProvider
from plasmangenuity.providers.hid_driver import HidDriverProvider
from plasmangenuity.config import Config


class BatteryTrayIcon(QSystemTrayIcon):
    """System tray icon that displays battery percentage with modern mouse icon."""

    def __init__(self):
        super().__init__()

        self._config = Config()

        # Per-device state for notifications
        self._notif_state: dict[str, dict] = {}
        # {stable_key: {"prev_battery": int|None, "was_charging": bool, "thresholds": set}}

        # Config panel (lazy-created)
        self._panel = None

        # The device currently shown on the tray icon (lowest battery or first)
        self._primary_key: str | None = None

        # Charging animation
        self._charging_frame = 0
        self._charging_timer = QTimer()
        self._charging_timer.timeout.connect(self._on_charging_tick)

        # --- Create DeviceManager ---
        providers_cfg = self._config.providers
        poll_interval_ms = self._config.polling["interval_seconds"] * 1000

        self._manager = DeviceManager(poll_interval_ms=poll_interval_ms, parent=self)

        if providers_cfg.get("upower", True):
            self._manager.register_provider(UPowerProvider())
        if providers_cfg.get("sysfs", True):
            self._manager.register_provider(SysfsProvider())
        if providers_cfg.get("hid", True):
            self._manager.register_provider(HidDriverProvider())

        self._manager.device_added.connect(self._on_device_added)
        self._manager.device_removed.connect(self._on_device_removed)
        self._manager.battery_updated.connect(self._on_battery_updated)

        # --- Context menu (built dynamically) ---
        self._menu = QMenu()
        self.setContextMenu(self._menu)
        self._rebuild_menu()
        self.activated.connect(self._on_activated)

        # Start manager (initial discovery + polling)
        self._manager.start()

        # Update icon after first discovery
        QTimer.singleShot(500, self._update_icon)
        self.show()

    # ---- DeviceManager signal handlers -----------------------------------

    def _on_device_added(self, device_info: DeviceInfo):
        key = device_info.device_id.stable_key
        self._notif_state.setdefault(key, {
            "prev_battery": None,
            "was_charging": False,
            "thresholds": set(),
        })
        self._rebuild_menu()
        self._update_icon()

    def _on_device_removed(self, stable_key: str):
        self._notif_state.pop(stable_key, None)
        if self._primary_key == stable_key:
            self._primary_key = None
        self._rebuild_menu()
        self._update_icon()

    def _on_battery_updated(self, stable_key: str, reading: BatteryReading):
        device = self._manager.get_device(stable_key)
        if device:
            self._check_notifications(stable_key, reading)
        self._update_icon()
        self._rebuild_menu()

    # ---- Menu building ---------------------------------------------------

    def _rebuild_menu(self):
        self._menu.clear()

        devices = self._manager.get_all_devices()

        if not devices:
            no_dev = QAction("No wireless mice found")
            no_dev.setEnabled(False)
            self._menu.addAction(no_dev)
        else:
            for dev in devices:
                batt = dev.battery
                if batt and batt.percent is not None:
                    pct = f"{batt.percent}%"
                    charging_str = " (charging)" if batt.is_charging else ""
                else:
                    pct = "N/A"
                    charging_str = ""
                label = f"{dev.name}: {pct}{charging_str}"
                action = QAction(label)
                action.setEnabled(False)
                self._menu.addAction(action)

        self._menu.addSeparator()

        # Config panel - show if any device has advanced capabilities
        any_configurable = any(
            d.capabilities.dpi or d.capabilities.led
            for d in devices
        )
        if any_configurable:
            config_action = QAction("Open Configuration...")
            config_action.triggered.connect(self._show_panel)
            self._menu.addAction(config_action)

        refresh_action = QAction("Refresh Now")
        refresh_action.triggered.connect(self._refresh_all)
        self._menu.addAction(refresh_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(quit_action)

    # ---- Icon rendering --------------------------------------------------

    def _update_icon(self):
        """Update tray icon and tooltip based on current device state."""
        devices = self._manager.get_all_devices()

        if not devices:
            self.setIcon(self._create_icon(None, error=True))
            self.setToolTip("PlasmaNGenuity\nNo wireless mice found")
            if self._charging_timer.isActive():
                self._charging_timer.stop()
            return

        # Pick primary device: lowest battery among non-charging, or first
        primary = min(
            devices,
            key=lambda d: (d.battery.percent if d.battery and d.battery.percent is not None else 999),
        )
        self._primary_key = primary.device_id.stable_key

        batt = primary.battery
        percent = batt.percent if batt else None
        charging = batt.is_charging if batt else False

        # Charging animation
        anim_enabled = self._config.tray.get("charging_animation", True)
        anim_fps = self._config.tray.get("animation_fps", 7)
        anim_interval = int(1000 / anim_fps) if anim_fps > 0 else 150

        if charging and anim_enabled and not self._charging_timer.isActive():
            self._charging_frame = 0
            self._charging_timer.start(anim_interval)
        elif (not charging or not anim_enabled) and self._charging_timer.isActive():
            self._charging_timer.stop()

        self.setIcon(self._create_icon(percent, charging, frame=self._charging_frame))

        # Build tooltip
        lines = ["PlasmaNGenuity"]
        for dev in devices:
            b = dev.battery
            if b and b.percent is not None:
                cs = " (charging)" if b.is_charging else ""
                lines.append(f"{dev.name}: {b.percent}%{cs}")
            else:
                lines.append(f"{dev.name}: N/A")
        self.setToolTip("\n".join(lines))

    def _on_charging_tick(self):
        self._charging_frame = (self._charging_frame + 1) % 8
        devices = self._manager.get_all_devices()
        primary = None
        if self._primary_key:
            primary = self._manager.get_device(self._primary_key)
        if not primary and devices:
            primary = devices[0]
        if primary and primary.battery:
            self.setIcon(self._create_icon(
                primary.battery.percent, primary.battery.is_charging,
                frame=self._charging_frame
            ))

    @staticmethod
    def _create_icon(percent, charging=False, error=False, frame=0):
        """Create modern mouse silhouette icon with battery indicator."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if error or percent is None:
            body_color = QColor(100, 100, 100)
            fill_color = QColor(80, 80, 80)
            text_color = QColor(200, 200, 200)
            percent_for_fill = 0
        elif charging:
            body_color = QColor(60, 60, 60)
            pulse = 0.7 + 0.3 * math.sin(frame * math.pi / 4)
            fill_color = QColor(
                int(80 * pulse), int(180 * pulse), int(255 * pulse)
            )
            text_color = QColor(255, 255, 255)
            percent_for_fill = percent
        else:
            body_color = QColor(60, 60, 60)
            if percent <= 10:
                fill_color = QColor(255, 60, 60)
            elif percent <= 25:
                t = (percent - 10) / 15
                fill_color = QColor(255, int(60 + 120 * t), 60)
            elif percent <= 50:
                t = (percent - 25) / 25
                fill_color = QColor(255, int(180 + 75 * t), 60)
            elif percent <= 75:
                t = (percent - 50) / 25
                fill_color = QColor(int(255 - 175 * t), 255, int(60 + 20 * t))
            else:
                fill_color = QColor(80, 200, 80)
            text_color = QColor(255, 255, 255)
            percent_for_fill = percent

        # Mouse body silhouette
        mouse_path = QPainterPath()
        mouse_path.moveTo(16, 14)
        mouse_path.lineTo(16, 52)
        mouse_path.quadTo(16, 58, 22, 58)
        mouse_path.lineTo(42, 58)
        mouse_path.quadTo(48, 58, 48, 52)
        mouse_path.lineTo(48, 14)
        mouse_path.quadTo(48, 6, 32, 6)
        mouse_path.quadTo(16, 6, 16, 14)
        mouse_path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(body_color)
        painter.drawPath(mouse_path)

        # Battery fill bar
        if percent_for_fill > 0:
            fill_height = int((percent_for_fill / 100.0) * 42)
            fill_rect = QRectF(20, 52 - fill_height, 24, fill_height)
            painter.setClipPath(mouse_path)
            painter.setBrush(fill_color)
            painter.drawRect(fill_rect)
            painter.setClipping(False)

        # Outline
        painter.setPen(QPen(QColor(120, 120, 120), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(mouse_path)

        # Button divider
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawLine(32, 8, 32, 28)

        # Scroll wheel
        wheel_rect = QRectF(29, 14, 6, 10)
        painter.setPen(QPen(QColor(140, 140, 140), 1))
        painter.setBrush(QColor(50, 50, 50))
        painter.drawRoundedRect(wheel_rect, 2, 2)

        # Lightning bolt (charging)
        if charging:
            bolt_path = QPainterPath()
            bolt_path.moveTo(36, 32)
            bolt_path.lineTo(30, 42)
            bolt_path.lineTo(33, 42)
            bolt_path.lineTo(28, 54)
            bolt_path.lineTo(38, 42)
            bolt_path.lineTo(35, 42)
            bolt_path.lineTo(40, 32)
            bolt_path.closeSubpath()

            pulse = 0.5 + 0.5 * math.sin(frame * math.pi / 4)
            glow_color = QColor(255, 220, 50, int(200 * pulse))
            painter.setPen(QPen(QColor(255, 200, 0), 1.5))
            painter.setBrush(glow_color)
            painter.drawPath(bolt_path)

        # Text
        if error or percent is None:
            painter.setPen(text_color)
            painter.setFont(QFont("Sans", 16, QFont.Bold))
            painter.drawText(QRectF(0, 20, size, 30), Qt.AlignCenter, "?")
        elif not charging:
            painter.setPen(text_color)
            text = str(percent)
            font_size = 11 if len(text) <= 2 else 9
            painter.setFont(QFont("Sans", font_size, QFont.Bold))
            text_rect = QRectF(16, 32, 32, 20)
            painter.drawText(text_rect, Qt.AlignCenter, text)

        painter.end()
        return QIcon(pixmap)

    # ---- Notifications ---------------------------------------------------

    def _check_notifications(self, stable_key: str, reading: BatteryReading):
        """Check if we should show battery notifications for a specific device."""
        notif_config = self._config.notifications
        if not notif_config["enabled"]:
            return

        state = self._notif_state.get(stable_key)
        if not state:
            state = {"prev_battery": None, "was_charging": False, "thresholds": set()}
            self._notif_state[stable_key] = state

        battery = reading.percent
        charging = reading.is_charging
        prev_battery = state["prev_battery"]
        was_charging = state["was_charging"]

        device = self._manager.get_device(stable_key)
        dev_name = device.name if device else "Mouse"

        # Charging state changed
        if notif_config.get("charging_notify", True):
            if charging and not was_charging:
                self._send_notification(
                    f"{dev_name}: Charging Started", f"Battery at {battery}%"
                )
                state["thresholds"].clear()
            elif not charging and was_charging:
                self._send_notification(
                    f"{dev_name}: Charging Stopped", f"Battery at {battery}%"
                )

        state["was_charging"] = charging

        # Fully charged
        if notif_config.get("full_notify", True) and charging and battery == 100:
            if "full" not in state["thresholds"]:
                self._send_notification(f"{dev_name}: Fully Charged", "Battery is at 100%")
                state["thresholds"].add("full")

        # Low battery thresholds (only when discharging)
        if not charging and prev_battery is not None and battery is not None:
            thresholds = sorted(notif_config.get("thresholds", [20, 10, 5]), reverse=True)
            for threshold in thresholds:
                if battery <= threshold < prev_battery:
                    if threshold not in state["thresholds"]:
                        urgency = "critical" if threshold <= 10 else "normal"
                        self._send_notification(
                            f"{dev_name}: Low Battery {battery}%",
                            f"Battery has dropped to {battery}%",
                            urgency=urgency,
                        )
                        state["thresholds"].add(threshold)

        # Reset thresholds if battery goes back up
        if prev_battery is not None and battery is not None and battery > prev_battery:
            state["thresholds"] = {t for t in state["thresholds"] if t < battery}

        state["prev_battery"] = battery

    def _send_notification(self, title: str, message: str, urgency: str = "normal"):
        import subprocess
        try:
            subprocess.run([
                "notify-send",
                "-a", "PlasmaNGenuity",
                "-u", urgency,
                "-i", "input-mouse",
                title,
                message,
            ], check=False, capture_output=True)
        except FileNotFoundError:
            pass

    # ---- Panel management ------------------------------------------------

    def _show_panel(self):
        from plasmangenuity.panel import ConfigPanel
        from PyQt5.QtGui import QCursor

        if self._panel is not None:
            self._panel.hide()
            self._panel.deleteLater()

        self._panel = ConfigPanel()
        self._panel.destroyed.connect(self._on_panel_closed)

        cursor_pos = QCursor.pos()
        self._panel.popup_at_tray(cursor_pos)

    def _on_panel_closed(self):
        pass  # Manager handles polling continuously now

    def _toggle_panel(self):
        if self._panel is not None and self._panel.isVisible():
            self._panel.hide()
            self._panel.deleteLater()
            self._panel = None
        else:
            self._show_panel()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_panel()

    def _refresh_all(self):
        """Force-refresh battery for all devices."""
        for dev in self._manager.get_all_devices():
            self._manager.refresh_battery(dev.device_id.stable_key)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("PlasmaNGenuity")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Error: System tray is not available on this desktop environment.")
        sys.exit(1)

    _tray = BatteryTrayIcon()  # noqa: F841
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
