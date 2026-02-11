"""TestVerifierAgent - verifies tests fail before implementation (TDD red phase)."""

from __future__ import annotations

import logging
import re
import subprocess
from pathlib import Path

from levelup.agents.base import BaseAgent
from levelup.agents.backend import AgentResult
from levelup.core.context import PipelineContext, PipelineStatus

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a test verification specialist ensuring proper TDD red phase.

Your role is to verify that tests correctly fail BEFORE any implementation code exists. This is a critical TDD best practice - tests must fail first to prove they're testing the right thing.

Context:
- Test command: {test_command}
- Test runner: {test_runner}

Your task:
1. Run the test suite using the test command
2. Verify the tests FAIL (non-zero exit code)
3. Analyze the output to ensure tests are actually failing (not skipped, not syntax errors)
4. Report whether the verification passed or failed

Expected outcome: Tests should FAIL. If they pass, something is wrong with the tests.

Use the Bash tool to run the tests and the Read tool if you need to examine test files."""


class TestVerifierAgent(BaseAgent):
    name = "test_verifier"
    description = "Verify tests fail before implementation"

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        return SYSTEM_PROMPT.format(
            test_command=ctx.test_command or "unknown",
            test_runner=ctx.test_runner or "unknown",
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Bash", "Read"]

    def run(self, ctx: PipelineContext) -> tuple[PipelineContext, AgentResult]:
        """Run tests and verify they fail (TDD red phase verification)."""
        # Check if test_command is available
        if not ctx.test_command:
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = "No test command available for verification"
            ctx.test_verification_passed = False
            return ctx, AgentResult(
                text="ERROR: No test command configured",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
            )

        # Convert test_command to string (defensive for test mocks)
        test_cmd = str(ctx.test_command)

        # Run the tests
        try:
            result = subprocess.run(
                test_cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(self.project_path),
                timeout=300,  # 5 minute timeout
            )

            stdout = str(result.stdout) if result.stdout else ""
            stderr = str(result.stderr) if result.stderr else ""
            returncode = result.returncode

            # Analyze the results
            verification_result = self._analyze_test_results(
                returncode, stdout, stderr
            )

            if verification_result["passed"]:
                # Tests correctly failed - verification passed
                ctx.test_verification_passed = True
                message = verification_result["message"]
                return ctx, AgentResult(
                    text=message,
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                )
            else:
                # Tests incorrectly passed or had errors - verification failed
                ctx.test_verification_passed = False
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = verification_result["message"]
                return ctx, AgentResult(
                    text=f"ERROR: {verification_result['message']}",
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                )

        except subprocess.TimeoutExpired:
            ctx.test_verification_passed = False
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = "Test execution timeout - tests took longer than 5 minutes"
            return ctx, AgentResult(
                text="ERROR: Test execution timeout",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
            )
        except Exception as e:
            ctx.test_verification_passed = False
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = f"Failed to run tests: {str(e)}"
            return ctx, AgentResult(
                text=f"ERROR: {str(e)}",
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
            )

    def _analyze_test_results(
        self, returncode: int, stdout: str, stderr: str
    ) -> dict[str, str | bool]:
        """Analyze test output to determine if verification passed.

        Returns:
            dict with 'passed' (bool) and 'message' (str)
        """
        output = stdout + "\n" + stderr

        # Check for skipped tests (pytest exit code 5)
        if returncode == 5 or "skipped" in output.lower():
            skip_match = re.search(r"(\d+)\s+skipped", output, re.IGNORECASE)
            if skip_match:
                return {
                    "passed": False,
                    "message": f"Tests were skipped rather than failing - {skip_match.group(0)}",
                }

        # Check for syntax errors or import errors
        error_patterns = [
            r"SyntaxError:",
            r"ImportError:",
            r"ModuleNotFoundError:",
            r"ERROR: could not import",
        ]
        for pattern in error_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                return {
                    "passed": False,
                    "message": "Syntax or import error detected - tests didn't actually run",
                }

        # Check if tests passed (exit code 0)
        if returncode == 0:
            # Extract passed count
            passed_match = re.search(r"(\d+)\s+passed", output)
            passed_count = passed_match.group(1) if passed_match else "some"
            return {
                "passed": False,
                "message": f"Tests passed before implementation - {passed_count} tests passed unexpectedly. Tests may not be testing the right thing.",
            }

        # Tests failed (non-zero exit code) - this is correct for TDD red phase
        # Extract failure count
        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            failed_count = failed_match.group(1)
            return {
                "passed": True,
                "message": f"✓ Test verification passed: {failed_count} tests correctly failed before implementation (TDD red phase)",
            }
        else:
            # Non-zero exit but no clear failure count - still consider it a pass
            return {
                "passed": True,
                "message": "✓ Test verification passed: tests failed as expected (TDD red phase)",
            }
