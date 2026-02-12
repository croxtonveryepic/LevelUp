"""Integration tests for ticket sidebar run status color flow.

These tests verify the complete integration from StateManager → MainWindow →
TicketSidebarWidget → color display, ensuring the entire pipeline works correctly.
"""

from __future__ import annotations

from pathlib import Path
import tempfile
from unittest.mock import patch
import time

import pytest

from levelup.core.tickets import add_ticket, set_ticket_status, TicketStatus


def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    """Ensure QApplication exists."""
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestEndToEndRunStatusColorFlow:
    """Test complete flow from DB to UI for run status colors."""

    def test_full_flow_new_run_updates_ticket_color(self, tmp_path):
        """Complete flow: Create run → Register in DB → Refresh UI → Verify color."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        # Setup
        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        # Create window
        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Initial refresh - no runs yet
        window._refresh()
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"  # Default

        # Create and register a new run
        ctx = PipelineContext(
            run_id="test_run",
            task=TaskInput(title="Test task"),
            project_path=str(project_path),
            ticket_number=1
        )
        ctx.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx)
        state_manager.update_run(ctx)

        # Refresh UI
        window._refresh()

        # Ticket should now be blue
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"

    def test_full_flow_run_status_transition(self, tmp_path):
        """Test ticket color updates as run status transitions."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Create run in "running" state
        ctx = PipelineContext(
            run_id="test_run",
            task=TaskInput(title="Test task"),
            project_path=str(project_path),
            ticket_number=1
        )
        ctx.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx)
        state_manager.update_run(ctx)

        window._refresh()
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"  # Blue

        # Transition to waiting_for_input
        ctx.status = PipelineStatus.WAITING_FOR_INPUT
        state_manager.update_run(ctx)

        window._refresh()
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"  # Yellow-orange

        # Transition to completed
        ctx.status = PipelineStatus.COMPLETED
        state_manager.update_run(ctx)

        window._refresh()
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"  # Back to default

    def test_full_flow_multiple_tickets_multiple_runs(self, tmp_path):
        """Test complete flow with multiple tickets and runs."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Running ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Waiting ticket")
        set_ticket_status(project_path, 2, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "No run ticket")
        set_ticket_status(project_path, 3, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Completed ticket")
        set_ticket_status(project_path, 4, TicketStatus.DONE)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Create multiple runs
        ctx1 = PipelineContext(run_id="run1", task="Task 1", project_path=str(project_path), ticket_number=1)
        ctx1.status = "running"
        state_manager.register_run(ctx1)
        state_manager.update_run(ctx1)

        ctx2 = PipelineContext(run_id="run2", task="Task 2", project_path=str(project_path), ticket_number=2)
        ctx2.status = "waiting_for_input"
        state_manager.register_run(ctx2)
        state_manager.update_run(ctx2)

        window._refresh()

        # Verify all colors
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"  # Running: blue
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#E6A817"  # Waiting: yellow-orange
        assert window._sidebar._list.item(2).foreground().color().name().upper() == "#E6A817"  # No run: default
        assert window._sidebar._list.item(3).foreground().color().name().upper() == "#2ECC71"  # Done: green

    def test_full_flow_theme_change_with_active_runs(self, tmp_path):
        """Test theme change preserves run status colors correctly."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus
        from PyQt6.QtWidgets import QApplication
        from levelup.gui.theme_manager import apply_theme

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Create running run
        ctx = PipelineContext(run_id="run1", task="Task", project_path=str(project_path), ticket_number=1)
        ctx.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx)
        state_manager.update_run(ctx)

        window._refresh()
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"  # Dark blue

        # Change to light theme
        app_instance = QApplication.instance()
        if app_instance:
            apply_theme(app_instance, "light")
        window._sidebar.update_theme("light")

        # Should be light theme blue
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#3498DB"  # Light blue

        # Change back to dark theme
        if app_instance:
            apply_theme(app_instance, "dark")
        window._sidebar.update_theme("dark")

        # Should be dark theme blue again
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestRefreshCycle:
    """Test the refresh cycle and timing."""

    def test_refresh_updates_run_status_mapping(self, tmp_path):
        """Each refresh should rebuild run status mapping from current runs."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # First refresh - no runs
        window._refresh()
        assert window._sidebar._run_status_map == {}

        # Create run
        ctx = PipelineContext(run_id="run1", task="Task", project_path=str(project_path), ticket_number=1)
        ctx.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx)
        state_manager.update_run(ctx)

        # Second refresh - should have run status
        window._refresh()
        assert window._sidebar._run_status_map == {1: "running"}

        # Update run status
        ctx.status = PipelineStatus.COMPLETED
        state_manager.update_run(ctx)

        # Third refresh - run status should be removed (completed not included)
        window._refresh()
        assert window._sidebar._run_status_map == {}

    def test_refresh_handles_stale_run_data(self, tmp_path):
        """Refresh should handle case where run data is stale."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Test ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Create run with ticket reference
        ctx = PipelineContext(run_id="run1", task="Task", project_path=str(project_path), ticket_number=99)
        ctx.status = PipelineStatus.RUNNING
        state_manager.register_run(ctx)
        state_manager.update_run(ctx)

        # Refresh - ticket 99 doesn't exist but shouldn't cause issues
        window._refresh()

        # Should have one ticket with default color
        assert window._sidebar._list.count() == 1
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMultiProjectScenarios:
    """Test scenarios with multiple projects."""

    def test_run_status_filtering_by_project(self, tmp_path):
        """Run status mapping should only include runs from current project."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        # Create two projects
        project1 = tmp_path / "project1"
        project1.mkdir()
        (project1 / "levelup").mkdir()
        add_ticket(project1, "Ticket 1")
        set_ticket_status(project1, 1, TicketStatus.IN_PROGRESS)

        project2 = tmp_path / "project2"
        project2.mkdir()
        (project2 / "levelup").mkdir()
        add_ticket(project2, "Ticket 1")
        set_ticket_status(project2, 1, TicketStatus.IN_PROGRESS)

        # Create runs for both projects
        ctx1 = PipelineContext(run_id="run1", task="Task 1", project_path=str(project1), ticket_number=1)
        ctx1.status = "running"
        state_manager.register_run(ctx1)
        state_manager.update_run(ctx1)

        ctx2 = PipelineContext(run_id="run2", task="Task 2", project_path=str(project2), ticket_number=1)
        ctx2.status = "waiting_for_input"
        state_manager.register_run(ctx2)
        state_manager.update_run(ctx2)

        # Create window for project1
        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window1 = MainWindow(state_manager, project_path=project1)

        window1._refresh()

        # Should only show run status from project1 (running = blue)
        assert window1._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Create window for project2
        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window2 = MainWindow(state_manager, project_path=project2)

        window2._refresh()

        # Should only show run status from project2 (waiting = yellow-orange)
        assert window2._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestErrorRecovery:
    """Test error recovery and resilience."""

    def test_refresh_continues_on_empty_ticket_db(self, tmp_path):
        """Refresh should handle empty ticket DB gracefully."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        # No tickets created -- empty DB

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Should not crash
        try:
            window._refresh()
        except Exception as e:
            pytest.fail(f"Refresh raised exception on empty ticket DB: {e}")

    def test_refresh_handles_no_levelup_dir(self, tmp_path):
        """Refresh should handle missing levelup directory gracefully."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        # Don't create levelup dir or any tickets

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Should not crash
        try:
            window._refresh()
        except Exception as e:
            pytest.fail(f"Refresh raised exception on missing levelup dir: {e}")

    def test_run_status_map_handles_invalid_ticket_numbers(self, tmp_path):
        """Run status mapping should handle invalid ticket numbers gracefully."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        add_ticket(project_path, "Ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Manually set runs with invalid ticket numbers
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task",
                project_path=str(project_path),
                status="running",
                ticket_number=-1,  # Invalid
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
            RunRecord(
                run_id="run2",
                task_title="Task",
                project_path=str(project_path),
                status="running",
                ticket_number=0,  # Invalid
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        # Should not crash
        try:
            window._refresh_tickets()
        except Exception as e:
            pytest.fail(f"_refresh_tickets raised exception on invalid ticket numbers: {e}")


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestPerformanceIntegration:
    """Integration tests for performance with realistic data volumes."""

    def test_refresh_performance_with_many_tickets_and_runs(self, tmp_path):
        """Refresh should be efficient with many tickets and runs."""
        app = _ensure_qapp()
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.context import PipelineContext, TaskInput, PipelineStatus

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()

        # Create 100 tickets
        for i in range(1, 101):
            add_ticket(project_path, f"Ticket {i}")
            set_ticket_status(project_path, i, TicketStatus.IN_PROGRESS)

        # Create 50 runs
        for i in range(1, 51):
            ctx = PipelineContext(
                run_id=f"run{i}",
                task=f"Task {i}",
                project_path=str(project_path),
                ticket_number=i
            )
            ctx.status = PipelineStatus.RUNNING if i % 2 == 0 else "waiting_for_input"
            state_manager.register_run(ctx)
            state_manager.update_run(ctx)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Measure refresh time
        start = time.time()
        window._refresh()
        elapsed = time.time() - start

        # Should complete in reasonable time
        assert elapsed < 2.0, f"Refresh took {elapsed:.2f}s with 100 tickets and 50 runs"

        # Verify some colors are correct
        assert window._sidebar._list.count() == 100
        # Even ticket numbers should be blue (running)
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#4A90D9"
        # Odd ticket numbers should be yellow-orange (waiting)
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#E6A817"
