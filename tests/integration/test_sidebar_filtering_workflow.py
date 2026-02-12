"""Integration tests for sidebar filtering workflow.

This test suite covers the end-to-end workflow of filtering merged tickets
in the sidebar, including interaction with ticket selection, theme changes,
and run status updates.

Requirements:
- Filtering works correctly during normal ticket workflow
- Filter state persists during ticket updates
- Filtering interacts correctly with ticket selection
- Theme changes preserve filter state
- Run status colors work correctly with filtering
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from levelup.core.tickets import add_ticket, set_ticket_status, TicketStatus

pytestmark = pytest.mark.regression

def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestSidebarFilteringWorkflow:
    """Test complete filtering workflow in realistic scenarios."""

    def test_hide_merged_filter_updates_on_ticket_status_change(self, tmp_path):
        """When a ticket changes to merged status, it should be filtered from view."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.tickets import read_tickets
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.DONE)
        add_ticket(project_path, "Ticket 2")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Initially should show 2 tickets (done ticket is visible)
        window._refresh_tickets()
        assert window._sidebar._list.count() == 2

        # Change ticket 1 to merged status
        tickets = read_tickets(project_path)
        set_ticket_status(project_path, tickets[0].number, TicketStatus.MERGED)

        # Refresh tickets
        window._refresh_tickets()

        # Should now only show 1 ticket (merged is hidden)
        assert window._sidebar._list.count() == 1

        window.close()

    def test_show_merged_toggle_reveals_newly_merged_tickets(self, tmp_path):
        """When toggle is on, newly merged tickets should appear."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.core.tickets import read_tickets
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Ticket 1")
        set_ticket_status(project_path, 1, TicketStatus.DONE)
        add_ticket(project_path, "Ticket 2")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Enable show merged
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)

        window._refresh_tickets()
        assert window._sidebar._list.count() == 2

        # Change ticket 1 to merged status
        tickets = read_tickets(project_path)
        set_ticket_status(project_path, tickets[0].number, TicketStatus.MERGED)

        # Refresh tickets
        window._refresh_tickets()

        # Should still show 2 tickets (merged is visible because toggle is on)
        assert window._sidebar._list.count() == 2

        window.close()

    def test_filter_persists_during_ticket_creation(self, tmp_path):
        """Filter state should persist when creating new tickets."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Merged ticket")
        set_ticket_status(project_path, 1, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Merged ticket should be hidden by default
        window._refresh_tickets()
        assert window._sidebar._list.count() == 0

        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        assert checkbox.isChecked() is False

        # Create a new pending ticket
        add_ticket(project_path, "New ticket", "Description")

        # Refresh tickets
        window._refresh_tickets()

        # Should show 1 ticket (new pending ticket)
        assert window._sidebar._list.count() == 1

        # Filter should still be off
        assert checkbox.isChecked() is False

        window.close()

    def test_selecting_ticket_before_filtering_preserves_selection(self, tmp_path):
        """Selecting a non-merged ticket, then hiding merged should preserve selection."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)
        add_ticket(project_path, "Done")
        set_ticket_status(project_path, 3, TicketStatus.DONE)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Show merged tickets first
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        window._refresh_tickets()

        # Select the pending ticket (index 0)
        window._sidebar._list.setCurrentRow(0)
        selected_text = window._sidebar._list.currentItem().text()
        assert "Pending" in selected_text

        # Hide merged tickets
        checkbox.setChecked(False)

        # Selection should be preserved (pending is still visible)
        assert window._sidebar._list.currentRow() == 0
        selected_text = window._sidebar._list.currentItem().text()
        assert "Pending" in selected_text

        window.close()

    def test_selecting_merged_ticket_then_filtering_clears_selection(self, tmp_path):
        """Selecting a merged ticket, then hiding merged should clear selection."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Show merged tickets
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        window._refresh_tickets()

        # Select the merged ticket (index 1)
        window._sidebar._list.setCurrentRow(1)
        selected_text = window._sidebar._list.currentItem().text()
        assert "Merged" in selected_text

        # Hide merged tickets
        checkbox.setChecked(False)

        # Selection should be cleared (merged ticket is hidden)
        assert window._sidebar._list.currentRow() == -1

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringWithRunStatus:
    """Test filtering interaction with run status colors."""

    def test_filtering_preserves_run_status_colors(self, tmp_path):
        """Hiding merged tickets should preserve run status colors for visible tickets."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Running ticket")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Merged ticket")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up mock run for ticket 1
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="running",
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        window._refresh_tickets()

        # Should show 1 ticket (merged hidden)
        assert window._sidebar._list.count() == 1

        # Ticket should be blue (running status)
        item = window._sidebar._list.item(0)
        assert item.foreground().color().name().upper() == "#4A90D9"

        window.close()

    def test_showing_merged_applies_run_status_to_all_tickets(self, tmp_path):
        """Showing merged tickets should apply run status colors to all visible tickets."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.state.models import RunRecord
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Running")
        set_ticket_status(project_path, 1, TicketStatus.IN_PROGRESS)
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Set up mock run
        window._runs = [
            RunRecord(
                run_id="run1",
                task_title="Task 1",
                project_path=str(project_path),
                status="running",
                ticket_number=1,
                started_at="2024-01-01T00:00:00",
                updated_at="2024-01-01T00:00:00",
            ),
        ]

        # Show merged tickets
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        window._refresh_tickets()

        # Should show 2 tickets
        assert window._sidebar._list.count() == 2

        # First ticket should be blue (running)
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#4A90D9"

        # Second ticket should be gray (merged)
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#6C7086"

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringWithTheme:
    """Test filtering interaction with theme changes."""

    def test_theme_change_preserves_filter_state_on(self, tmp_path):
        """Changing theme should preserve filter state when show merged is on."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Show merged tickets
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        window._refresh_tickets()

        # Should show 2 tickets
        assert window._sidebar._list.count() == 2

        # Cycle theme
        window._cycle_theme()

        # Should still show 2 tickets
        assert window._sidebar._list.count() == 2
        assert checkbox.isChecked() is True

        window.close()

    def test_theme_change_preserves_filter_state_off(self, tmp_path):
        """Changing theme should preserve filter state when show merged is off."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Merged hidden by default
        window._refresh_tickets()
        assert window._sidebar._list.count() == 1

        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        assert checkbox.isChecked() is False

        # Cycle theme
        window._cycle_theme()

        # Should still show 1 ticket (merged still hidden)
        assert window._sidebar._list.count() == 1
        assert checkbox.isChecked() is False

        window.close()

    def test_filtered_tickets_use_correct_theme_colors_after_toggle(self, tmp_path):
        """After toggling filter, tickets should use correct theme colors."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Show merged tickets
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")
        checkbox.setChecked(True)
        window._refresh_tickets()

        # Check colors in dark theme
        assert window._sidebar._list.item(0).foreground().color().name().upper() == "#CDD6F4"  # Pending
        assert window._sidebar._list.item(1).foreground().color().name().upper() == "#6C7086"  # Merged

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestFilteringEdgeCases:
    """Test edge cases in filtering workflow."""

    def test_all_tickets_merged_empty_sidebar(self, tmp_path):
        """When all tickets are merged and filter is on, sidebar should be empty."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Merged 1")
        set_ticket_status(project_path, 1, TicketStatus.MERGED)
        add_ticket(project_path, "Merged 2")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        window._refresh_tickets()

        # Should show 0 tickets (all merged)
        assert window._sidebar._list.count() == 0

        window.close()

    def test_rapid_filter_toggling_maintains_consistency(self, tmp_path):
        """Rapidly toggling filter should maintain consistent state."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        add_ticket(project_path, "Pending")
        add_ticket(project_path, "Merged")
        set_ticket_status(project_path, 2, TicketStatus.MERGED)

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")

        # Rapid toggling
        for _ in range(10):
            checkbox.setChecked(True)
            checkbox.setChecked(False)

        window._refresh_tickets()

        # Should end in correct state (merged hidden)
        assert window._sidebar._list.count() == 1
        assert checkbox.isChecked() is False

        window.close()

    def test_filter_with_no_tickets_file(self, tmp_path):
        """Filter should work correctly even with no tickets file."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QCheckBox

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        # No tickets file created

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Should handle gracefully
        checkbox = window._sidebar.findChild(QCheckBox, "showMergedCheckbox")

        # Should not raise
        checkbox.setChecked(True)
        checkbox.setChecked(False)

        window.close()
