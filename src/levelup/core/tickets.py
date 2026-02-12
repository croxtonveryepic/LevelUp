"""DB-backed ticketing system with markdown parsing utilities preserved."""

from __future__ import annotations

import enum
import json
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from levelup.state.db import DEFAULT_DB_PATH


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in progress"
    DONE = "done"
    MERGED = "merged"
    DECLINED = "declined"


_STATUS_PATTERN = re.compile(
    r"^\[(" + "|".join(re.escape(s.value) for s in TicketStatus if s != TicketStatus.PENDING) + r")\]\s*",
    re.IGNORECASE,
)

# Sentinel value for "not provided" in update_ticket
_NOT_PROVIDED = object()

# Run options that should be filtered from ticket metadata
_RUN_OPTION_KEYS = {"model", "effort", "skip_planning"}


class Ticket(BaseModel):
    """A single ticket."""

    number: int  # stable ticket_number (not positional)
    title: str
    description: str = ""
    status: TicketStatus = TicketStatus.PENDING
    metadata: dict[str, Any] | None = None

    def to_task_input(self):
        """Convert to TaskInput for pipeline consumption."""
        from levelup.core.context import TaskInput

        return TaskInput(
            title=self.title,
            description=self.description,
            source="ticket",
            source_id=f"ticket:{self.number}",
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _filter_run_options(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove run option keys from metadata. Returns None if empty after filtering."""
    if not metadata:
        return None
    filtered = {k: v for k, v in metadata.items() if k not in _RUN_OPTION_KEYS}
    return filtered if filtered else None


def _record_to_ticket(rec: object) -> Ticket:
    """Convert a TicketRecord (from StateManager) to a Ticket model."""
    from levelup.state.models import TicketRecord

    assert isinstance(rec, TicketRecord)
    metadata: dict[str, Any] | None = None
    if rec.metadata_json:
        try:
            metadata = json.loads(rec.metadata_json)
        except (json.JSONDecodeError, TypeError):
            metadata = None

    # Map DB status strings to TicketStatus enum
    status = TicketStatus(rec.status)

    return Ticket(
        number=rec.ticket_number,
        title=rec.title,
        description=rec.description,
        status=status,
        metadata=metadata,
    )


def _get_state_manager(db_path: Path | None = None):
    """Create a StateManager for the given db_path."""
    from levelup.state.manager import StateManager

    if db_path is not None:
        return StateManager(db_path=db_path)
    return StateManager()


def _normalize_project_path(project_path: Path) -> str:
    """Normalize project path to a consistent string for DB storage."""
    return str(project_path.resolve())


# ---------------------------------------------------------------------------
# Markdown parsing (preserved for future migration command)
# ---------------------------------------------------------------------------


def get_tickets_path(project_path: Path, filename: str | None = None) -> Path:
    """Return the path to the tickets markdown file (for migration use)."""
    return project_path / (filename or "levelup/tickets.md")


def parse_tickets(text: str) -> list[Ticket]:
    """Parse a markdown string into a list of Tickets.

    Preserved for future markdown-to-DB migration command.
    """
    lines = text.splitlines(keepends=True)
    tickets: list[Ticket] = []
    in_code_block = False
    current_title: str | None = None
    current_status = TicketStatus.PENDING
    current_metadata: dict[str, Any] | None = None
    description_lines: list[str] = []
    in_metadata_block = False
    metadata_lines: list[str] = []

    def _flush():
        nonlocal current_title, current_status, current_metadata, description_lines
        if current_title is not None:
            desc = "".join(description_lines).strip()
            tickets.append(Ticket(
                number=len(tickets) + 1,
                title=current_title,
                description=desc,
                status=current_status,
                metadata=current_metadata,
            ))
        current_title = None
        current_status = TicketStatus.PENDING
        current_metadata = None
        description_lines = []

    for line in lines:
        stripped = line.rstrip("\r\n")

        # Track fenced code blocks
        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            if current_title is not None and not in_metadata_block:
                description_lines.append(line)
            continue

        if in_code_block:
            if current_title is not None and not in_metadata_block:
                description_lines.append(line)
            continue

        # Check for metadata block start
        if current_title is not None and stripped.strip() == "<!--metadata":
            in_metadata_block = True
            metadata_lines = []
            continue

        # Check for metadata block end
        if in_metadata_block and stripped.strip() == "-->":
            in_metadata_block = False
            # Parse metadata YAML
            if metadata_lines:
                try:
                    metadata_text = "\n".join(metadata_lines)
                    current_metadata = yaml.safe_load(metadata_text)
                    if not isinstance(current_metadata, dict):
                        current_metadata = None
                except yaml.YAMLError:
                    # Ignore malformed metadata
                    current_metadata = None
            metadata_lines = []
            continue

        # Collect metadata lines
        if in_metadata_block:
            metadata_lines.append(stripped)
            continue

        # Check for ## heading (but not ### or more)
        if stripped.startswith("## ") and not stripped.startswith("### "):
            _flush()
            heading_text = stripped[3:].strip()
            # Check for status tag
            m = _STATUS_PATTERN.match(heading_text)
            if m:
                current_status = TicketStatus(m.group(1).lower())
                current_title = heading_text[m.end():].strip()
            else:
                current_status = TicketStatus.PENDING
                current_title = heading_text
        elif stripped.startswith("# ") and not stripped.startswith("## "):
            # H1 heading — ignored, but flush any current ticket
            if current_title is not None:
                description_lines.append(line)
            continue
        else:
            if current_title is not None:
                description_lines.append(line)

    # Flush last ticket
    _flush()

    return tickets


# ---------------------------------------------------------------------------
# DB-backed public API
# ---------------------------------------------------------------------------


def read_tickets(project_path: Path, *, db_path: Path | None = None) -> list[Ticket]:
    """Read all tickets for a project from the database."""
    sm = _get_state_manager(db_path)
    records = sm.list_tickets(_normalize_project_path(project_path))
    return [_record_to_ticket(r) for r in records]


def get_ticket(project_path: Path, ticket_number: int, *, db_path: Path | None = None) -> Ticket | None:
    """Get a single ticket by number. Returns None if not found."""
    sm = _get_state_manager(db_path)
    rec = sm.get_ticket(_normalize_project_path(project_path), ticket_number)
    if rec is None:
        return None
    return _record_to_ticket(rec)


def get_next_ticket(project_path: Path, *, db_path: Path | None = None) -> Ticket | None:
    """Return the first pending ticket, or None."""
    sm = _get_state_manager(db_path)
    rec = sm.get_next_pending_ticket(_normalize_project_path(project_path))
    if rec is None:
        return None
    return _record_to_ticket(rec)


def set_ticket_status(
    project_path: Path,
    ticket_number: int,
    new_status: TicketStatus,
    *,
    db_path: Path | None = None,
) -> None:
    """Update the status of a ticket.

    Raises ``IndexError`` if the ticket number is not found.
    """
    sm = _get_state_manager(db_path)
    sm.set_ticket_status(
        _normalize_project_path(project_path),
        ticket_number,
        new_status.value,
    )


def update_ticket(
    project_path: Path,
    ticket_number: int,
    *,
    title: str | None = None,
    description: str | None = None,
    metadata: dict[str, Any] | None | object = _NOT_PROVIDED,
    db_path: Path | None = None,
) -> None:
    """Update the title, description, and/or metadata of a ticket.

    Raises ``IndexError`` if the ticket number is not found.
    """
    sm = _get_state_manager(db_path)
    proj = _normalize_project_path(project_path)

    # Determine metadata_json to pass
    from levelup.state.manager import _SENTINEL

    if metadata is _NOT_PROVIDED:
        metadata_json: str | object = _SENTINEL  # don't update
    elif metadata is None:
        metadata_json = None
    else:
        filtered = _filter_run_options(metadata)
        metadata_json = json.dumps(filtered) if filtered else None

    sm.update_ticket(
        proj,
        ticket_number,
        title=title,
        description=description,
        metadata_json=metadata_json,
    )


def delete_ticket(
    project_path: Path,
    ticket_number: int,
    *,
    db_path: Path | None = None,
) -> str:
    """Delete a ticket. Returns the deleted ticket's title.

    Raises ``IndexError`` if the ticket number is not found.
    """
    sm = _get_state_manager(db_path)
    title = sm.delete_ticket(_normalize_project_path(project_path), ticket_number)

    # Clean up associated images
    cleanup_ticket_images(ticket_number, project_path)

    return title


def add_ticket(
    project_path: Path,
    title: str,
    description: str = "",
    *,
    metadata: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> Ticket:
    """Create a new ticket and return it."""
    sm = _get_state_manager(db_path)

    # Filter run options from metadata before storing
    filtered_metadata = _filter_run_options(metadata)
    metadata_json = json.dumps(filtered_metadata) if filtered_metadata else None

    rec = sm.add_ticket(
        _normalize_project_path(project_path),
        title,
        description.strip(),
        metadata_json=metadata_json,
    )
    return _record_to_ticket(rec)


# ---------------------------------------------------------------------------
# File-based utilities (kept as-is)
# ---------------------------------------------------------------------------


def cleanup_ticket_images(
    ticket_number: int,
    project_path: Path,
) -> None:
    """Remove all images associated with a ticket.

    Args:
        ticket_number: Ticket number to clean up
        project_path: Project root path
    """
    asset_dir = project_path / "levelup" / "ticket-assets"

    if not asset_dir.exists():
        return

    # Pattern to match ticket-N-* files
    pattern = f"ticket-{ticket_number}-*"

    for img_file in asset_dir.glob(pattern):
        try:
            img_file.unlink()
        except Exception:
            # Ignore errors (file may be locked, etc.)
            pass
