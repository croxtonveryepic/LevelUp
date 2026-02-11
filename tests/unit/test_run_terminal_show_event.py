"""Tests specifically for RunTerminalWidget.showEvent behavior.

This module contains focused tests on the showEvent method to ensure that
the automatic shell initialization has been properly removed and that the
widget can be shown without starting a PTY process.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch, call

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
class TestRunTerminalShowEvent:
    """Test showEvent method behavior."""

    @pytest.fixture(autouse=True)
    def _setup(self):
        """Setup QApplication for PyQt6 tests."""
        from PyQt6.QtWidgets import QApplication
        self._app = QApplication.instance() or QApplication([])

    def _make_widget(self):
        """Create a RunTerminalWidget with the embedded terminal's PtyBackend mocked."""
        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            from levelup.gui.run_terminal import RunTerminalWidget
            widget = RunTerminalWidget()
        return widget

    # -------------------------------------------------------------------------
    # Core showEvent behavior tests
    # -------------------------------------------------------------------------

    def test_show_event_exists(self):
        """Verify showEvent method exists and can be called."""
        widget = self._make_widget()

        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()

        # Should not raise
        widget.showEvent(event)

    def test_show_event_does_not_call_ensure_shell(self):
        """CRITICAL: Verify showEvent does NOT call _ensure_shell."""
        widget = self._make_widget()

        # Spy on _ensure_shell
        with patch.object(widget, "_ensure_shell", wraps=widget._ensure_shell) as mock_ensure:
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # This is the critical test - _ensure_shell must NOT be called
            mock_ensure.assert_not_called()

    def test_show_event_does_not_start_pty(self):
        """Verify showEvent does not start the PTY backend."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # PTY must not be started
            mock_start.assert_not_called()

    def test_show_event_does_not_modify_shell_started_flag(self):
        """Verify showEvent does not change _shell_started flag."""
        widget = self._make_widget()

        # Record initial state
        initial_state = widget._shell_started
        assert initial_state is False

        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()
        widget.showEvent(event)

        # Should remain unchanged
        assert widget._shell_started is initial_state

    def test_show_event_calls_super(self):
        """Verify showEvent properly calls super().showEvent()."""
        widget = self._make_widget()

        # Mock the parent class's showEvent
        with patch("PyQt6.QtWidgets.QWidget.showEvent") as mock_super:
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # Should have called parent's showEvent
            mock_super.assert_called_once()

    # -------------------------------------------------------------------------
    # Multiple show event tests
    # -------------------------------------------------------------------------

    def test_multiple_show_events_remain_safe(self):
        """Verify multiple showEvent calls don't cause issues."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            from PyQt6.QtGui import QShowEvent

            # Call showEvent multiple times
            for i in range(10):
                event = QShowEvent()
                widget.showEvent(event)

            # Should never start shell
            mock_start.assert_not_called()
            assert widget._shell_started is False

    def test_show_hide_show_pattern(self):
        """Verify show-hide-show pattern doesn't start shell."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            from PyQt6.QtGui import QShowEvent, QHideEvent

            # Show
            show_event = QShowEvent()
            widget.showEvent(show_event)

            # Hide
            hide_event = QHideEvent()
            widget.hideEvent(hide_event)

            # Show again
            widget.showEvent(show_event)

            # Should never start shell
            mock_start.assert_not_called()
            assert widget._shell_started is False

    # -------------------------------------------------------------------------
    # Integration with widget lifecycle
    # -------------------------------------------------------------------------

    def test_show_then_run_starts_shell_once(self):
        """Verify show followed by run starts shell exactly once."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # Show the widget first
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)
            assert mock_start.call_count == 0

            # Then run
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1

    def test_run_then_show_starts_shell_once(self):
        """Verify run followed by show starts shell exactly once."""
        widget = self._make_widget()

        with patch.object(widget._terminal, "start_shell") as mock_start, \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):

            # Run first
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")
            assert mock_start.call_count == 1

            # Then show
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)
            # Should not start again
            assert mock_start.call_count == 1

    def test_show_does_not_interfere_with_state_tracking(self):
        """Verify showEvent doesn't interfere with command state tracking."""
        widget = self._make_widget()

        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()

        # Initial state
        assert widget._command_running is False

        # Show
        widget.showEvent(event)
        assert widget._command_running is False

        # Start a run
        with patch.object(widget._terminal, "start_shell"), \
             patch.object(widget._terminal, "send_command"), \
             patch.object(widget._terminal, "setFocus"):
            widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

        assert widget._command_running is True

        # Show again during run
        widget.showEvent(event)
        assert widget._command_running is True

    # -------------------------------------------------------------------------
    # Widget visibility state tests
    # -------------------------------------------------------------------------

    def test_hidden_widget_show_does_not_start_shell(self):
        """Verify making a hidden widget visible doesn't start shell."""
        widget = self._make_widget()

        # Start hidden
        widget.hide()
        assert not widget.isVisible()

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Make visible
            widget.show()

            # Process events to ensure showEvent is triggered
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            # Should not start shell
            mock_start.assert_not_called()

    def test_widget_added_to_layout_does_not_start_shell(self):
        """Verify adding widget to a layout doesn't start shell."""
        widget = self._make_widget()

        from PyQt6.QtWidgets import QVBoxLayout, QWidget
        container = QWidget()
        layout = QVBoxLayout(container)

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Add to layout
            layout.addWidget(widget)
            container.show()

            # Process events
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            # Should not start shell
            mock_start.assert_not_called()

    def test_widget_in_stacked_widget_does_not_start_shell(self):
        """Verify widget in QStackedWidget being shown doesn't start shell."""
        widget = self._make_widget()

        from PyQt6.QtWidgets import QStackedWidget, QWidget
        stack = QStackedWidget()
        stack.addWidget(QWidget())  # Add another widget first
        stack.addWidget(widget)

        with patch.object(widget._terminal, "start_shell") as mock_start:
            # Show the stacked widget
            stack.show()

            # Switch to our widget
            stack.setCurrentWidget(widget)

            # Process events
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()

            # Should not start shell
            mock_start.assert_not_called()

    # -------------------------------------------------------------------------
    # Edge cases and error conditions
    # -------------------------------------------------------------------------

    def test_show_event_with_none_project_path(self):
        """Verify showEvent works safely even without project path set."""
        widget = self._make_widget()
        widget._project_path = None

        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()

        # Should not raise
        widget.showEvent(event)
        assert widget._shell_started is False

    def test_show_event_after_terminal_created(self):
        """Verify showEvent is safe after terminal widget is created."""
        widget = self._make_widget()

        # Ensure terminal widget exists
        assert widget._terminal is not None

        with patch.object(widget._terminal, "start_shell") as mock_start:
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            mock_start.assert_not_called()

    def test_show_event_before_context_set(self):
        """Verify showEvent is safe before context is set."""
        widget = self._make_widget()

        # Don't set context
        assert widget._project_path is None
        assert widget._db_path is None

        from PyQt6.QtGui import QShowEvent
        event = QShowEvent()

        # Should not raise
        widget.showEvent(event)
        assert widget._shell_started is False

    # -------------------------------------------------------------------------
    # Comparison with old behavior (what we're fixing)
    # -------------------------------------------------------------------------

    def test_old_behavior_would_have_started_shell(self):
        """Document what the OLD behavior was (for regression testing).

        This test documents that in the OLD code, showEvent would call
        _ensure_shell, which would start the PTY. This test verifies that
        this NO LONGER happens.
        """
        widget = self._make_widget()

        # In the old code, this sequence would have started the shell:
        # 1. Widget is created
        # 2. showEvent is triggered (e.g., by selecting a ticket)
        # 3. _ensure_shell is called from showEvent
        # 4. PTY is started

        with patch.object(widget._terminal, "start_shell") as mock_start:
            from PyQt6.QtGui import QShowEvent
            event = QShowEvent()
            widget.showEvent(event)

            # NEW behavior: shell should NOT be started
            mock_start.assert_not_called()
            assert widget._shell_started is False

            # Only when we explicitly run should shell start
            with patch.object(widget._terminal, "send_command"), \
                 patch.object(widget._terminal, "setFocus"):
                widget.start_run(ticket_number=1, project_path="/p", db_path="/d")

                # NOW the shell is started
                assert mock_start.call_count == 1
                assert widget._shell_started is True

    def test_showEvent_implementation_matches_requirement(self):
        """Verify the actual showEvent implementation matches requirements.

        This test reads the actual implementation to verify the fix is correct.
        """
        from levelup.gui.run_terminal import RunTerminalWidget
        import inspect

        # Get the source code of showEvent
        source = inspect.getsource(RunTerminalWidget.showEvent)

        # Verify it does NOT call _ensure_shell
        # (This is a code inspection test - it checks the implementation)
        assert "_ensure_shell" not in source, \
            "showEvent implementation should not call _ensure_shell"

        # Verify it DOES call super
        assert "super()" in source or "super(" in source, \
            "showEvent should call super().showEvent()"
