"""Macros section widget - macro editor with event list and assignment."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QComboBox, QSpinBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox
)
from PyQt5.QtCore import Qt

from hyperx_battery.device import HyperXDevice
from hyperx_battery.protocol import (
    MacroEvent, MacroRepeatMode, BUTTON_NAMES,
)
from hyperx_battery.widgets.buttons_section import KEYBOARD_CODES


# Reverse lookup for keyboard codes
KEYBOARD_NAMES = {v: k for k, v in KEYBOARD_CODES.items()}


class MacrosSection(QWidget):
    """Macro editor and assignment section."""

    def __init__(self, device: HyperXDevice, parent=None):
        super().__init__(parent)
        self._device = device
        self._events: list[MacroEvent] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Assignment Group
        assign_group = QGroupBox("Macro Assignment")
        assign_layout = QHBoxLayout(assign_group)

        assign_layout.addWidget(QLabel("Assign to:"))
        self._button_combo = QComboBox()
        for idx, name in BUTTON_NAMES.items():
            self._button_combo.addItem(name, idx)
        assign_layout.addWidget(self._button_combo)

        assign_layout.addWidget(QLabel("Repeat:"))
        self._repeat_combo = QComboBox()
        self._repeat_combo.addItem("Single", MacroRepeatMode.SINGLE)
        self._repeat_combo.addItem("Toggle (On/Off)", MacroRepeatMode.TOGGLE)
        self._repeat_combo.addItem("Hold (While Pressed)", MacroRepeatMode.HOLD)
        assign_layout.addWidget(self._repeat_combo)

        assign_layout.addStretch()
        layout.addWidget(assign_group)

        # Events Group
        events_group = QGroupBox("Macro Events")
        events_layout = QVBoxLayout(events_group)

        # Event table
        self._events_table = QTableWidget()
        self._events_table.setColumnCount(3)
        self._events_table.setHorizontalHeaderLabels(["Type", "Code/Key", "Value"])
        self._events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._events_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._events_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._events_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._events_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._events_table.setMinimumHeight(200)
        events_layout.addWidget(self._events_table)

        # Event controls
        controls_layout = QHBoxLayout()

        # Add event type
        self._event_type_combo = QComboBox()
        self._event_type_combo.addItem("Key Press", "key_press")
        self._event_type_combo.addItem("Key Down", "key_down")
        self._event_type_combo.addItem("Key Up", "key_up")
        self._event_type_combo.addItem("Mouse Down", "mouse_down")
        self._event_type_combo.addItem("Mouse Up", "mouse_up")
        self._event_type_combo.addItem("Delay", "delay")
        self._event_type_combo.currentIndexChanged.connect(self._on_event_type_changed)
        controls_layout.addWidget(self._event_type_combo)

        # Key/code selector
        self._code_combo = QComboBox()
        for name, code in KEYBOARD_CODES.items():
            if name != "None":
                self._code_combo.addItem(name, code)
        controls_layout.addWidget(self._code_combo)

        # Delay spinbox (hidden by default)
        self._delay_spin = QSpinBox()
        self._delay_spin.setRange(1, 10000)
        self._delay_spin.setSuffix(" ms")
        self._delay_spin.setValue(50)
        self._delay_spin.hide()
        controls_layout.addWidget(self._delay_spin)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._on_add_clicked)
        controls_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._on_remove_clicked)
        controls_layout.addWidget(remove_btn)

        controls_layout.addStretch()

        move_up_btn = QPushButton("Up")
        move_up_btn.clicked.connect(self._on_move_up)
        controls_layout.addWidget(move_up_btn)

        move_down_btn = QPushButton("Down")
        move_down_btn.clicked.connect(self._on_move_down)
        controls_layout.addWidget(move_down_btn)

        events_layout.addLayout(controls_layout)
        layout.addWidget(events_group)

        # Upload button
        upload_layout = QHBoxLayout()
        upload_btn = QPushButton("Upload Macro to Device")
        upload_btn.clicked.connect(self._on_upload_clicked)
        upload_layout.addWidget(upload_btn)

        clear_btn = QPushButton("Clear All Events")
        clear_btn.clicked.connect(self._on_clear_clicked)
        upload_layout.addWidget(clear_btn)

        upload_layout.addStretch()
        layout.addLayout(upload_layout)

        # Info
        info_label = QLabel(
            "Create a macro by adding events, then upload to the device.\n"
            "Use 'Key Press' for a down+up combination, or individual Down/Up for more control."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def _on_event_type_changed(self, index: int):
        """Show/hide appropriate input widgets based on event type."""
        event_type = self._event_type_combo.currentData()
        if event_type == "delay":
            self._code_combo.hide()
            self._delay_spin.show()
        else:
            self._code_combo.show()
            self._delay_spin.hide()

            # Update code combo for mouse events
            if event_type in ("mouse_down", "mouse_up"):
                self._code_combo.clear()
                self._code_combo.addItem("Left", 1)
                self._code_combo.addItem("Right", 2)
                self._code_combo.addItem("Middle", 3)
            else:
                # Restore keyboard codes if not already
                if self._code_combo.count() < 10:
                    self._code_combo.clear()
                    for name, code in KEYBOARD_CODES.items():
                        if name != "None":
                            self._code_combo.addItem(name, code)

    def _on_add_clicked(self):
        """Add a new event to the list."""
        event_type = self._event_type_combo.currentData()

        if event_type == "delay":
            delay_ms = self._delay_spin.value()
            self._events.append(MacroEvent("delay", delay_ms))
        elif event_type == "key_press":
            # Key press = key_down + key_up
            code = self._code_combo.currentData()
            self._events.append(MacroEvent("key_down", code))
            self._events.append(MacroEvent("key_up", code))
        else:
            code = self._code_combo.currentData()
            self._events.append(MacroEvent(event_type, code))

        self._refresh_table()

    def _on_remove_clicked(self):
        """Remove selected event."""
        row = self._events_table.currentRow()
        if row >= 0 and row < len(self._events):
            del self._events[row]
            self._refresh_table()

    def _on_move_up(self):
        """Move selected event up."""
        row = self._events_table.currentRow()
        if row > 0:
            self._events[row], self._events[row - 1] = self._events[row - 1], self._events[row]
            self._refresh_table()
            self._events_table.selectRow(row - 1)

    def _on_move_down(self):
        """Move selected event down."""
        row = self._events_table.currentRow()
        if row >= 0 and row < len(self._events) - 1:
            self._events[row], self._events[row + 1] = self._events[row + 1], self._events[row]
            self._refresh_table()
            self._events_table.selectRow(row + 1)

    def _on_clear_clicked(self):
        """Clear all events."""
        self._events.clear()
        self._refresh_table()

    def _on_upload_clicked(self):
        """Upload macro to device."""
        if not self._events:
            QMessageBox.warning(self, "No Events", "Please add at least one event to the macro.")
            return

        if not self._device.is_open:
            QMessageBox.warning(self, "Not Connected", "Device is not connected.")
            return

        button_idx = self._button_combo.currentData()

        # Upload macro data to the button
        success = self._device.upload_macro(button_idx, self._events)
        if not success:
            QMessageBox.critical(self, "Upload Failed", "Failed to upload macro data.")
            return

        # Set button to macro type
        from hyperx_battery.protocol import ButtonType
        success = self._device.set_button(button_idx, ButtonType.MACRO, 0x00)
        if success:
            QMessageBox.information(
                self, "Success",
                f"Macro uploaded and assigned to {BUTTON_NAMES[button_idx]}."
            )
        else:
            QMessageBox.critical(self, "Assignment Failed", "Failed to assign macro to button.")

    def _refresh_table(self):
        """Refresh the events table from the internal list."""
        self._events_table.setRowCount(len(self._events))

        for row, event in enumerate(self._events):
            # Type
            type_item = QTableWidgetItem(event.event_type.replace("_", " ").title())
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self._events_table.setItem(row, 0, type_item)

            # Code/Key name
            if event.event_type == "delay":
                code_item = QTableWidgetItem("Delay")
            elif event.event_type in ("mouse_down", "mouse_up"):
                names = {1: "Left", 2: "Right", 3: "Middle"}
                code_item = QTableWidgetItem(names.get(event.code, str(event.code)))
            else:
                code_item = QTableWidgetItem(KEYBOARD_NAMES.get(event.code, f"0x{event.code:02X}"))
            code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
            self._events_table.setItem(row, 1, code_item)

            # Value
            if event.event_type == "delay":
                value_item = QTableWidgetItem(f"{event.code} ms")
            else:
                value_item = QTableWidgetItem(f"0x{event.code:02X}")
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self._events_table.setItem(row, 2, value_item)

    def refresh(self):
        """Refresh section (no device query needed)."""
        pass
