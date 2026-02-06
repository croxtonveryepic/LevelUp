"""Glob + content search tool (sandboxed to project directory)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from levelup.tools.base import BaseTool


class FileSearchTool(BaseTool):
    name = "file_search"
    description = "Search for files by glob pattern and optionally search file contents. Returns matching file paths and content snippets."

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "Glob pattern to match files (e.g. '**/*.py', 'src/**/*.js')",
                },
                "content_pattern": {
                    "type": "string",
                    "description": "Optional text to search for within matched files",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 50)",
                },
            },
            "required": ["pattern"],
        }

    def execute(self, **kwargs: Any) -> str:
        pattern = kwargs["pattern"]
        content_pattern = kwargs.get("content_pattern")
        max_results = kwargs.get("max_results", 50)

        matches: list[str] = []
        try:
            for p in sorted(self._root.glob(pattern)):
                if not p.is_file():
                    continue
                rel = str(p.relative_to(self._root)).replace("\\", "/")

                # Skip hidden and common non-source dirs
                parts = rel.split("/")
                if any(
                    part.startswith(".")
                    or part in ("node_modules", "__pycache__", ".venv", "venv")
                    for part in parts
                ):
                    continue

                if content_pattern:
                    try:
                        text = p.read_text(encoding="utf-8", errors="ignore")
                        if content_pattern in text:
                            # Find matching lines
                            lines = text.splitlines()
                            matching = [
                                f"  L{i + 1}: {line.strip()}"
                                for i, line in enumerate(lines)
                                if content_pattern in line
                            ][:5]
                            matches.append(f"{rel}\n" + "\n".join(matching))
                    except Exception:
                        continue
                else:
                    matches.append(rel)

                if len(matches) >= max_results:
                    break
        except Exception as e:
            return f"Error searching: {e}"

        if not matches:
            return "No files matched."

        return "\n".join(matches)
