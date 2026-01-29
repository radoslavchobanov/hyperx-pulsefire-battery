"""Settings section widget - polling rate and battery alert configuration."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QSpinBox, QGridLayout
)
from PyQt5.QtCore import Qt

from hyperx_battery.device import HyperXDevice


class SettingsSection(QWidget):
    """Settings section for polling rate and battery alert threshold."""

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Polling Rate Group
        polling_group = QGroupBox("Polling Rate")
        polling_layout = QHBoxLayout(polling_group)

        polling_layout.addWidget(QLabel("Rate:"))
        self._polling_combo = QComboBox()
        self._polling_combo.addItem("125 Hz", 125)
        self._polling_combo.addItem("250 Hz", 250)
        self._polling_combo.addItem("500 Hz", 500)
        self._polling_combo.addItem("1000 Hz (Recommended)", 1000)
        self._polling_combo.setCurrentIndex(3)  # Default to 1000 Hz
        self._polling_combo.currentIndexChanged.connect(self._on_polling_changed)
        polling_layout.addWidget(self._polling_combo)
        polling_layout.addStretch()

        layout.addWidget(polling_group)

        # Battery Alert Group
        battery_group = QGroupBox("Battery Alert")
        battery_layout = QGridLayout(battery_group)
        battery_layout.setSpacing(8)

        battery_layout.addWidget(QLabel("Alert Threshold:"), 0, 0)
        self._alert_spin = QSpinBox()
        self._alert_spin.setRange(5, 25)
        self._alert_spin.setSuffix("%")
        self._alert_spin.setValue(10)
        self._alert_spin.valueChanged.connect(self._on_alert_changed)
        battery_layout.addWidget(self._alert_spin, 0, 1)

        info_label = QLabel("The mouse will alert when battery falls below this level.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        battery_layout.addWidget(info_label, 1, 0, 1, 2)

        layout.addWidget(battery_group)

        layout.addStretch()

    def refresh(self):
        """Refresh settings from device (placeholder - device may not report these)."""
        self._updating = True
        # Note: The device may not support querying current polling rate/alert
        # Keep current UI values as defaults
        self._updating = False

    def _on_polling_changed(self, index: int):
        if self._updating:
            return
        hz = self._polling_combo.itemData(index)
        if hz and self._device.is_open:
            self._device.set_polling_rate(hz)

    def _on_alert_changed(self, value: int):
        if self._updating:
            return
        if self._device.is_open:
            self._device.set_battery_alert(value)
