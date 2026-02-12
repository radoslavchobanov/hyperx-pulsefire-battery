"""Abstract base class for brand-specific HID mouse drivers."""

from abc import ABC, abstractmethod
from typing import Optional, List, Any

from plasmangenuity.core.types import BatteryReading, Capabilities


class HidMouseDriver(ABC):
    """A driver for a specific brand/model of wireless mouse.

    Subclasses implement battery reading and optionally configuration
    features (DPI, LED, buttons, macros).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Driver name, e.g., 'hyperx_pulsefire_dart'."""
        ...

    @property
    @abstractmethod
    def brand(self) -> str:
        """Brand name, e.g., 'HyperX'."""
        ...

    @staticmethod
    @abstractmethod
    def match(vendor_id: int, product_id: int,
              usage_page: int, interface_number: int) -> bool:
        """Return True if this driver handles the given HID device."""
        ...

    @abstractmethod
    def get_capabilities(self) -> Capabilities:
        """Return what this driver can do beyond battery."""
        ...

    @abstractmethod
    def open(self, device_path: bytes) -> bool:
        """Open HID connection to the device."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close HID connection."""
        ...

    @property
    @abstractmethod
    def is_open(self) -> bool:
        ...

    @abstractmethod
    def read_battery(self) -> Optional[BatteryReading]:
        """Read battery status from the device."""
        ...

    # --- Optional configuration methods (override in subclass) ---

    def get_hw_info(self) -> Optional[Any]:
        return None

    def get_dpi_settings(self) -> Optional[Any]:
        return None

    def set_dpi_active(self, profile: int) -> bool:
        return False

    def set_dpi_value(self, profile: int, dpi: int) -> bool:
        return False

    def set_dpi_color(self, profile: int, r: int, g: int, b: int) -> bool:
        return False

    def set_dpi_enable_mask(self, mask: int) -> bool:
        return False

    def get_led_settings(self) -> Optional[Any]:
        return None

    def set_led(self, **kwargs) -> bool:
        return False

    def set_button(self, button: int, button_type: int, code: int) -> bool:
        return False

    def upload_macro(self, button: int, events: list) -> bool:
        return False

    def save_to_memory(self) -> bool:
        return False

    @property
    def mode(self) -> Optional[str]:
        """Connection mode string (e.g. 'wireless', 'wired')."""
        return None
