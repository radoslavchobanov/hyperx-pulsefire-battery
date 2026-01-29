"""LED section widget - LED color, effect, brightness and speed configuration."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QSlider, QPushButton, QGridLayout, QColorDialog
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from hyperx_battery.device import HyperXDevice
from hyperx_battery.protocol import LedTarget, LedEffect


class LedSection(QWidget):
    """LED configuration section."""

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._updating = False
        self._current_color = QColor(255, 0, 0)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # LED Settings Group
        led_group = QGroupBox("LED Settings")
        led_layout = QGridLayout(led_group)
        led_layout.setSpacing(8)

        # Target Zone
        row = 0
        led_layout.addWidget(QLabel("Target:"), row, 0)
        self._target_combo = QComboBox()
        self._target_combo.addItem("Logo", LedTarget.LOGO)
        self._target_combo.addItem("Scroll Wheel", LedTarget.SCROLL)
        self._target_combo.addItem("Both", LedTarget.BOTH)
        self._target_combo.setCurrentIndex(2)  # Default to Both
        self._target_combo.currentIndexChanged.connect(self._on_setting_changed)
        led_layout.addWidget(self._target_combo, row, 1)

        # Effect
        row += 1
        led_layout.addWidget(QLabel("Effect:"), row, 0)
        self._effect_combo = QComboBox()
        self._effect_combo.addItem("Static", LedEffect.STATIC)
        self._effect_combo.addItem("Breathing", LedEffect.BREATHING)
        self._effect_combo.addItem("Spectrum Cycle", LedEffect.SPECTRUM_CYCLE)
        self._effect_combo.addItem("Trigger Fade", LedEffect.TRIGGER_FADE)
        self._effect_combo.currentIndexChanged.connect(self._on_setting_changed)
        led_layout.addWidget(self._effect_combo, row, 1)

        # Color
        row += 1
        led_layout.addWidget(QLabel("Color:"), row, 0)
        self._color_button = QPushButton()
        self._color_button.setFixedSize(80, 28)
        self._update_color_button()
        self._color_button.clicked.connect(self._on_color_clicked)
        led_layout.addWidget(self._color_button, row, 1, alignment=Qt.AlignLeft)

        # Brightness
        row += 1
        led_layout.addWidget(QLabel("Brightness:"), row, 0)
        brightness_layout = QHBoxLayout()
        self._brightness_slider = QSlider(Qt.Horizontal)
        self._brightness_slider.setRange(0, 100)
        self._brightness_slider.setValue(100)
        self._brightness_slider.valueChanged.connect(self._on_setting_changed)
        brightness_layout.addWidget(self._brightness_slider)
        self._brightness_label = QLabel("100%")
        self._brightness_label.setFixedWidth(40)
        brightness_layout.addWidget(self._brightness_label)
        led_layout.addLayout(brightness_layout, row, 1)

        # Speed
        row += 1
        led_layout.addWidget(QLabel("Speed:"), row, 0)
        speed_layout = QHBoxLayout()
        self._speed_slider = QSlider(Qt.Horizontal)
        self._speed_slider.setRange(0, 100)
        self._speed_slider.setValue(50)
        self._speed_slider.valueChanged.connect(self._on_setting_changed)
        speed_layout.addWidget(self._speed_slider)
        self._speed_label = QLabel("50%")
        self._speed_label.setFixedWidth(40)
        speed_layout.addWidget(self._speed_label)
        led_layout.addLayout(speed_layout, row, 1)

        led_layout.setColumnStretch(1, 1)
        layout.addWidget(led_group)

        info_label = QLabel("Note: Speed only affects Breathing and Spectrum effects.")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def _update_color_button(self):
        """Update the color button background to match current color."""
        self._color_button.setStyleSheet(
            f"background-color: {self._current_color.name()}; border: 1px solid #888;"
        )

    def refresh(self):
        """Refresh LED settings from device."""
        if not self._device.is_open:
            return

        self._updating = True

        # Query current LED settings from memory
        settings = self._device.get_led_settings()
        if settings:
            # Set color from memory
            self._current_color = QColor(settings.red, settings.green, settings.blue)
            self._update_color_button()

            # Set brightness
            self._brightness_slider.setValue(settings.brightness)
            self._brightness_label.setText(f"{settings.brightness}%")

        self._updating = False

    def _on_color_clicked(self):
        """Open color picker dialog."""
        color = QColorDialog.getColor(self._current_color, self, "Select LED Color")
        if color.isValid():
            self._current_color = color
            self._update_color_button()
            self._apply_settings()

    def _on_setting_changed(self):
        """Handle any setting change."""
        if self._updating:
            return

        # Update labels
        self._brightness_label.setText(f"{self._brightness_slider.value()}%")
        self._speed_label.setText(f"{self._speed_slider.value()}%")

        self._apply_settings()

    def _apply_settings(self):
        """Apply current settings to device."""
        if self._updating or not self._device.is_open:
            return

        target = self._target_combo.currentData()
        effect = self._effect_combo.currentData()
        brightness = self._brightness_slider.value()
        speed = self._speed_slider.value()

        self._device.set_led(
            target=target,
            effect=effect,
            red=self._current_color.red(),
            green=self._current_color.green(),
            blue=self._current_color.blue(),
            brightness=brightness,
            speed=speed,
        )
