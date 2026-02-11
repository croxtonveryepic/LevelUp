"""Comprehensive tests for RunTerminalWidget button state logic.

This test suite covers the requirements for fixing the run and resume button
state logic, specifically:
1. Fix resume button enabled state to properly check for resumable runs
2. Disable run button when a resumable run exists
3. Update _set_running_state() to respect resumable run state
4. Update _update_button_states() to properly check for resumable runs

Tests follow TDD approach - these tests SHOULD FAIL initially until the
implementation is fixed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestResumeButtonState:
    """Test resume button enabled state logic.

    AC: Resume button is enabled when not running AND there is a run with
    status 'failed', 'aborted', or 'paused'
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_resume_enabled_when_not_running_and_run_failed(self):
        """Resume button should be enabled when not running and run status is 'failed'."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call _set_running_state to update button states
        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is True

    def test_resume_enabled_when_not_running_and_run_aborted(self):
        """Resume button should be enabled when not running and run status is 'aborted'."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-456"

        # Mock state manager with aborted run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is True

    def test_resume_enabled_when_not_running_and_run_paused(self):
        """Resume button should be enabled when not running and run status is 'paused'."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-789"

        # Mock state manager with paused run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is True

    def test_resume_disabled_when_no_run_exists(self):
        """Resume button should be disabled when no run exists."""
        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = None

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False

    def test_resume_disabled_when_run_not_resumable(self):
        """Resume button should be disabled when run is not in a resumable state."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-999"

        # Mock state manager with completed run (not resumable)
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False

    def test_resume_disabled_while_running(self):
        """Resume button should be disabled while a pipeline is actively running."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = True
        widget._last_run_id = "test-run-123"

        # Mock state manager with failed run (resumable)
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(True)

        assert widget._resume_btn.isEnabled() is False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestRunButtonDisabledWhenResumable:
    """Test that run button is disabled when a resumable run exists.

    AC: Run button is disabled when there is an existing run with status
    'failed', 'aborted', or 'paused'
    AC: User must either resume or forget the existing run before starting a new run
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_run_disabled_when_failed_run_exists(self):
        """Run button should be disabled when a failed run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call _set_running_state to transition to not-running
        widget._set_running_state(False)

        # Run button should be disabled because a resumable run exists
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled"
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled when resumable run exists"

    def test_run_disabled_when_aborted_run_exists(self):
        """Run button should be disabled when an aborted run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-456"
        widget._ticket_number = 3
        widget._project_path = "/some/project"

        # Mock state manager with aborted run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled"
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled when resumable run exists"

    def test_run_disabled_when_paused_run_exists(self):
        """Run button should be disabled when a paused run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-789"
        widget._ticket_number = 7
        widget._project_path = "/some/project"

        # Mock state manager with paused run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled"
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled when resumable run exists"

    def test_run_enabled_when_no_resumable_run_exists(self):
        """Run button should be enabled when no resumable run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-999"
        widget._ticket_number = 2
        widget._project_path = "/some/project"

        # Mock state manager with completed run (not resumable)
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled"
        assert widget._run_btn.isEnabled() is True, "Run button should be enabled when no resumable run"

    def test_run_enabled_after_forgetting_resumable_run(self):
        """Run button should be enabled after forgetting a resumable run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 4
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        mock_sm.delete_run.return_value = None
        widget.set_state_manager(mock_sm)

        # Initially, run button should be disabled
        widget._set_running_state(False)
        assert widget._run_btn.isEnabled() is False

        # Forget the run (simulating _on_forget_clicked)
        widget._last_run_id = None
        widget._update_button_states()

        # Now run button should be enabled
        assert widget._run_btn.isEnabled() is True

    def test_run_disabled_while_running(self):
        """Run button should be disabled while a pipeline is actively running."""
        widget = self._make_widget()
        widget._command_running = True

        widget._set_running_state(True)

        assert widget._run_btn.isEnabled() is False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestSetRunningStateRespectsResumable:
    """Test that _set_running_state() respects resumable run state.

    AC: _set_running_state() should call _is_resumable() when determining run button state
    AC: _set_running_state() should not unconditionally enable the run button
    AC: When transitioning to not-running state, run button should remain disabled
        if a resumable run exists
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_set_running_state_false_checks_resumable(self):
        """When _set_running_state(False) is called, it should check for resumable runs."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Transition from running to not-running
        widget._command_running = True
        widget._set_running_state(False)

        # Verify _is_resumable() was checked by verifying button states
        assert widget._resume_btn.isEnabled() is True
        assert widget._run_btn.isEnabled() is False, "Run button should be disabled when resumable run exists"

    def test_set_running_state_false_does_not_unconditionally_enable_run(self):
        """_set_running_state(False) should NOT unconditionally enable run button."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-456"
        widget._ticket_number = 3
        widget._project_path = "/some/project"

        # Mock state manager with paused run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call _set_running_state(False) with a resumable run
        widget._set_running_state(False)

        # The current buggy implementation sets _run_btn.setEnabled(not running)
        # which would be True. The fixed version should check _is_resumable() and be False
        assert widget._run_btn.isEnabled() is False, "Run button should NOT be unconditionally enabled"

    def test_set_running_state_true_disables_run_button(self):
        """_set_running_state(True) should disable the run button regardless of resumable state."""
        widget = self._make_widget()

        widget._set_running_state(True)

        assert widget._run_btn.isEnabled() is False
        assert widget._command_running is True

    def test_transition_to_not_running_with_resumable_keeps_run_disabled(self):
        """Transitioning to not-running with resumable run should keep run button disabled."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-789"
        widget._ticket_number = 7
        widget._project_path = "/some/project"

        # Mock state manager with aborted run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Start from running state
        widget._command_running = True
        widget._set_running_state(True)
        assert widget._run_btn.isEnabled() is False

        # Transition to not-running
        widget._set_running_state(False)

        # Run button should STILL be disabled because of resumable run
        assert widget._run_btn.isEnabled() is False
        assert widget._resume_btn.isEnabled() is True


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestUpdateButtonStatesRespectsResumable:
    """Test that _update_button_states() properly checks for resumable runs.

    AC: _update_button_states() should disable the run button when _is_resumable() returns True
    AC: _update_button_states() should only enable the run button when:
        - not running AND
        - has ticket/project AND
        - no resumable run exists
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_update_button_states_disables_run_when_resumable(self):
        """_update_button_states() should disable run button when a resumable run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False, "Run button should be disabled"
        assert widget._resume_btn.isEnabled() is True, "Resume button should be enabled"

    def test_update_button_states_enables_run_when_no_resumable(self):
        """_update_button_states() should enable run button when no resumable run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-999"
        widget._ticket_number = 2
        widget._project_path = "/some/project"

        # Mock state manager with completed run (not resumable)
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is True, "Run button should be enabled"
        assert widget._resume_btn.isEnabled() is False, "Resume button should be disabled"

    def test_update_button_states_disables_run_when_no_ticket(self):
        """_update_button_states() should disable run button when no ticket exists."""
        widget = self._make_widget()
        widget._command_running = False
        widget._ticket_number = None
        widget._project_path = "/some/project"

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False

    def test_update_button_states_disables_run_when_no_project(self):
        """_update_button_states() should disable run button when no project path exists."""
        widget = self._make_widget()
        widget._command_running = False
        widget._ticket_number = 5
        widget._project_path = None

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False

    def test_update_button_states_disables_run_when_running(self):
        """_update_button_states() should disable run button when pipeline is running."""
        widget = self._make_widget()
        widget._command_running = True
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        widget._update_button_states()

        assert widget._run_btn.isEnabled() is False

    def test_update_button_states_checks_all_conditions(self):
        """_update_button_states() should only enable run when ALL conditions met."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._ticket_number = 5
        widget._project_path = "/some/project"
        widget._last_run_id = None  # No previous run

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        widget._update_button_states()

        # All conditions met: not running, has ticket, has project, no resumable run
        assert widget._run_btn.isEnabled() is True


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestEnableRunRespectsResumable:
    """Test that enable_run() method respects resumable run state.

    AC: enable_run() should NOT unconditionally set button state
    AC: When a resumable run exists, enable_run(True) should NOT enable the button
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_enable_run_does_not_enable_when_resumable_exists(self):
        """enable_run(True) should NOT enable button when a resumable run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Try to enable the run button
        widget.enable_run(True)

        # Should remain disabled because resumable run exists
        assert widget._run_btn.isEnabled() is False

    def test_enable_run_enables_when_no_resumable_exists(self):
        """enable_run(True) should enable button when no resumable run exists."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = None

        # Mock state manager
        mock_sm = MagicMock(spec=StateManager)
        widget.set_state_manager(mock_sm)

        # Enable the run button
        widget.enable_run(True)

        # Should be enabled since no resumable run exists
        assert widget._run_btn.isEnabled() is True

    def test_enable_run_disables_always_works(self):
        """enable_run(False) should always disable the button."""
        widget = self._make_widget()
        widget._command_running = False

        # First enable it
        widget._run_btn.setEnabled(True)
        assert widget._run_btn.isEnabled() is True

        # Then disable it
        widget.enable_run(False)

        assert widget._run_btn.isEnabled() is False

    def test_enable_run_noop_when_running(self):
        """enable_run() should be no-op when pipeline is running."""
        widget = self._make_widget()
        widget._command_running = True
        widget._run_btn.setEnabled(False)

        # Try to enable
        widget.enable_run(True)

        # Should remain disabled because running
        assert widget._run_btn.isEnabled() is False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestButtonStateConsistency:
    """Test that button states are consistent across both state management methods.

    AC: All button states should be consistent across both _set_running_state()
        and _update_button_states() methods
    """

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_consistent_states_when_resumable_run_exists(self):
        """Both methods should produce consistent button states with resumable run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with failed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call _set_running_state
        widget._set_running_state(False)
        run_enabled_1 = widget._run_btn.isEnabled()
        resume_enabled_1 = widget._resume_btn.isEnabled()

        # Call _update_button_states
        widget._update_button_states()
        run_enabled_2 = widget._run_btn.isEnabled()
        resume_enabled_2 = widget._resume_btn.isEnabled()

        # States should be consistent
        assert run_enabled_1 == run_enabled_2, "Run button state should be consistent"
        assert resume_enabled_1 == resume_enabled_2, "Resume button state should be consistent"

        # Both should be: run disabled, resume enabled
        assert run_enabled_1 is False
        assert resume_enabled_1 is True

    def test_consistent_states_when_no_resumable_run(self):
        """Both methods should produce consistent button states without resumable run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-999"
        widget._ticket_number = 2
        widget._project_path = "/some/project"

        # Mock state manager with completed run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        # Call _set_running_state
        widget._set_running_state(False)
        run_enabled_1 = widget._run_btn.isEnabled()
        resume_enabled_1 = widget._resume_btn.isEnabled()

        # Call _update_button_states
        widget._update_button_states()
        run_enabled_2 = widget._run_btn.isEnabled()
        resume_enabled_2 = widget._resume_btn.isEnabled()

        # States should be consistent
        assert run_enabled_1 == run_enabled_2, "Run button state should be consistent"
        assert resume_enabled_1 == resume_enabled_2, "Resume button state should be consistent"

        # Both should be: run enabled, resume disabled
        assert run_enabled_1 is True
        assert resume_enabled_1 is False

    def test_consistent_states_when_running(self):
        """Both methods should produce consistent button states when running."""
        widget = self._make_widget()
        widget._command_running = True
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Call _set_running_state
        widget._set_running_state(True)
        run_enabled_1 = widget._run_btn.isEnabled()
        resume_enabled_1 = widget._resume_btn.isEnabled()
        terminate_enabled_1 = widget._terminate_btn.isEnabled()
        pause_enabled_1 = widget._pause_btn.isEnabled()

        # Call _update_button_states
        widget._update_button_states()
        run_enabled_2 = widget._run_btn.isEnabled()
        resume_enabled_2 = widget._resume_btn.isEnabled()
        terminate_enabled_2 = widget._terminate_btn.isEnabled()
        pause_enabled_2 = widget._pause_btn.isEnabled()

        # States should be consistent
        assert run_enabled_1 == run_enabled_2
        assert resume_enabled_1 == resume_enabled_2
        assert terminate_enabled_1 == terminate_enabled_2
        assert pause_enabled_1 == pause_enabled_2

        # All should show running state
        assert run_enabled_1 is False
        assert resume_enabled_1 is False
        assert terminate_enabled_1 is True
        assert pause_enabled_1 is True


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions for button state logic."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_no_state_manager_disables_resume(self):
        """Resume button should be disabled when no state manager is set."""
        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"

        # No state manager set
        widget._state_manager = None

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False

    def test_state_manager_returns_none_disables_resume(self):
        """Resume button should be disabled when state manager returns None for run."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"

        # Mock state manager that returns None (run not found)
        mock_sm = MagicMock(spec=StateManager)
        mock_sm.get_run.return_value = None
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False

    def test_run_status_pending_not_resumable(self):
        """Run with status 'pending' should not be resumable."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with pending run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "pending"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False
        assert widget._run_btn.isEnabled() is True

    def test_run_status_running_not_resumable(self):
        """Run with status 'running' should not be resumable."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-456"
        widget._ticket_number = 5
        widget._project_path = "/some/project"

        # Mock state manager with running run
        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "running"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        widget._set_running_state(False)

        assert widget._resume_btn.isEnabled() is False
        assert widget._run_btn.isEnabled() is True

    def test_forget_button_enabled_when_run_exists_and_not_running(self):
        """Forget button should be enabled when a run exists and not running."""
        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = "test-run-123"

        widget._set_running_state(False)

        assert widget._forget_btn.isEnabled() is True

    def test_forget_button_disabled_when_no_run(self):
        """Forget button should be disabled when no run exists."""
        widget = self._make_widget()
        widget._command_running = False
        widget._last_run_id = None

        widget._set_running_state(False)

        assert widget._forget_btn.isEnabled() is False

    def test_forget_button_disabled_when_running(self):
        """Forget button should be disabled when pipeline is running."""
        widget = self._make_widget()
        widget._command_running = True
        widget._last_run_id = "test-run-123"

        widget._set_running_state(True)

        assert widget._forget_btn.isEnabled() is False


@pytest.mark.skipif(
    not _can_import_pyqt6(),
    reason="PyQt6 not available",
)
class TestIsResumableMethod:
    """Test the _is_resumable() method directly."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with mocked TerminalEmulatorWidget."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    def test_is_resumable_returns_true_for_failed(self):
        """_is_resumable() should return True for failed status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-123"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "failed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is True

    def test_is_resumable_returns_true_for_aborted(self):
        """_is_resumable() should return True for aborted status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-456"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "aborted"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is True

    def test_is_resumable_returns_true_for_paused(self):
        """_is_resumable() should return True for paused status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-789"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "paused"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is True

    def test_is_resumable_returns_false_for_completed(self):
        """_is_resumable() should return False for completed status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-999"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "completed"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is False

    def test_is_resumable_returns_false_for_running(self):
        """_is_resumable() should return False for running status."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-111"

        mock_sm = MagicMock(spec=StateManager)
        mock_record = MagicMock()
        mock_record.status = "running"
        mock_sm.get_run.return_value = mock_record
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is False

    def test_is_resumable_returns_false_when_no_run_id(self):
        """_is_resumable() should return False when no run_id exists."""
        widget = self._make_widget()
        widget._last_run_id = None

        assert widget._is_resumable() is False

    def test_is_resumable_returns_false_when_no_state_manager(self):
        """_is_resumable() should return False when no state manager exists."""
        widget = self._make_widget()
        widget._last_run_id = "test-run-123"
        widget._state_manager = None

        assert widget._is_resumable() is False

    def test_is_resumable_returns_false_when_run_not_found(self):
        """_is_resumable() should return False when run is not found in DB."""
        from levelup.state.manager import StateManager

        widget = self._make_widget()
        widget._last_run_id = "test-run-deleted"

        mock_sm = MagicMock(spec=StateManager)
        mock_sm.get_run.return_value = None
        widget.set_state_manager(mock_sm)

        assert widget._is_resumable() is False
