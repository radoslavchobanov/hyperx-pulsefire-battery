"""DPI section widget - 5 DPI profiles with enable, value, and color settings."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QSpinBox, QPushButton, QGridLayout, QCheckBox, QRadioButton,
    QButtonGroup, QColorDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from hyperx_battery.device import HyperXDevice


class DpiProfileRow(QWidget):
    """Single DPI profile row with enable, value, and color controls."""

    def __init__(self, profile_idx: int, parent=None):
        super().__init__(parent)
        self.profile_idx = profile_idx
        self._color = QColor(255, 255, 255)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # Enable checkbox
        self.enable_check = QCheckBox()
        self.enable_check.setChecked(True)
        layout.addWidget(self.enable_check)

        # Active radio button
        self.active_radio = QRadioButton(f"Profile {self.profile_idx + 1}")
        self.active_radio.setFixedWidth(80)
        layout.addWidget(self.active_radio)

        # DPI value spinbox
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(50, 16000)
        self.dpi_spin.setSingleStep(50)
        self.dpi_spin.setSuffix(" DPI")
        self.dpi_spin.setValue(800 + self.profile_idx * 400)  # Default progression
        self.dpi_spin.setFixedWidth(120)
        layout.addWidget(self.dpi_spin)

        # Color button
        self.color_button = QPushButton()
        self.color_button.setFixedSize(40, 24)
        self._update_color_button()
        layout.addWidget(self.color_button)

        layout.addStretch()

    def _update_color_button(self):
        """Update color button background."""
        self.color_button.setStyleSheet(
            f"background-color: {self._color.name()}; border: 1px solid #888;"
        )

    def get_color(self) -> QColor:
        return self._color

    def set_color(self, color: QColor):
        self._color = color
        self._update_color_button()


class DpiSection(QWidget):
    """DPI configuration section with 5 profiles."""

    DEFAULT_COLORS = [
        QColor(255, 0, 0),      # Profile 1: Red
        QColor(255, 165, 0),    # Profile 2: Orange
        QColor(255, 255, 0),    # Profile 3: Yellow
        QColor(0, 255, 0),      # Profile 4: Green
        QColor(0, 128, 255),    # Profile 5: Blue
    ]

    DEFAULT_DPIS = [400, 800, 1600, 3200, 6400]

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._updating = False
        self._profiles: list[DpiProfileRow] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # DPI Profiles Group
        profiles_group = QGroupBox("DPI Profiles")
        profiles_layout = QVBoxLayout(profiles_group)

        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("On"))
        header_layout.addWidget(QLabel("Active"))
        header_layout.addSpacing(50)
        header_layout.addWidget(QLabel("DPI Value"))
        header_layout.addSpacing(30)
        header_layout.addWidget(QLabel("Color"))
        header_layout.addStretch()
        profiles_layout.addLayout(header_layout)

        # Radio button group for active profile
        self._active_group = QButtonGroup(self)

        # Profile rows
        for i in range(5):
            row = DpiProfileRow(i)
            row.set_color(self.DEFAULT_COLORS[i])
            row.dpi_spin.setValue(self.DEFAULT_DPIS[i])
            self._profiles.append(row)
            self._active_group.addButton(row.active_radio, i)

            # Connect signals
            row.enable_check.stateChanged.connect(lambda state, idx=i: self._on_enable_changed(idx, state))
            row.dpi_spin.valueChanged.connect(lambda value, idx=i: self._on_dpi_changed(idx, value))
            row.color_button.clicked.connect(lambda checked, idx=i: self._on_color_clicked(idx))

            profiles_layout.addWidget(row)

        # Set first profile as active by default
        self._profiles[0].active_radio.setChecked(True)
        self._active_group.buttonClicked.connect(self._on_active_changed)

        layout.addWidget(profiles_group)

        # Info
        info_label = QLabel(
            "Enable/disable profiles to control which DPI levels are available when cycling.\n"
            "The active profile shows the current DPI level."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def refresh(self):
        """Refresh DPI settings from device."""
        if not self._device.is_open:
            return

        self._updating = True

        dpi_settings = self._device.get_dpi_settings()
        if dpi_settings:
            # Set active profile
            active = dpi_settings.get('active_profile', 0)
            if 0 <= active < 5:
                self._profiles[active].active_radio.setChecked(True)

            # Set DPI values
            dpi_values = dpi_settings.get('dpi_values', [])
            for i, dpi in enumerate(dpi_values[:5]):
                if i < len(self._profiles):
                    self._profiles[i].dpi_spin.setValue(dpi)

            # Set colors if available
            colors = dpi_settings.get('colors', [])
            for i, color in enumerate(colors[:5]):
                if i < len(self._profiles) and len(color) == 3:
                    from PyQt5.QtGui import QColor
                    self._profiles[i].set_color(QColor(color[0], color[1], color[2]))

        self._updating = False

    def _on_enable_changed(self, profile_idx: int, state: int):
        if self._updating or not self._device.is_open:
            return

        # Build enable mask from all checkboxes
        mask = 0
        for i, row in enumerate(self._profiles):
            if row.enable_check.isChecked():
                mask |= (1 << i)

        self._device.set_dpi_enable_mask(mask)

    def _on_dpi_changed(self, profile_idx: int, value: int):
        if self._updating or not self._device.is_open:
            return

        # Round to step of 50
        value = (value // 50) * 50
        self._device.set_dpi_value(profile_idx, value)

    def _on_color_clicked(self, profile_idx: int):
        row = self._profiles[profile_idx]
        color = QColorDialog.getColor(row.get_color(), self, f"Profile {profile_idx + 1} Color")
        if color.isValid():
            row.set_color(color)
            if self._device.is_open:
                self._device.set_dpi_color(profile_idx, color.red(), color.green(), color.blue())

    def _on_active_changed(self, button):
        if self._updating or not self._device.is_open:
            return

        profile_idx = self._active_group.id(button)
        if profile_idx >= 0:
            self._device.set_dpi_active(profile_idx)
