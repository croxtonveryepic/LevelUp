"""Unit tests for test_verification step in the pipeline."""

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
from levelup.core.pipeline import DEFAULT_PIPELINE, PipelineStep, StepType


class TestPipelineTestVerificationStep:
    """Tests for the test_verification pipeline step configuration."""

    def test_test_verification_step_exists_in_default_pipeline(self):
        """test_verification step is present in DEFAULT_PIPELINE."""
        step_names = [s.name for s in DEFAULT_PIPELINE]
        assert "test_verification" in step_names

    def test_test_verification_step_positioned_after_test_writing(self):
        """test_verification step comes immediately after test_writing."""
        step_names = [s.name for s in DEFAULT_PIPELINE]
        test_writing_idx = step_names.index("test_writing")
        test_verification_idx = step_names.index("test_verification")

        assert test_verification_idx == test_writing_idx + 1

    def test_test_verification_step_positioned_before_coding(self):
        """test_verification step comes immediately before coding."""
        step_names = [s.name for s in DEFAULT_PIPELINE]
        test_verification_idx = step_names.index("test_verification")
        coding_idx = step_names.index("coding")

        assert coding_idx == test_verification_idx + 1

    def test_test_verification_step_has_correct_type(self):
        """test_verification step has step_type=StepType.AGENT."""
        test_verification = next(s for s in DEFAULT_PIPELINE if s.name == "test_verification")
        assert test_verification.step_type == StepType.AGENT

    def test_test_verification_step_has_correct_agent_name(self):
        """test_verification step has agent_name='test_verifier'."""
        test_verification = next(s for s in DEFAULT_PIPELINE if s.name == "test_verification")
        assert test_verification.agent_name == "test_verifier"

    def test_test_verification_step_has_no_checkpoint(self):
        """test_verification step has checkpoint_after=False (no user approval needed)."""
        test_verification = next(s for s in DEFAULT_PIPELINE if s.name == "test_verification")
        assert test_verification.checkpoint_after is False

    def test_test_verification_step_has_description(self):
        """test_verification step has a descriptive description."""
        test_verification = next(s for s in DEFAULT_PIPELINE if s.name == "test_verification")
        assert test_verification.description is not None
        assert len(test_verification.description) > 0
        assert "verify" in test_verification.description.lower() or "fail" in test_verification.description.lower()

    def test_pipeline_step_order_is_correct(self):
        """Verify complete pipeline order includes test_verification in correct position."""
        step_names = [s.name for s in DEFAULT_PIPELINE]

        # Expected order (partial, focusing on test-related steps)
        expected_sequence = [
            "detect",
            "requirements",
            "planning",
            "test_writing",
            "test_verification",
            "coding",
            "security",
            "review",
        ]

        assert step_names == expected_sequence

    def test_test_verification_is_not_checkpoint_step(self):
        """test_verification should not be in list of checkpoint steps."""
        checkpoint_steps = [s.name for s in DEFAULT_PIPELINE if s.checkpoint_after]
        assert "test_verification" not in checkpoint_steps

    def test_test_verification_step_is_frozen(self):
        """Pipeline steps are immutable (frozen dataclass)."""
        test_verification = next(s for s in DEFAULT_PIPELINE if s.name == "test_verification")
        with pytest.raises(AttributeError):
            test_verification.name = "changed"


class TestOrchestratorTestVerifierRegistration:
    """Tests for TestVerifierAgent registration in Orchestrator."""

    def _make_settings(self, tmp_path: Path, backend: str = "claude_code") -> LevelUpSettings:
        return LevelUpSettings(
            llm=LLMSettings(
                api_key="test-key",
                model="test-model",
                backend=backend,
            ),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(
                require_checkpoints=False,
                create_git_branch=False,
                max_code_iterations=2,
            ),
        )

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_orchestrator_registers_test_verifier_agent(
        self, mock_subprocess, mock_which, tmp_path
    ):
        """Orchestrator._register_agents() includes test_verifier agent."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        backend = orch._create_backend(tmp_path)
        orch._register_agents(backend, tmp_path)

        assert "test_verifier" in orch._agents
        assert orch._agents["test_verifier"] is not None

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_test_verifier_agent_is_correct_type(
        self, mock_subprocess, mock_which, tmp_path
    ):
        """Registered test_verifier is an instance of TestVerifierAgent."""
        from levelup.agents.test_verifier import TestVerifierAgent

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        backend = orch._create_backend(tmp_path)
        orch._register_agents(backend, tmp_path)

        assert isinstance(orch._agents["test_verifier"], TestVerifierAgent)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    def test_test_verifier_agent_receives_backend_and_path(
        self, mock_subprocess, mock_which, tmp_path
    ):
        """TestVerifierAgent is initialized with backend and project_path."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        backend = orch._create_backend(tmp_path)
        orch._register_agents(backend, tmp_path)

        agent = orch._agents["test_verifier"]
        assert agent.backend is not None
        assert agent.project_path == tmp_path


class TestOrchestratorTestVerificationExecution:
    """Integration tests for test_verification step execution in pipeline."""

    def _make_settings(self, tmp_path: Path) -> LevelUpSettings:
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

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_executes_test_verification_step(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Pipeline executes test_verification step during run."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        # Track which agents were called
        called_agents = []

        def track_agent(name, ctx):
            called_agents.append(name)
            return ctx

        mock_agent.side_effect = track_agent

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Verify test_verifier was called
        assert "test_verifier" in called_agents

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_executes_test_verification_after_test_writing(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """test_verification executes after test_writing in pipeline."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        called_agents = []

        def track_agent(name, ctx):
            called_agents.append(name)
            return ctx

        mock_agent.side_effect = track_agent

        task = TaskInput(title="Test task")
        orch.run(task)

        # Find positions
        test_writer_idx = called_agents.index("test_writer")
        test_verifier_idx = called_agents.index("test_verifier")

        assert test_verifier_idx == test_writer_idx + 1

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_executes_test_verification_before_coding(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """test_verification executes before coding in pipeline."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        called_agents = []

        def track_agent(name, ctx):
            called_agents.append(name)
            return ctx

        mock_agent.side_effect = track_agent

        task = TaskInput(title="Test task")
        orch.run(task)

        # Find positions
        test_verifier_idx = called_agents.index("test_verifier")
        coder_idx = called_agents.index("coder")

        assert coder_idx == test_verifier_idx + 1

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_stops_if_test_verification_fails(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Pipeline stops execution if test_verification marks context as FAILED."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def agent_behavior(name, ctx):
            if name == "test_verifier":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "Tests passed before implementation"
            return ctx

        mock_agent.side_effect = agent_behavior

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Pipeline should have failed
        assert ctx.status == PipelineStatus.FAILED
        # Coder should not have been called (test_verifier failed)
        call_args_list = mock_agent.call_args_list
        called_agents = [call[0][0] for call in call_args_list]
        assert "test_verifier" in called_agents
        assert "coder" not in called_agents

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_pipeline_continues_if_test_verification_passes(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Pipeline continues to coding step if test_verification passes."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def agent_behavior(name, ctx):
            if name == "test_verifier":
                ctx.test_verification_passed = True
            return ctx

        mock_agent.side_effect = agent_behavior

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Pipeline should complete successfully
        assert ctx.status == PipelineStatus.COMPLETED
        # Coder should have been called
        call_args_list = mock_agent.call_args_list
        called_agents = [call[0][0] for call in call_args_list]
        assert "test_verifier" in called_agents
        assert "coder" in called_agents

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_all_agents_called_in_successful_pipeline(
        self, mock_detect, mock_agent, mock_subprocess, mock_which, tmp_path
    ):
        """Full pipeline with test_verification includes all expected agents."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Should call 7 agents now (was 6, now includes test_verifier)
        assert mock_agent.call_count == 7

        call_args_list = mock_agent.call_args_list
        called_agents = [call[0][0] for call in call_args_list]

        expected_agents = [
            "requirements",
            "planning",
            "test_writer",
            "test_verifier",
            "coder",
            "security",
            "reviewer",
        ]
        assert called_agents == expected_agents


class TestTestVerificationContextField:
    """Tests for test_verification_passed field in PipelineContext."""

    def test_pipeline_context_has_test_verification_field(self, tmp_path):
        """PipelineContext model includes test_verification_passed field."""
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )

        # Field should exist (may be None initially or have default value)
        assert hasattr(ctx, "test_verification_passed")

    def test_test_verification_field_can_be_set_to_true(self, tmp_path):
        """test_verification_passed field can be set to True."""
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )

        ctx.test_verification_passed = True
        assert ctx.test_verification_passed is True

    def test_test_verification_field_can_be_set_to_false(self, tmp_path):
        """test_verification_passed field can be set to False."""
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )

        ctx.test_verification_passed = False
        assert ctx.test_verification_passed is False

    def test_test_verification_field_is_boolean_type(self, tmp_path):
        """test_verification_passed field is boolean or optional boolean."""
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )

        # Set to True and verify type
        ctx.test_verification_passed = True
        assert isinstance(ctx.test_verification_passed, bool)

        # Set to False and verify type
        ctx.test_verification_passed = False
        assert isinstance(ctx.test_verification_passed, bool)
