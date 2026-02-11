"""Markdown-based ticketing system — parse, read, and update tickets."""

from __future__ import annotations

import enum
import re
from pathlib import Path
from typing import Any

import yaml
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

# Sentinel value for "not provided" in update_ticket
_NOT_PROVIDED = object()

# Run options that should be filtered from ticket metadata
_RUN_OPTION_KEYS = {"model", "effort", "skip_planning"}


class Ticket(BaseModel):
    """A single ticket parsed from the markdown file."""

    number: int  # 1-based ordinal in file
    title: str  # Heading text without status tag
    description: str = ""  # Body text below heading
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


def _filter_run_options(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Remove run option keys from metadata. Returns None if empty after filtering."""
    if not metadata:
        return None
    filtered = {k: v for k, v in metadata.items() if k not in _RUN_OPTION_KEYS}
    return filtered if filtered else None


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

    # Parse to get current ticket data and filter metadata
    tickets = parse_tickets(text)
    if ticket_number < 1 or ticket_number > len(tickets):
        raise IndexError(f"Ticket #{ticket_number} not found (file has {len(tickets)} ticket(s))")

    current_ticket = tickets[ticket_number - 1]
    # Filter run options from metadata
    filtered_metadata = _filter_run_options(current_ticket.metadata)

    lines = text.splitlines(keepends=True)

    in_code_block = False
    ticket_count = 0
    found = False
    in_metadata_block = False
    metadata_start_idx: int | None = None
    metadata_end_idx: int | None = None

    new_lines: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")

        if stripped.lstrip().startswith("```"):
            in_code_block = not in_code_block
            new_lines.append(line)
            continue

        if in_code_block:
            new_lines.append(line)
            continue

        # Track metadata blocks for the target ticket
        if ticket_count == ticket_number:
            if stripped.strip() == "<!--metadata" and not in_metadata_block:
                in_metadata_block = True
                metadata_start_idx = i
                continue
            elif in_metadata_block and stripped.strip() == "-->":
                in_metadata_block = False
                metadata_end_idx = i
                # Write filtered metadata after this ticket's heading
                if filtered_metadata:
                    new_lines.append("<!--metadata\n")
                    new_lines.append(yaml.dump(filtered_metadata, default_flow_style=False, sort_keys=False))
                    new_lines.append("-->\n")
                continue
            elif in_metadata_block:
                # Skip old metadata lines
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
    metadata: dict[str, Any] | None | object = _NOT_PROVIDED,  # sentinel for "not provided"
    filename: str | None = None,
) -> None:
    """Update the title and/or description of a ticket in-place.

    Raises ``IndexError`` if the ticket number is out of range.
    """
    path = get_tickets_path(project_path, filename)
    if not path.exists():
        raise IndexError(f"Tickets file not found: {path}")

    text = path.read_text(encoding="utf-8")

    # First, parse to get current ticket data
    tickets = parse_tickets(text)
    if ticket_number < 1 or ticket_number > len(tickets):
        raise IndexError(
            f"Ticket #{ticket_number} not found (file has {len(tickets)} ticket(s))"
        )

    current_ticket = tickets[ticket_number - 1]

    # Determine what metadata to use and filter run options
    if metadata is _NOT_PROVIDED:  # Not provided
        new_metadata = _filter_run_options(current_ticket.metadata)
    else:
        new_metadata = _filter_run_options(metadata)

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
                break

    if heading_idx is None:
        raise IndexError(f"Ticket #{ticket_number} not found (file has {len(tickets)} ticket(s))")

    if next_heading_idx is None:
        next_heading_idx = len(lines)

    # Extract status from original heading
    original_heading = lines[heading_idx].rstrip("\r\n")
    heading_text = original_heading[3:].strip()  # Strip "## "
    m = _STATUS_PATTERN.match(heading_text)
    if m:
        current_status = m.group(1).lower()
        bare_title = heading_text[m.end():].strip()
    else:
        current_status = "pending"
        bare_title = heading_text

    # Build new heading
    new_title_text = title if title is not None else bare_title
    if current_status == "pending":
        new_heading = f"## {new_title_text}"
    else:
        new_heading = f"## [{current_status}] {new_title_text}"

    # Build new body
    new_body_lines: list[str] = []
    if new_metadata:
        new_body_lines.append("<!--metadata\n")
        new_body_lines.append(yaml.dump(new_metadata, default_flow_style=False, sort_keys=False))
        new_body_lines.append("-->\n")

    if description is not None:
        new_body_lines.append(description.rstrip("\n\r") + "\n")
    else:
        # Preserve original description
        in_metadata = False
        for i in range(heading_idx + 1, next_heading_idx):
            stripped = lines[i].rstrip("\r\n")
            if stripped.strip() == "<!--metadata":
                in_metadata = True
                continue
            elif stripped.strip() == "-->":
                in_metadata = False
                continue
            if not in_metadata:
                new_body_lines.append(lines[i])

    # Reassemble file
    ending = lines[heading_idx][len(lines[heading_idx].rstrip("\r\n")):]
    new_lines = lines[:heading_idx] + [new_heading + ending] + new_body_lines + lines[next_heading_idx:]

    path.write_text("".join(new_lines), encoding="utf-8")


def delete_ticket(
    project_path: Path,
    ticket_number: int,
    filename: str | None = None,
) -> str:
    """Delete a ticket from the markdown file. Returns the deleted ticket's title.

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
                break

    if heading_idx is None:
        tickets = parse_tickets(text)
        count = len(tickets)
        raise IndexError(
            f"Ticket #{ticket_number} not found (file has {count} ticket(s))"
        )

    if next_heading_idx is None:
        next_heading_idx = len(lines)

    # Extract title from heading
    heading_text = lines[heading_idx].rstrip("\r\n")[3:].strip()  # Strip "## "
    m = _STATUS_PATTERN.match(heading_text)
    if m:
        title = heading_text[m.end():].strip()
    else:
        title = heading_text

    # Delete lines from heading_idx to next_heading_idx (exclusive)
    # If there's a blank line before the heading, also remove it
    start_idx = heading_idx
    if heading_idx > 0 and lines[heading_idx - 1].strip() == "":
        start_idx = heading_idx - 1

    new_lines = lines[:start_idx] + lines[next_heading_idx:]

    path.write_text("".join(new_lines), encoding="utf-8")

    return title


def add_ticket(
    project_path: Path,
    title: str,
    description: str = "",
    filename: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Ticket:
    """Append a new ticket to the markdown file and return it.

    Creates the parent directory and file if they don't exist.
    """
    path = get_tickets_path(project_path, filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Read existing tickets to determine next number
    existing = parse_tickets(path.read_text(encoding="utf-8")) if path.exists() else []
    new_number = len(existing) + 1

    # Filter run options from metadata before writing
    filtered_metadata = _filter_run_options(metadata)

    # Build the markdown block
    block = f"## {title}\n"
    if filtered_metadata:
        block += "<!--metadata\n"
        block += yaml.dump(filtered_metadata, default_flow_style=False, sort_keys=False)
        block += "-->\n"
    if description:
        block += description.rstrip("\n\r") + "\n"

    # Append with a blank-line separator
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current and not current.endswith("\n"):
            block = "\n" + block
        elif current:
            block = "\n" + block
        path.write_text(current + block, encoding="utf-8")
    else:
        path.write_text(block, encoding="utf-8")

    return Ticket(
        number=new_number,
        title=title,
        description=description.strip(),
        status=TicketStatus.PENDING,
        metadata=filtered_metadata,
    )
