"""Button mapping section widget - remap 6 mouse buttons."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QGridLayout, QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt, QEvent
from PyQt5.QtGui import QKeySequence

from hyperx_battery.device import HyperXDevice
from hyperx_battery.protocol import (
    ButtonType, MouseButton, MediaCode, DpiFunction,
    BUTTON_NAMES, MEDIA_CODE_NAMES,
)


# Common keyboard scancodes (HID Usage Table)
KEYBOARD_CODES = {
    "None": 0x00,
    "A": 0x04, "B": 0x05, "C": 0x06, "D": 0x07, "E": 0x08, "F": 0x09,
    "G": 0x0A, "H": 0x0B, "I": 0x0C, "J": 0x0D, "K": 0x0E, "L": 0x0F,
    "M": 0x10, "N": 0x11, "O": 0x12, "P": 0x13, "Q": 0x14, "R": 0x15,
    "S": 0x16, "T": 0x17, "U": 0x18, "V": 0x19, "W": 0x1A, "X": 0x1B,
    "Y": 0x1C, "Z": 0x1D,
    "1": 0x1E, "2": 0x1F, "3": 0x20, "4": 0x21, "5": 0x22,
    "6": 0x23, "7": 0x24, "8": 0x25, "9": 0x26, "0": 0x27,
    "Enter": 0x28, "Escape": 0x29, "Backspace": 0x2A, "Tab": 0x2B,
    "Space": 0x2C, "F1": 0x3A, "F2": 0x3B, "F3": 0x3C, "F4": 0x3D,
    "F5": 0x3E, "F6": 0x3F, "F7": 0x40, "F8": 0x41, "F9": 0x42,
    "F10": 0x43, "F11": 0x44, "F12": 0x45,
    "Print Screen": 0x46, "Scroll Lock": 0x47, "Pause": 0x48,
    "Insert": 0x49, "Home": 0x4A, "Page Up": 0x4B,
    "Delete": 0x4C, "End": 0x4D, "Page Down": 0x4E,
    "Right Arrow": 0x4F, "Left Arrow": 0x50, "Down Arrow": 0x51, "Up Arrow": 0x52,
}


class ButtonMappingRow(QWidget):
    """Single button mapping row."""

    def __init__(self, button_idx: int, button_name: str, parent=None):
        super().__init__(parent)
        self.button_idx = button_idx
        self.button_name = button_name
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)

        # Button name label
        name_label = QLabel(self.button_name)
        name_label.setMinimumWidth(90)
        layout.addWidget(name_label)

        # Type combo
        self.type_combo = QComboBox()
        self.type_combo.addItem("Mouse", ButtonType.MOUSE)
        self.type_combo.addItem("Keyboard", ButtonType.KEYBOARD)
        self.type_combo.addItem("Media", ButtonType.MEDIA)
        self.type_combo.addItem("DPI", ButtonType.DPI)
        self.type_combo.addItem("Disabled", ButtonType.DISABLED)
        self.type_combo.setMinimumWidth(100)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addWidget(self.type_combo)

        # Function combo (changes based on type)
        self.function_combo = QComboBox()
        self.function_combo.setMinimumWidth(140)
        layout.addWidget(self.function_combo, 1)  # stretch factor 1

        layout.addStretch()

        # Initialize function options
        self._on_type_changed(0)

    def _on_type_changed(self, index: int):
        """Update function combo options based on selected type."""
        button_type = self.type_combo.currentData()
        self.function_combo.clear()

        if button_type == ButtonType.MOUSE:
            self.function_combo.addItem("Left Click", MouseButton.LEFT)
            self.function_combo.addItem("Right Click", MouseButton.RIGHT)
            self.function_combo.addItem("Middle Click", MouseButton.MIDDLE)
            self.function_combo.addItem("Back", MouseButton.BACK)
            self.function_combo.addItem("Forward", MouseButton.FORWARD)

        elif button_type == ButtonType.KEYBOARD:
            for name, code in KEYBOARD_CODES.items():
                self.function_combo.addItem(name, code)

        elif button_type == ButtonType.MEDIA:
            for code, name in MEDIA_CODE_NAMES.items():
                self.function_combo.addItem(name, code)

        elif button_type == ButtonType.DPI:
            self.function_combo.addItem("Cycle Up", DpiFunction.CYCLE_UP)
            self.function_combo.addItem("Cycle Down", DpiFunction.CYCLE_DOWN)
            self.function_combo.addItem("Cycle All", DpiFunction.CYCLE)

        elif button_type == ButtonType.DISABLED:
            self.function_combo.addItem("Disabled", 0)

    def get_mapping(self) -> tuple:
        """Get current mapping as (button_type, code)."""
        button_type = self.type_combo.currentData()
        code = self.function_combo.currentData()
        return button_type, code if code is not None else 0

    def set_default_mapping(self):
        """Set default mapping for this button."""
        # Default mappings
        defaults = {
            0: (ButtonType.MOUSE, MouseButton.LEFT),
            1: (ButtonType.MOUSE, MouseButton.RIGHT),
            2: (ButtonType.MOUSE, MouseButton.MIDDLE),
            3: (ButtonType.MOUSE, MouseButton.FORWARD),
            4: (ButtonType.MOUSE, MouseButton.BACK),
            5: (ButtonType.DPI, DpiFunction.CYCLE),
        }

        if self.button_idx in defaults:
            btn_type, code = defaults[self.button_idx]
            # Set type
            for i in range(self.type_combo.count()):
                if self.type_combo.itemData(i) == btn_type:
                    self.type_combo.setCurrentIndex(i)
                    break
            # Set function
            for i in range(self.function_combo.count()):
                if self.function_combo.itemData(i) == code:
                    self.function_combo.setCurrentIndex(i)
                    break


class ButtonsSection(QWidget):
    """Button mapping configuration section."""

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._updating = False
        self._rows: list[ButtonMappingRow] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Button Mappings Group
        mappings_group = QGroupBox("Button Mappings")
        mappings_layout = QVBoxLayout(mappings_group)

        # No header - labels are clear enough in each row

        # Button rows
        for button_idx, button_name in BUTTON_NAMES.items():
            row = ButtonMappingRow(button_idx, button_name)
            row.set_default_mapping()
            row.type_combo.currentIndexChanged.connect(
                lambda idx, b=button_idx: self._on_mapping_changed(b)
            )
            row.function_combo.currentIndexChanged.connect(
                lambda idx, b=button_idx: self._on_mapping_changed(b)
            )
            self._rows.append(row)
            mappings_layout.addWidget(row)

        layout.addWidget(mappings_group)

        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._on_reset_clicked)
        layout.addWidget(reset_btn, alignment=Qt.AlignLeft)

        # Info
        info_label = QLabel(
            "Changes are applied immediately. Use 'Save to Device Memory' to persist across power cycles."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def refresh(self):
        """Refresh button mappings (placeholder - device may not support query)."""
        self._updating = True
        # Keep default values
        self._updating = False

    def _on_mapping_changed(self, button_idx: int):
        if self._updating or not self._device.is_open:
            return

        row = self._rows[button_idx]
        button_type, code = row.get_mapping()
        self._device.set_button(button_idx, button_type, code)

    def _on_reset_clicked(self):
        self._updating = True
        for row in self._rows:
            row.set_default_mapping()
        self._updating = False

        # Apply all defaults to device
        if self._device.is_open:
            for row in self._rows:
                button_type, code = row.get_mapping()
                self._device.set_button(row.button_idx, button_type, code)
