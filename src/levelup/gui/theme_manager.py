"""Theme management for the GUI application."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from PyQt6.QtWidgets import QApplication

from levelup.gui.styles import DARK_THEME, LIGHT_THEME

try:
    import darkdetect
except ImportError:
    darkdetect = None  # type: ignore[assignment]


# Global state for theme preference
_current_preference: Literal["light", "dark", "system"] = "system"

# Theme change listeners
_theme_listeners: list = []


def theme_changed(theme: Literal["light", "dark"]) -> None:
    """Signal that theme has changed (for listener pattern)."""
    for listener in _theme_listeners:
        listener(theme)


def add_theme_listener(callback) -> None:
    """Add a callback to be notified when theme changes."""
    _theme_listeners.append(callback)


def get_system_theme() -> Literal["light", "dark"]:
    """Detect the system's current theme preference.

    Returns:
        "light" or "dark"
    """
    if darkdetect is None:
        # Fallback to dark if darkdetect not available
        return "dark"

    try:
        system_theme = darkdetect.theme()
        if system_theme and system_theme.lower() == "light":
            return "light"
        elif system_theme and system_theme.lower() == "dark":
            return "dark"
        else:
            # If None or unknown, default to dark
            return "dark"
    except Exception:
        # If detection fails, default to dark
        return "dark"


def get_current_theme(preference: Literal["light", "dark", "system"] | None = None) -> Literal["light", "dark"]:
    """Get the actual theme to use based on preference.

    Args:
        preference: Theme preference ("light", "dark", or "system").
                   If None, uses the stored preference.

    Returns:
        "light" or "dark"
    """
    if preference is None:
        preference = _current_preference

    if preference == "light":
        return "light"
    elif preference == "dark":
        return "dark"
    elif preference == "system":
        return get_system_theme()
    else:
        # Invalid preference, fall back to system detection
        return get_system_theme()


def apply_theme(app: QApplication, theme: Literal["light", "dark"]) -> None:
    """Apply a theme stylesheet to the application.

    Args:
        app: QApplication instance
        theme: "light" or "dark"

    Raises:
        ValueError: If theme is not "light" or "dark"
    """
    if theme == "light":
        app.setStyleSheet(LIGHT_THEME)
    elif theme == "dark":
        app.setStyleSheet(DARK_THEME)
    else:
        raise ValueError(f"Invalid theme: {theme}. Must be 'light' or 'dark'.")

    # Notify listeners
    theme_changed(theme)


def set_theme_preference(
    preference: Literal["light", "dark", "system"],
    project_path: Path | None = None
) -> None:
    """Set and persist the theme preference.

    Args:
        preference: "light", "dark", or "system"
        project_path: Path to project directory (for saving config)
    """
    global _current_preference
    _current_preference = preference

    # Notify listeners of theme change
    actual_theme = get_current_theme(preference)
    theme_changed(actual_theme)

    # Persist to config file if project_path is provided
    if project_path is not None:
        try:
            from levelup.config.loader import find_config_file, load_config_file
            import yaml

            config_file = find_config_file(project_path)
            if config_file is None:
                # Create new config file
                config_file = project_path / "levelup.yaml"
                config_data = {}
            else:
                config_data = load_config_file(config_file)

            # Update gui.theme
            if "gui" not in config_data:
                config_data["gui"] = {}
            config_data["gui"]["theme"] = preference

            # Write back to file
            with open(config_file, "w") as f:
                yaml.dump(config_data, f, default_flow_style=False)
        except Exception:
            # If config save fails, continue (preference is stored in memory)
            pass


def get_theme_preference() -> Literal["light", "dark", "system"]:
    """Get the current theme preference.

    Returns:
        "light", "dark", or "system"
    """
    return _current_preference
