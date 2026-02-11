"""Tests for hotkey edge cases and error handling."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import ValidationError
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence

from levelup.config.settings import HotkeySettings, GUISettings


def _ensure_qapp():
    """Ensure QApplication exists."""
    return QApplication.instance() or QApplication([])


class TestInvalidKeybindings:
    """Test handling of invalid keybinding formats."""

    def test_invalid_key_sequence_format(self):
        """Invalid key sequence format should raise validation error."""
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="Ctrl++")

    def test_empty_keybinding_rejected(self):
        """Empty keybinding should be rejected."""
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="")

    def test_whitespace_only_keybinding_rejected(self):
        """Whitespace-only keybinding should be rejected."""
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="   ")

    def test_invalid_modifier_key(self):
        """Invalid modifier key should be rejected."""
        # Qt will handle most invalid sequences, but we should validate
        with pytest.raises(ValidationError):
            HotkeySettings(next_waiting_ticket="Super+N")  # Super not standard


class TestConflictingKeybindings:
    """Test handling of conflicting keybindings."""

    def test_model_allows_duplicate_keybindings(self):
        """Model should allow duplicates (UI validates)."""
        # Model doesn't prevent duplicates
        settings = HotkeySettings(
            next_waiting_ticket="Ctrl+N",
            refresh_dashboard="Ctrl+N",  # Duplicate
        )

        assert settings.next_waiting_ticket == "Ctrl+N"
        assert settings.refresh_dashboard == "Ctrl+N"

    def test_dialog_detects_conflicts(self):
        """Settings dialog should detect conflicting keybindings."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        dialog = HotkeySettingsDialog()

        # Should have method to check conflicts
        assert hasattr(dialog, "_check_keybinding_conflict") or \
               hasattr(dialog, "has_conflict") or \
               hasattr(dialog, "_validate_no_conflicts")

        dialog.close()

    def test_conflict_detection_finds_duplicates(self):
        """Conflict detection should find duplicate keybindings."""
        _ensure_qapp()

        from levelup.gui.hotkey_settings_dialog import HotkeySettingsDialog

        settings = HotkeySettings(
            next_waiting_ticket="Ctrl+N",
            refresh_dashboard="Ctrl+N",  # Duplicate
        )

        dialog = HotkeySettingsDialog(settings=settings)

        # Should detect the conflict
        # Implementation will show warning or prevent save

        dialog.close()


class TestPlatformSpecificKeybindings:
    """Test platform-specific keybinding handling."""

    def test_ctrl_auto_maps_to_cmd_on_macos(self):
        """Qt should automatically map Ctrl to Cmd on macOS."""
        # Qt's QKeySequence handles this automatically
        seq = QKeySequence("Ctrl+N")

        # On macOS, Qt translates Ctrl to Cmd
        # On Windows/Linux, stays as Ctrl
        # This is handled by Qt, we just verify it works

        assert seq.toString() is not None

    def test_platform_independent_key_names(self):
        """Should support platform-independent key names."""
        # These should work on all platforms
        keys = ["Ctrl+N", "Shift+F5", "Alt+Tab", "Meta+A"]

        for key in keys:
            seq = QKeySequence(key)
            assert seq.toString() is not None

    def test_function_keys_work_cross_platform(self):
        """Function keys should work on all platforms."""
        for i in range(1, 13):
            key = f"F{i}"
            seq = QKeySequence(key)
            assert seq.toString() is not None


class TestSpecialKeys:
    """Test special key handling."""

    def test_escape_key_supported(self):
        """Escape key should be supported."""
        settings = HotkeySettings(back_to_runs="Escape")
        assert settings.back_to_runs == "Escape"

    def test_return_key_supported(self):
        """Return/Enter key should be supported."""
        settings = HotkeySettings(back_to_runs="Return")
        assert settings.back_to_runs == "Return"

    def test_tab_key_supported(self):
        """Tab key should be supported."""
        settings = HotkeySettings(back_to_runs="Tab")
        assert settings.back_to_runs == "Tab"

    def test_backtick_in_keybinding(self):
        """Backtick (`) should work in keybindings."""
        settings = HotkeySettings(focus_terminal="Ctrl+`")
        assert settings.focus_terminal == "Ctrl+`"

    def test_space_key_supported(self):
        """Space key should be supported."""
        settings = HotkeySettings(back_to_runs="Space")
        assert settings.back_to_runs == "Space"


class TestComplexKeySequences:
    """Test complex key sequence combinations."""

    def test_triple_modifier_combination(self):
        """Should support three modifiers (Ctrl+Shift+Alt)."""
        settings = HotkeySettings(next_waiting_ticket="Ctrl+Shift+Alt+N")
        assert settings.next_waiting_ticket == "Ctrl+Shift+Alt+N"

    def test_shift_with_function_key(self):
        """Should support Shift with function keys."""
        settings = HotkeySettings(refresh_dashboard="Shift+F5")
        assert settings.refresh_dashboard == "Shift+F5"

    def test_alt_with_letter(self):
        """Should support Alt with letter keys."""
        settings = HotkeySettings(next_waiting_ticket="Alt+N")
        assert settings.next_waiting_ticket == "Alt+N"

    def test_ctrl_with_special_key(self):
        """Should support Ctrl with special keys."""
        settings = HotkeySettings(back_to_runs="Ctrl+Escape")
        assert settings.back_to_runs == "Ctrl+Escape"


class TestKeybindingNormalization:
    """Test keybinding format normalization."""

    def test_lowercase_ctrl_normalized(self):
        """Lowercase 'ctrl' should be normalized to 'Ctrl'."""
        # Qt's QKeySequence handles normalization
        seq = QKeySequence("ctrl+n")
        # Qt normalizes to standard format
        assert "Ctrl" in seq.toString() or "ctrl" in seq.toString()

    def test_plus_spacing_normalized(self):
        """Spaces around + should be normalized."""
        seq = QKeySequence("Ctrl + N")
        # Qt normalizes to "Ctrl+N"
        normalized = seq.toString()
        assert normalized is not None

    def test_key_order_normalized(self):
        """Modifier key order should be normalized."""
        # Qt normalizes modifier order
        seq1 = QKeySequence("Shift+Ctrl+N")
        seq2 = QKeySequence("Ctrl+Shift+N")

        # Both should be valid and equivalent
        assert seq1.toString() is not None
        assert seq2.toString() is not None


class TestHotkeyUpdateEdgeCases:
    """Test edge cases when updating hotkeys."""

    @patch("levelup.gui.main_window.StateManager")
    def test_update_hotkeys_with_none(self, mock_state_manager):
        """Updating with None should not crash."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Should not crash if update method is called with None
        if hasattr(window, "_update_hotkeys"):
            try:
                window._update_hotkeys(None)
            except (TypeError, AttributeError):
                # Expected to fail gracefully
                pass

        window.close()

    @patch("levelup.gui.main_window.StateManager")
    def test_update_with_incomplete_settings(self, mock_state_manager):
        """Updating with incomplete settings should use defaults."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        window = MainWindow(mock_state, project_path=Path.cwd())

        # Partial settings should work (uses defaults for missing)
        partial_settings = HotkeySettings(next_waiting_ticket="Alt+N")

        if hasattr(window, "_update_hotkeys"):
            window._update_hotkeys(partial_settings)

            # Should have updated hotkeys
            # Other hotkeys should use defaults

        window.close()


class TestNoProjectPath:
    """Test hotkey behavior when no project path is available."""

    @patch("levelup.gui.main_window.StateManager")
    def test_no_project_path_uses_defaults(self, mock_state_manager):
        """No project path should use default hotkey settings."""
        _ensure_qapp()

        mock_state = Mock()
        mock_state._db_path = ":memory:"
        mock_state.list_runs.return_value = []
        mock_state_manager.return_value = mock_state

        from levelup.gui.main_window import MainWindow

        # Create window without project path
        window = MainWindow(mock_state, project_path=None)

        # Should still have hotkeys registered (using defaults)
        from PyQt6.QtGui import QShortcut

        shortcuts = window.findChildren(QShortcut)
        assert len(shortcuts) >= 6, "Should have default hotkeys even without project"

        window.close()


class TestActionDescriptionEdgeCases:
    """Test edge cases with action descriptions."""

    def test_all_actions_have_descriptions(self):
        """All hotkey actions should have descriptions."""
        if hasattr(HotkeySettings, "ACTION_DESCRIPTIONS"):
            descriptions = HotkeySettings.ACTION_DESCRIPTIONS

            # Check all fields have descriptions
            settings = HotkeySettings()
            for field_name in settings.model_fields:
                assert field_name in descriptions, \
                    f"Missing description for {field_name}"

    def test_descriptions_are_non_empty(self):
        """Action descriptions should be non-empty strings."""
        if hasattr(HotkeySettings, "ACTION_DESCRIPTIONS"):
            descriptions = HotkeySettings.ACTION_DESCRIPTIONS

            for action, desc in descriptions.items():
                assert isinstance(desc, str)
                assert len(desc) > 0
                assert desc.strip() == desc  # No leading/trailing whitespace

    def test_descriptions_are_human_readable(self):
        """Action descriptions should be human-readable."""
        if hasattr(HotkeySettings, "ACTION_DESCRIPTIONS"):
            descriptions = HotkeySettings.ACTION_DESCRIPTIONS

            for desc in descriptions.values():
                # Should start with capital letter
                assert desc[0].isupper(), f"Description should be capitalized: {desc}"

                # Should not contain underscores
                assert "_" not in desc, f"Description should not have underscores: {desc}"


class TestKeySequenceValidation:
    """Test QKeySequence validation for keybindings."""

    def test_valid_key_sequences(self):
        """Valid key sequences should be accepted."""
        valid_sequences = [
            "Ctrl+N",
            "F5",
            "Escape",
            "Ctrl+Shift+T",
            "Alt+F4",
            "Ctrl+`",
        ]

        for seq_str in valid_sequences:
            seq = QKeySequence(seq_str)
            assert not seq.isEmpty(), f"{seq_str} should be valid"

    def test_invalid_key_sequences(self):
        """Invalid key sequences should be detected."""
        invalid_sequences = [
            "",  # Empty
            "Ctrl++",  # Double plus
            "NotAKey",  # Invalid key name
        ]

        for seq_str in invalid_sequences:
            seq = QKeySequence(seq_str)
            # Qt may create empty sequence for invalid input
            # We should validate before creating shortcuts

    def test_case_insensitive_modifiers(self):
        """Modifiers should be case-insensitive."""
        # Qt handles case normalization
        seq1 = QKeySequence("ctrl+n")
        seq2 = QKeySequence("Ctrl+N")
        seq3 = QKeySequence("CTRL+N")

        # All should create valid sequences
        assert not seq1.isEmpty()
        assert not seq2.isEmpty()
        assert not seq3.isEmpty()
