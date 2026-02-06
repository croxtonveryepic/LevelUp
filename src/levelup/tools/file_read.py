"""Read file contents tool (sandboxed to project directory)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from levelup.tools.base import BaseTool


class FileReadTool(BaseTool):
    name = "file_read"
    description = "Read the contents of a file. Path must be relative to the project root."

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to read",
                },
            },
            "required": ["path"],
        }

    def execute(self, **kwargs: Any) -> str:
        rel_path = kwargs["path"]
        full = (self._root / rel_path).resolve()

        if not str(full).startswith(str(self._root)):
            return "Error: path escapes project root"

        if not full.is_file():
            return f"Error: file not found: {rel_path}"

        try:
            return full.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"
