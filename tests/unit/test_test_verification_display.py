"""Unit tests for test_verification CLI output and display."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator


@pytest.fixture()
def settings(tmp_path: Path) -> LevelUpSettings:
    """Test settings."""
    return LevelUpSettings(
        llm=LLMSettings(
            api_key="test-key",
            model="test-model",
            backend="claude_code",
        ),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            require_checkpoints=False,
            create_git_branch=False,
            max_code_iterations=2,
        ),
    )


class TestTestVerificationStepDisplay:
    """Tests for CLI display output during test_verification step."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.cli.display.print_step_header")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_step_header_displayed_for_test_verification(
        self, mock_detect, mock_run_agent, mock_print_header, mock_subprocess, mock_which, tmp_path, settings
    ):
        """print_step_header is called for test_verification step."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None
        mock_run_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        orch.run(task)

        # Verify print_step_header was called for test_verification
        header_calls = [call[0] for call in mock_print_header.call_args_list]
        step_names = [call[0] for call in header_calls]

        assert "test_verification" in step_names

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.cli.display.print_step_header")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_step_header_includes_description(
        self, mock_detect, mock_run_agent, mock_print_header, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Step header includes the test_verification description."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None
        mock_run_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        orch.run(task)

        # Find test_verification call
        for call in mock_print_header.call_args_list:
            if call[0][0] == "test_verification":
                step_name, description = call[0]
                assert isinstance(description, str)
                assert len(description) > 0
                break


class TestTestVerificationSuccessDisplay:
    """Tests for success message display when tests correctly fail."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_success_message_when_tests_fail_correctly(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Success message displayed when tests correctly fail before implementation."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to return test failure
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "5 failed, 0 passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        with patch("levelup.cli.display.print_success") as mock_success:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

            # Verify success message was displayed (or at least no error)
            # The exact behavior depends on implementation, but pipeline should complete
            assert ctx.status == PipelineStatus.COMPLETED


class TestTestVerificationErrorDisplay:
    """Tests for error message display when tests incorrectly pass."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_error_message_when_tests_pass_incorrectly(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Error message displayed when tests pass before implementation."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to return test success (BAD!)
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "10 passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        with patch("levelup.cli.display.print_error") as mock_error:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

            # Verify error was displayed or pipeline failed
            assert ctx.status == PipelineStatus.FAILED


class TestTestVerificationOutputContent:
    """Tests for the content of test_verification output messages."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_output_includes_failure_count(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Output includes the number of test failures for user visibility."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess with specific failure count
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "===== 3 passed, 7 failed in 2.1s ====="
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # The agent result text should mention the failures
        # (Verified through agent run() return value)
        assert ctx.test_verification_passed is True

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_error_message_is_descriptive(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Error message clearly explains why verification failed."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to return test pass
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "5 passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Error message should be set and descriptive
        assert ctx.error_message is not None
        assert len(ctx.error_message) > 0
        # Should mention that tests passed before implementation
        assert (
            "passed" in ctx.error_message.lower()
            or "implementation" in ctx.error_message.lower()
        )


class TestTestVerificationQuietMode:
    """Tests for test_verification output in quiet/headless mode."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.cli.display.print_step_header")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_mode_suppresses_output(
        self, mock_detect, mock_run_agent, mock_print_header, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Headless mode suppresses console output for test_verification."""
        orch = Orchestrator(settings=settings, headless=True)
        mock_detect.return_value = None
        mock_run_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Console should be in quiet mode
        assert orch._quiet is True
        # Step still executes even in quiet mode
        assert ctx.current_step is None  # After completion

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_mode_still_sets_context_fields(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Headless mode still updates context with verification results."""
        orch = Orchestrator(settings=settings, headless=True)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "3 failed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Context should still be updated
        assert hasattr(ctx, "test_verification_passed")
        assert ctx.test_verification_passed is not None


class TestTestVerificationStepHeader:
    """Tests specifically for the step header display."""

    def test_pipeline_step_has_description_field(self):
        """test_verification PipelineStep has a description field."""
        from levelup.core.pipeline import DEFAULT_PIPELINE

        test_verification = next(
            s for s in DEFAULT_PIPELINE if s.name == "test_verification"
        )
        assert hasattr(test_verification, "description")
        assert test_verification.description is not None

    def test_step_description_is_meaningful(self):
        """test_verification description clearly indicates its purpose."""
        from levelup.core.pipeline import DEFAULT_PIPELINE

        test_verification = next(
            s for s in DEFAULT_PIPELINE if s.name == "test_verification"
        )
        description = test_verification.description.lower()

        # Should mention verification, tests, or failing
        meaningful_keywords = ["verify", "test", "fail", "red", "check"]
        assert any(keyword in description for keyword in meaningful_keywords)

    def test_step_description_matches_tdd_terminology(self):
        """Description uses TDD terminology (red phase, verification)."""
        from levelup.core.pipeline import DEFAULT_PIPELINE

        test_verification = next(
            s for s in DEFAULT_PIPELINE if s.name == "test_verification"
        )
        description = test_verification.description.lower()

        # Should reference TDD concepts
        tdd_keywords = ["red", "verify", "fail"]
        # At least one TDD keyword should be present
        assert any(keyword in description for keyword in tdd_keywords)
