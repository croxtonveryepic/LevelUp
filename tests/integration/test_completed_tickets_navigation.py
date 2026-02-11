"""Integration tests for completed tickets page navigation in MainWindow.

This test suite covers the integration of the completed tickets widget
into MainWindow's stacked widget and navigation flow.

Requirements:
- New button/menu item in MainWindow provides access to completed tickets page
- Completed tickets page is added to MainWindow's QStackedWidget
- Navigation to completed tickets page works correctly
- Back button returns to the main runs table view
- Clicking a ticket navigates to ticket detail view
- Theme changes propagate to completed tickets widget
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch
import tempfile
import pytest


def _can_import_pyqt6() -> bool:
    """Check if PyQt6 is available."""
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsPageIntegration:
    """Test integration of completed tickets page into MainWindow."""

    def test_completed_tickets_page_added_to_stack(self, tmp_path):
        """MainWindow should have completed tickets page in its stacked widget."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text(
            "## [done] Done ticket\n## [merged] Merged ticket\n"
        )

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Stacked widget should have at least 3 pages (0=runs, 1=detail, 2=docs, 3=completed)
        assert window._stack.count() >= 4

        window.close()

    def test_completed_tickets_button_exists(self, tmp_path):
        """MainWindow should have a button to access completed tickets page."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QPushButton

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## Test ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Find completed tickets button
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        assert completed_btn is not None

        window.close()

    def test_clicking_completed_button_shows_completed_page(self, tmp_path):
        """Clicking completed tickets button should show the completed tickets page."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QPushButton

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Initially should be on runs table (page 0)
        assert window._stack.currentIndex() == 0

        # Click completed tickets button
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Should switch to completed tickets page (assuming index 3)
        assert window._stack.currentIndex() >= 3

        window.close()

    def test_completed_page_back_button_returns_to_runs_table(self, tmp_path):
        """Clicking back button on completed page should return to runs table."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QPushButton

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Click back button
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        completed_widget = window.findChild(CompletedTicketsWidget)
        back_btn = completed_widget.findChild(QPushButton, "backBtn")
        back_btn.click()

        # Should return to runs table (page 0)
        assert window._stack.currentIndex() == 0

        window.close()

    def test_completed_page_clears_sidebar_selection(self, tmp_path):
        """Navigating to completed page should clear sidebar selection."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QPushButton

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text(
            "## Pending ticket\n## [done] Done ticket\n"
        )

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Select a ticket in sidebar
        window._sidebar._list.setCurrentRow(0)
        assert window._sidebar._list.currentRow() == 0

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Sidebar selection should be cleared
        assert window._sidebar._list.currentRow() == -1

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsFiltering:
    """Test that completed tickets page shows correct filtered tickets."""

    def test_completed_page_shows_only_done_and_merged(self, tmp_path):
        """Completed tickets page should only show done and merged tickets."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text(
            "## Pending ticket\n"
            "## [in progress] In progress ticket\n"
            "## [done] Done ticket\n"
            "## [merged] Merged ticket\n"
        )

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Get the completed tickets widget
        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)

        # Should show 2 tickets (done and merged)
        assert list_widget.count() == 2

        window.close()

    def test_completed_page_updates_on_ticket_refresh(self, tmp_path):
        """Completed tickets page should update when tickets are refreshed."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        tickets_file = project_path / "levelup" / "tickets.md"
        tickets_file.write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)

        # Should show 1 ticket
        assert list_widget.count() == 1

        # Add another completed ticket
        tickets_file.write_text("## [done] Done ticket\n## [merged] Merged ticket\n")

        # Trigger refresh
        window._refresh_tickets()

        # Should now show 2 tickets
        assert list_widget.count() == 2

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsNavigation:
    """Test navigation from completed tickets to ticket detail."""

    def test_clicking_ticket_navigates_to_detail(self, tmp_path):
        """Clicking a ticket in completed list should navigate to ticket detail."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Click a ticket
        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)
        list_widget.setCurrentRow(0)

        # Should navigate to ticket detail page (index 1)
        assert window._stack.currentIndex() == 1

        window.close()

    def test_detail_back_returns_to_runs_not_completed(self, tmp_path):
        """After viewing ticket from completed page, back should return to runs table."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Click a ticket to go to detail
        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)
        list_widget.setCurrentRow(0)

        # Now on detail page (index 1)
        assert window._stack.currentIndex() == 1

        # Click back on detail page
        back_btn = window._detail.findChild(QPushButton, "backBtn")
        back_btn.click()

        # Should return to runs table (index 0), not completed page
        assert window._stack.currentIndex() == 0

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsThemeIntegration:
    """Test theme support integration for completed tickets page."""

    def test_completed_page_receives_initial_theme(self, tmp_path):
        """Completed tickets page should receive initial theme from MainWindow."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Completed widget should exist
        completed_widget = window.findChild(CompletedTicketsWidget)
        assert completed_widget is not None

        # Should have a theme set
        assert hasattr(completed_widget, "_theme")

        window.close()

    def test_theme_change_propagates_to_completed_page(self, tmp_path):
        """Changing theme in MainWindow should propagate to completed tickets page."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from levelup.core.tickets import Ticket, TicketStatus
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)
        item = list_widget.item(0)
        dark_color = item.foreground().color().name().upper()

        # Cycle theme (should trigger update_theme on all widgets)
        window._cycle_theme()

        # Color should change
        item = list_widget.item(0)
        new_color = item.foreground().color().name().upper()

        # Colors should be different (theme changed)
        assert dark_color != new_color or window._current_theme == "dark"

        window.close()


@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestCompletedTicketsEdgeCases:
    """Test edge cases for completed tickets page integration."""

    def test_completed_page_with_no_project_path(self):
        """MainWindow without project path should still create completed page."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            state_manager = StateManager(db_path)

            with patch.object(MainWindow, "_start_refresh_timer"), \
                 patch.object(MainWindow, "_refresh"):
                window = MainWindow(state_manager, project_path=None)

            # Completed page should still exist in stack
            assert window._stack.count() >= 4

            window.close()

    def test_completed_page_with_empty_tickets_file(self, tmp_path):
        """Completed page should handle empty tickets file gracefully."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
        from PyQt6.QtWidgets import QApplication, QPushButton, QListWidget

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        # Navigate to completed tickets page
        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")
        completed_btn.click()

        # Should show empty list without error
        completed_widget = window.findChild(CompletedTicketsWidget)
        list_widget = completed_widget.findChild(QListWidget)
        assert list_widget.count() == 0

        window.close()

    def test_rapid_navigation_between_pages(self, tmp_path):
        """Rapidly navigating between pages should work correctly."""
        from levelup.gui.main_window import MainWindow
        from levelup.state.manager import StateManager
        from PyQt6.QtWidgets import QApplication, QPushButton

        app = QApplication.instance() or QApplication([])

        db_path = tmp_path / "test.db"
        state_manager = StateManager(db_path)

        project_path = tmp_path / "project"
        project_path.mkdir()
        (project_path / "levelup").mkdir()
        (project_path / "levelup" / "tickets.md").write_text("## [done] Done ticket\n")

        with patch.object(MainWindow, "_start_refresh_timer"), \
             patch.object(MainWindow, "_refresh"):
            window = MainWindow(state_manager, project_path=project_path)

        completed_btn = window.findChild(QPushButton, "completedTicketsBtn")

        # Rapidly navigate
        for _ in range(5):
            completed_btn.click()  # Go to completed
            assert window._stack.currentIndex() >= 3

            from levelup.gui.completed_tickets_widget import CompletedTicketsWidget
            completed_widget = window.findChild(CompletedTicketsWidget)
            back_btn = completed_widget.findChild(QPushButton, "backBtn")
            back_btn.click()  # Go back to runs
            assert window._stack.currentIndex() == 0

        window.close()
