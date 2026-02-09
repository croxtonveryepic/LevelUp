"""Subprocess client for `claude -p` invocations."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class ClaudeCodeError(Exception):
    """Raised when a `claude -p` subprocess fails."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = "") -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stderr = stderr


@dataclass
class ClaudeCodeResult:
    """Parsed result from a `claude -p` invocation."""

    text: str = ""
    session_id: str = ""
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    num_turns: int = 0
    is_error: bool = False
    returncode: int = 0
    stderr: str = ""


class ClaudeCodeClient:
    """Spawns `claude -p` subprocesses and parses JSON results."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-5-20250929",
        claude_executable: str = "claude",
    ) -> None:
        self._model = model
        resolved = shutil.which(claude_executable)
        self._claude_executable = resolved or claude_executable

    def run(
        self,
        prompt: str,
        system_prompt: str = "",
        allowed_tools: list[str] | None = None,
        working_directory: str | None = None,
        timeout: int = 600,
    ) -> ClaudeCodeResult:
        """Run a `claude -p` subprocess and return the parsed result.

        Args:
            prompt: The user prompt (passed via stdin).
            system_prompt: System prompt for the agent.
            allowed_tools: List of Claude Code tool names to allow.
            working_directory: Working directory for file sandboxing.
            timeout: Timeout in seconds (default 600).

        Returns:
            ClaudeCodeResult with parsed response.

        Raises:
            ClaudeCodeError: On subprocess failures, timeouts, or parse errors.
        """
        cmd = [
            self._claude_executable,
            "-p",
            "--output-format", "json",
            "--model", self._model,
        ]

        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        if allowed_tools:
            cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        logger.debug("Running: %s (cwd=%s)", " ".join(cmd), working_directory)

        try:
            proc = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=timeout,
                cwd=working_directory,
            )
        except FileNotFoundError:
            if working_directory and not Path(working_directory).is_dir():
                raise ClaudeCodeError(
                    f"Working directory does not exist: {working_directory}",
                    returncode=-1,
                )
            raise ClaudeCodeError(
                f"'{self._claude_executable}' not found.\n"
                "  - Install Claude Code: https://docs.anthropic.com/en/docs/claude-code\n"
                "  - Or set a custom path in levelup.yaml:  llm: { claude_executable: /path/to/claude }\n"
                "  - Or use env var: LEVELUP_LLM__CLAUDE_EXECUTABLE=/path/to/claude\n"
                "  - Or switch backend: llm: { backend: anthropic_sdk }",
                returncode=-1,
            )
        except subprocess.TimeoutExpired:
            raise ClaudeCodeError(
                f"claude -p timed out after {timeout}s",
                returncode=-1,
            )

        stderr = proc.stderr.strip() if proc.stderr else ""

        if proc.returncode != 0:
            raise ClaudeCodeError(
                f"claude -p exited with code {proc.returncode}: {stderr}",
                returncode=proc.returncode,
                stderr=stderr,
            )

        stdout = proc.stdout.strip() if proc.stdout else ""
        if not stdout:
            raise ClaudeCodeError(
                "claude -p returned empty output",
                returncode=proc.returncode,
                stderr=stderr,
            )

        return self._parse_response(stdout, proc.returncode, stderr)

    def _parse_response(
        self, stdout: str, returncode: int, stderr: str
    ) -> ClaudeCodeResult:
        """Parse JSON response from claude -p."""
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise ClaudeCodeError(
                f"Failed to parse claude -p JSON output: {e}",
                returncode=returncode,
                stderr=stderr,
            )

        result = ClaudeCodeResult(
            text=data.get("result", ""),
            session_id=data.get("session_id", ""),
            cost_usd=data.get("cost_usd", 0.0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            duration_ms=data.get("duration_ms", 0.0),
            num_turns=data.get("num_turns", 0),
            is_error=data.get("is_error", False),
            returncode=returncode,
            stderr=stderr,
        )

        if result.is_error:
            raise ClaudeCodeError(
                f"claude -p reported error: {result.text}",
                returncode=returncode,
                stderr=stderr,
            )

        return result
