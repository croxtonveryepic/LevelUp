"""CLAUDE.md management — add, list, remove project rules in the target project."""

from __future__ import annotations

import re
from pathlib import Path

SECTION_HEADER = "## Project Rules"


def get_claude_md_path(project_path: Path) -> Path:
    """Return the path to the target project's CLAUDE.md."""
    return project_path / "CLAUDE.md"


def read_instructions(project_path: Path) -> list[str]:
    """Parse the ``## Project Rules`` section and return bullet items."""
    path = get_claude_md_path(project_path)
    if not path.exists():
        return []

    text = path.read_text(encoding="utf-8")
    return _parse_rules(text)


def add_instruction(project_path: Path, text: str) -> None:
    """Append ``- text`` under ``## Project Rules`` (creates file/section if missing)."""
    path = get_claude_md_path(project_path)

    if not path.exists():
        path.write_text(
            f"{SECTION_HEADER}\n\n- {text}\n", encoding="utf-8"
        )
        return

    content = path.read_text(encoding="utf-8")

    # Find the section
    idx = content.find(SECTION_HEADER)
    if idx == -1:
        # Append section at end
        separator = "\n\n" if content and not content.endswith("\n\n") else (
            "\n" if content and not content.endswith("\n") else ""
        )
        content += f"{separator}{SECTION_HEADER}\n\n- {text}\n"
    else:
        # Find the end of the section (next ## heading or end of file)
        after_header = idx + len(SECTION_HEADER)
        next_section = _find_next_section(content, after_header)

        if next_section == -1:
            # Section goes to end of file
            # Ensure trailing newline before appending
            if content and not content.endswith("\n"):
                content += "\n"
            content += f"- {text}\n"
        else:
            # Insert before the next section
            insert_at = next_section
            # Ensure a blank line before the rule
            prefix = content[:insert_at]
            if not prefix.endswith("\n"):
                prefix += "\n"
            content = prefix + f"- {text}\n\n" + content[insert_at:]

    path.write_text(content, encoding="utf-8")


def remove_instruction(project_path: Path, index: int) -> str:
    """Remove a 1-based indexed rule and return its text.

    Raises ``IndexError`` if the index is out of range.
    """
    path = get_claude_md_path(project_path)
    if not path.exists():
        raise IndexError(f"No CLAUDE.md found at {project_path}")

    content = path.read_text(encoding="utf-8")
    rules = _parse_rules(content)

    if index < 1 or index > len(rules):
        raise IndexError(
            f"Rule index {index} out of range (1–{len(rules)})"
        )

    removed_text = rules[index - 1]

    # Remove the line from the file content
    lines = content.splitlines(keepends=True)
    rule_count = 0
    new_lines: list[str] = []
    in_section = False

    for line in lines:
        stripped = line.strip()

        if stripped == SECTION_HEADER:
            in_section = True
            new_lines.append(line)
            continue

        if in_section and stripped.startswith("## "):
            in_section = False

        if in_section and stripped.startswith("- "):
            rule_count += 1
            if rule_count == index:
                continue  # skip this line

        new_lines.append(line)

    path.write_text("".join(new_lines), encoding="utf-8")
    return removed_text


def build_instruct_review_prompt(instruction: str, changed_files: list[str]) -> str:
    """Build a system prompt for the instruct review agent."""
    files_list = "\n".join(f"- {f}" for f in changed_files)
    return (
        "You are a code review agent. A new project rule has been added:\n\n"
        f"  Rule: {instruction}\n\n"
        "Review the following files for violations of this rule and fix any violations "
        "by editing the files directly. Only make changes necessary to comply with the rule.\n\n"
        f"Files to review:\n{files_list}"
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_rules(text: str) -> list[str]:
    """Extract bullet items from the ``## Project Rules`` section."""
    idx = text.find(SECTION_HEADER)
    if idx == -1:
        return []

    after_header = idx + len(SECTION_HEADER)
    next_section = _find_next_section(text, after_header)
    section_text = text[after_header:] if next_section == -1 else text[after_header:next_section]

    rules: list[str] = []
    for line in section_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            rules.append(stripped[2:])

    return rules


def _find_next_section(text: str, start: int) -> int:
    """Find the position of the next ``## `` heading after *start*, or -1."""
    match = re.search(r"^## ", text[start:], re.MULTILINE)
    if match:
        return start + match.start()
    return -1
