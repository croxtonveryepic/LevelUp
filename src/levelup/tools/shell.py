"""Execute shell commands tool (with timeout, sandboxed to project directory)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from levelup.tools.base import BaseTool

DEFAULT_TIMEOUT = 60


class ShellTool(BaseTool):
    name = "shell"
    description = "Execute a shell command in the project directory. Commands run with a timeout."

    def __init__(self, project_root: Path, timeout: int = DEFAULT_TIMEOUT) -> None:
        self._root = project_root.resolve()
        self._timeout = timeout

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default {self._timeout})",
                },
            },
            "required": ["command"],
        }

    def execute(self, **kwargs: Any) -> str:
        command = kwargs["command"]
        timeout = kwargs.get("timeout", self._timeout)

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            output_parts: list[str] = []
            if result.stdout:
                output_parts.append(result.stdout)
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")
            output_parts.append(f"Exit code: {result.returncode}")

            output = "\n".join(output_parts)
            # Truncate very long output
            if len(output) > 10000:
                output = output[:10000] + "\n... (truncated)"
            return output

        except subprocess.TimeoutExpired:
            return f"Error: command timed out after {timeout}s"
        except Exception as e:
            return f"Error executing command: {e}"
