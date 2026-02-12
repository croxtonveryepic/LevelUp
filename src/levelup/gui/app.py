"""Entry point for the LevelUp GUI dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from levelup.config.loader import load_settings
from levelup.gui.main_window import MainWindow
from levelup.gui.theme_manager import get_current_theme, apply_theme, set_theme_preference
from levelup.state.manager import StateManager


def launch_gui(
    db_path: Path | None = None,
    project_path: Path | None = None,
) -> None:
    """Create QApplication and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("LevelUp Dashboard")

    # Load settings and apply theme
    try:
        settings = load_settings(project_path=project_path or Path.cwd())
        theme_preference = settings.gui.theme
        # Store preference globally for theme manager
        set_theme_preference(theme_preference, project_path=None)  # Don't save, just set in memory
        actual_theme = get_current_theme(theme_preference)
        apply_theme(app, actual_theme)
    except Exception:
        # Fallback to dark theme if config loading fails
        from levelup.gui.styles import DARK_THEME
        app.setStyleSheet(DARK_THEME)

    mgr_kwargs = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**mgr_kwargs)

    # Register explicitly provided project so it appears in the selector
    if project_path is not None:
        state_manager.add_project(str(project_path.resolve()))

    window = MainWindow(state_manager, project_path=project_path)
    window.show()

    sys.exit(app.exec())
