"""Configuration panel popup for wireless mouse - Plasma style."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QLabel, QApplication, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QRegion

from plasmangenuity.device import HyperXDevice
from plasmangenuity.widgets import (
    InfoSection, SettingsSection, LedSection,
    DpiSection, ButtonsSection, MacrosSection
)


class ConfigPanel(QWidget):
    """Plasma-style popup configuration panel for a wireless mouse."""

    PANEL_WIDTH = 500
    PANEL_HEIGHT = 600
    CORNER_RADIUS = 10
    MARGIN_FROM_EDGE = 8

    def __init__(self, parent=None, device_info=None, driver=None):
        """Create the config panel.

        Args:
            parent: Parent widget.
            device_info: A DeviceInfo object (from the new system). Optional.
            driver: A HidMouseDriver instance (for config features). Optional.
        """
        super().__init__(parent)
        self._device_info = device_info
        self._driver = driver

        # Legacy path: if no driver provided, use HyperXDevice for backward compat.
        # The widget sections still expect HyperXDevice-compatible interface.
        if driver is None:
            self._device = HyperXDevice()
        else:
            self._device = driver

        self._sections = []
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        """Configure window flags for Plasma-like popup."""
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.PANEL_WIDTH, self.PANEL_HEIGHT)

    def _setup_ui(self):
        """Build the panel UI with Plasma styling."""
        self._container = QWidget(self)
        self._container.setObjectName("panelContainer")

        self._container.setStyleSheet("""
            #panelContainer {
                background-color: rgba(35, 38, 41, 245);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
            }
            QLabel {
                color: #eff0f1;
            }
            QGroupBox {
                color: #eff0f1;
                font-weight: bold;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 6px;
                background-color: rgba(255, 255, 255, 0.03);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #eff0f1;
            }
            QComboBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 5px 10px;
                color: #eff0f1;
                min-height: 22px;
            }
            QComboBox:hover {
                border-color: #3daee9;
                background-color: rgba(255, 255, 255, 0.15);
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid #eff0f1;
                margin-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #31363b;
                border: 1px solid rgba(255, 255, 255, 0.15);
                selection-background-color: #3daee9;
                color: #eff0f1;
            }
            QSpinBox {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 5px 10px;
                color: #eff0f1;
                min-height: 22px;
            }
            QSpinBox:hover {
                border-color: #3daee9;
            }
            QSlider::groove:horizontal {
                height: 4px;
                background: rgba(255, 255, 255, 0.2);
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #3daee9;
                width: 16px;
                height: 16px;
                margin: -6px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #5bc0f2;
            }
            QSlider::sub-page:horizontal {
                background: #3daee9;
                border-radius: 2px;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 4px;
                padding: 6px 14px;
                color: #eff0f1;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                border-color: #3daee9;
            }
            QPushButton:pressed {
                background-color: rgba(61, 174, 233, 0.3);
            }
            QCheckBox, QRadioButton {
                color: #eff0f1;
                spacing: 6px;
            }
            QCheckBox::indicator, QRadioButton::indicator {
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                background: rgba(255, 255, 255, 0.1);
            }
            QCheckBox::indicator:checked, QRadioButton::indicator:checked {
                background-color: #3daee9;
                border-color: #3daee9;
            }
            QRadioButton::indicator {
                border-radius: 9px;
            }
            QTableWidget {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                gridline-color: rgba(255, 255, 255, 0.1);
                color: #eff0f1;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: rgba(61, 174, 233, 0.3);
            }
            QHeaderView::section {
                background-color: rgba(255, 255, 255, 0.05);
                border: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
                padding: 6px;
                color: #eff0f1;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(255, 255, 255, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        # Dynamic title from device info
        title_text = "Wireless Mouse"
        if self._device_info:
            title_text = self._device_info.name or title_text
        elif hasattr(self._device, 'brand'):
            title_text = f"{self._device.brand} Mouse"
        else:
            title_text = "HyperX Pulsefire Dart"

        title_label = QLabel(title_text)
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #eff0f1;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        close_btn = QPushButton("\u00d7")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                color: #eff0f1;
                font-size: 20px;
                font-weight: normal;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        close_btn.clicked.connect(self.hide)
        header_layout.addWidget(close_btn)
        container_layout.addLayout(header_layout)

        # Determine capabilities
        caps = None
        if self._device_info:
            caps = self._device_info.capabilities

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                background: rgba(255, 255, 255, 0.02);
                top: -1px;
            }
            QTabBar::tab {
                background: transparent;
                border: none;
                padding: 8px 16px;
                margin-right: 2px;
                color: rgba(239, 240, 241, 0.7);
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background: rgba(255, 255, 255, 0.1);
                color: #eff0f1;
            }
            QTabBar::tab:hover:!selected {
                background: rgba(255, 255, 255, 0.05);
                color: #eff0f1;
            }
        """)

        # Always add Info tab
        self._info_section = InfoSection(self._device)
        self._tabs.addTab(self._info_section, "Info")
        self._sections.append(self._info_section)

        # Conditionally add config tabs based on capabilities
        has_config = caps is None or caps.dpi  # None = legacy mode, show all

        if has_config:
            self._dpi_section = DpiSection(self._device)
            self._tabs.addTab(self._dpi_section, "DPI")
            self._sections.append(self._dpi_section)

        if caps is None or caps.led:
            self._led_section = LedSection(self._device)
            self._tabs.addTab(self._led_section, "LED")
            self._sections.append(self._led_section)

        if caps is None or caps.buttons:
            self._buttons_section = ButtonsSection(self._device)
            self._tabs.addTab(self._buttons_section, "Buttons")
            self._sections.append(self._buttons_section)

        if caps is None or caps.macros:
            self._macros_section = MacrosSection(self._device)
            self._tabs.addTab(self._macros_section, "Macros")
            self._sections.append(self._macros_section)

        if caps is None or caps.polling_rate:
            self._settings_section = SettingsSection(self._device)
            self._tabs.addTab(self._settings_section, "Settings")
            self._sections.append(self._settings_section)

        container_layout.addWidget(self._tabs)

        # Save button — only show if the device supports saving
        has_save = caps is None or caps.dpi  # devices with config support saving
        if has_save:
            save_layout = QHBoxLayout()
            save_layout.addStretch()
            self._save_btn = QPushButton("Save to Device Memory")
            self._save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3daee9;
                    border: none;
                    border-radius: 4px;
                    color: white;
                    font-weight: bold;
                    padding: 8px 20px;
                }
                QPushButton:hover {
                    background-color: #5bc0f2;
                }
                QPushButton:pressed {
                    background-color: #2d9ad8;
                }
            """)
            self._save_btn.clicked.connect(self._on_save_clicked)
            save_layout.addWidget(self._save_btn)
            container_layout.addLayout(save_layout)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._container)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self._container.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, self.width(), self.height(),
            self.CORNER_RADIUS, self.CORNER_RADIUS
        )
        region = QRegion(path.toFillPolygon().toPolygon())
        self.setMask(region)

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self._device, 'open') and callable(self._device.open):
            # Legacy HyperXDevice: auto-discover and open
            if not hasattr(self._device, 'is_open') or not self._device.is_open:
                self._device.open()

        if hasattr(self._device, 'is_open') and self._device.is_open:
            for section in self._sections:
                section.refresh()
        else:
            self._info_section._set_disconnected()

    def hideEvent(self, event):
        super().hideEvent(event)
        if hasattr(self._device, 'close'):
            self._device.close()

    def popup_at_tray(self, cursor_pos: QPoint):
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()

        screen_geo = screen.availableGeometry()

        panel_x = screen_geo.right() - self.PANEL_WIDTH - self.MARGIN_FROM_EDGE
        panel_y = screen_geo.bottom() - self.PANEL_HEIGHT - self.MARGIN_FROM_EDGE

        if panel_x < screen_geo.left() + self.MARGIN_FROM_EDGE:
            panel_x = screen_geo.left() + self.MARGIN_FROM_EDGE
        elif panel_x + self.PANEL_WIDTH > screen_geo.right() - self.MARGIN_FROM_EDGE:
            panel_x = screen_geo.right() - self.PANEL_WIDTH - self.MARGIN_FROM_EDGE

        if panel_y < screen_geo.top() + self.MARGIN_FROM_EDGE:
            panel_y = screen_geo.top() + self.MARGIN_FROM_EDGE
        elif panel_y + self.PANEL_HEIGHT > screen_geo.bottom() - self.MARGIN_FROM_EDGE:
            panel_y = screen_geo.bottom() - self.PANEL_HEIGHT - self.MARGIN_FROM_EDGE

        self.move(int(panel_x), int(panel_y))
        self.show()
        self.raise_()
        self.activateWindow()

    def _on_save_clicked(self):
        device = self._device
        if hasattr(device, 'is_open') and not device.is_open:
            QMessageBox.warning(
                self, "Not Connected",
                "Cannot save: Device is not connected."
            )
            return

        if device.save_to_memory():
            QMessageBox.information(
                self, "Saved",
                "Settings saved to device memory.\n"
                "They will persist across power cycles."
            )
        else:
            QMessageBox.critical(
                self, "Save Failed",
                "Failed to save settings to device memory."
            )
