"""Entry point for the LevelUp GUI dashboard."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from levelup.gui.main_window import MainWindow
from levelup.gui.styles import DARK_THEME
from levelup.state.manager import StateManager


def launch_gui(
    db_path: Path | None = None,
    project_path: Path | None = None,
) -> None:
    """Create QApplication and show the main window."""
    app = QApplication(sys.argv)
    app.setApplicationName("LevelUp Dashboard")
    app.setStyleSheet(DARK_THEME)

    mgr_kwargs = {}
    if db_path:
        mgr_kwargs["db_path"] = db_path
    state_manager = StateManager(**mgr_kwargs)

    window = MainWindow(state_manager, project_path=project_path)
    window.show()

    sys.exit(app.exec())
