"""Status-to-color/icon mapping for GUI elements."""

from __future__ import annotations

from typing import Literal

# Dark theme status colors
STATUS_COLORS: dict[str, str] = {
    "running": "#4A90D9",
    "waiting_for_input": "#E6A817",
    "paused": "#F5A623",
    "completed": "#2ECC71",
    "failed": "#E74C3C",
    "aborted": "#95A5A6",
    "pending": "#95A5A6",
}

# Light theme status colors
_LIGHT_STATUS_COLORS: dict[str, str] = {
    "running": "#3498DB",
    "waiting_for_input": "#F39C12",
    "paused": "#E67E22",
    "completed": "#27AE60",
    "failed": "#C0392B",
    "aborted": "#7F8C8D",
    "pending": "#95A5A6",
}

STATUS_LABELS: dict[str, str] = {
    "running": "Running",
    "waiting_for_input": "Needs Input",
    "paused": "Paused",
    "completed": "Completed",
    "failed": "Failed",
    "aborted": "Aborted",
    "pending": "Pending",
}

STATUS_ICONS: dict[str, str] = {
    "running": "\u25B6",       # play
    "waiting_for_input": "\u26A0",  # warning
    "paused": "\u23F8",        # pause
    "completed": "\u2714",     # checkmark
    "failed": "\u2718",        # X
    "aborted": "\u25A0",       # stop
    "pending": "\u25CB",       # circle
}


def get_status_color(status: str, theme: Literal["light", "dark"] = "dark") -> str:
    """Get theme-aware status color.

    Args:
        status: Status key (e.g., "running", "completed")
        theme: "light" or "dark"

    Returns:
        Hex color string
    """
    if theme == "light":
        return _LIGHT_STATUS_COLORS.get(status, "#95A5A6")
    else:
        return STATUS_COLORS.get(status, "#95A5A6")


def status_display(status: str) -> str:
    """Return a human-readable status string with icon."""
    icon = STATUS_ICONS.get(status, "")
    label = STATUS_LABELS.get(status, status)
    return f"{icon} {label}"


# Dark theme ticket status colors
TICKET_STATUS_COLORS: dict[str, str] = {
    "pending": "#CDD6F4",
    "in progress": "#E6A817",
    "done": "#2ECC71",
    "merged": "#6C7086",
}

# Light theme ticket status colors
_LIGHT_TICKET_STATUS_COLORS: dict[str, str] = {
    "pending": "#4C566A",
    "in progress": "#F39C12",
    "done": "#27AE60",
    "merged": "#95A5A6",
}

TICKET_STATUS_ICONS: dict[str, str] = {
    "pending": "\u25CB",       # empty circle
    "in progress": "\u25B6",   # play arrow
    "done": "\u2714",          # checkmark
    "merged": "\u25CF",        # filled circle
}


def get_ticket_status_color(status: str, theme: Literal["light", "dark"] = "dark") -> str:
    """Get theme-aware ticket status color.

    Args:
        status: Ticket status key (e.g., "pending", "done")
        theme: "light" or "dark"

    Returns:
        Hex color string
    """
    if theme == "light":
        return _LIGHT_TICKET_STATUS_COLORS.get(status, "#4C566A")
    else:
        return TICKET_STATUS_COLORS.get(status, "#CDD6F4")
