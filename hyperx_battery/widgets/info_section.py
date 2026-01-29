"""Info section widget - displays read-only device information."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from hyperx_battery.device import HyperXDevice


class InfoSection(QWidget):
    """Read-only section displaying device information."""

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Device Info Group
        device_group = QGroupBox("Device Information")
        device_layout = QGridLayout(device_group)
        device_layout.setSpacing(8)

        self._firmware_label = QLabel("---")
        self._name_label = QLabel("---")
        self._vendor_label = QLabel("---")
        self._product_label = QLabel("---")
        self._mode_label = QLabel("---")

        row = 0
        device_layout.addWidget(QLabel("Firmware:"), row, 0)
        device_layout.addWidget(self._firmware_label, row, 1)
        row += 1
        device_layout.addWidget(QLabel("Device Name:"), row, 0)
        device_layout.addWidget(self._name_label, row, 1)
        row += 1
        device_layout.addWidget(QLabel("Vendor ID:"), row, 0)
        device_layout.addWidget(self._vendor_label, row, 1)
        row += 1
        device_layout.addWidget(QLabel("Product ID:"), row, 0)
        device_layout.addWidget(self._product_label, row, 1)
        row += 1
        device_layout.addWidget(QLabel("Connection:"), row, 0)
        device_layout.addWidget(self._mode_label, row, 1)

        device_layout.setColumnStretch(1, 1)
        layout.addWidget(device_group)

        # Battery Group
        battery_group = QGroupBox("Battery Status")
        battery_layout = QGridLayout(battery_group)
        battery_layout.setSpacing(8)

        self._battery_label = QLabel("---")
        self._battery_label.setFont(QFont("Sans", 16, QFont.Bold))
        self._charging_label = QLabel("---")

        battery_layout.addWidget(QLabel("Level:"), 0, 0)
        battery_layout.addWidget(self._battery_label, 0, 1)
        battery_layout.addWidget(QLabel("Status:"), 1, 0)
        battery_layout.addWidget(self._charging_label, 1, 1)

        battery_layout.setColumnStretch(1, 1)
        layout.addWidget(battery_group)

        layout.addStretch()

    def refresh(self):
        """Refresh all displayed information from the device."""
        if not self._device.is_open:
            self._set_disconnected()
            return

        # Get hardware info
        hw_info = self._device.get_hw_info()
        if hw_info:
            self._firmware_label.setText(hw_info.firmware_version)
            self._name_label.setText(hw_info.device_name or "HyperX Pulsefire Dart")
            self._vendor_label.setText(f"0x{hw_info.vendor_id:04X}")
            self._product_label.setText(f"0x{hw_info.product_id:04X}")
        else:
            self._firmware_label.setText("Unknown")
            self._name_label.setText("HyperX Pulsefire Dart")
            self._vendor_label.setText("0x0951")
            self._product_label.setText("---")

        # Connection mode
        self._mode_label.setText(self._device.mode.capitalize() if self._device.mode else "Unknown")

        # Get battery status
        battery = self._device.get_battery()
        if battery:
            self._battery_label.setText(f"{battery.percent}%")
            if battery.is_charging:
                self._charging_label.setText("Charging")
                self._charging_label.setStyleSheet("color: #64C8FF;")
            else:
                self._charging_label.setText("Discharging")
                self._charging_label.setStyleSheet("")
        else:
            self._battery_label.setText("---")
            self._charging_label.setText("Unknown")
            self._charging_label.setStyleSheet("")

    def _set_disconnected(self):
        """Set all labels to disconnected state."""
        self._firmware_label.setText("---")
        self._name_label.setText("---")
        self._vendor_label.setText("---")
        self._product_label.setText("---")
        self._mode_label.setText("Disconnected")
        self._battery_label.setText("---")
        self._charging_label.setText("---")
        self._charging_label.setStyleSheet("")
