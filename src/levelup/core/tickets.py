"""Markdown-based ticketing system — parse, read, and update tickets."""

from __future__ import annotations

import enum
import re
from pathlib import Path

from pydantic import BaseModel


class TicketStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in progress"
    DONE = "done"
    MERGED = "merged"


_STATUS_PATTERN = re.compile(
    r"^\[(" + "|".join(re.escape(s.value) for s in TicketStatus if s != TicketStatus.PENDING) + r")\]\s*",
    re.IGNORECASE,
)


class Ticket(BaseModel):
    """A single ticket parsed from the markdown file."""

    number: int  # 1-based ordinal in file
    title: str  # Heading text without status tag
    description: str = ""  # Body text below heading
    status: TicketStatus = TicketStatus.PENDING

    def to_task_input(self):
        """Convert to TaskInput for pipeline consumption."""
        from levelup.core.context import TaskInput

        return TaskInput(
            title=self.title,
            description=self.description,
            source="ticket",
            source_id=f"ticket:{self.number}",
        )


def get_tickets_path(project_path: Path, filename: str | None = None) -> Path:
    """Return the path to the tickets file."""
    return project_path / (filename or "levelup/tickets.md")


def parse_tickets(text: str) -> list[Ticket]:
    """Parse a markdown string into a list of Tickets."""
    lines = text.splitlines(keepends=True)
    tickets: list[Ticket] = []
    in_code_block = False
    current_title: str | None = None
    current_status = TicketStatus.PENDING
    description_lines: list[str] = []

    def _flush():
        nonlocal current_title, current_status, description_lines
        if current_title is not None:
            desc = "".join(description_lines).strip()
            tickets.append(Ticket(
                number=len(tickets) + 1,
                title=current_title,
                description=desc,
                status=current_status,
            ))
        current_title = None
        current_status = TicketStatus.PENDING
        description_lines = []

    for line in lines:
        stripped = line.rstrip("\r\n")

        # Track fenced code blocks
        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            if current_title is not None:
                description_lines.append(line)
            continue

        if in_code_block:
            if current_title is not None:
                description_lines.append(line)
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
            # Actually, H1 should not be part of description — skip it
            # But only if we're not already in a ticket body
            continue
        else:
            if current_title is not None:
                description_lines.append(line)

    # Flush last ticket
    _flush()

    return tickets


def read_tickets(project_path: Path, filename: str | None = None) -> list[Ticket]:
    """Read tickets from the markdown file. Returns [] if file is missing."""
    path = get_tickets_path(project_path, filename)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    return parse_tickets(text)


def get_next_ticket(project_path: Path, filename: str | None = None) -> Ticket | None:
    """Return the first pending ticket, or None."""
    tickets = read_tickets(project_path, filename)
    for t in tickets:
        if t.status == TicketStatus.PENDING:
            return t
    return None


def set_ticket_status(
    project_path: Path,
    ticket_number: int,
    new_status: TicketStatus,
    filename: str | None = None,
) -> None:
    """Update the status tag of a ticket in-place in the file.

    Raises ``IndexError`` if the ticket number is out of range.
    """
    path = get_tickets_path(project_path, filename)
    if not path.exists():
        raise IndexError(f"Tickets file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    in_code_block = False
    ticket_count = 0
    found = False

    new_lines: list[str] = []
    for line in lines:
        stripped = line.rstrip("\r\n")

        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        if in_code_block:
            new_lines.append(line)
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            ticket_count += 1
            if ticket_count == ticket_number:
                found = True
                heading_text = stripped[3:].strip()
                # Strip existing status tag
                m = _STATUS_PATTERN.match(heading_text)
                if m:
                    bare_title = heading_text[m.end():].strip()
                else:
                    bare_title = heading_text

                # Build new heading
                if new_status == TicketStatus.PENDING:
                    new_heading = f"## {bare_title}"
                else:
                    new_heading = f"## [{new_status.value}] {bare_title}"

                # Preserve original line ending
                ending = line[len(line.rstrip("\r\n")):]
                new_lines.append(new_heading + ending)
                continue

        new_lines.append(line)

    if not found:
        tickets = parse_tickets(text)
        count = len(tickets)
        raise IndexError(
            f"Ticket #{ticket_number} not found (file has {count} ticket(s))"
        )

    path.write_text("".join(new_lines), encoding="utf-8")


def update_ticket(
    project_path: Path,
    ticket_number: int,
    *,
    title: str | None = None,
    description: str | None = None,
    filename: str | None = None,
) -> None:
    """Update the title and/or description of a ticket in-place.

    Raises ``IndexError`` if the ticket number is out of range.
    """
    path = get_tickets_path(project_path, filename)
    if not path.exists():
        raise IndexError(f"Tickets file not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    in_code_block = False
    ticket_count = 0
    heading_idx: int | None = None
    # Index of the first line after the heading that belongs to the next ticket (or EOF)
    next_heading_idx: int | None = None

    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")

        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        if stripped.startswith("## ") and not stripped.startswith("### "):
            ticket_count += 1
            if ticket_count == ticket_number:
                heading_idx = i
            elif heading_idx is not None and next_heading_idx is None:
                next_heading_idx = i

    if heading_idx is None:
        tickets = parse_tickets(text)
        count = len(tickets)
        raise IndexError(
            f"Ticket #{ticket_number} not found (file has {count} ticket(s))"
        )

    if next_heading_idx is None:
        next_heading_idx = len(lines)

    new_lines = list(lines)

    # Update heading (title) if requested
    if title is not None:
        old_heading = lines[heading_idx]
        stripped_heading = old_heading.rstrip("\r\n")
        heading_text = stripped_heading[3:].strip()
        # Preserve existing status tag
        m = _STATUS_PATTERN.match(heading_text)
        if m:
            tag = heading_text[: m.end()]
            new_heading_text = f"## {tag}{title}"
        else:
            new_heading_text = f"## {title}"
        ending = old_heading[len(old_heading.rstrip("\r\n")) :]
        new_lines[heading_idx] = new_heading_text + ending

    # Update description if requested
    if description is not None:
        # Strip newlines from each individual line (user can pass multiline string)
        desc_text = description.rstrip("\n\r")
        if desc_text:
            desc_lines = [ln + "\n" for ln in desc_text.split("\n")]
        else:
            desc_lines = []
        # Replace everything between heading and next heading
        body_start = heading_idx + 1
        new_lines[body_start:next_heading_idx] = desc_lines

    path.write_text("".join(new_lines), encoding="utf-8")
