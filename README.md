# HyperX Pulsefire Dart Configuration Tool

**Full NGenuity replacement for the HyperX Pulsefire Dart wireless gaming mouse on Linux.**

HyperX only provides NGenuity (Windows-only) for configuring their mice. This project provides a complete Linux alternative, communicating directly with the mouse over USB HID to configure all settings — battery monitoring, LED effects, DPI profiles, button mapping, macros, and more.

[![PyPI](https://img.shields.io/pypi/v/hyperx-pulsefire-battery)](https://pypi.org/project/hyperx-pulsefire-battery/)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-green)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Linux](https://img.shields.io/badge/platform-Linux-blue)](https://kernel.org/)
[![Qt5](https://img.shields.io/badge/GUI-Qt5-41cd52)](https://www.qt.io/)

---

## Features

### System Tray Application
- **Modern mouse icon** with battery level fill bar
- **Color-coded status**: green (>50%) → yellow (25-50%) → orange (10-25%) → red (<10%)
- **Charging animation**: pulsing lightning bolt indicator
- **Instant hotplug detection** via udev monitoring
- **Left-click** opens the configuration panel
- **Right-click** context menu for quick actions

### Configuration Panel
A Plasma-style popup panel with full mouse configuration:

| Tab | Features |
|-----|----------|
| **Info** | Firmware version, battery %, charging status, connection mode, voltage |
| **DPI** | 5 profiles with enable/disable, DPI values (50-16000), per-profile colors |
| **LED** | Logo/scroll wheel lighting, effects (static/breathing/spectrum/trigger), color picker, brightness, speed |
| **Buttons** | Remap 6 buttons to mouse/keyboard/media/DPI functions |
| **Macros** | Record and assign macro sequences with delays |
| **Settings** | Polling rate (125/250/500/1000 Hz), battery alert threshold |

### CLI Tool
- Quick battery check from terminal
- JSON output for scripting
- Continuous monitoring mode
- Device listing

---

## Supported Devices

| Device | USB ID | Mode |
|--------|--------|------|
| HyperX Pulsefire Dart (wireless dongle) | `0951:16E1` | Wireless |
| HyperX Pulsefire Dart (USB cable) | `0951:16E2` | Wired |

The protocol may work with other HyperX mice using the NGenuity2 protocol.

---

## Installation

### Option 1: pip (Recommended)

#### 1. Install system dependencies

**Arch / Manjaro:**
```bash
sudo pacman -S hidapi python-pyqt5 python-pyudev
```

**Debian / Ubuntu:**
```bash
sudo apt install libhidapi-hidraw0 python3-pyqt5 python3-pyudev
```

**Fedora:**
```bash
sudo dnf install hidapi python3-qt5 python3-pyudev
```

#### 2. Install from PyPI

```bash
# Full installation with GUI (recommended)
pip install "hyperx-pulsefire-battery[tray]"

# CLI only (no Qt dependencies)
pip install hyperx-pulsefire-battery
```

#### 3. Set up udev rules (required for non-root access)

```bash
# Download and install udev rules
sudo curl -o /etc/udev/rules.d/99-hyperx-pulsefire.rules \
  https://raw.githubusercontent.com/radoslavchobanov/hyperx-pulsefire-battery/master/99-hyperx-pulsefire.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Then **unplug and replug** your wireless dongle.

### Option 2: Arch Linux / Manjaro (PKGBUILD)

```bash
# Clone the repository
git clone https://github.com/radoslavchobanov/hyperx-pulsefire-battery.git
cd hyperx-pulsefire-battery

# Build and install the package (includes udev rules)
makepkg -si
```

---

## Usage

### System Tray Application

```bash
hyperx-battery-tray &
```

- **Left-click** the tray icon to open the configuration panel
- **Right-click** for the context menu (refresh, quit)
- All changes are applied immediately to the mouse
- Click **"Save to Device Memory"** to persist settings across power cycles

### CLI

```bash
# Show battery status
hyperx-battery

# JSON output (for scripts/waybar)
hyperx-battery --json

# Continuous monitoring
hyperx-battery --watch --interval 10

# List detected HyperX devices
hyperx-battery --list
```

### Autostart on Login

The package installs a desktop file for autostart:

```bash
# Manual setup (if not using PKGBUILD)
cp hyperx-battery-tray.desktop ~/.config/autostart/
```

### Waybar Integration

Add to your waybar config:

```json
"custom/hyperx": {
    "exec": "hyperx-battery --json",
    "return-type": "json",
    "interval": 60,
    "format": "{icon} {percentage}%",
    "format-icons": ["", "", "", "", ""]
}
```

---

## Configuration Options

### DPI Profiles
- **5 independent profiles** (1-5)
- **DPI range**: 50 - 16,000 in steps of 50
- **Per-profile RGB color** for on-mouse indicator
- Enable/disable individual profiles
- Set active profile

### LED Effects
- **Targets**: Logo, Scroll Wheel, or Both
- **Effects**:
  - Static — constant color
  - Breathing — fade in/out
  - Spectrum Cycle — rainbow rotation
  - Trigger Fade — lights up on click, fades out
- **Brightness**: 0-100%
- **Speed**: 0-100% (for animated effects)
- **Full RGB color picker**

### Button Mapping
Remap any of the 6 buttons:

| Button | Default |
|--------|---------|
| Left Click | Mouse Left |
| Right Click | Mouse Right |
| Middle Click | Mouse Middle |
| Forward | Mouse Forward |
| Back | Mouse Back |
| DPI Button | DPI Cycle |

**Available mappings:**
- **Mouse**: Left, Right, Middle, Back, Forward
- **Keyboard**: Any key (A-Z, 0-9, F1-F12, modifiers, etc.)
- **Media**: Play/Pause, Stop, Next, Previous, Volume Up/Down, Mute
- **DPI**: Cycle Up, Cycle Down, Cycle All
- **Disabled**: No action

### Macros
- Record sequences of keyboard/mouse actions
- Add delays between actions (0-10,000 ms)
- Assign to any button
- Repeat modes: Single, Toggle, Hold

### Settings
- **Polling Rate**: 125 / 250 / 500 / 1000 Hz
- **Battery Alert Threshold**: 5-25%

### User Configuration File

The tray application stores user preferences in `~/.config/hyperx-pulsefire/config.json`:

```json
{
  "notifications": {
    "enabled": true,
    "thresholds": [20, 10, 5],
    "charging_notify": true,
    "full_notify": true
  },
  "polling": {
    "interval_seconds": 60,
    "retry_delay_seconds": 2,
    "max_retries": 5
  },
  "tray": {
    "show_percentage_text": true,
    "charging_animation": true,
    "animation_fps": 7
  }
}
```

Edit this file to customize notification thresholds, polling intervals, and tray behavior.

---

## Protocol Documentation

The mouse communicates over USB HID using 64-byte interrupt transfers.

### Command Structure
```
Byte 0: Command ID
Byte 1-63: Command-specific data
```

### Key Commands

| Command | Description |
|---------|-------------|
| `0x50` | Get hardware info (firmware, device name) |
| `0x51` | Get battery status |
| `0xD2` | Set LED configuration |
| `0xD3` | Set DPI configuration |
| `0xD4` | Set button mapping |
| `0xD5` | Assign macro to button |
| `0xD6` | Upload macro data |
| `0xDA` | Set polling rate |
| `0xDB` | Set battery alert threshold |
| `0xDE` | Save settings to device memory |

### Battery Response (0x51)
| Byte | Content |
|------|---------|
| 0x00 | Command echo (0x51) |
| 0x04 | Battery percentage (0-100) |
| 0x05 | Charging status (0x00=discharging, 0x01=charging) |
| 0x07-0x08 | Voltage values |

---

## Project Structure

```
hyperx-pulsefire-battery/
├── hyperx_battery/
│   ├── __init__.py
│   ├── protocol.py      # Protocol constants, packet builders, parsers
│   ├── device.py        # HyperXDevice class, HID communication
│   ├── config.py        # User configuration management
│   ├── cli.py           # Command-line interface
│   ├── tray.py          # System tray application
│   ├── panel.py         # Configuration panel (Plasma-style popup)
│   └── widgets/
│       ├── __init__.py
│       ├── info_section.py      # Device info display
│       ├── dpi_section.py       # DPI profile configuration
│       ├── led_section.py       # LED effect configuration
│       ├── buttons_section.py   # Button remapping
│       ├── macros_section.py    # Macro editor
│       └── settings_section.py  # Polling rate, battery alert
├── 99-hyperx-pulsefire.rules    # udev rules for non-root access
├── hyperx-battery-tray.desktop  # Desktop autostart file
├── pyproject.toml               # Python package configuration
├── PKGBUILD                     # Arch Linux package build
├── LICENSE                      # MIT License
└── README.md
```

---

## Troubleshooting

### "Device not found"
- Ensure the wireless dongle is plugged in
- Check udev rules: `ls /etc/udev/rules.d/99-hyperx-pulsefire.rules`
- Run `hyperx-battery --list` to see detected interfaces
- Try running with `sudo` to rule out permission issues

### "IO Error: open failed"
- udev rules not installed or not active
- Run: `sudo udevadm control --reload-rules && sudo udevadm trigger`
- Unplug and replug the dongle

### Tray icon shows "?"
- Mouse is not connected or not detected
- Check USB connection
- Wait a few seconds after plugging in

### Settings not persisting after power cycle
- Click **"Save to Device Memory"** in the configuration panel
- This writes settings to the mouse's onboard memory

### Panel appears in wrong position
- The panel positions itself at the bottom-right of the screen
- On multi-monitor setups, it appears on the screen where the cursor is

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with a real HyperX Pulsefire Dart
5. Submit a pull request

### Development Setup

```bash
git clone https://github.com/radoslavchobanov/hyperx-pulsefire-battery.git
cd hyperx-pulsefire-battery
pip install -e ".[tray]"
```

---

## Credits

- Protocol reverse engineering by [santeri3700](https://github.com/santeri3700/hyperx_pulsefire_dart_reverse_engineering)
- Inspired by the lack of Linux support from HyperX/HP

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

**Note:** This is an unofficial project and is not affiliated with HyperX or HP Inc.
