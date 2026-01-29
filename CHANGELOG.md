# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025

### Added
- **Full configuration panel** - Plasma-style popup with all mouse settings
- **LED configuration** - Effects (static, breathing, spectrum, trigger), colors, brightness, speed
- **DPI profiles** - 5 profiles with individual enable, DPI values (50-16000), and RGB colors
- **Button remapping** - Remap 6 buttons to mouse/keyboard/media/DPI functions
- **Macro support** - Record and assign macro sequences with delays
- **Settings tab** - Polling rate (125-1000 Hz), battery alert threshold
- **Modern tray icon** - Mouse silhouette with battery fill bar and charging animation
- **Save to device memory** - Persist settings across power cycles
- **Protocol layer** - Complete HID protocol implementation for all NGenuity features

### Changed
- Left-click on tray icon now opens configuration panel instead of showing notification
- Tray icon redesigned with modern mouse silhouette and gradient fill
- Upgraded from simple battery monitor to full NGenuity replacement

### Fixed
- Device connection handling when panel is open
- Wayland compatibility for popup positioning

## [1.0.0] - 2024

### Added
- Initial release
- CLI tool for battery status
- System tray widget with battery percentage
- Charging status detection
- USB hotplug detection via udev
- JSON output for waybar integration
- Desktop notifications via notify-send

---

[2.0.0]: https://github.com/radoslavchobanov/hyperx-pulsefire-battery/releases/tag/v2.0.0
[1.0.0]: https://github.com/radoslavchobanov/hyperx-pulsefire-battery/releases/tag/v1.0.0
