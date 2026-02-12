"""Sidebar widget displaying the ticket list."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from pathlib import Path

from levelup.core.tickets import Ticket, TicketStatus
from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS, get_ticket_status_color


class TicketSidebarWidget(QWidget):
    """Left-hand sidebar listing all tickets with status indicators."""

    ticket_selected = pyqtSignal(int)  # emits ticket number
    create_ticket_clicked = pyqtSignal()
    jira_import_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, theme: str = "dark") -> None:
        super().__init__(parent)
        self._tickets: list[Ticket] = []
        self._filtered_tickets: list[Ticket] = []
        self._current_theme = theme
        self._run_status_map: dict[int, str] = {}
        self._show_merged = False  # Hide merged by default

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        header_label = QLabel("Tickets")
        header_label.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        add_btn = QPushButton("+")
        add_btn.setObjectName("addTicketBtn")
        add_btn.setToolTip("Create new ticket")
        add_btn.clicked.connect(lambda: self.create_ticket_clicked.emit())
        header_layout.addWidget(add_btn)

        self._jira_btn = QPushButton("J")
        self._jira_btn.setObjectName("jiraImportBtn")
        self._jira_btn.setToolTip("Import tickets from Jira")
        self._jira_btn.clicked.connect(lambda: self.jira_import_clicked.emit())
        self._jira_btn.setVisible(False)
        header_layout.addWidget(self._jira_btn)

        layout.addLayout(header_layout)

        # Add merged ticket filter checkbox
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(8, 0, 8, 8)
        self._show_merged_checkbox = QCheckBox("Show merged")
        self._show_merged_checkbox.setObjectName("showMergedCheckbox")
        self._show_merged_checkbox.setChecked(False)
        self._show_merged_checkbox.stateChanged.connect(self._on_filter_changed)
        filter_layout.addWidget(self._show_merged_checkbox)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

    def _on_filter_changed(self) -> None:
        """Handle filter checkbox state change."""
        self._show_merged = self._show_merged_checkbox.isChecked()
        # Re-render the list with current filter state
        self._apply_filter()

    def _apply_filter(self) -> None:
        """Apply filter to ticket list and re-render."""
        # Remember current selection by ticket number
        current_number: int | None = None
        current_row = self._list.currentRow()
        if 0 <= current_row < len(self._filtered_tickets):
            current_number = self._filtered_tickets[current_row].number

        # Apply filter
        if self._show_merged:
            self._filtered_tickets = list(self._tickets)
        else:
            self._filtered_tickets = [t for t in self._tickets if t.status != TicketStatus.MERGED]

        # Re-render list
        self._list.blockSignals(True)
        self._list.clear()

        restore_row = -1
        for i, ticket in enumerate(self._filtered_tickets):
            icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
            item = QListWidgetItem(f"{icon}  #{ticket.number} {ticket.title}")

            # Get run status for this ticket if available
            run_status = self._run_status_map.get(ticket.number)
            color = get_ticket_status_color(
                ticket.status.value,
                theme=self._current_theme,
                run_status=run_status
            )
            item.setForeground(QColor(color))
            self._list.addItem(item)
            if ticket.number == current_number:
                restore_row = i

        # Restore selection if the ticket is still visible
        if restore_row >= 0:
            self._list.setCurrentRow(restore_row)
        else:
            # Selection was filtered out, clear it
            self._list.setCurrentRow(-1)

        self._list.blockSignals(False)

    def set_tickets(self, tickets: list[Ticket], run_status_map: dict[int, str] | None = None) -> None:
        """Populate the list, preserving current selection by ticket number.

        Args:
            tickets: List of tickets to display
            run_status_map: Optional mapping of ticket number to run status
        """
        self._tickets = list(tickets)
        self._run_status_map = run_status_map or {}
        self._filtered_tickets = []

        # Apply filter and render
        self._apply_filter()

    def update_theme(self, theme: str) -> None:
        """Update widget styling for theme change.

        Args:
            theme: "light" or "dark"
        """
        self._current_theme = theme
        # Refresh the list to update colors, preserving run status map
        tickets = self._tickets.copy()
        run_status_map = self._run_status_map.copy()
        self.set_tickets(tickets, run_status_map=run_status_map)

    def clear_selection(self) -> None:
        """Deselect any selected item."""
        self._list.blockSignals(True)
        self._list.setCurrentRow(-1)
        self._list.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._filtered_tickets):
            self.ticket_selected.emit(self._filtered_tickets[row].number)

    @property
    def ticket_list(self) -> QListWidget:
        """Get the ticket list widget (for testing)."""
        return self._list

    def refresh(self) -> None:
        """Refresh the ticket list (alias for updating with current tickets)."""
        # Re-render with current tickets
        self.set_tickets(self._tickets)

    def set_jira_enabled(self, enabled: bool) -> None:
        """Show or hide the Jira import button."""
        self._jira_btn.setVisible(enabled)

    def set_jira_importing(self, importing: bool) -> None:
        """Disable the Jira button and update tooltip during import."""
        self._jira_btn.setEnabled(not importing)
        if importing:
            self._jira_btn.setToolTip("Importing from Jira...")
        else:
            self._jira_btn.setToolTip("Import tickets from Jira")


class TicketSidebar(TicketSidebarWidget):
    """Alias for TicketSidebarWidget with auto-loading capability."""

    def __init__(self, parent: QWidget | None = None, theme: str = "dark", project_path: Path | str | None = None) -> None:
        super().__init__(parent, theme)
        self._project_path = Path(project_path) if project_path else None
        if project_path:
            self.refresh()

    def refresh(self) -> None:
        """Refresh tickets from DB."""
        if self._project_path:
            from levelup.core.tickets import read_tickets
            tickets = read_tickets(self._project_path)
            self.set_tickets(tickets)
        else:
            super().refresh()
