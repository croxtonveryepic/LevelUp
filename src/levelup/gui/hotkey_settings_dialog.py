"""Dialog for customizing keyboard shortcuts."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QLabel,
)

from levelup.config.settings import HotkeySettings


class HotkeySettingsDialog(QDialog):
    """Dialog for customizing keyboard shortcuts."""

    def __init__(self, settings: HotkeySettings | None = None, parent=None):
        super().__init__(parent)
        self._settings = settings or HotkeySettings()
        self._original_settings = self._settings.model_copy()

        self.setWindowTitle("Keyboard Shortcuts Settings")
        self.setMinimumSize(600, 400)

        self._build_ui()
        self._populate_table()

    def _build_ui(self) -> None:
        """Build the dialog UI."""
        layout = QVBoxLayout(self)

        # Header label
        header = QLabel("Customize keyboard shortcuts:")
        layout.addWidget(header)

        # Table widget for showing hotkeys
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Action", "Keybinding"])

        # Make action column readable, keybinding column editable
        header = self._table.horizontalHeader()
        assert header is not None
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self._table.itemChanged.connect(self._on_keybinding_edited)

        layout.addWidget(self._table)

        # Buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def _populate_table(self) -> None:
        """Populate the table with current hotkey settings."""
        # Block signals while populating
        self._table.blockSignals(True)

        actions = [
            "next_waiting_ticket",
            "back_to_runs",
            "toggle_theme",
            "refresh_dashboard",
            "open_documentation",
            "focus_terminal",
        ]

        self._table.setRowCount(len(actions))

        for row, action in enumerate(actions):
            # Action description (read-only)
            desc_item = QTableWidgetItem(HotkeySettings.get_action_description(action))
            desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, desc_item)

            # Keybinding (editable)
            keybinding = getattr(self._settings, action)
            key_item = QTableWidgetItem(keybinding)
            key_item.setData(Qt.ItemDataRole.UserRole, action)  # Store action name
            self._table.setItem(row, 1, key_item)

        self._table.blockSignals(False)

    def _on_keybinding_edited(self, item: QTableWidgetItem) -> None:
        """Handle keybinding edit."""
        if item.column() != 1:
            return

        action = item.data(Qt.ItemDataRole.UserRole)
        new_keybinding = item.text().strip()

        # Validate keybinding
        if not self._validate_keybinding(new_keybinding):
            # Revert to original
            old_keybinding = getattr(self._settings, action)
            self._table.blockSignals(True)
            item.setText(old_keybinding)
            self._table.blockSignals(False)
            return

        # Check for conflicts
        if self._check_keybinding_conflict(new_keybinding, action):
            QMessageBox.warning(
                self,
                "Duplicate Keybinding",
                f"The keybinding '{new_keybinding}' is already in use by another action. "
                "Please choose a different keybinding.",
            )
            # Revert to original
            old_keybinding = getattr(self._settings, action)
            self._table.blockSignals(True)
            item.setText(old_keybinding)
            self._table.blockSignals(False)
            return

        # Update settings
        setattr(self._settings, action, new_keybinding)

    def _validate_keybinding(self, keybinding: str) -> bool:
        """Validate keybinding format."""
        if not keybinding or not keybinding.strip():
            self._show_error("Keybinding cannot be empty")
            return False

        # Use QKeySequence to validate
        seq = QKeySequence(keybinding)
        if seq.isEmpty():
            self._show_error(f"Invalid keybinding: {keybinding}")
            return False

        return True

    def _check_keybinding_conflict(self, keybinding: str, current_action: str) -> bool:
        """Check if keybinding is already in use by another action."""
        for action in ["next_waiting_ticket", "back_to_runs", "toggle_theme",
                       "refresh_dashboard", "open_documentation", "focus_terminal"]:
            if action != current_action:
                if getattr(self._settings, action) == keybinding:
                    return True
        return False

    def _validate_all(self) -> bool:
        """Validate all keybindings before saving."""
        # Check for empty keybindings
        for action in ["next_waiting_ticket", "back_to_runs", "toggle_theme",
                       "refresh_dashboard", "open_documentation", "focus_terminal"]:
            keybinding = getattr(self._settings, action)
            if not keybinding or not keybinding.strip():
                self._show_error(f"Keybinding for {action} cannot be empty")
                return False

            # Validate with QKeySequence
            seq = QKeySequence(keybinding)
            if seq.isEmpty():
                self._show_error(f"Invalid keybinding for {action}: {keybinding}")
                return False

        return True

    def _show_error(self, message: str) -> None:
        """Show error message."""
        QMessageBox.critical(self, "Validation Error", message)

    def show_validation_error(self, message: str) -> None:
        """Show validation error (alias for _show_error)."""
        self._show_error(message)

    def _reset_to_defaults(self) -> None:
        """Reset all keybindings to defaults."""
        self._settings = HotkeySettings()
        self._populate_table()

    def _save_settings(self) -> None:
        """Validate and save settings."""
        if self._validate_all():
            self.accept()

    def get_settings(self) -> HotkeySettings:
        """Get the updated settings."""
        return self._settings

    @property
    def settings(self) -> HotkeySettings:
        """Get the updated settings."""
        return self._settings

    def has_conflict(self) -> bool:
        """Check if there are any conflicts in current settings."""
        seen = set()
        for action in ["next_waiting_ticket", "back_to_runs", "toggle_theme",
                       "refresh_dashboard", "open_documentation", "focus_terminal"]:
            keybinding = getattr(self._settings, action)
            if keybinding in seen:
                return True
            seen.add(keybinding)
        return False

    def update_keybinding(self, action: str, keybinding: str) -> None:
        """Update a specific keybinding."""
        if hasattr(self._settings, action):
            setattr(self._settings, action, keybinding)
            self._populate_table()

    def _edit_keybinding(self, row: int) -> None:
        """Edit a keybinding (placeholder for future key capture widget)."""
        pass
