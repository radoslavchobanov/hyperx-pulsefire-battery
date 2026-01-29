"""Configuration panel popup for HyperX Pulsefire Dart mouse - Plasma style."""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QLabel, QApplication, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QRegion, QPalette

from hyperx_battery.device import HyperXDevice
from hyperx_battery.widgets import (
    InfoSection, SettingsSection, LedSection,
    DpiSection, ButtonsSection, MacrosSection
)


class ConfigPanel(QWidget):
    """Plasma-style popup configuration panel for the HyperX mouse."""

    PANEL_WIDTH = 500
    PANEL_HEIGHT = 600
    CORNER_RADIUS = 10
    MARGIN_FROM_EDGE = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self._device = HyperXDevice()
        self._sections = []
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        """Configure window flags for Plasma-like popup."""
        self.setWindowFlags(
            Qt.Window |
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # Prevents taskbar entry
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(self.PANEL_WIDTH, self.PANEL_HEIGHT)

    def _setup_ui(self):
        """Build the panel UI with Plasma styling."""
        # Main container
        self._container = QWidget(self)
        self._container.setObjectName("panelContainer")

        # Plasma Breeze-like dark theme
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

        title_label = QLabel("HyperX Pulsefire Dart")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #eff0f1;")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Close button (Plasma style)
        close_btn = QPushButton("×")
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

        # Tab widget with Plasma styling
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

        # Create sections
        self._info_section = InfoSection(self._device)
        self._settings_section = SettingsSection(self._device)
        self._led_section = LedSection(self._device)
        self._dpi_section = DpiSection(self._device)
        self._buttons_section = ButtonsSection(self._device)
        self._macros_section = MacrosSection(self._device)

        self._sections = [
            self._info_section,
            self._settings_section,
            self._led_section,
            self._dpi_section,
            self._buttons_section,
            self._macros_section,
        ]

        self._tabs.addTab(self._info_section, "Info")
        self._tabs.addTab(self._dpi_section, "DPI")
        self._tabs.addTab(self._led_section, "LED")
        self._tabs.addTab(self._buttons_section, "Buttons")
        self._tabs.addTab(self._macros_section, "Macros")
        self._tabs.addTab(self._settings_section, "Settings")

        container_layout.addWidget(self._tabs)

        # Save button (Plasma accent style)
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

        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self._container.setGraphicsEffect(shadow)

    def paintEvent(self, event):
        """Custom paint for rounded corners."""
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
        """Open device connection when panel is shown."""
        super().showEvent(event)
        if self._device.open():
            for section in self._sections:
                section.refresh()
        else:
            self._info_section._set_disconnected()

    def hideEvent(self, event):
        """Close device connection when panel is hidden."""
        super().hideEvent(event)
        self._device.close()

    def popup_at_tray(self, cursor_pos: QPoint):
        """Position and show the panel above the system tray.

        Args:
            cursor_pos: QPoint of cursor position when clicked
        """
        screen = QApplication.screenAt(cursor_pos)
        if not screen:
            screen = QApplication.primaryScreen()

        screen_geo = screen.availableGeometry()

        # Position panel at bottom-right, above the taskbar area
        # Horizontally: align to right side of screen with margin
        panel_x = screen_geo.right() - self.PANEL_WIDTH - self.MARGIN_FROM_EDGE
        # Vertically: at the bottom of available screen area
        panel_y = screen_geo.bottom() - self.PANEL_HEIGHT - self.MARGIN_FROM_EDGE

        # Keep panel on screen
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
        """Save settings to device memory."""
        if not self._device.is_open:
            QMessageBox.warning(
                self, "Not Connected",
                "Cannot save: Device is not connected."
            )
            return

        if self._device.save_to_memory():
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
