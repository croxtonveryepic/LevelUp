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
    FileChange,
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
        assert "security" in names
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
        assert "security" in checkpoint_steps
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

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_runs_pipeline_no_checkpoints(
        self, mock_detect, mock_agent, mock_which, tmp_path
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
        assert mock_agent.call_count == 6  # 6 agent steps (requirements, planning, test_writer, coder, security, reviewer)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_with_checkpoints_approve(
        self, mock_checkpoint, mock_detect, mock_agent, mock_which, tmp_path
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
        assert mock_checkpoint.call_count == 4  # 4 checkpoints (requirements, test_writing, security, review)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_orchestrator_checkpoint_reject_aborts(
        self, mock_checkpoint, mock_detect, mock_agent, mock_which, tmp_path
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

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_agent_failure(self, mock_detect, mock_agent, mock_which, tmp_path):
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

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_orchestrator_with_state_manager_persists(
        self, mock_detect, mock_agent, mock_which, tmp_path
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

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_headless_no_checkpoints_completes(
        self, mock_detect, mock_agent, mock_which, tmp_path
    ):
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings, headless=True)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_create_backend_claude_code(self, mock_which, tmp_path):
        """Verify claude_code backend creates ClaudeCodeBackend."""
        from levelup.agents.backend import ClaudeCodeBackend
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, ClaudeCodeBackend)

    @patch("shutil.which", return_value=None)
    def test_create_backend_claude_code_missing_executable(self, mock_which, tmp_path):
        """Raise RuntimeError when claude executable is not found on PATH."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        with pytest.raises(RuntimeError, match="executable not found on PATH"):
            orch._create_backend(tmp_path)

    @patch("shutil.which", return_value=None)
    def test_create_backend_missing_executable_shows_workarounds(self, mock_which, tmp_path):
        """Error message includes install link, config path, env var, and alt backend."""
        settings = self._make_settings(tmp_path, backend="claude_code")
        orch = Orchestrator(settings=settings)
        with pytest.raises(RuntimeError, match="Install Claude Code") as exc_info:
            orch._create_backend(tmp_path)
        msg = str(exc_info.value)
        assert "claude_executable" in msg
        assert "LEVELUP_LLM__CLAUDE_EXECUTABLE" in msg
        assert "anthropic_sdk" in msg

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_create_backend_anthropic_sdk(self, MockAnthropic, tmp_path):
        """Verify anthropic_sdk backend creates AnthropicSDKBackend."""
        from levelup.agents.backend import AnthropicSDKBackend
        settings = self._make_settings(tmp_path, backend="anthropic_sdk")
        orch = Orchestrator(settings=settings)
        backend = orch._create_backend(tmp_path)
        assert isinstance(backend, AnthropicSDKBackend)

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.run_checkpoint")
    def test_instruct_at_checkpoint_loops_then_approves(
        self, mock_checkpoint, mock_detect, mock_agent, mock_which, tmp_path
    ):
        """INSTRUCT decision loops back; next APPROVE proceeds normally."""
        settings = self._make_settings(tmp_path)
        settings.pipeline.require_checkpoints = True
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # First checkpoint: INSTRUCT then APPROVE; rest: APPROVE
        call_count = {"n": 0}

        def checkpoint_side_effect(step_name, ctx):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return CheckpointDecision.INSTRUCT, "Use type hints"
            return CheckpointDecision.APPROVE, ""

        mock_checkpoint.side_effect = checkpoint_side_effect

        # Patch _run_instruct to avoid real backend call
        with patch.object(orch, "_run_instruct") as mock_instruct:
            task = TaskInput(title="Test task")
            ctx = orch.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # _run_instruct was called once (for the INSTRUCT at checkpoint 1)
        mock_instruct.assert_called_once()
        # Checkpoint was called 5 times: 1 INSTRUCT + 4 APPROVE (4 checkpoint steps)
        assert mock_checkpoint.call_count == 5

    def test_run_instruct_adds_rule_to_claude_md(self, tmp_path):
        """_run_instruct writes to CLAUDE.md."""
        from levelup.core.instructions import read_instructions

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        journal = MagicMock()

        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        rules = read_instructions(tmp_path)
        assert "Use type hints" in rules
        journal.log_instruct.assert_called_once()

    def test_run_instruct_skips_review_when_no_files(self, tmp_path):
        """_run_instruct skips review agent when there are no changed files."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
        )
        journal = MagicMock()

        # No pre_run_sha, no code_files, no test_files → no changed files
        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        # Should still log the instruction
        journal.log_instruct.assert_called_once_with("Use type hints")

    def test_run_instruct_tracks_usage(self, tmp_path):
        """_run_instruct captures usage into ctx.step_usage."""
        from levelup.agents.backend import AgentResult

        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        # Set up a mock backend
        mock_backend = MagicMock()
        mock_backend.run_agent.return_value = AgentResult(
            text="Fixed", cost_usd=0.01, input_tokens=100, output_tokens=50,
        )
        orch._backend = mock_backend

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            code_files=[FileChange(path="src/foo.py", content="x = 1")],
        )
        journal = MagicMock()

        orch._run_instruct(ctx, "Use type hints", tmp_path, journal)

        assert "instruct_review" in ctx.step_usage
        assert ctx.step_usage["instruct_review"].cost_usd == 0.01

    def test_get_changed_files_from_context(self, tmp_path):
        """_get_changed_files falls back to context when no git."""
        settings = self._make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            project_path=tmp_path,
            code_files=[
                FileChange(path="src/a.py", content=""),
                FileChange(path="src/b.py", content=""),
            ],
            test_files=[FileChange(path="tests/test_a.py", content="")],
        )
        files = orch._get_changed_files(ctx, tmp_path)
        assert set(files) == {"src/a.py", "src/b.py", "tests/test_a.py"}
