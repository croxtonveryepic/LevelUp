"""Run tests and parse results tool."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from levelup.core.context import TestResult
from levelup.tools.base import BaseTool

DEFAULT_TIMEOUT = 120


class TestRunnerTool(BaseTool):
    name = "test_runner"
    description = "Run the project's test suite and return structured results."

    def __init__(
        self, project_root: Path, test_command: str | None = None, timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        self._root = project_root.resolve()
        self._test_command = test_command
        self._timeout = timeout

    def get_input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Test command to run (overrides default if set)",
                },
                "timeout": {
                    "type": "integer",
                    "description": f"Timeout in seconds (default {self._timeout})",
                },
            },
        }

    def execute(self, **kwargs: Any) -> str:
        command = kwargs.get("command") or self._test_command
        if not command:
            return "Error: no test command configured. Pass a command or set test_command."

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

            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n{result.stderr}"

            # Truncate very long output
            if len(output) > 10000:
                output = output[:10000] + "\n... (truncated)"

            test_result = _parse_test_output(output, result.returncode, command)

            # Return both structured summary and raw output
            summary = (
                f"Tests {'PASSED' if test_result.passed else 'FAILED'}: "
                f"{test_result.total} total, {test_result.failures} failures, "
                f"{test_result.errors} errors\n\n{output}"
            )
            return summary

        except subprocess.TimeoutExpired:
            return f"Error: tests timed out after {timeout}s"
        except Exception as e:
            return f"Error running tests: {e}"

    def run_and_parse(self, command: str | None = None) -> TestResult:
        """Run tests and return a structured TestResult."""
        cmd = command or self._test_command
        if not cmd:
            return TestResult(passed=False, output="No test command configured", command="")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self._root),
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
            output = result.stdout + ("\n" + result.stderr if result.stderr else "")
            return _parse_test_output(output, result.returncode, cmd)
        except subprocess.TimeoutExpired:
            return TestResult(passed=False, output=f"Timed out after {self._timeout}s", command=cmd)
        except Exception as e:
            return TestResult(passed=False, output=str(e), command=cmd)


def _extract_number_before(text: str, keyword: str) -> int | None:
    """Extract the integer immediately before a keyword in text.

    E.g. _extract_number_before("3 passed", "passed") -> 3
         _extract_number_before("===== 3 passed", "passed") -> 3
    """
    import re

    pattern = rf"(\d+)\s+{re.escape(keyword)}"
    match = re.search(pattern, text)
    if match:
        return int(match.group(1))
    return None


def _parse_test_output(output: str, returncode: int, command: str) -> TestResult:
    """Best-effort parse of test output for common test runners."""
    passed = returncode == 0
    total = 0
    failures = 0
    errors = 0

    for line in output.splitlines():
        line_lower = line.lower().strip()

        # jest/mocha style: "Tests: 2 failed, 8 passed, 10 total"
        # Check this FIRST since it has an explicit "total" field
        if "tests:" in line_lower and "total" in line_lower:
            t = _extract_number_before(line_lower, "total")
            f = _extract_number_before(line_lower, "failed")
            if t is not None:
                total = t
            if f is not None:
                failures = f
            break

        # pytest style: "3 passed, 2 failed" or "4 passed, 1 failed, 2 error"
        if "passed" in line_lower and ("failed" in line_lower or "error" in line_lower):
            p = _extract_number_before(line_lower, "passed") or 0
            f = _extract_number_before(line_lower, "failed") or 0
            e = _extract_number_before(line_lower, "error") or 0
            failures = f
            errors = e
            total = p + f + e
            break

        # pytest style: "5 passed" (no failures)
        if "passed" in line_lower and "failed" not in line_lower:
            p = _extract_number_before(line_lower, "passed")
            if p is not None:
                total = p

    return TestResult(
        passed=passed,
        total=total,
        failures=failures,
        errors=errors,
        output=output,
        command=command,
    )
