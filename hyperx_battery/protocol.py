"""HyperX Pulsefire Dart protocol constants, packet builders, and response parsers.

Protocol based on reverse engineering by santeri3700:
https://github.com/santeri3700/hyperx_pulsefire_dart_reverse_engineering

This module is pure-data with no I/O operations. All HID communication
is handled by device.py.
"""

from enum import IntEnum
from typing import NamedTuple, Optional, List

# =============================================================================
# PROTOCOL CONSTANTS
# =============================================================================

PACKET_SIZE = 64

# Command bytes (actual protocol)
CMD_HW_INFO = 0x50            # Hardware info query
CMD_HEARTBEAT = 0x51          # Battery/status query
CMD_LED_QUERY = 0x52          # Query LED settings (from memory)
CMD_DPI_QUERY = 0x53          # Query DPI settings
CMD_LED_SET = 0xD2            # Set LED parameters (direct mode)
CMD_DPI_SET = 0xD3            # Set DPI parameters
CMD_BUTTON_SET = 0xD4         # Set button mapping
CMD_MACRO_DATA = 0xD6         # Upload macro data
CMD_SAVE = 0xDE               # Save settings to device memory


# =============================================================================
# ENUMERATIONS
# =============================================================================

class PollingRate(IntEnum):
    """Polling rate options in Hz."""
    HZ_125 = 0x00
    HZ_250 = 0x01
    HZ_500 = 0x02
    HZ_1000 = 0x03


POLLING_RATE_HZ = {
    PollingRate.HZ_125: 125,
    PollingRate.HZ_250: 250,
    PollingRate.HZ_500: 500,
    PollingRate.HZ_1000: 1000,
}

POLLING_RATE_FROM_HZ = {v: k for k, v in POLLING_RATE_HZ.items()}


class LedTarget(IntEnum):
    """LED target zones."""
    LOGO = 0x00
    SCROLL = 0x10
    BOTH = 0x20


class LedEffect(IntEnum):
    """LED effect modes."""
    STATIC = 0x00
    SPECTRUM_UNOFFICIAL = 0x10
    SPECTRUM_CYCLE = 0x12
    BREATHING = 0x20
    TRIGGER_FADE = 0x30


class DpiMode(IntEnum):
    """DPI command modes."""
    SELECT_PROFILE = 0x00
    ENABLE_PROFILES = 0x01
    SET_DPI_VALUE = 0x02
    SET_COLOR = 0x03


class ButtonType(IntEnum):
    """Button action types."""
    DISABLED = 0x00
    MOUSE = 0x01
    KEYBOARD = 0x02
    MEDIA = 0x03
    MACRO = 0x04
    DPI = 0x07


class MouseButton(IntEnum):
    """Mouse button codes."""
    LEFT = 0x01
    RIGHT = 0x02
    MIDDLE = 0x03
    BACK = 0x04
    FORWARD = 0x05


class DpiFunction(IntEnum):
    """DPI button functions."""
    CYCLE_UP = 0x01
    CYCLE_DOWN = 0x02
    CYCLE = 0x03


class MediaCode(IntEnum):
    """Media key codes (HID Usage Table)."""
    PLAY_PAUSE = 0xCD
    STOP = 0xB7
    NEXT_TRACK = 0xB5
    PREV_TRACK = 0xB6
    VOLUME_UP = 0xE9
    VOLUME_DOWN = 0xEA
    MUTE = 0xE2


MEDIA_CODE_NAMES = {
    MediaCode.PLAY_PAUSE: "Play/Pause",
    MediaCode.STOP: "Stop",
    MediaCode.NEXT_TRACK: "Next Track",
    MediaCode.PREV_TRACK: "Previous Track",
    MediaCode.VOLUME_UP: "Volume Up",
    MediaCode.VOLUME_DOWN: "Volume Down",
    MediaCode.MUTE: "Mute",
}


class MacroRepeatMode(IntEnum):
    """Macro repeat modes."""
    SINGLE = 0x00
    TOGGLE = 0x01
    HOLD = 0x02


# Button indices for mapping
BUTTON_LEFT = 0x00
BUTTON_RIGHT = 0x01
BUTTON_MIDDLE = 0x02
BUTTON_FORWARD = 0x03
BUTTON_BACK = 0x04
BUTTON_DPI = 0x05

BUTTON_NAMES = {
    BUTTON_LEFT: "Left Click",
    BUTTON_RIGHT: "Right Click",
    BUTTON_MIDDLE: "Middle Click",
    BUTTON_FORWARD: "Forward",
    BUTTON_BACK: "Back",
    BUTTON_DPI: "DPI Button",
}


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class HWInfo(NamedTuple):
    """Hardware information from the device."""
    firmware_version: str
    device_name: str
    vendor_id: int
    product_id: int


class BatteryStatus(NamedTuple):
    """Battery status from heartbeat response."""
    percent: int
    is_charging: bool


class LedSettings(NamedTuple):
    """LED settings for a zone."""
    target: LedTarget
    effect: LedEffect
    red: int
    green: int
    blue: int
    brightness: int  # 0-100
    speed: int       # 0-100


class DpiProfile(NamedTuple):
    """DPI profile settings."""
    enabled: bool
    dpi: int
    red: int
    green: int
    blue: int


class ButtonMapping(NamedTuple):
    """Button mapping configuration."""
    button_type: ButtonType
    code: int  # Mouse button, keyboard scancode, media code, or DPI function


class MacroEvent(NamedTuple):
    """Single macro event."""
    event_type: str  # 'key_down', 'key_up', 'mouse_down', 'mouse_up', 'delay'
    code: int        # Key scancode, mouse button, or delay in ms


# =============================================================================
# PACKET BUILDERS
# =============================================================================

def _make_packet(data: List[int]) -> bytes:
    """Create a 64-byte HID packet with report ID prefix."""
    packet = [0x00] * PACKET_SIZE
    packet[0] = 0x00  # Report ID
    for i, byte in enumerate(data):
        if i + 1 < PACKET_SIZE:
            packet[i + 1] = byte
    return bytes(packet)


def build_heartbeat_packet() -> bytes:
    """Build battery/status query packet."""
    return _make_packet([CMD_HEARTBEAT])


def build_hw_info_packet() -> bytes:
    """Build hardware info query packet."""
    return _make_packet([CMD_HW_INFO])


def build_led_query_packet() -> bytes:
    """Build LED settings query packet."""
    return _make_packet([CMD_LED_QUERY])


def build_dpi_query_packet() -> bytes:
    """Build DPI settings query packet."""
    return _make_packet([CMD_DPI_QUERY])


def build_led_packet(
    target: LedTarget,
    effect: LedEffect,
    red: int,
    green: int,
    blue: int,
    brightness: int = 100,
    speed: int = 0,
    red2: int = None,
    green2: int = None,
    blue2: int = None,
) -> bytes:
    """Build LED settings packet (direct mode).

    Args:
        target: LED zone (logo, scroll, or both).
        effect: LED effect mode.
        red, green, blue: Primary color values (0-255).
        brightness: Brightness level (0-100).
        speed: Effect speed (0-100), used for breathing/spectrum.
        red2, green2, blue2: Secondary color (for breathing). Defaults to primary.
    """
    brightness = max(0, min(100, brightness))
    speed = max(0, min(100, speed))

    # Default secondary color to primary
    if red2 is None:
        red2 = red
    if green2 is None:
        green2 = green
    if blue2 is None:
        blue2 = blue

    return _make_packet([
        CMD_LED_SET,      # 0xD2
        target,           # 0x00=Logo, 0x10=Scroll, 0x20=Both
        effect,           # Effect mode
        0x08,             # Data length indicator
        red, green, blue, # Primary RGB
        red2, green2, blue2,  # Secondary RGB
        brightness,       # 0-100
        speed,            # 0-100 (reversed for non-static)
    ])


def build_dpi_select_packet(profile: int) -> bytes:
    """Build packet to select active DPI profile.

    Args:
        profile: Profile index (0-4).
    """
    profile = max(0, min(4, profile))
    return _make_packet([
        CMD_DPI_SET,          # 0xD3
        DpiMode.SELECT_PROFILE,  # 0x00
        profile,              # Profile number
        0x00,                 # Data length
    ])


def build_dpi_enable_packet(enable_mask: int) -> bytes:
    """Build DPI profile enable mask packet.

    Args:
        enable_mask: Bitmask of enabled profiles (bit 0 = profile 0, etc).
                     Note: Bits are reversed in protocol (bit 0 = profile 4).
    """
    # Reverse the bits for the protocol
    reversed_mask = 0
    for i in range(5):
        if enable_mask & (1 << i):
            reversed_mask |= (1 << (4 - i))

    return _make_packet([
        CMD_DPI_SET,           # 0xD3
        DpiMode.ENABLE_PROFILES,  # 0x01
        0x00,                  # Not used
        0x01,                  # Data length
        reversed_mask,         # Reversed bitmask
    ])


def build_dpi_value_packet(profile: int, dpi: int) -> bytes:
    """Build DPI value set packet.

    Args:
        profile: Profile index (0-4).
        dpi: DPI value (50-16000, step 50).
    """
    profile = max(0, min(4, profile))
    dpi = max(50, min(16000, dpi))
    dpi = (dpi // 50) * 50  # Round to step of 50

    # DPI value divided by 50, then split into low/high bytes
    dpi_scaled = dpi // 50
    dpi_low = dpi_scaled & 0xFF
    dpi_high = (dpi_scaled >> 8) & 0xFF

    return _make_packet([
        CMD_DPI_SET,           # 0xD3
        DpiMode.SET_DPI_VALUE, # 0x02
        profile,               # Profile number
        0x02,                  # Data length
        dpi_low,               # DPI / 50 low byte
        dpi_high,              # DPI / 50 high byte
    ])


def build_dpi_color_packet(profile: int, red: int, green: int, blue: int) -> bytes:
    """Build DPI profile color packet.

    Args:
        profile: Profile index (0-4).
        red, green, blue: Color values (0-255).
    """
    profile = max(0, min(4, profile))
    return _make_packet([
        CMD_DPI_SET,        # 0xD3
        DpiMode.SET_COLOR,  # 0x03
        profile,            # Profile number
        0x03,               # Data length
        red, green, blue,   # RGB
    ])


def build_button_packet(button: int, button_type: ButtonType, code: int) -> bytes:
    """Build button mapping packet.

    Args:
        button: Button index (0-5).
        button_type: Type of action (mouse, keyboard, media, DPI, macro).
        code: Action code (button code, scancode, media code, etc).
    """
    button = max(0, min(5, button))

    # For macro type, second byte is 0x00; otherwise 0x04
    extra_byte = 0x00 if button_type == ButtonType.MACRO else 0x04

    return _make_packet([
        CMD_BUTTON_SET,    # 0xD4
        button,            # Physical button
        button_type,       # Assignment type
        0x02,              # Data length
        code,              # Function code
        extra_byte,        # Extra byte
    ])


def build_macro_packets(button: int, events: List[MacroEvent]) -> List[bytes]:
    """Build macro data upload packets.

    Each packet can hold up to 6 events (10 bytes each).

    Args:
        button: Button index (0-5).
        events: List of macro events.

    Returns:
        List of packets to send in order.
    """
    packets = []

    # Encode events into 10-byte rows
    event_rows = []
    for event in events:
        if event.event_type == 'delay':
            # Delay: ms / 2, split into low/high bytes
            delay_val = event.code // 2
            row = [0x00] * 10
            row[0] = delay_val & 0xFF
            row[1] = (delay_val >> 8) & 0xFF
            event_rows.append(row)
        elif event.event_type in ('key_down', 'key_up'):
            row = [0x00] * 10
            row[0] = 0x1A  # Keyboard event marker
            row[1] = event.code  # Key code
            row[2] = 0x01 if event.event_type == 'key_down' else 0x02
            event_rows.append(row)
        elif event.event_type in ('mouse_down', 'mouse_up'):
            row = [0x00] * 10
            row[0] = 0x25  # Mouse event marker
            row[1] = event.code  # Button code
            row[2] = 0x01 if event.event_type == 'mouse_down' else 0x02
            event_rows.append(row)

    # Split into packets of 6 events each
    for i in range(0, len(event_rows), 6):
        chunk = event_rows[i:i+6]
        is_last = (i + 6) >= len(event_rows)

        data = [
            CMD_MACRO_DATA,    # 0xD6
            button,            # Target button
            i // 6,            # Sequence order
            len(chunk) if is_last else 0x86,  # Event count or continuation marker
        ]

        # Add event rows
        for row in chunk:
            data.extend(row)

        packets.append(_make_packet(data))

    # If no events, send empty packet
    if not packets:
        packets.append(_make_packet([CMD_MACRO_DATA, button, 0x00, 0x00]))

    return packets


def build_save_packet() -> bytes:
    """Build save-to-device-memory packet."""
    return _make_packet([CMD_SAVE, 0xFF])


# =============================================================================
# RESPONSE PARSERS
# =============================================================================

def parse_hw_info(response: bytes) -> Optional[HWInfo]:
    """Parse hardware info response.

    Args:
        response: 64-byte response from device.

    Returns:
        HWInfo named tuple or None if invalid.
    """
    if len(response) < 32 or response[0] != CMD_HW_INFO:
        return None

    # Product ID at bytes 4-5 (little-endian)
    product_id = response[4] | (response[5] << 8)

    # Vendor ID at bytes 6-7 (little-endian)
    vendor_id = response[6] | (response[7] << 8)

    # Device name is null-terminated string starting at byte 12
    name_bytes = response[12:44]
    null_idx = name_bytes.find(0)
    if null_idx != -1:
        name_bytes = name_bytes[:null_idx]
    device_name = bytes(name_bytes).decode('ascii', errors='ignore')

    # Firmware version - derive from byte 3 or use a placeholder
    # The actual format isn't fully documented
    firmware_version = f"{response[3]}.0.0"

    return HWInfo(
        firmware_version=firmware_version,
        device_name=device_name,
        vendor_id=vendor_id,
        product_id=product_id,
    )


def parse_battery(response: bytes) -> Optional[BatteryStatus]:
    """Parse heartbeat/battery response.

    Args:
        response: 64-byte response from device.

    Returns:
        BatteryStatus named tuple or None if invalid.
    """
    if len(response) < 6 or response[0] != CMD_HEARTBEAT:
        return None

    return BatteryStatus(
        percent=response[4],
        is_charging=response[5] == 0x01,
    )


def parse_led_settings(response: bytes) -> Optional[LedSettings]:
    """Parse LED settings query response.

    Note: This returns settings from device memory, not necessarily
    the currently active settings (which may be in direct mode).

    Args:
        response: 64-byte response from device.

    Returns:
        LedSettings named tuple or None if invalid.
    """
    if len(response) < 21 or response[0] != CMD_LED_QUERY:
        return None

    # LED data appears at bytes 17-20: brightness, R, G, B
    return LedSettings(
        target=LedTarget.BOTH,  # Query doesn't specify
        effect=LedEffect.STATIC,  # Query doesn't specify effect clearly
        red=response[18],
        green=response[19],
        blue=response[20],
        brightness=response[17],
        speed=0,
    )


def parse_dpi_settings(response: bytes) -> Optional[dict]:
    """Parse DPI settings query response.

    Args:
        response: 64-byte response from device.

    Returns:
        Dict with DPI settings or None if invalid.
    """
    if len(response) < 30 or response[0] != CMD_DPI_QUERY:
        return None

    # Active profile at byte 5
    active_profile = response[5]

    # DPI values are 2-byte little-endian at bytes 10, 12, 14, 16, 18
    # Each value is DPI / 50
    dpi_values = []
    for offset in [10, 12, 14, 16, 18]:
        raw = response[offset] | (response[offset + 1] << 8)
        dpi_values.append(raw * 50)

    # Colors are at bytes 22+ (3 bytes RGB per profile)
    colors = []
    for i in range(5):
        offset = 22 + i * 3
        if offset + 2 < len(response):
            colors.append((response[offset], response[offset + 1], response[offset + 2]))

    return {
        'active_profile': active_profile,
        'dpi_values': dpi_values,
        'colors': colors,
    }
