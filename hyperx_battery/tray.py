#!/usr/bin/env python3
"""System tray widget showing HyperX Pulsefire Dart battery level."""

import sys
import threading
import math

from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtGui import (
    QIcon, QPainter, QColor, QFont, QPixmap, QPainterPath,
    QLinearGradient, QPen, QBrush
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject, QPointF, QRectF

import pyudev

from hyperx_battery.device import (
    find_device,
    get_battery_status,
    VENDOR_ID_STR,
)
from hyperx_battery.config import Config


class _DeviceSignal(QObject):
    """Thread-safe bridge: udev monitor thread -> Qt main thread."""

    changed = pyqtSignal()


class BatteryTrayIcon(QSystemTrayIcon):
    """System tray icon that displays battery percentage with modern mouse icon."""

    def __init__(self):
        super().__init__()

        # Load configuration
        self._config = Config()

        self.battery_percent = None
        self.is_charging = False
        self.mode = None
        self.error = None

        # Track notification state to avoid repeats
        self._notified_thresholds = set()
        self._was_charging = False

        # Config panel (lazy-created)
        self._panel = None

        # Charging animation
        self._charging_frame = 0
        self._charging_timer = QTimer()
        self._charging_timer.timeout.connect(self._on_charging_tick)

        # --- udev hotplug detection ---
        self._device_signal = _DeviceSignal()
        self._device_signal.changed.connect(self._on_device_event)
        self._start_udev_monitor()

        # --- Context menu ---
        self._menu = QMenu()

        self._status_action = QAction("Battery: ---%")
        self._status_action.setEnabled(False)
        self._menu.addAction(self._status_action)

        self._mode_action = QAction("Mode: ---")
        self._mode_action.setEnabled(False)
        self._menu.addAction(self._mode_action)

        self._menu.addSeparator()

        config_action = QAction("Open Configuration...")
        config_action.triggered.connect(self._show_panel)
        self._menu.addAction(config_action)

        refresh_action = QAction("Refresh Now")
        refresh_action.triggered.connect(self.update_battery)
        self._menu.addAction(refresh_action)

        self._menu.addSeparator()

        quit_action = QAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self._menu.addAction(quit_action)

        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

        # --- Periodic polling (fallback) ---
        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self.update_battery)
        poll_interval_ms = self._config.polling["interval_seconds"] * 1000
        self._poll_timer.start(poll_interval_ms)

        # Initial read
        self.update_battery()
        self.show()

    # ---- udev monitoring -----------------------------------------------

    def _start_udev_monitor(self):
        context = pyudev.Context()
        monitor = pyudev.Monitor.from_netlink(context)
        monitor.filter_by(subsystem="usb")

        def _watch():
            for device in iter(monitor.poll, None):
                vendor = device.get("ID_VENDOR_ID", "")
                if vendor == VENDOR_ID_STR or device.action == "remove":
                    self._device_signal.changed.emit()

        threading.Thread(target=_watch, daemon=True).start()

        # Debounce timer — waits for rapid events to settle
        self._debounce_timer = QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._on_device_settled)

        # Retry timer — device may not be ready immediately after plug-in
        self._retry_timer = QTimer()
        self._retry_timer.setSingleShot(True)
        self._retry_timer.timeout.connect(self._retry_update)
        self._retry_count = 0

    def _on_device_event(self):
        self._retry_count = 0
        self._debounce_timer.start(2000)

    def _on_device_settled(self):
        self._retry_count = 0
        self._try_update()

    def _try_update(self):
        self.update_battery()
        max_retries = self._config.polling["max_retries"]
        retry_delay = self._config.polling["retry_delay_seconds"] * 1000
        if self.error and self._retry_count < max_retries:
            self._retry_count += 1
            self._retry_timer.start(retry_delay)

    def _retry_update(self):
        self._try_update()

    # ---- Charging animation --------------------------------------------

    def _on_charging_tick(self):
        """Update charging animation frame."""
        self._charging_frame = (self._charging_frame + 1) % 8
        self.setIcon(self._create_icon(
            self.battery_percent, self.is_charging, self.error is not None,
            self._charging_frame
        ))

    # ---- Icon rendering -------------------------------------------------

    @staticmethod
    def _create_icon(percent, charging=False, error=False, animation_frame=0):
        """Create modern mouse silhouette icon with battery indicator."""
        size = 64
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # Colors
        if error or percent is None:
            body_color = QColor(100, 100, 100)
            fill_color = QColor(80, 80, 80)
            text_color = QColor(200, 200, 200)
            percent_for_fill = 0
        elif charging:
            body_color = QColor(60, 60, 60)
            # Pulsing blue for charging
            pulse = 0.7 + 0.3 * math.sin(animation_frame * math.pi / 4)
            fill_color = QColor(
                int(80 * pulse),
                int(180 * pulse),
                int(255 * pulse)
            )
            text_color = QColor(255, 255, 255)
            percent_for_fill = percent
        else:
            body_color = QColor(60, 60, 60)
            # Color gradient from red -> orange -> yellow -> green
            if percent <= 10:
                fill_color = QColor(255, 60, 60)  # Red
            elif percent <= 25:
                # Red to orange
                t = (percent - 10) / 15
                fill_color = QColor(255, int(60 + 120 * t), 60)
            elif percent <= 50:
                # Orange to yellow
                t = (percent - 25) / 25
                fill_color = QColor(255, int(180 + 75 * t), 60)
            elif percent <= 75:
                # Yellow to green
                t = (percent - 50) / 25
                fill_color = QColor(int(255 - 175 * t), 255, int(60 + 20 * t))
            else:
                fill_color = QColor(80, 200, 80)  # Green
            text_color = QColor(255, 255, 255)
            percent_for_fill = percent

        # Draw mouse body silhouette
        mouse_path = QPainterPath()
        # Main body - rounded rectangle with pointed top
        mouse_path.moveTo(16, 14)  # Top left of body
        mouse_path.lineTo(16, 52)  # Left side
        mouse_path.quadTo(16, 58, 22, 58)  # Bottom left corner
        mouse_path.lineTo(42, 58)  # Bottom
        mouse_path.quadTo(48, 58, 48, 52)  # Bottom right corner
        mouse_path.lineTo(48, 14)  # Right side
        mouse_path.quadTo(48, 6, 32, 6)  # Top curve (center)
        mouse_path.quadTo(16, 6, 16, 14)  # Top curve (left)
        mouse_path.closeSubpath()

        # Body fill (dark)
        painter.setPen(Qt.NoPen)
        painter.setBrush(body_color)
        painter.drawPath(mouse_path)

        # Battery fill bar inside mouse body
        if percent_for_fill > 0:
            fill_height = int((percent_for_fill / 100.0) * 42)
            fill_rect = QRectF(20, 52 - fill_height, 24, fill_height)

            # Clip to mouse shape
            painter.setClipPath(mouse_path)
            painter.setBrush(fill_color)
            painter.drawRect(fill_rect)
            painter.setClipping(False)

        # Mouse outline
        painter.setPen(QPen(QColor(120, 120, 120), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(mouse_path)

        # Divider line (between buttons)
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawLine(32, 8, 32, 28)

        # Scroll wheel
        wheel_rect = QRectF(29, 14, 6, 10)
        painter.setPen(QPen(QColor(140, 140, 140), 1))
        painter.setBrush(QColor(50, 50, 50))
        painter.drawRoundedRect(wheel_rect, 2, 2)

        # Charging indicator (lightning bolt)
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

            # Pulsing glow effect
            pulse = 0.5 + 0.5 * math.sin(animation_frame * math.pi / 4)
            glow_color = QColor(255, 220, 50, int(200 * pulse))
            painter.setPen(QPen(QColor(255, 200, 0), 1.5))
            painter.setBrush(glow_color)
            painter.drawPath(bolt_path)

        # Percentage text (below mouse or inside if disconnected)
        if error or percent is None:
            painter.setPen(text_color)
            painter.setFont(QFont("Sans", 16, QFont.Bold))
            painter.drawText(QRectF(0, 20, size, 30), Qt.AlignCenter, "?")
        elif not charging:
            # Draw percentage inside the mouse body
            painter.setPen(text_color)
            text = str(percent)
            font_size = 11 if len(text) <= 2 else 9
            painter.setFont(QFont("Sans", font_size, QFont.Bold))
            text_rect = QRectF(16, 32, 32, 20)
            painter.drawText(text_rect, Qt.AlignCenter, text)

        painter.end()
        return QIcon(pixmap)

    # ---- State update ---------------------------------------------------

    def update_battery(self):
        device_info, mode = find_device()
        device_path = device_info["path"] if device_info else None

        if not device_path:
            self.battery_percent = None
            self.is_charging = False
            self.mode = None
            self.error = "Mouse not found"
            self._charging_timer.stop()
            self.setIcon(self._create_icon(None, error=True))
            self.setToolTip("HyperX Pulsefire Dart\nNot connected")
            self._status_action.setText("Not connected")
            self._mode_action.setText("Mode: ---")
            return

        self.mode = mode
        battery, charging, error = get_battery_status(device_path)

        if error:
            self.error = error
            self._charging_timer.stop()
            self.setIcon(self._create_icon(None, error=True))
            self.setToolTip(f"HyperX Pulsefire Dart\nError: {error}")
            self._status_action.setText(f"Error: {error}")
            return

        prev_battery = self.battery_percent
        self.battery_percent = battery
        self.is_charging = charging
        self.error = None

        # Handle notifications
        self._check_notifications(battery, charging, prev_battery)

        # Start/stop charging animation
        anim_enabled = self._config.tray["charging_animation"]
        anim_fps = self._config.tray["animation_fps"]
        anim_interval = int(1000 / anim_fps) if anim_fps > 0 else 150

        if charging and anim_enabled and not self._charging_timer.isActive():
            self._charging_frame = 0
            self._charging_timer.start(anim_interval)
        elif (not charging or not anim_enabled) and self._charging_timer.isActive():
            self._charging_timer.stop()

        self.setIcon(self._create_icon(battery, charging))

        charging_str = " (Charging)" if charging else ""
        self.setToolTip(f"HyperX Pulsefire Dart\nBattery: {battery}%{charging_str}\nMode: {mode}")
        self._status_action.setText(f"Battery: {battery}%{charging_str}")
        self._mode_action.setText(f"Mode: {mode}")

    # ---- Notifications ----------------------------------------------------

    def _check_notifications(self, battery: int, charging: bool, prev_battery: int | None):
        """Check if we should show battery notifications."""
        notif_config = self._config.notifications

        if not notif_config["enabled"]:
            return

        # Charging state changed
        if notif_config["charging_notify"]:
            if charging and not self._was_charging:
                self._send_notification("Charging Started", f"Battery at {battery}%")
                self._notified_thresholds.clear()  # Reset thresholds when charging
            elif not charging and self._was_charging:
                self._send_notification("Charging Stopped", f"Battery at {battery}%")

        self._was_charging = charging

        # Fully charged
        if notif_config["full_notify"] and charging and battery == 100:
            if "full" not in self._notified_thresholds:
                self._send_notification("Fully Charged", "Battery is at 100%")
                self._notified_thresholds.add("full")

        # Low battery thresholds (only when discharging)
        if not charging and prev_battery is not None:
            thresholds = sorted(notif_config["thresholds"], reverse=True)
            for threshold in thresholds:
                if battery <= threshold < prev_battery:
                    if threshold not in self._notified_thresholds:
                        urgency = "critical" if threshold <= 10 else "normal"
                        self._send_notification(
                            f"Low Battery: {battery}%",
                            f"Battery has dropped to {battery}%",
                            urgency=urgency
                        )
                        self._notified_thresholds.add(threshold)

        # Reset thresholds if battery goes back up (e.g., after charging)
        if prev_battery is not None and battery > prev_battery:
            self._notified_thresholds = {t for t in self._notified_thresholds if t < battery}

    def _send_notification(self, title: str, message: str, urgency: str = "normal"):
        """Send a desktop notification."""
        import subprocess
        try:
            subprocess.run([
                "notify-send",
                "-a", "HyperX Pulsefire",
                "-u", urgency,
                "-i", "input-mouse",
                title,
                message
            ], check=False, capture_output=True)
        except FileNotFoundError:
            pass  # notify-send not available

    # ---- Panel management -----------------------------------------------

    def _show_panel(self):
        """Create and show the configuration panel."""
        # Lazy import to avoid circular dependency
        from hyperx_battery.panel import ConfigPanel
        from PyQt5.QtGui import QCursor

        # Stop polling while panel is open (panel uses device connection)
        self._poll_timer.stop()

        # Create new panel each time (destroyed on close)
        if self._panel is not None:
            self._panel.hide()
            self._panel.deleteLater()

        self._panel = ConfigPanel()
        self._panel.destroyed.connect(self._on_panel_closed)

        # Use cursor position - works reliably on Wayland
        cursor_pos = QCursor.pos()
        self._panel.popup_at_tray(cursor_pos)

    def _on_panel_closed(self):
        """Resume polling when panel is closed."""
        poll_interval_ms = self._config.polling["interval_seconds"] * 1000
        self._poll_timer.start(poll_interval_ms)
        self.update_battery()

    def _toggle_panel(self):
        """Toggle panel visibility."""
        if self._panel is not None and self._panel.isVisible():
            self._panel.hide()
            self._panel.deleteLater()
            self._panel = None
            self._on_panel_closed()
        else:
            self._show_panel()

    # ---- Click handler --------------------------------------------------

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            # Left click - toggle panel
            self._toggle_panel()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("HyperX Battery Monitor")

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("Error: System tray is not available on this desktop environment.")
        sys.exit(1)

    _tray = BatteryTrayIcon()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
