"""Write/create files tool (sandboxed to project directory)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from levelup.tools.base import BaseTool


class FileWriteTool(BaseTool):
    name = "file_write"
    description = "Write content to a file. Creates parent directories if needed. Path must be relative to the project root."

    def __init__(self, project_root: Path) -> None:
        self._root = project_root.resolve()

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file to write",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        }

    def execute(self, **kwargs: Any) -> str:
        rel_path = kwargs["path"]
        content = kwargs["content"]
        full = (self._root / rel_path).resolve()

        if not str(full).startswith(str(self._root)):
            return "Error: path escapes project root"

        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {rel_path}"
        except Exception as e:
            return f"Error writing file: {e}"
