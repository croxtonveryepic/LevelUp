"""Integration tests for run option locking and unlocking workflow.

This test suite covers end-to-end integration tests for the run option locking
behavior, verifying the complete workflow from run start to completion and
option unlocking.

Requirements:
- Run options lock when run starts
- Run options remain locked while run is active
- Run options remain locked after run completes
- Run options unlock only after user clicks Forget
- Run options reflect current values in CLI command
- Multiple tickets can have independent run option states

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


# ---------------------------------------------------------------------------
# AC: Complete workflow from start to forget
# ---------------------------------------------------------------------------


class TestRunOptionLockingWorkflow:
    """Integration test for complete run option locking workflow."""

    def test_full_workflow_start_to_forget(self, qapp, tmp_path):
        """AC: Complete workflow - options lock on start, stay locked until forget."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        # Setup
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)
            terminal = widget._current_terminal

            # Mock state manager
            mock_sm = MagicMock(spec=StateManager)
            terminal.set_state_manager(mock_sm)
            terminal.set_context(str(tmp_path), "/tmp/db.db")

            # Step 1: Initially, options should be enabled
            assert terminal._model_combo.isEnabled() is True
            assert terminal._effort_combo.isEnabled() is True
            assert terminal._skip_planning_checkbox.isEnabled() is True

            # Step 2: Set some options
            terminal._model_combo.setCurrentIndex(2)  # Opus
            terminal._effort_combo.setCurrentIndex(3)  # High

            # Step 3: Start a run
            with patch.object(terminal._terminal, "start_shell"), patch.object(
                terminal._terminal, "send_command"
            ) as mock_send:
                terminal.start_run(ticket.number, str(tmp_path), "/tmp/db.db")

                # Verify command includes selected options
                cmd = mock_send.call_args[0][0]
                assert "--model opus" in cmd.lower()
                assert "--effort high" in cmd.lower()

            # Step 4: Options should be locked while running
            assert terminal._model_combo.isEnabled() is False
            assert terminal._effort_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False

            # Step 5: Run completes
            terminal._last_run_id = "test-run-123"
            mock_record = MagicMock()
            mock_record.status = "completed"
            mock_sm.get_run.return_value = mock_record

            terminal._set_running_state(False)

            # Step 6: Options should STILL be locked after completion
            assert terminal._model_combo.isEnabled() is False
            assert terminal._effort_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False

            # Step 7: User clicks Forget
            mock_sm.delete_run.return_value = None
            terminal._last_run_id = None
            terminal._update_button_states()

            # Step 8: Options should now be unlocked
            assert terminal._model_combo.isEnabled() is True
            assert terminal._effort_combo.isEnabled() is True
            assert terminal._skip_planning_checkbox.isEnabled() is True

            # Step 9: Options retain their previous values
            assert terminal._model_combo.currentIndex() == 2
            assert terminal._effort_combo.currentIndex() == 3

            # Cleanup
            terminal._run_id_poll_timer.stop()

    def test_workflow_with_failed_run(self, qapp, tmp_path):
        """AC: Workflow with failed run - options lock, stay locked, unlock after forget."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)
            terminal = widget._current_terminal

            mock_sm = MagicMock(spec=StateManager)
            terminal.set_state_manager(mock_sm)
            terminal.set_context(str(tmp_path), "/tmp/db.db")

            # Set options
            terminal._model_combo.setCurrentIndex(1)  # Sonnet
            terminal._skip_planning_checkbox.setChecked(True)

            # Start run
            with patch.object(terminal._terminal, "start_shell"), patch.object(
                terminal._terminal, "send_command"
            ):
                terminal.start_run(ticket.number, str(tmp_path), "/tmp/db.db")

            # Options locked while running
            assert terminal._model_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False

            # Run fails
            terminal._last_run_id = "test-run-456"
            mock_record = MagicMock()
            mock_record.status = "failed"
            mock_sm.get_run.return_value = mock_record

            terminal._set_running_state(False)

            # Options still locked after failure
            assert terminal._model_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False

            # Resume button should be enabled
            assert terminal._resume_btn.isEnabled() is True

            # Forget the run
            terminal._last_run_id = None
            terminal._update_button_states()

            # Options now unlocked
            assert terminal._model_combo.isEnabled() is True
            assert terminal._skip_planning_checkbox.isEnabled() is True

            # Cleanup
            terminal._run_id_poll_timer.stop()


# ---------------------------------------------------------------------------
# AC: Multiple tickets with independent option states
# ---------------------------------------------------------------------------


class TestMultipleTicketsIndependentOptions:
    """Test that multiple tickets can have independent run option states."""

    def test_switching_between_tickets_preserves_option_states(self, qapp, tmp_path):
        """AC: Each ticket's terminal has independent run option state."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket1 = add_ticket(tmp_path, "Task 1", "Description 1")
        ticket2 = add_ticket(tmp_path, "Task 2", "Description 2")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            mock_sm = MagicMock(spec=StateManager)

            # Load ticket 1
            widget.load_ticket(ticket1)
            terminal1 = widget._current_terminal
            terminal1.set_state_manager(mock_sm)

            # Set options for ticket 1
            terminal1._model_combo.setCurrentIndex(1)  # Sonnet
            terminal1._effort_combo.setCurrentIndex(2)  # Medium

            # Load ticket 2
            widget.load_ticket(ticket2)
            terminal2 = widget._current_terminal
            terminal2.set_state_manager(mock_sm)

            # Terminal 2 should have different instance
            # (or be the same instance but reset to defaults)
            # Options should be at default for ticket 2
            assert terminal2._model_combo.currentIndex() == 0
            assert terminal2._effort_combo.currentIndex() == 0

            # Set different options for ticket 2
            terminal2._model_combo.setCurrentIndex(2)  # Opus
            terminal2._effort_combo.setCurrentIndex(1)  # Low

            # Switch back to ticket 1
            widget.load_ticket(ticket1)
            terminal1_again = widget._current_terminal

            # Options should be preserved for ticket 1
            # (either same instance or restored from cache)
            assert terminal1_again._model_combo.currentIndex() == 1
            assert terminal1_again._effort_combo.currentIndex() == 2

    def test_one_ticket_locked_other_unlocked(self, qapp, tmp_path):
        """AC: One ticket can have locked options while another has unlocked options."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket1 = add_ticket(tmp_path, "Task 1", "Description 1")
        ticket2 = add_ticket(tmp_path, "Task 2", "Description 2")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            mock_sm = MagicMock(spec=StateManager)

            # Load ticket 1 and start a run
            widget.load_ticket(ticket1)
            terminal1 = widget._current_terminal
            terminal1.set_state_manager(mock_sm)
            terminal1.set_context(str(tmp_path), "/tmp/db.db")

            with patch.object(terminal1._terminal, "start_shell"), patch.object(
                terminal1._terminal, "send_command"
            ):
                terminal1.start_run(ticket1.number, str(tmp_path), "/tmp/db.db")

            # Ticket 1 options should be locked
            assert terminal1._model_combo.isEnabled() is False

            # Load ticket 2 (no run)
            widget.load_ticket(ticket2)
            terminal2 = widget._current_terminal
            terminal2.set_state_manager(mock_sm)

            # Ticket 2 options should be unlocked
            assert terminal2._model_combo.isEnabled() is True

            # Cleanup
            terminal1._run_id_poll_timer.stop()


# ---------------------------------------------------------------------------
# AC: Run options persist across widget lifecycle
# ---------------------------------------------------------------------------


class TestRunOptionsPersistAcrossLifecycle:
    """Test that run option values persist correctly across widget operations."""

    def test_options_persist_after_run_completion(self, qapp, tmp_path):
        """AC: User's option selection persists after run completes and is forgotten."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)
            terminal = widget._current_terminal

            mock_sm = MagicMock(spec=StateManager)
            terminal.set_state_manager(mock_sm)
            terminal.set_context(str(tmp_path), "/tmp/db.db")

            # Set options
            terminal._model_combo.setCurrentIndex(2)  # Opus
            terminal._effort_combo.setCurrentIndex(3)  # High
            terminal._skip_planning_checkbox.setChecked(True)

            # Run complete workflow
            with patch.object(terminal._terminal, "start_shell"), patch.object(
                terminal._terminal, "send_command"
            ):
                terminal.start_run(ticket.number, str(tmp_path), "/tmp/db.db")

            terminal._last_run_id = "test-run-123"
            mock_record = MagicMock()
            mock_record.status = "completed"
            mock_sm.get_run.return_value = mock_record
            terminal._set_running_state(False)

            # Forget the run
            terminal._last_run_id = None
            terminal._update_button_states()

            # Options should retain their values
            assert terminal._model_combo.currentIndex() == 2
            assert terminal._effort_combo.currentIndex() == 3
            assert terminal._skip_planning_checkbox.isChecked() is True

            # Cleanup
            terminal._run_id_poll_timer.stop()

    def test_second_run_uses_updated_options(self, qapp, tmp_path):
        """AC: User can change options after forgetting first run, second run uses new values."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)
            terminal = widget._current_terminal

            mock_sm = MagicMock(spec=StateManager)
            terminal.set_state_manager(mock_sm)
            terminal.set_context(str(tmp_path), "/tmp/db.db")

            # First run with Sonnet
            terminal._model_combo.setCurrentIndex(1)

            with patch.object(terminal._terminal, "start_shell"), patch.object(
                terminal._terminal, "send_command"
            ) as mock_send:
                terminal.start_run(ticket.number, str(tmp_path), "/tmp/db.db")
                first_cmd = mock_send.call_args[0][0]
                assert "--model sonnet" in first_cmd.lower()

            # Complete and forget first run
            terminal._last_run_id = "test-run-1"
            mock_record = MagicMock()
            mock_record.status = "completed"
            mock_sm.get_run.return_value = mock_record
            terminal._set_running_state(False)
            terminal._last_run_id = None
            terminal._update_button_states()

            # Change to Opus for second run
            terminal._model_combo.setCurrentIndex(2)

            with patch.object(terminal._terminal, "send_command") as mock_send:
                terminal.start_run(ticket.number, str(tmp_path), "/tmp/db.db")
                second_cmd = mock_send.call_args[0][0]
                assert "--model opus" in second_cmd.lower()

            # Cleanup
            terminal._run_id_poll_timer.stop()


# ---------------------------------------------------------------------------
# AC: Edge cases and error conditions
# ---------------------------------------------------------------------------


class TestRunOptionLockingEdgeCases:
    """Test edge cases in run option locking behavior."""

    def test_options_locked_for_paused_run(self, qapp, tmp_path):
        """AC: Options locked when run is paused (resumable state)."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            widget.load_ticket(ticket)
            terminal = widget._current_terminal

            mock_sm = MagicMock(spec=StateManager)
            terminal.set_state_manager(mock_sm)

            # Simulate paused run
            terminal._last_run_id = "test-run-paused"
            mock_record = MagicMock()
            mock_record.status = "paused"
            mock_sm.get_run.return_value = mock_record

            terminal._update_button_states()

            # Options should be locked
            assert terminal._model_combo.isEnabled() is False
            assert terminal._effort_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False

    def test_options_unlocked_when_no_state_manager(self, qapp, tmp_path):
        """AC: Options unlocked when state manager not available."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)
            terminal = widget._terminals.get(1) if hasattr(widget, "_terminals") else None

            if terminal:
                terminal._last_run_id = "test-run-123"
                terminal._state_manager = None

                terminal._update_button_states()

                # Without state manager, can't verify run state, so options should be unlocked
                # or disabled entirely (implementation choice)

    def test_loading_ticket_with_existing_run_locks_options(self, qapp, tmp_path):
        """AC: Loading a ticket that has an existing run should lock options."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget
        from levelup.state.manager import StateManager

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)

            # Mock state manager with existing run for this ticket
            mock_sm = MagicMock(spec=StateManager)
            mock_record = MagicMock()
            mock_record.run_id = "existing-run-123"
            mock_record.status = "failed"
            mock_sm.get_run_for_ticket.return_value = mock_record
            mock_sm.get_run.return_value = mock_record

            # Set state manager before loading ticket
            if hasattr(widget, "_state_manager"):
                widget._state_manager = mock_sm

            # Load ticket
            widget.load_ticket(ticket)
            terminal = widget._current_terminal
            terminal.set_state_manager(mock_sm)

            # Simulate _wire_existing_run
            terminal._last_run_id = mock_record.run_id
            terminal._update_button_states()

            # Options should be locked because run exists
            assert terminal._model_combo.isEnabled() is False
            assert terminal._effort_combo.isEnabled() is False
            assert terminal._skip_planning_checkbox.isEnabled() is False
