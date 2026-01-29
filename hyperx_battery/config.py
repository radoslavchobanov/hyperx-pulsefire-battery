"""Configuration management for HyperX Pulsefire Dart tool."""

import json
import os
from pathlib import Path
from typing import Any


# Default configuration values
DEFAULTS = {
    # Battery notifications
    "notifications": {
        "enabled": True,
        "thresholds": [20, 10, 5],  # Notify at these percentages
        "charging_notify": True,  # Notify when charging starts/stops
        "full_notify": True,  # Notify when fully charged
    },

    # Polling settings
    "polling": {
        "interval_seconds": 60,  # How often to check battery
        "retry_delay_seconds": 2,  # Delay before retrying on error
        "max_retries": 5,  # Max retries on device error
    },

    # Tray icon appearance
    "tray": {
        "show_percentage_text": True,  # Show % number on icon
        "charging_animation": True,  # Animate icon when charging
        "animation_fps": 7,  # Charging animation speed
    },

    # Panel behavior
    "panel": {
        "close_on_focus_loss": True,  # Close panel when clicking outside
        "remember_last_tab": False,  # Remember which tab was open
        "last_tab_index": 0,
    },

    # Default device settings (applied on first connect if set)
    "device_defaults": {
        "apply_on_connect": False,  # Apply defaults when device connects
        "polling_rate_hz": 1000,
        "battery_alert_percent": 10,
    },
}


def get_config_dir() -> Path:
    """Get the configuration directory, creating it if needed."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg_config:
        config_dir = Path(xdg_config) / "hyperx-pulsefire"
    else:
        config_dir = Path.home() / ".config" / "hyperx-pulsefire"

    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    return get_config_dir() / "config.json"


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge override into base, returning new dict."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    """Load configuration from file, merging with defaults."""
    config_path = get_config_path()

    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                user_config = json.load(f)
            return _deep_merge(DEFAULTS, user_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
            return DEFAULTS.copy()

    # Create default config file on first run
    save_config(DEFAULTS)
    return DEFAULTS.copy()


def save_config(config: dict) -> bool:
    """Save configuration to file."""
    config_path = get_config_path()

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error: Could not save config to {config_path}: {e}")
        return False


def get(key: str, default: Any = None) -> Any:
    """Get a config value using dot notation (e.g., 'notifications.enabled')."""
    config = load_config()
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value


def set(key: str, value: Any) -> bool:
    """Set a config value using dot notation."""
    config = load_config()
    keys = key.split(".")

    # Navigate to parent
    target = config
    for k in keys[:-1]:
        if k not in target:
            target[k] = {}
        target = target[k]

    target[keys[-1]] = value
    return save_config(config)


# Convenience accessors
class Config:
    """Configuration accessor with attribute-style access."""

    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._config = load_config()
        return cls._instance

    def reload(self):
        """Reload configuration from file."""
        self._config = load_config()

    def save(self):
        """Save current configuration to file."""
        save_config(self._config)

    @property
    def notifications(self) -> dict:
        return self._config.get("notifications", DEFAULTS["notifications"])

    @property
    def polling(self) -> dict:
        return self._config.get("polling", DEFAULTS["polling"])

    @property
    def tray(self) -> dict:
        return self._config.get("tray", DEFAULTS["tray"])

    @property
    def panel(self) -> dict:
        return self._config.get("panel", DEFAULTS["panel"])

    @property
    def device_defaults(self) -> dict:
        return self._config.get("device_defaults", DEFAULTS["device_defaults"])

    def __getitem__(self, key: str) -> Any:
        return get(key)

    def __setitem__(self, key: str, value: Any):
        set(key, value)
        self._config = load_config()
