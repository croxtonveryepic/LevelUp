"""Sidebar widget displaying the ticket list."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from levelup.core.tickets import Ticket
from levelup.gui.resources import TICKET_STATUS_COLORS, TICKET_STATUS_ICONS


class TicketSidebarWidget(QWidget):
    """Left-hand sidebar listing all tickets with status indicators."""

    ticket_selected = pyqtSignal(int)  # emits ticket number

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tickets: list[Ticket] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Tickets")
        header.setStyleSheet("font-size: 15px; font-weight: bold; padding: 8px;")
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_row_changed)
        layout.addWidget(self._list)

    def set_tickets(self, tickets: list[Ticket]) -> None:
        """Populate the list, preserving current selection by ticket number."""
        # Remember current selection
        current_number: int | None = None
        current_row = self._list.currentRow()
        if 0 <= current_row < len(self._tickets):
            current_number = self._tickets[current_row].number

        self._tickets = list(tickets)

        self._list.blockSignals(True)
        self._list.clear()

        restore_row = -1
        for i, ticket in enumerate(tickets):
            icon = TICKET_STATUS_ICONS.get(ticket.status.value, "")
            item = QListWidgetItem(f"{icon}  #{ticket.number} {ticket.title}")
            color = TICKET_STATUS_COLORS.get(ticket.status.value, "#CDD6F4")
            item.setForeground(QColor(color))
            self._list.addItem(item)
            if ticket.number == current_number:
                restore_row = i

        if restore_row >= 0:
            self._list.setCurrentRow(restore_row)

        self._list.blockSignals(False)

    def clear_selection(self) -> None:
        """Deselect any selected item."""
        self._list.blockSignals(True)
        self._list.setCurrentRow(-1)
        self._list.blockSignals(False)

    def _on_row_changed(self, row: int) -> None:
        if 0 <= row < len(self._tickets):
            self.ticket_selected.emit(self._tickets[row].number)
