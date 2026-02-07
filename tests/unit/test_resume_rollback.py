"""Tests for resume and rollback features (orchestrator + CLI)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.state.models import RunRecord

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path) -> LevelUpSettings:
    return LevelUpSettings(
        llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(require_checkpoints=False, create_git_branch=False),
    )


def _make_ctx(tmp_path: Path, **overrides) -> PipelineContext:
    """Build a PipelineContext with sensible defaults, applying overrides."""
    defaults = dict(
        task=TaskInput(title="Test task", description="A test"),
        project_path=tmp_path,
        status=PipelineStatus.FAILED,
        current_step="coding",
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


# ---------------------------------------------------------------------------
# Orchestrator.resume() tests
# ---------------------------------------------------------------------------


class TestOrchestratorResume:
    """Test the Orchestrator.resume() method."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_runs_remaining_steps_from_current_step(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() with no from_step uses ctx.current_step and runs remaining steps."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.COMPLETED

        # coding step uses agent "coder", review step uses "reviewer"
        called_agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert called_agent_names == ["coder", "reviewer"]

        # Detection should NOT have been called (coding is past detect)
        mock_detect.assert_not_called()

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_from_specific_step_override(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() with from_step overrides ctx.current_step."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx, from_step="planning")

        assert result.status == PipelineStatus.COMPLETED

        # planning -> test_writing -> coding -> review
        called_agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert called_agent_names == ["planning", "test_writer", "coder", "reviewer"]

        # Detection should NOT be called (planning is after detect)
        mock_detect.assert_not_called()

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_from_detect_runs_full_pipeline(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() from the detect step runs the entire pipeline."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ctx = _make_ctx(tmp_path, current_step="detect", status=PipelineStatus.FAILED)
        result = orch.resume(ctx, from_step="detect")

        assert result.status == PipelineStatus.COMPLETED
        mock_detect.assert_called_once()

        called_agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert called_agent_names == [
            "requirements", "planning", "test_writer", "coder", "reviewer"
        ]

    def test_resume_raises_for_unknown_step(self, tmp_path):
        """resume() with an invalid from_step raises ValueError."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = _make_ctx(tmp_path)
        with pytest.raises(ValueError, match="Unknown step 'nonexistent'"):
            orch.resume(ctx, from_step="nonexistent")

    def test_resume_raises_when_no_current_step(self, tmp_path):
        """resume() raises ValueError when current_step is None and no from_step."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = _make_ctx(tmp_path, current_step=None)
        with pytest.raises(ValueError, match="No step to resume from"):
            orch.resume(ctx)

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_resets_status_and_error(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() resets ctx.status to RUNNING and clears error_message."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ctx = _make_ctx(
            tmp_path,
            current_step="review",
            status=PipelineStatus.FAILED,
            error_message="Previous error",
        )
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.COMPLETED
        assert result.error_message is None

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_handles_agent_failure(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() sets FAILED status if an agent fails during resumed execution."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_on_reviewer(name, ctx):
            if name == "reviewer":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "Review failed"
            return ctx

        mock_agent.side_effect = fail_on_reviewer

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.FAILED


# ---------------------------------------------------------------------------
# CLI resume command tests
# ---------------------------------------------------------------------------


class TestCLIResume:
    """Test the `levelup resume` CLI command."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_nonexistent_run_shows_error(self, MockStateManager, _banner):
        """resume with a non-existent run ID exits with error."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = None
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume", "nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_completed_run_shows_error(self, MockStateManager, _banner):
        """resume on a completed run exits with error about status."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = RunRecord(
            run_id="abc123",
            task_title="Test task",
            project_path="/tmp/test",
            status="completed",
            started_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume", "abc123"])

        assert result.exit_code == 1
        assert "only failed or aborted" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_running_run_shows_error(self, MockStateManager, _banner):
        """resume on a still-running run exits with error."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = RunRecord(
            run_id="abc123",
            task_title="Test task",
            project_path="/tmp/test",
            status="running",
            started_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume", "abc123"])

        assert result.exit_code == 1
        assert "only failed or aborted" in result.output.lower()


# ---------------------------------------------------------------------------
# CLI rollback command tests
# ---------------------------------------------------------------------------


class TestCLIRollback:
    """Test the `levelup rollback` CLI command."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_rollback_nonexistent_run_shows_error(self, MockStateManager, _banner):
        """rollback with a non-existent run ID exits with error."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = None
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["rollback", "nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_rollback_no_pre_run_sha_shows_error(self, MockStateManager, _banner):
        """rollback when context has no pre_run_sha exits with error."""
        ctx = PipelineContext(
            task=TaskInput(title="Test task"),
            project_path=Path("/tmp/test"),
            status=PipelineStatus.FAILED,
            pre_run_sha=None,
        )

        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = RunRecord(
            run_id="abc123",
            task_title="Test task",
            project_path="/tmp/test",
            status="failed",
            context_json=ctx.model_dump_json(),
            started_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["rollback", "abc123"])

        assert result.exit_code == 1
        assert "no pre-run sha" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_rollback_no_context_json_shows_error(self, MockStateManager, _banner):
        """rollback when run record has no context_json exits with error."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = RunRecord(
            run_id="abc123",
            task_title="Test task",
            project_path="/tmp/test",
            status="failed",
            context_json=None,
            started_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
        )
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["rollback", "abc123"])

        assert result.exit_code == 1
        assert "no saved context" in result.output.lower()
