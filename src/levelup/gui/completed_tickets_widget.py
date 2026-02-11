"""Widget displaying completed (done + merged) tickets."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from levelup.core.tickets import Ticket, TicketStatus
from levelup.gui.resources import TICKET_STATUS_ICONS, get_ticket_status_color


class CompletedTicketsWidget(QWidget):
    """Widget showing completed (done + merged) tickets."""

    back_clicked = pyqtSignal()
    ticket_selected = pyqtSignal(int)  # emits ticket number

    def __init__(self, parent: QWidget | None = None, theme: str = "dark") -> None:
        super().__init__(parent)
        self._tickets: list[Ticket] = []
        self._theme = theme
        self._run_status_map: dict[int, str] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header with back button and title
        header_layout = QHBoxLayout()

        back_btn = QPushButton("← Back")
        back_btn.setObjectName("backBtn")
        back_btn.clicked.connect(lambda: self.back_clicked.emit())
        header_layout.addWidget(back_btn)

        header_label = QLabel("Completed Tickets")
        header_label.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px;")
        header_layout.addWidget(header_label)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # List widget
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

    def set_tickets(self, tickets: list[Ticket], run_status_map: dict[int, str] | None = None) -> None:
        """Set tickets to display, filtering to show only done and merged.

        Args:
            tickets: List of all tickets
            run_status_map: Optional mapping of ticket number to run status
        """
        self._tickets = [t for t in tickets if t.status in (TicketStatus.DONE, TicketStatus.MERGED)]
        self._run_status_map = run_status_map or {}

        self._list.blockSignals(True)
        self._list.clear()

        for ticket in self._tickets:
            icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
            item = QListWidgetItem(f"{icon}  #{ticket.number} {ticket.title}")

            # Get run status for this ticket if available
            run_status = self._run_status_map.get(ticket.number)
            color = get_ticket_status_color(
                ticket.status.value,
                theme=self._theme,
                run_status=run_status
            )
            item.setForeground(QColor(color))
            self._list.addItem(item)

        self._list.blockSignals(False)

    def update_theme(self, theme: str) -> None:
        """Update widget styling for theme change.

        Args:
            theme: "light" or "dark"
        """
        self._theme = theme
        # Refresh the list with new theme colors
        tickets = self._tickets.copy()
        run_status_map = self._run_status_map.copy()

        # Re-render with new theme
        self._list.blockSignals(True)
        self._list.clear()

        for ticket in tickets:
            icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
            item = QListWidgetItem(f"{icon}  #{ticket.number} {ticket.title}")

            run_status = run_status_map.get(ticket.number)
            color = get_ticket_status_color(
                ticket.status.value,
                theme=self._theme,
                run_status=run_status
            )
            item.setForeground(QColor(color))
            self._list.addItem(item)

        self._list.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._tickets):
            self.ticket_selected.emit(self._tickets[row].number)
