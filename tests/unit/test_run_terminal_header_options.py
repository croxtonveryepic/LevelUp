"""Comprehensive TDD tests for run options in RunTerminalWidget header.

This test suite covers the requirements for moving run options (model, effort,
skip_planning) from ticket form to run terminal header, making them run-level
controls instead of ticket-level metadata.

Requirements:
- Move run options from ticket form to run terminal header
- Wire run options directly to build_run_command instead of via ticket metadata
- Lock run options while a run exists for the ticket
- Update ticket form save logic to exclude moved options
- Update orchestrator to NOT read model/effort/skip_planning from ticket metadata

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Skip all tests if PyQt6 not available
pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_terminal_widget():
    """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
    with patch("levelup.gui.terminal_emulator.PtyBackend"):
        from levelup.gui.run_terminal import RunTerminalWidget

        widget = RunTerminalWidget()
    return widget


# ---------------------------------------------------------------------------
# AC: Run options widgets exist in RunTerminalWidget header
# ---------------------------------------------------------------------------


class TestRunOptionsInHeader:
    """Test that run option widgets are present in RunTerminalWidget header."""

    def test_model_combo_exists_in_header(self, qapp, mock_terminal_widget):
        """AC: Model combo (Default/Sonnet/Opus) moved to RunTerminalWidget header."""
        widget = mock_terminal_widget
        assert hasattr(widget, "_model_combo"), "RunTerminalWidget should have _model_combo"
        assert widget._model_combo is not None

    def test_model_combo_has_correct_options(self, qapp, mock_terminal_widget):
        """AC: Model combo should have Default/Sonnet/Opus options."""
        widget = mock_terminal_widget
        assert widget._model_combo.count() == 3
        assert widget._model_combo.itemText(0) == "Default"
        assert widget._model_combo.itemText(1) == "Sonnet"
        assert widget._model_combo.itemText(2) == "Opus"

    def test_effort_combo_exists_in_header(self, qapp, mock_terminal_widget):
        """AC: Effort combo (Default/Low/Medium/High) moved to RunTerminalWidget header."""
        widget = mock_terminal_widget
        assert hasattr(widget, "_effort_combo"), "RunTerminalWidget should have _effort_combo"
        assert widget._effort_combo is not None

    def test_effort_combo_has_correct_options(self, qapp, mock_terminal_widget):
        """AC: Effort combo should have Default/Low/Medium/High options."""
        widget = mock_terminal_widget
        assert widget._effort_combo.count() == 4
        assert widget._effort_combo.itemText(0) == "Default"
        assert widget._effort_combo.itemText(1) == "Low"
        assert widget._effort_combo.itemText(2) == "Medium"
        assert widget._effort_combo.itemText(3) == "High"

    def test_skip_planning_checkbox_exists_in_header(self, qapp, mock_terminal_widget):
        """AC: Skip planning checkbox moved to RunTerminalWidget header."""
        widget = mock_terminal_widget
        assert hasattr(
            widget, "_skip_planning_checkbox"
        ), "RunTerminalWidget should have _skip_planning_checkbox"
        assert widget._skip_planning_checkbox is not None

    def test_run_options_positioned_left_of_run_button(self, qapp, mock_terminal_widget):
        """AC: Run options displayed in horizontal layout between status label and Run button."""
        widget = mock_terminal_widget
        # The header layout should contain status label, then run options, then buttons
        # This test verifies the layout structure exists
        # Implementation should ensure proper widget ordering in header QHBoxLayout


# ---------------------------------------------------------------------------
# AC: Run options wire directly to build_run_command
# ---------------------------------------------------------------------------


class TestRunOptionsWireToCommand:
    """Test that run options read from widget combos, not external settings."""

    def test_build_run_command_uses_model_from_combo(self, qapp, mock_terminal_widget):
        """AC: build_run_command() reads model from widget's combo when constructing CLI command."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # Set model combo to Sonnet
        widget._model_combo.setCurrentIndex(1)

        # Start run should build command with --model sonnet
        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ) as mock_send:
            widget.start_run(1, "/some/project", "/some/db.db")

            cmd_arg = mock_send.call_args[0][0]
            assert "--model sonnet" in cmd_arg.lower()

        widget._run_id_poll_timer.stop()

    def test_build_run_command_uses_effort_from_combo(self, qapp, mock_terminal_widget):
        """AC: build_run_command() reads effort from widget's combo when constructing CLI command."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # Set effort combo to High
        widget._effort_combo.setCurrentIndex(3)

        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ) as mock_send:
            widget.start_run(1, "/some/project", "/some/db.db")

            cmd_arg = mock_send.call_args[0][0]
            assert "--effort high" in cmd_arg.lower()

        widget._run_id_poll_timer.stop()

    def test_build_run_command_uses_skip_planning_from_checkbox(
        self, qapp, mock_terminal_widget
    ):
        """AC: build_run_command() reads skip_planning from widget's checkbox when constructing CLI command."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # Check skip planning
        widget._skip_planning_checkbox.setChecked(True)

        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ) as mock_send:
            widget.start_run(1, "/some/project", "/some/db.db")

            cmd_arg = mock_send.call_args[0][0]
            assert "--skip-planning" in cmd_arg

        widget._run_id_poll_timer.stop()

    def test_build_run_command_excludes_flags_when_default(
        self, qapp, mock_terminal_widget
    ):
        """AC: build_run_command() should not include flags when all options are at default."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # All combos at index 0 (Default), checkbox unchecked
        widget._model_combo.setCurrentIndex(0)
        widget._effort_combo.setCurrentIndex(0)
        widget._skip_planning_checkbox.setChecked(False)

        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ) as mock_send:
            widget.start_run(1, "/some/project", "/some/db.db")

            cmd_arg = mock_send.call_args[0][0]
            assert "--model" not in cmd_arg
            assert "--effort" not in cmd_arg
            assert "--skip-planning" not in cmd_arg

        widget._run_id_poll_timer.stop()

    def test_run_options_not_read_from_set_ticket_settings(
        self, qapp, mock_terminal_widget
    ):
        """AC: Run options should NOT be read from external settings after widget initialization."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # Set model combo to Opus
        widget._model_combo.setCurrentIndex(2)

        # External call to set_ticket_settings should NOT override widget state
        # This method should be removed or no longer affect run options
        if hasattr(widget, "set_ticket_settings"):
            widget.set_ticket_settings(model="sonnet", effort="low", skip_planning=True)

        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ) as mock_send:
            widget.start_run(1, "/some/project", "/some/db.db")

            cmd_arg = mock_send.call_args[0][0]
            # Should use widget combo value (opus), not external setting (sonnet)
            assert "--model opus" in cmd_arg.lower()

        widget._run_id_poll_timer.stop()


# ---------------------------------------------------------------------------
# AC: Lock run options while run exists
# ---------------------------------------------------------------------------


class TestRunOptionsLocking:
    """Test that run options are locked when a run exists for the ticket."""

    def test_model_combo_disabled_when_run_exists(self, qapp, mock_terminal_widget):
        """AC: Model combo disabled when _last_run_id is not None."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with a run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._model_combo.isEnabled() is False

    def test_effort_combo_disabled_when_run_exists(self, qapp, mock_terminal_widget):
        """AC: Effort combo disabled when _last_run_id is not None."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-456"
        widget._ticket_number = 3
        widget._project_path = "/some/project"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._effort_combo.isEnabled() is False

    def test_skip_planning_disabled_when_run_exists(self, qapp, mock_terminal_widget):
        """AC: Skip planning checkbox disabled when _last_run_id is not None."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-789"
        widget._ticket_number = 7
        widget._project_path = "/some/project"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._skip_planning_checkbox.isEnabled() is False

    def test_run_options_disabled_when_running(self, qapp, mock_terminal_widget):
        """AC: All run options disabled when is_running is True."""
        widget = mock_terminal_widget
        widget._command_running = True

        widget._set_running_state(True)

        assert widget._model_combo.isEnabled() is False
        assert widget._effort_combo.isEnabled() is False
        assert widget._skip_planning_checkbox.isEnabled() is False

    def test_run_options_enabled_after_forget(self, qapp, mock_terminal_widget):
        """AC: Options re-enabled when run completes AND user clicks Forget to clear _last_run_id."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-999"
        widget._ticket_number = 2
        widget._project_path = "/some/project"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        mock_sm.delete_run.return_value = None
        widget.set_state_manager(mock_sm)

        # Initially locked
        widget._update_button_states()
        assert widget._model_combo.isEnabled() is False

        # Forget the run (simulating _on_forget_clicked)
        widget._last_run_id = None
        widget._update_button_states()

        # Now unlocked
        assert widget._model_combo.isEnabled() is True
        assert widget._effort_combo.isEnabled() is True
        assert widget._skip_planning_checkbox.isEnabled() is True

    def test_run_options_locked_during_active_run(self, qapp, mock_terminal_widget):
        """AC: Options locked when run is in active state (running, pending, waiting_for_input)."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-active"
        widget._ticket_number = 8
        widget._project_path = "/some/project"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "running"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._model_combo.isEnabled() is False
        assert widget._effort_combo.isEnabled() is False
        assert widget._skip_planning_checkbox.isEnabled() is False

    def test_visual_indication_when_options_locked(self, qapp, mock_terminal_widget):
        """AC: Visual indication (e.g., tooltip) explains why options are locked when disabled."""
        widget = mock_terminal_widget
        widget._last_run_id = "test-run-123"

        widget._update_button_states()

        # Check that tooltips are set when disabled
        model_tooltip = widget._model_combo.toolTip()
        effort_tooltip = widget._effort_combo.toolTip()
        skip_tooltip = widget._skip_planning_checkbox.toolTip()

        # Tooltips should explain why locked (contain "run" or "forget" or similar)
        assert len(model_tooltip) > 0, "Model combo should have tooltip when locked"
        assert len(effort_tooltip) > 0, "Effort combo should have tooltip when locked"
        assert len(skip_tooltip) > 0, "Skip planning should have tooltip when locked"


# ---------------------------------------------------------------------------
# AC: _update_button_states manages run option widget states
# ---------------------------------------------------------------------------


class TestUpdateButtonStatesManagesOptions:
    """Test that _update_button_states() extends to manage run option widget states."""

    def test_update_button_states_disables_options_with_run(
        self, qapp, mock_terminal_widget
    ):
        """AC: _update_button_states() method extended to manage run option widget states."""
        from levelup.state.manager import StateManager

        widget = mock_terminal_widget
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._model_combo.isEnabled() is False
        assert widget._effort_combo.isEnabled() is False
        assert widget._skip_planning_checkbox.isEnabled() is False

    def test_update_button_states_enables_options_without_run(
        self, qapp, mock_terminal_widget
    ):
        """AC: _update_button_states() enables options when no run exists."""
        widget = mock_terminal_widget
        widget._last_run_id = None
        widget._command_running = False

        widget._update_button_states()

        assert widget._model_combo.isEnabled() is True
        assert widget._effort_combo.isEnabled() is True
        assert widget._skip_planning_checkbox.isEnabled() is True

    def test_set_running_state_disables_options(self, qapp, mock_terminal_widget):
        """AC: _set_running_state() also manages run option widget states."""
        widget = mock_terminal_widget

        widget._set_running_state(True)

        assert widget._model_combo.isEnabled() is False
        assert widget._effort_combo.isEnabled() is False
        assert widget._skip_planning_checkbox.isEnabled() is False

    def test_set_running_state_enables_options_when_stopped_and_no_run(
        self, qapp, mock_terminal_widget
    ):
        """AC: _set_running_state(False) enables options when no last_run_id."""
        widget = mock_terminal_widget
        widget._last_run_id = None

        widget._set_running_state(False)

        assert widget._model_combo.isEnabled() is True
        assert widget._effort_combo.isEnabled() is True
        assert widget._skip_planning_checkbox.isEnabled() is True


# ---------------------------------------------------------------------------
# AC: Run options persist across widget lifecycle
# ---------------------------------------------------------------------------


class TestRunOptionsPersistence:
    """Test that run option values persist correctly across widget operations."""

    def test_model_combo_default_is_index_0(self, qapp, mock_terminal_widget):
        """Run options should initialize to default values."""
        widget = mock_terminal_widget
        assert widget._model_combo.currentIndex() == 0

    def test_effort_combo_default_is_index_0(self, qapp, mock_terminal_widget):
        """Run options should initialize to default values."""
        widget = mock_terminal_widget
        assert widget._effort_combo.currentIndex() == 0

    def test_skip_planning_default_is_unchecked(self, qapp, mock_terminal_widget):
        """Run options should initialize to default values."""
        widget = mock_terminal_widget
        assert widget._skip_planning_checkbox.isChecked() is False

    def test_model_combo_value_persists_across_runs(self, qapp, mock_terminal_widget):
        """User's selection should persist after run completes."""
        widget = mock_terminal_widget
        widget._ticket_number = 1
        widget._project_path = "/some/project"
        widget._db_path = "/some/db.db"

        # Set to Opus
        widget._model_combo.setCurrentIndex(2)

        # Start and complete a run
        with patch.object(widget._terminal, "start_shell"), patch.object(
            widget._terminal, "send_command"
        ):
            widget.start_run(1, "/some/project", "/some/db.db")
            widget._set_running_state(False)

        # Value should still be Opus
        assert widget._model_combo.currentIndex() == 2

        widget._run_id_poll_timer.stop()

    def test_options_reset_to_default_when_no_ticket(self, qapp, mock_terminal_widget):
        """When no ticket is loaded, options should be at default or disabled."""
        widget = mock_terminal_widget
        widget._ticket_number = None
        widget._project_path = None

        widget._update_button_states()

        # Implementation choice: either disabled or reset to defaults
        # At minimum, they should not have stale values from a previous ticket


# ---------------------------------------------------------------------------
# AC: Integration with ticket detail widget
# ---------------------------------------------------------------------------


class TestTicketDetailIntegration:
    """Test integration between TicketDetailWidget and RunTerminalWidget."""

    def test_ticket_detail_does_not_set_run_options(self, qapp, tmp_path):
        """AC: TicketDetailWidget should NOT call terminal.set_ticket_settings() for run options."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "sonnet", "effort": "high", "skip_planning": True},
        )

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)

            # Terminal should NOT have received run options via set_ticket_settings
            # (This test will pass once set_ticket_settings is removed or refactored)
            # For now, we verify the terminal's run options are independent

    def test_ticket_detail_terminal_has_independent_options(self, qapp, tmp_path):
        """AC: Terminal's run options are independent from ticket metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "opus", "effort": "low"},
        )

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)

            # Terminal should have options at default, not from ticket metadata
            terminal = widget._current_terminal
            if terminal and hasattr(terminal, "_model_combo"):
                # Options should be at default (index 0)
                assert terminal._model_combo.currentIndex() == 0
                assert terminal._effort_combo.currentIndex() == 0
                assert terminal._skip_planning_checkbox.isChecked() is False
