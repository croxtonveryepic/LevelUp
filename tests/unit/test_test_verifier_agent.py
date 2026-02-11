"""Unit tests for TestVerifierAgent."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.agents.backend import AgentResult, Backend
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput, TestResult


@pytest.fixture()
def basic_ctx(tmp_path: Path) -> PipelineContext:
    """A minimal pipeline context for test verifier tests."""
    return PipelineContext(
        task=TaskInput(title="Add login", description="Implement login"),
        project_path=tmp_path,
        language="python",
        framework="fastapi",
        test_runner="pytest",
        test_command="pytest tests/",
    )


@pytest.fixture()
def mock_backend() -> MagicMock:
    """A MagicMock standing in for Backend."""
    backend = MagicMock(spec=Backend)
    return backend


class TestTestVerifierAgent:
    """Tests for the TestVerifierAgent that verifies tests fail before implementation."""

    def test_agent_exists_and_has_correct_name(self, mock_backend, tmp_path):
        """TestVerifierAgent class exists and has name 'test_verifier'."""
        from levelup.agents.test_verifier import TestVerifierAgent

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        assert agent.name == "test_verifier"

    def test_agent_extends_base_agent(self, mock_backend, tmp_path):
        """TestVerifierAgent extends BaseAgent."""
        from levelup.agents.base import BaseAgent
        from levelup.agents.test_verifier import TestVerifierAgent

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        assert isinstance(agent, BaseAgent)

    def test_get_system_prompt_contains_verification_purpose(self, mock_backend, tmp_path, basic_ctx):
        """System prompt explains the agent's role in verifying TDD red phase."""
        from levelup.agents.test_verifier import TestVerifierAgent

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        prompt = agent.get_system_prompt(basic_ctx)

        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "verify" in prompt.lower() or "red" in prompt.lower() or "fail" in prompt.lower()
        assert "test" in prompt.lower()

    def test_get_allowed_tools_includes_bash(self, mock_backend, tmp_path):
        """Agent needs Bash tool to run tests."""
        from levelup.agents.test_verifier import TestVerifierAgent

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        tools = agent.get_allowed_tools()

        assert "Bash" in tools

    def test_get_allowed_tools_includes_read(self, mock_backend, tmp_path):
        """Agent may need Read tool to examine test output."""
        from levelup.agents.test_verifier import TestVerifierAgent

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        tools = agent.get_allowed_tools()

        assert "Read" in tools

    @patch("subprocess.run")
    def test_run_verifies_tests_fail_with_nonzero_exit_code(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """When tests fail (exit code != 0), agent marks verification as passed."""
        from levelup.agents.test_verifier import TestVerifierAgent

        # Mock subprocess to return non-zero exit code (test failure)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Verification should pass when tests fail (TDD red phase is correct)
        assert hasattr(ctx, "test_verification_passed")
        assert ctx.test_verification_passed is True
        assert ctx.status != PipelineStatus.FAILED

    @patch("subprocess.run")
    def test_run_fails_when_tests_pass_unexpectedly(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """When tests pass (exit code 0), agent marks verification as failed and sets error status."""
        from levelup.agents.test_verifier import TestVerifierAgent

        # Mock subprocess to return zero exit code (test success - BAD in TDD red phase!)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5 passed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Verification should fail when tests pass before implementation
        assert hasattr(ctx, "test_verification_passed")
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED
        assert ctx.error_message is not None
        assert "passed before implementation" in ctx.error_message.lower()

    @patch("subprocess.run")
    def test_run_parses_test_output_for_failure_count(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent parses test output to extract failure count."""
        from levelup.agents.test_verifier import TestVerifierAgent

        # Mock subprocess with pytest-style output
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "===== 3 passed, 5 failed in 2.3s ====="
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Agent should extract the failure count
        assert ctx.test_verification_passed is True
        # Result text should mention failure count for user visibility
        assert "5" in result.text or "failed" in result.text.lower()

    @patch("subprocess.run")
    def test_run_handles_test_command_from_context(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent uses test_command from context to run tests."""
        from levelup.agents.test_verifier import TestVerifierAgent

        basic_ctx.test_command = "npm test"

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "2 failed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        agent.run(basic_ctx)

        # Verify subprocess was called with the correct command
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert "npm test" in str(call_args)

    @patch("subprocess.run")
    def test_run_handles_missing_test_command(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent handles case where test_command is None or empty."""
        from levelup.agents.test_verifier import TestVerifierAgent

        basic_ctx.test_command = None

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail gracefully
        assert ctx.status == PipelineStatus.FAILED
        assert "test command" in ctx.error_message.lower()

    @patch("subprocess.run")
    def test_run_detects_syntax_errors_vs_test_failures(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent distinguishes between actual test failures and syntax errors."""
        from levelup.agents.test_verifier import TestVerifierAgent

        # Mock subprocess with syntax error output (no test results)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "SyntaxError: invalid syntax"
        mock_result.stderr = "ERROR: could not import module"
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail verification because tests didn't actually run
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED
        assert "syntax" in ctx.error_message.lower() or "error" in ctx.error_message.lower()

    @patch("subprocess.run")
    def test_run_detects_skipped_tests(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent detects when tests are skipped rather than failing."""
        from levelup.agents.test_verifier import TestVerifierAgent

        # Mock subprocess with all tests skipped
        mock_result = MagicMock()
        mock_result.returncode = 5  # pytest uses exit code 5 for all tests skipped
        mock_result.stdout = "===== 10 skipped in 0.5s ====="
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail verification because tests didn't actually fail (just skipped)
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED
        assert "skip" in ctx.error_message.lower()

    @patch("subprocess.run")
    def test_run_returns_agent_result_with_text(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent returns AgentResult with descriptive text."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "3 failed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        assert isinstance(result, AgentResult)
        assert isinstance(result.text, str)
        assert len(result.text) > 0
        assert "fail" in result.text.lower() or "correct" in result.text.lower()

    @patch("subprocess.run")
    def test_run_updates_context_with_verification_results(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent updates context with test_verification_passed field."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "2 failed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Context should have the verification result
        assert hasattr(ctx, "test_verification_passed")
        assert isinstance(ctx.test_verification_passed, bool)

    @patch("subprocess.run")
    def test_run_handles_subprocess_timeout(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent handles subprocess timeout gracefully."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_subprocess.side_effect = subprocess.TimeoutExpired("pytest", 120)

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail verification with timeout message
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED
        assert "timeout" in ctx.error_message.lower()

    @patch("subprocess.run")
    def test_run_handles_subprocess_exception(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent handles subprocess exceptions gracefully."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_subprocess.side_effect = OSError("Command not found")

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail verification with error message
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED
        assert ctx.error_message is not None

    @patch("subprocess.run")
    def test_run_uses_project_path_as_cwd(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent runs tests with project_path as working directory."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        agent.run(basic_ctx)

        # Verify subprocess was called with correct cwd
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args.kwargs
        assert call_kwargs.get("cwd") == str(tmp_path)

    @patch("subprocess.run")
    def test_run_captures_stdout_and_stderr(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Agent captures both stdout and stderr for analysis."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Test output"
        mock_result.stderr = "Warning message"
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        agent.run(basic_ctx)

        # Verify subprocess was called with capture_output=True
        mock_subprocess.assert_called_once()
        call_kwargs = mock_subprocess.call_args.kwargs
        assert call_kwargs.get("capture_output") is True
        assert call_kwargs.get("text") is True

    @patch("subprocess.run")
    def test_run_with_zero_failures_is_invalid(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """When tests report 0 failures but exit code is 0, verification fails."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "===== 0 failed, 10 passed ====="
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should fail because tests passed (no failures)
        assert ctx.test_verification_passed is False
        assert ctx.status == PipelineStatus.FAILED

    @patch("subprocess.run")
    def test_run_with_multiple_test_failures_passes_verification(
        self, mock_subprocess, mock_backend, tmp_path, basic_ctx
    ):
        """Multiple test failures correctly indicate TDD red phase."""
        from levelup.agents.test_verifier import TestVerifierAgent

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "===== 2 passed, 15 failed in 5.2s ====="
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        agent = TestVerifierAgent(backend=mock_backend, project_path=tmp_path)
        ctx, result = agent.run(basic_ctx)

        # Should pass verification (tests are failing as expected in red phase)
        assert ctx.test_verification_passed is True
        assert ctx.status != PipelineStatus.FAILED
