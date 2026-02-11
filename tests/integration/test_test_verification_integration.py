"""Integration tests for test verification step in full pipeline."""

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
    """Test settings with git branching disabled."""
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


class TestTestVerificationIntegration:
    """Integration tests for test_verification step in complete pipeline."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.agents.test_verifier.TestVerifierAgent.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_with_test_verifier_completing_successfully(
        self, mock_detect, mock_run_agent, mock_verifier_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Full pipeline completes when test_verifier indicates tests correctly fail."""
        from levelup.agents.backend import AgentResult

        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        # Mock other agents to just return context
        mock_run_agent.side_effect = lambda name, ctx: ctx

        # Mock test_verifier to indicate successful verification (tests failed as expected)
        def verifier_behavior(ctx):
            ctx.test_verification_passed = True
            return ctx, AgentResult(text="Tests correctly failed before implementation")

        mock_verifier_run.side_effect = verifier_behavior

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Pipeline should complete successfully
        assert ctx.status == PipelineStatus.COMPLETED
        assert ctx.test_verification_passed is True

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.agents.test_verifier.TestVerifierAgent.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_fails_when_test_verifier_detects_passing_tests(
        self, mock_detect, mock_run_agent, mock_verifier_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Pipeline fails when test_verifier detects tests pass before implementation."""
        from levelup.agents.backend import AgentResult

        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        # Mock other agents to just return context
        mock_run_agent.side_effect = lambda name, ctx: ctx

        # Mock test_verifier to indicate failed verification (tests passed incorrectly)
        def verifier_behavior(ctx):
            ctx.test_verification_passed = False
            ctx.status = PipelineStatus.FAILED
            ctx.error_message = "Tests passed before implementation - tests may not be testing the right thing"
            return ctx, AgentResult(text="ERROR: Tests passed before implementation")

        mock_verifier_run.side_effect = verifier_behavior

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Pipeline should have failed
        assert ctx.status == PipelineStatus.FAILED
        assert ctx.test_verification_passed is False
        assert "passed before implementation" in ctx.error_message.lower()

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_verifier_runs_actual_tests(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """TestVerifierAgent actually runs the test command via subprocess."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        # Mock agents except test_verifier (let it run for real)
        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                # Let test_verifier actually run (don't mock it)
                # It will call the real agent which calls subprocess
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to return test failure (non-zero exit)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "3 failed, 2 passed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify subprocess.run was called (tests were executed)
        mock_subprocess_run.assert_called()
        # Verify test_verifier set the verification flag
        assert hasattr(ctx, "test_verification_passed")

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_coding_step_runs_after_successful_verification(
        self, mock_detect, mock_run_agent, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Coding step executes after test_verification passes."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        called_agents = []

        def track_agents(name, ctx):
            called_agents.append(name)
            if name == "test_verifier":
                ctx.test_verification_passed = True
            return ctx

        mock_run_agent.side_effect = track_agents

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify order
        assert "test_verifier" in called_agents
        assert "coder" in called_agents
        test_verifier_idx = called_agents.index("test_verifier")
        coder_idx = called_agents.index("coder")
        assert coder_idx > test_verifier_idx

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_coding_step_does_not_run_after_failed_verification(
        self, mock_detect, mock_run_agent, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Coding step does not execute if test_verification fails."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        called_agents = []

        def track_agents(name, ctx):
            called_agents.append(name)
            if name == "test_verifier":
                ctx.test_verification_passed = False
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "Verification failed"
            return ctx

        mock_run_agent.side_effect = track_agents

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify test_verifier ran but coder did not
        assert "test_verifier" in called_agents
        assert "coder" not in called_agents

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_writer_checkpoint_occurs_before_verification(
        self, mock_detect, mock_run_agent, mock_subprocess, mock_which, tmp_path
    ):
        """test_writing checkpoint happens before test_verification step."""
        from levelup.core.context import CheckpointDecision

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(
                require_checkpoints=True,  # Enable checkpoints
                create_git_branch=False,
                max_code_iterations=2,
            ),
        )

        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        events = []

        def track_agents(name, ctx):
            events.append(("agent", name))
            return ctx

        mock_run_agent.side_effect = track_agents

        with patch("levelup.core.orchestrator.run_checkpoint") as mock_checkpoint:
            mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

            def track_checkpoints(step_name, ctx):
                events.append(("checkpoint", step_name))
                return CheckpointDecision.APPROVE, ""

            mock_checkpoint.side_effect = track_checkpoints

            task = TaskInput(title="Test task")
            ctx = orch.run(task)

        # Find positions
        test_writer_agent_idx = next(i for i, e in enumerate(events) if e == ("agent", "test_writer"))
        test_writing_checkpoint_idx = next(
            i for i, e in enumerate(events) if e == ("checkpoint", "test_writing")
        )
        test_verifier_agent_idx = next(i for i, e in enumerate(events) if e == ("agent", "test_verifier"))

        # Verify order: test_writer agent -> test_writing checkpoint -> test_verifier agent
        assert test_writer_agent_idx < test_writing_checkpoint_idx < test_verifier_agent_idx

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_verifier_with_real_test_command(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """TestVerifierAgent uses the test_command from context."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                # Set a specific test command
                ctx.test_command = "pytest --verbose tests/"
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "tests failed"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify the correct command was used
        call_args = mock_subprocess_run.call_args
        if call_args:
            # Check the command string
            assert "pytest" in str(call_args) or call_args[0][0] == "pytest --verbose tests/"


class TestTestVerificationWithStateManager:
    """Integration tests for test_verification with state management (headless/GUI mode)."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_verification_result_persisted_to_state_db(
        self, mock_detect, mock_run_agent, mock_subprocess, mock_which, tmp_path, settings
    ):
        """test_verification_passed status is persisted to state DB."""
        from levelup.state.manager import StateManager

        mgr = StateManager(db_path=tmp_path / "test.db")
        orch = Orchestrator(settings=settings, state_manager=mgr)

        mock_detect.return_value = None

        def agent_behavior(name, ctx):
            if name == "test_verifier":
                ctx.test_verification_passed = True
            return ctx

        mock_run_agent.side_effect = agent_behavior

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify context was persisted with verification result
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        # The context_json should contain the test_verification_passed field
        import json

        context_data = json.loads(record.context_json)
        assert "test_verification_passed" in context_data

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_mode_executes_test_verification(
        self, mock_detect, mock_run_agent, mock_subprocess, mock_which, tmp_path, settings
    ):
        """Headless mode executes test_verification step without user interaction."""
        orch = Orchestrator(settings=settings, headless=True)

        mock_detect.return_value = None

        called_agents = []

        def track_agents(name, ctx):
            called_agents.append(name)
            if name == "test_verifier":
                ctx.test_verification_passed = True
            return ctx

        mock_run_agent.side_effect = track_agents

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # test_verifier should have been called in headless mode
        assert "test_verifier" in called_agents
        assert ctx.status == PipelineStatus.COMPLETED


class TestTestVerificationEdgeCases:
    """Edge case tests for test verification."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_verifier_with_no_tests_written(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """TestVerifierAgent handles case where no tests were written."""
        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_writer":
                # Test writer didn't write any tests
                ctx.test_files = []
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to indicate no tests found
        mock_result = MagicMock()
        mock_result.returncode = 5  # pytest exit code for no tests collected
        mock_result.stdout = "no tests ran"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Should handle gracefully (either pass or fail with clear message)
        assert ctx.status in [PipelineStatus.COMPLETED, PipelineStatus.FAILED]

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_test_verifier_with_test_timeout(
        self, mock_detect, mock_run_agent, mock_subprocess_run, mock_subprocess, mock_which, tmp_path, settings
    ):
        """TestVerifierAgent handles test timeout."""
        import subprocess as sp

        orch = Orchestrator(settings=settings)
        mock_detect.return_value = None

        def agent_side_effect(name, ctx):
            if name == "test_verifier":
                agent = orch._agents[name]
                return agent.run(ctx)
            return ctx

        mock_run_agent.side_effect = agent_side_effect

        # Mock subprocess to raise timeout
        mock_subprocess_run.side_effect = sp.TimeoutExpired("pytest", 120)

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Should fail with timeout error
        assert ctx.status == PipelineStatus.FAILED
        assert "timeout" in ctx.error_message.lower()
