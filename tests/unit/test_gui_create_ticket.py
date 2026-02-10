"""Tests for the create-ticket flow in the GUI (sidebar -> detail -> main window)."""

from __future__ import annotations

from pathlib import Path

import pytest


def _can_import_pyqt6() -> bool:
    try:
        import PyQt6  # noqa: F401
        return True
    except ImportError:
        return False


def _ensure_qapp():
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _make_state_manager(tmp_path: Path):
    """Create a real StateManager backed by a temp DB."""
    from levelup.state.manager import StateManager
    db_path = tmp_path / "test_state.db"
    return StateManager(db_path=db_path)


def _make_main_window(state_manager, project_path=None):
    """Build a MainWindow with timer and refresh patched out."""
    from unittest.mock import patch as _patch
    from levelup.gui.main_window import MainWindow

    with _patch.object(MainWindow, "_start_refresh_timer"), \
         _patch.object(MainWindow, "_refresh"):
        win = MainWindow(state_manager, project_path=project_path)
    return win


# ---------------------------------------------------------------------------
# TestTicketSidebarSignals
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketSidebarSignals:
    """Verify the plus button exists and its signal fires correctly."""

    def test_plus_button_exists(self):
        app = _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        sidebar = TicketSidebarWidget()
        btn = sidebar.findChild(QPushButton, "addTicketBtn")
        assert btn is not None
        assert btn.text() == "+"

    def test_click_emits_signal(self):
        app = _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        sidebar = TicketSidebarWidget()
        received = []
        sidebar.create_ticket_clicked.connect(lambda: received.append(True))

        btn = sidebar.findChild(QPushButton, "addTicketBtn")
        assert btn is not None
        btn.click()

        assert len(received) == 1

    def test_signal_with_empty_list(self):
        app = _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget

        sidebar = TicketSidebarWidget()
        received = []
        sidebar.create_ticket_clicked.connect(lambda: received.append(True))

        btn = sidebar.findChild(QPushButton, "addTicketBtn")
        btn.click()
        assert len(received) == 1

    def test_signal_after_set_tickets(self):
        app = _ensure_qapp()
        from PyQt6.QtWidgets import QPushButton
        from levelup.gui.ticket_sidebar import TicketSidebarWidget
        from levelup.core.tickets import Ticket, TicketStatus

        sidebar = TicketSidebarWidget()
        sidebar.set_tickets([
            Ticket(number=1, title="First", status=TicketStatus.PENDING),
            Ticket(number=2, title="Second", status=TicketStatus.IN_PROGRESS),
        ])

        received = []
        sidebar.create_ticket_clicked.connect(lambda: received.append(True))

        btn = sidebar.findChild(QPushButton, "addTicketBtn")
        btn.click()
        assert len(received) == 1


# ---------------------------------------------------------------------------
# TestTicketDetailCreateMode
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestTicketDetailCreateMode:
    """Verify create-mode behaviour on the detail widget."""

    def _make_detail(self):
        from levelup.gui.ticket_detail import TicketDetailWidget
        return TicketDetailWidget()

    def test_set_create_mode_state(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        assert detail._create_mode is True
        assert detail._title_edit.text() == ""
        assert detail._desc_edit.toPlainText() == ""
        assert detail._save_btn.isEnabled() is False
        assert detail._dirty is False

    def test_typing_title_enables_save(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        detail._title_edit.setText("X")
        assert detail._save_btn.isEnabled() is True
        assert detail._dirty is True

    def test_typing_description_enables_save(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        detail._desc_edit.setPlainText("Some description")
        assert detail._save_btn.isEnabled() is True
        assert detail._dirty is True

    def test_save_emits_ticket_created(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        received = []
        detail.ticket_created.connect(lambda t, d: received.append((t, d)))

        detail._title_edit.setText("New Feature")
        detail._desc_edit.setPlainText("Details here")
        detail._on_save()

        assert len(received) == 1
        assert received[0] == ("New Feature", "Details here")

    def test_save_empty_title_blocked(self):
        app = _ensure_qapp()
        from unittest.mock import patch as _patch

        detail = self._make_detail()
        detail.set_create_mode()

        received = []
        detail.ticket_created.connect(lambda t, d: received.append((t, d)))

        # Leave title empty, type description
        detail._desc_edit.setPlainText("Body only")

        with _patch("levelup.gui.ticket_detail.QMessageBox.warning") as mock_warn:
            detail._on_save()

        assert len(received) == 0
        mock_warn.assert_called_once()

    def test_save_strips_whitespace(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        received = []
        detail.ticket_created.connect(lambda t, d: received.append((t, d)))

        detail._title_edit.setText("  Foo  ")
        detail._on_save()

        assert received[0][0] == "Foo"

    def test_cancel_not_dirty_emits_back(self):
        app = _ensure_qapp()
        detail = self._make_detail()
        detail.set_create_mode()

        received = []
        detail.back_clicked.connect(lambda: received.append(True))

        detail._on_cancel()
        assert len(received) == 1
        assert detail._create_mode is False

    def test_cancel_dirty_confirmed(self):
        app = _ensure_qapp()
        from unittest.mock import patch as _patch

        detail = self._make_detail()
        detail.set_create_mode()
        detail._title_edit.setText("Draft")  # makes it dirty

        received = []
        detail.back_clicked.connect(lambda: received.append(True))

        from PyQt6.QtWidgets import QMessageBox as _QMB
        with _patch("levelup.gui.ticket_detail.QMessageBox.question",
                     return_value=_QMB.StandardButton.Yes):
            detail._on_cancel()

        assert len(received) == 1
        assert detail._create_mode is False


# ---------------------------------------------------------------------------
# TestMainWindowCreateTicket
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestMainWindowCreateTicket:
    """Verify the main window wiring for the create-ticket flow."""

    def test_create_when_no_project_path(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=None)

        win._on_create_ticket()

        # Stack should stay on page 0 (runs table)
        assert win._stack.currentIndex() == 0
        assert win._detail._create_mode is False

    def test_create_when_project_path_set(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        win._on_create_ticket()

        assert win._stack.currentIndex() == 1
        assert win._detail._create_mode is True
        assert win._detail._title_edit.text() == ""

    def test_create_clears_sidebar_selection(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        from levelup.core.tickets import Ticket, TicketStatus
        win._sidebar.set_tickets([
            Ticket(number=1, title="Ticket A", status=TicketStatus.PENDING),
        ])
        win._sidebar._list.setCurrentRow(0)

        win._on_create_ticket()

        assert win._sidebar._list.currentRow() == -1

    def test_ticket_created_persists_file(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)
        win._tickets_file = None  # default location

        win._on_ticket_created("My New Ticket", "Some description")

        tickets_path = tmp_path / "levelup" / "tickets.md"
        assert tickets_path.exists()
        content = tickets_path.read_text(encoding="utf-8")
        assert "## My New Ticket" in content
        assert "Some description" in content

    def test_ticket_created_no_project_path(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=None)

        # Should silently return without error
        win._on_ticket_created("Orphan", "No project")

        tickets_path = tmp_path / "levelup" / "tickets.md"
        assert not tickets_path.exists()

    def test_full_create_flow(self, tmp_path):
        """Plus -> type -> save -> file on disk, detail in view mode."""
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)
        win._tickets_file = None

        # 1. Click plus (simulated)
        win._on_create_ticket()
        assert win._detail._create_mode is True
        assert win._stack.currentIndex() == 1

        # 2. Type title + description
        win._detail._title_edit.setText("E2E Ticket")
        win._detail._desc_edit.setPlainText("Full flow test")

        # 3. Save
        win._detail._on_save()

        # 4. Verify file on disk
        tickets_path = tmp_path / "levelup" / "tickets.md"
        assert tickets_path.exists()
        content = tickets_path.read_text(encoding="utf-8")
        assert "## E2E Ticket" in content

        # 5. Detail should now be in view mode (set_ticket was called)
        assert win._detail._create_mode is False
        assert win._detail._dirty is False


# ---------------------------------------------------------------------------
# TestRefreshDoesNotResetCreateMode
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _can_import_pyqt6(), reason="PyQt6 not available")
class TestRefreshDoesNotResetCreateMode:
    """Ensure periodic refresh doesn't clobber an in-progress create."""

    def test_refresh_skips_when_dirty(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Enter create mode and make it dirty
        win._on_create_ticket()
        win._detail._title_edit.setText("Draft")
        assert win._detail.is_dirty is True

        # Refresh should skip because detail is dirty
        win._refresh_tickets()

        # Create mode should be intact
        assert win._detail._create_mode is True
        assert win._detail._title_edit.text() == "Draft"

    def test_refresh_preserves_create_mode_when_clean(self, tmp_path):
        app = _ensure_qapp()
        sm = _make_state_manager(tmp_path)
        win = _make_main_window(sm, project_path=tmp_path)

        # Enter create mode (clean — no typing yet)
        win._on_create_ticket()
        assert win._detail._create_mode is True
        assert win._detail.is_dirty is False

        # Refresh runs — sidebar reloads but detail should not be touched
        win._refresh_tickets()

        # Create mode must still be active
        assert win._detail._create_mode is True
        assert win._detail._title_edit.text() == ""
