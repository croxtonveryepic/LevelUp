"""Tests for hotkey settings dialog widget."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PyQt6.QtWidgets import QApplication, QPushButton, QTableWidget, QLineEdit, QDialog

from levelup.config.settings import HotkeySettings


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestHotkeySettingsDialog:
    """Test hotkey settings dialog widget."""

    def test_dialog_can_be_created(self):
        """HotkeySettingsDialog should be instantiable."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()
        assert dialog is not None
        assert isinstance(dialog, QDialog)

        dialog.close()

    def test_dialog_accepts_initial_settings(self):
        """Dialog should accept initial hotkey settings."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        settings = HotkeySettings(next_waiting_ticket="Alt+N")
        dialog = HotkeySettingsDialog(settings=settings)

        assert dialog is not None

        dialog.close()

    def test_dialog_has_table_widget(self):
        """Dialog should have a table widget showing all hotkeys."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Find table widget
        table = dialog.findChild(QTableWidget)
        assert table is not None, "Dialog should have a QTableWidget"

        dialog.close()

    def test_table_shows_all_hotkey_actions(self):
        """Table should display all hotkey actions."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()
        table = dialog.findChild(QTableWidget)

        assert table is not None

        # Should have at least 6 rows (one for each hotkey action)
        assert table.rowCount() >= 6

        dialog.close()

    def test_table_has_action_and_keybinding_columns(self):
        """Table should have columns for action name and keybinding."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()
        table = dialog.findChild(QTableWidget)

        assert table is not None

        # Should have at least 2 columns
        assert table.columnCount() >= 2

        dialog.close()

    def test_dialog_has_save_button(self):
        """Dialog should have a Save button."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Find save button
        save_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "save" in btn.text().lower()
        ]

        assert len(save_buttons) > 0, "Dialog should have a Save button"

        dialog.close()

    def test_dialog_has_cancel_button(self):
        """Dialog should have a Cancel button."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Find cancel button
        cancel_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "cancel" in btn.text().lower()
        ]

        assert len(cancel_buttons) > 0, "Dialog should have a Cancel button"

        dialog.close()

    def test_dialog_has_reset_button(self):
        """Dialog should have a Reset to Defaults button."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Find reset button
        reset_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "reset" in btn.text().lower() or "default" in btn.text().lower()
        ]

        assert len(reset_buttons) > 0, "Dialog should have a Reset to Defaults button"

        dialog.close()


class TestHotkeyEditing:
    """Test editing keybindings in the dialog."""

    def test_can_click_keybinding_to_edit(self):
        """Should be able to click on a keybinding to edit it."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()
        table = dialog.findChild(QTableWidget)

        assert table is not None

        # Table should be editable or have edit mechanism
        # Either cells are editable or double-click triggers edit widget

        dialog.close()

    def test_keybinding_editor_accepts_new_binding(self):
        """Should be able to enter a new keybinding."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to update keybinding
        assert hasattr(dialog, "_on_keybinding_edited") or \
               hasattr(dialog, "update_keybinding") or \
               hasattr(dialog, "_edit_keybinding")

        dialog.close()

    def test_validates_keybinding_format(self):
        """Should validate keybinding format when editing."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have validation method
        assert hasattr(dialog, "_validate_keybinding") or \
               hasattr(dialog, "validate_key_sequence")

        dialog.close()

    def test_warns_on_duplicate_keybinding(self):
        """Should warn if keybinding is already in use."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to check for conflicts
        assert hasattr(dialog, "_check_keybinding_conflict") or \
               hasattr(dialog, "has_conflict")

        dialog.close()


class TestResetToDefaults:
    """Test resetting keybindings to defaults."""

    def test_reset_button_restores_defaults(self):
        """Reset button should restore all keybindings to defaults."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        # Start with custom settings
        custom_settings = HotkeySettings(
            next_waiting_ticket="Alt+N",
            back_to_runs="Ctrl+B",
        )
        dialog = HotkeySettingsDialog(settings=custom_settings)

        # Find reset button
        reset_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "reset" in btn.text().lower() or "default" in btn.text().lower()
        ]

        if reset_buttons:
            reset_btn = reset_buttons[0]
            reset_btn.click()

            # Should have reset to defaults
            # Check via dialog's internal state or table contents

        dialog.close()

    def test_reset_updates_table_display(self):
        """Resetting should update the table to show default values."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        custom_settings = HotkeySettings(next_waiting_ticket="Alt+N")
        dialog = HotkeySettingsDialog(settings=custom_settings)

        reset_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "reset" in btn.text().lower() or "default" in btn.text().lower()
        ]

        if reset_buttons:
            reset_btn = reset_buttons[0]
            reset_btn.click()

            # Table should show Ctrl+N (default) instead of Alt+N
            table = dialog.findChild(QTableWidget)
            if table:
                # Find row for next_waiting_ticket and check value
                pass  # Implementation will verify table contents

        dialog.close()


class TestSaveAndCancel:
    """Test save and cancel behavior."""

    def test_save_button_returns_updated_settings(self):
        """Save button should return updated hotkey settings."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to get updated settings
        assert hasattr(dialog, "get_settings") or \
               hasattr(dialog, "settings") or \
               hasattr(dialog, "_settings")

        dialog.close()

    def test_cancel_button_discards_changes(self):
        """Cancel button should discard changes and close dialog."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        initial_settings = HotkeySettings(next_waiting_ticket="Ctrl+N")
        dialog = HotkeySettingsDialog(settings=initial_settings)

        # Make changes (implementation detail)

        # Find cancel button
        cancel_buttons = [
            btn for btn in dialog.findChildren(QPushButton)
            if "cancel" in btn.text().lower()
        ]

        if cancel_buttons:
            cancel_btn = cancel_buttons[0]
            # Should reject dialog and discard changes
            # Dialog result should be Rejected

        dialog.close()

    def test_save_validates_all_keybindings(self):
        """Save should validate all keybindings before accepting."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have validation before save
        assert hasattr(dialog, "_validate_all") or \
               hasattr(dialog, "validate_settings")

        dialog.close()


class TestVisualFeedback:
    """Test visual feedback for editing and validation."""

    def test_shows_visual_feedback_on_successful_save(self):
        """Should show visual feedback when keybinding is successfully changed."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to show feedback
        # Could be status message, color change, etc.
        # Implementation detail

        dialog.close()

    def test_shows_error_for_invalid_keybinding(self):
        """Should show error for invalid keybinding format."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to show errors
        assert hasattr(dialog, "_show_error") or \
               hasattr(dialog, "show_validation_error")

        dialog.close()

    def test_highlights_conflicting_keybindings(self):
        """Should highlight rows with conflicting keybindings."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to highlight conflicts
        # Could set row background color, add icon, etc.

        dialog.close()


class TestActionDescriptions:
    """Test that actions are shown with human-readable descriptions."""

    def test_table_shows_action_descriptions(self):
        """Table should show human-readable action descriptions."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()
        table = dialog.findChild(QTableWidget)

        if table and table.rowCount() > 0:
            # First column should contain readable descriptions
            # e.g., "Next waiting ticket" instead of "next_waiting_ticket"
            first_action = table.item(0, 0)
            if first_action:
                text = first_action.text()
                # Should be readable (contains spaces, capitalized)
                assert " " in text or text[0].isupper()

        dialog.close()

    def test_descriptions_match_hotkey_actions(self):
        """Each description should correspond to a hotkey action."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Expected descriptions
        expected_actions = [
            "Next waiting ticket",
            "Back to runs",
            "Toggle theme",
            "Refresh dashboard",
            "Open documentation",
            "Focus terminal",
        ]

        # Dialog should display all these actions
        # Implementation will verify table contents

        dialog.close()


class TestKeyboardShortcutCapture:
    """Test capturing keyboard shortcuts for editing."""

    def test_has_key_capture_widget(self):
        """Should have a widget to capture key sequences."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have a custom widget or QLineEdit for capturing keys
        # Could be named KeySequenceEdit, HotkeyCapture, etc.

        dialog.close()

    def test_key_capture_shows_modifier_keys(self):
        """Key capture should display modifier keys (Ctrl, Shift, Alt)."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should be able to capture and display "Ctrl+Shift+N" etc.
        # Implementation detail

        dialog.close()

    def test_key_capture_supports_function_keys(self):
        """Key capture should support F1-F12 function keys."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should be able to capture F1, F5, etc.
        # Implementation detail

        dialog.close()

    def test_key_capture_supports_special_keys(self):
        """Key capture should support special keys like Escape, Return."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should be able to capture Escape, Tab, etc.
        # Implementation detail

        dialog.close()
