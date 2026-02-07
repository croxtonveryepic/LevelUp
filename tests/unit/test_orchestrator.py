"""Tests for the Orchestrator and pipeline logic."""

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
from levelup.core.context import (
    CheckpointDecision,
    PipelineContext,
    PipelineStatus,
    Requirements,
    TaskInput,
)
from levelup.core.orchestrator import Orchestrator
from levelup.core.pipeline import DEFAULT_PIPELINE, PipelineStep, StepType


# --- Pipeline definitions ---


class TestPipelineDefinitions:
    def test_default_pipeline_has_expected_steps(self):
        names = [s.name for s in DEFAULT_PIPELINE]
        assert "detect" in names
        assert "requirements" in names
        assert "planning" in names
        assert "test_writing" in names
        assert "coding" in names
        assert "review" in names

    def test_pipeline_step_types(self):
        detect = next(s for s in DEFAULT_PIPELINE if s.name == "detect")
        assert detect.step_type == StepType.DETECTION

        reqs = next(s for s in DEFAULT_PIPELINE if s.name == "requirements")
        assert reqs.step_type == StepType.AGENT
        assert reqs.agent_name == "requirements"
        assert reqs.checkpoint_after is True

    def test_checkpoints_on_correct_steps(self):
        checkpoint_steps = [s.name for s in DEFAULT_PIPELINE if s.checkpoint_after]
        assert "requirements" in checkpoint_steps
        assert "test_writing" in checkpoint_steps
        assert "review" in checkpoint_steps
        assert "planning" not in checkpoint_steps
        assert "coding" not in checkpoint_steps

    def test_pipeline_step_frozen(self):
        step = PipelineStep(name="test", step_type=StepType.AGENT)
        with pytest.raises(AttributeError):
            step.name = "changed"


# --- Orchestrator ---


class TestOrchestrator:
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

    def test_orchestrator_creates(self, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)
        assert orch is not None

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_runs_pipeline_no_checkpoints(
        self, mock_detect, mock_agent, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fake_agent(name, ctx):
            return ctx

        mock_agent.side_effect = fake_agent

        task = TaskInput(title="Test task", description="A test")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert mock_detect.called
        assert mock_agent.call_count == 5  # 5 agent steps

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_with_checkpoints_approve(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx
        mock_checkpoint.return_value = (CheckpointDecision.APPROVE, "")

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert mock_checkpoint.call_count == 3  # 3 checkpoints

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_checkpoint_reject_aborts(
        self, mock_checkpoint, mock_detect, mock_agent, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx
        mock_checkpoint.return_value = (CheckpointDecision.REJECT, "")

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.ABORTED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_agent_failure(self, mock_detect, mock_agent, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_agent(name, ctx):
            if name == "requirements":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "API error"
            return ctx

        mock_agent.side_effect = fail_agent

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.FAILED

    def test_orchestrator_creates_with_headless(self, tmp_path):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, headless=True)
        assert orch._headless is True

    def test_orchestrator_creates_with_state_manager(self, tmp_path):
        from levelup.state.manager import StateManager

        settings = self._make_settings(tmp_path)
        mgr = StateManager(db_path=tmp_path / "test.db")
        orch = Orchestrator(settings=settings, state_manager=mgr)
        assert orch._state_manager is mgr

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_with_state_manager_persists(
        self, mock_detect, mock_agent, tmp_path
    ):
        from levelup.state.manager import StateManager

        settings = self._make_settings(tmp_path)
        mgr = StateManager(db_path=tmp_path / "test.db")
        orch = Orchestrator(settings=settings, state_manager=mgr)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.status == "completed"

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_no_checkpoints_completes(
        self, mock_detect, mock_agent, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

    def test_create_backend_claude_code(self, tmp_path):
        """Verify claude_code backend creates ClaudeCodeBackend."""
        from levelup.agents.backend import ClaudeCodeBackend
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, ClaudeCodeBackend)

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_create_backend_anthropic_sdk(self, MockAnthropic, tmp_path):
        """Verify anthropic_sdk backend creates AnthropicSDKBackend."""
        from levelup.agents.backend import AnthropicSDKBackend
        settings = self._make_settings(tmp_path, backend="anthropic_sdk")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, AnthropicSDKBackend)
