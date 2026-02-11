"""Dialog showing keyboard shortcuts reference."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from levelup.config.settings import HotkeySettings


class KeyboardShortcutsHelp(QDialog):
    """Dialog showing all available keyboard shortcuts."""

    def __init__(self, settings: HotkeySettings | None = None, parent=None):
        super().__init__(parent)
        self._settings = settings or HotkeySettings()

        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(500, 350)

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Available Keyboard Shortcuts")
        header_font = header.font()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        # Table showing shortcuts
        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Set column resize modes
        header_view = table.horizontalHeader()
        assert header_view is not None
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

        # Add shortcuts
        shortcuts = [
            ("Next waiting ticket", self._settings.next_waiting_ticket),
            ("Back to runs", self._settings.back_to_runs),
            ("Toggle theme", self._settings.toggle_theme),
            ("Refresh dashboard", self._settings.refresh_dashboard),
            ("Open documentation", self._settings.open_documentation),
            ("Focus terminal", self._settings.focus_terminal),
        ]

        table.setRowCount(len(shortcuts))

        for row, (action, keybinding) in enumerate(shortcuts):
            # Action
            action_item = QTableWidgetItem(action)
            table.setItem(row, 0, action_item)

            # Keybinding (use monospace font)
            key_item = QTableWidgetItem(keybinding)
            key_font = key_item.font()
            key_font.setFamily("Courier New")
            key_item.setFont(key_font)
            table.setItem(row, 1, key_item)

        layout.addWidget(table)

        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
