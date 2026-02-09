"""Normalize natural-language branch naming patterns to canonical {placeholder} format."""

from __future__ import annotations

import re

# Canonical placeholders recognized by the system.
_PLACEHOLDERS = {"{run_id}", "{task_title}", "{date}"}

# Aliases sorted longest-first so greedy matching works correctly.
_ALIASES: list[tuple[str, str]] = [
    ("task-title-in-kebab-case", "{task_title}"),
    ("task-title", "{task_title}"),
    ("task_title", "{task_title}"),
    ("title", "{task_title}"),
    ("task", "{task_title}"),
    ("run-id", "{run_id}"),
    ("run_id", "{run_id}"),
    ("runid", "{run_id}"),
    ("id", "{run_id}"),
    ("date", "{date}"),
]

# Regex to strip trailing format descriptors from segments that already contain
# a {placeholder}.  Matches things like "-in-kebab-case", "-in-snake-case",
# "-slug", "-kebab", etc.
_FORMAT_DESCRIPTOR_RE = re.compile(
    r"[-_]in[-_](kebab|snake|camel|pascal)[-_]case"
    r"|[-_](slug|kebab|snake|camel|pascal)"
    r"$",
    re.IGNORECASE,
)


def _has_placeholder(text: str) -> bool:
    return any(p in text for p in _PLACEHOLDERS)


def _replace_aliases_in_segment(segment: str) -> str:
    """Replace natural-language aliases with {placeholder} tokens in a single segment.

    Uses word-boundary matching: aliases only match at segment start or after
    a separator (-/_/.), and must be followed by end-of-segment or a separator.
    Replacements are tried longest-first and each character position is consumed
    at most once.
    """
    result: list[str] = []
    i = 0
    lower = segment.lower()

    while i < len(segment):
        # Check word boundary: must be at start or preceded by a separator.
        if i == 0 or segment[i - 1] in "-_.":
            matched = False
            for alias, placeholder in _ALIASES:
                end = i + len(alias)
                if end > len(segment):
                    continue
                if lower[i:end] != alias:
                    continue
                # Check trailing boundary: end of segment or separator.
                if end < len(segment) and segment[end] not in "-_.":
                    continue
                result.append(placeholder)
                i = end
                matched = True
                break
            if matched:
                continue
        result.append(segment[i])
        i += 1

    return "".join(result)


def _strip_format_descriptors(segment: str) -> str:
    """Remove trailing format descriptors from a segment that contains a placeholder."""
    if not _has_placeholder(segment):
        return segment
    return _FORMAT_DESCRIPTOR_RE.sub("", segment)


def normalize_branch_convention(raw: str) -> str:
    """Convert a natural-language branch pattern to canonical {placeholder} format.

    - If the input already contains {run_id}, {task_title}, or {date}, return as-is.
    - Otherwise, split on ``/``, replace known aliases with placeholders,
      strip trailing format descriptors, and rejoin.

    Examples::

        >>> normalize_branch_convention("levelup/{run_id}")
        'levelup/{run_id}'
        >>> normalize_branch_convention("levelup/task-title-in-kebab-case")
        'levelup/{task_title}'
        >>> normalize_branch_convention("feature/task-title")
        'feature/{task_title}'
        >>> normalize_branch_convention("dev/date-run-id")
        'dev/{date}-{run_id}'
    """
    stripped = raw.strip()
    if not stripped:
        return stripped

    # Pass-through: already uses canonical placeholders.
    if _has_placeholder(stripped):
        return stripped

    segments = stripped.split("/")
    normalized = []
    for seg in segments:
        replaced = _replace_aliases_in_segment(seg)
        replaced = _strip_format_descriptors(replaced)
        normalized.append(replaced)

    return "/".join(normalized)
