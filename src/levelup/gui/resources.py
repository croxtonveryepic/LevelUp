"""Status-to-color/icon mapping for GUI elements."""

from __future__ import annotations

STATUS_COLORS: dict[str, str] = {
    "running": "#4A90D9",
    "waiting_for_input": "#E6A817",
    "completed": "#2ECC71",
    "failed": "#E74C3C",
    "aborted": "#95A5A6",
    "pending": "#95A5A6",
}

STATUS_LABELS: dict[str, str] = {
    "running": "Running",
    "waiting_for_input": "Needs Input",
    "completed": "Completed",
    "failed": "Failed",
    "aborted": "Aborted",
    "pending": "Pending",
}

STATUS_ICONS: dict[str, str] = {
    "running": "\u25B6",       # play
    "waiting_for_input": "\u26A0",  # warning
    "completed": "\u2714",     # checkmark
    "failed": "\u2718",        # X
    "aborted": "\u25A0",       # stop
    "pending": "\u25CB",       # circle
}


def status_display(status: str) -> str:
    """Return a human-readable status string with icon."""
    icon = STATUS_ICONS.get(status, "")
    label = STATUS_LABELS.get(status, status)
    return f"{icon} {label}"
