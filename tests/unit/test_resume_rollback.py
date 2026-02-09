"""Tests for resume and rollback features (orchestrator + CLI)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.cli.prompts import pick_resumable_run
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

        # coding step uses agent "coder", security uses "security", review uses "reviewer"
        called_agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert called_agent_names == ["coder", "security", "reviewer"]

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

        # planning -> test_writing -> coding -> security -> review
        called_agent_names = [call.args[0] for call in mock_agent.call_args_list]
        assert called_agent_names == ["planning", "test_writer", "coder", "security", "reviewer"]

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
            "requirements", "planning", "test_writer", "coder", "security", "reviewer"
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
        # current_step should be preserved (not cleared) on failure
        assert result.current_step is not None

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_failed_run_preserves_current_step(
        self, mock_detect, mock_agent, tmp_path
    ):
        """After agent failure, current_step is preserved so resume can use it."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None

        def fail_on_coder(name, ctx):
            if name == "coder":
                ctx.status = PipelineStatus.FAILED
                ctx.error_message = "Coding failed"
            return ctx

        mock_agent.side_effect = fail_on_coder

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.FAILED
        assert result.current_step == "coding"

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_completed_run_clears_current_step(
        self, mock_detect, mock_agent, tmp_path
    ):
        """After successful completion, current_step is cleared to None."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.COMPLETED
        assert result.current_step is None

    @patch("levelup.core.orchestrator.shutil.which", return_value=None)
    def test_create_backend_failure_is_caught_in_run(self, _mock_which, tmp_path):
        """RuntimeError from _create_backend() is caught, sets FAILED status."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task", description="A test")
        result = orch.run(task)

        assert result.status == PipelineStatus.FAILED
        assert "not found on PATH" in result.error_message

    @patch("levelup.core.orchestrator.shutil.which", return_value=None)
    def test_create_backend_failure_is_caught_in_resume(self, _mock_which, tmp_path):
        """RuntimeError from _create_backend() in resume() is caught, sets FAILED status."""
        settings = _make_settings(tmp_path)
        orch = Orchestrator(settings=settings)

        ctx = _make_ctx(tmp_path, current_step="coding", status=PipelineStatus.FAILED)
        result = orch.resume(ctx)

        assert result.status == PipelineStatus.FAILED
        assert "not found on PATH" in result.error_message
        # current_step preserved even when backend creation fails
        assert result.current_step == "coding"


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


# ---------------------------------------------------------------------------
# Interactive resume picker tests
# ---------------------------------------------------------------------------


def _make_run_record(**overrides) -> RunRecord:
    """Build a RunRecord with sensible defaults."""
    defaults = dict(
        run_id="abc12345-6789-0000-0000-000000000000",
        task_title="Test task",
        project_path="/tmp/test",
        status="failed",
        current_step="coding",
        context_json='{"some": "json"}',
        started_at="2025-01-15T10:00:00",
        updated_at="2025-01-15T12:00:00",
    )
    defaults.update(overrides)
    return RunRecord(**defaults)


class TestResumeInteractivePicker:
    """Test the `levelup resume` (no args) interactive picker flow."""

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_no_args_no_resumable_runs(self, MockStateManager, _banner):
        """resume with no args and no resumable runs shows message and exits 0."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = []
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "no resumable runs" in result.output.lower()

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_no_args_skips_non_resumable_runs(self, MockStateManager, _banner):
        """resume with no args filters out completed/running runs."""
        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [
            _make_run_record(run_id="completed-1", status="completed"),
            _make_run_record(run_id="running-1", status="running"),
            _make_run_record(run_id="no-ctx", status="failed", context_json=None),
        ]
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume"])

        assert result.exit_code == 0
        assert "no resumable runs" in result.output.lower()

    @patch("levelup.cli.prompts.pick_resumable_run")
    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_no_args_shows_picker(self, MockStateManager, _banner, mock_picker):
        """resume with no args calls picker and proceeds with selected run."""
        ctx = _make_ctx(Path("/tmp/test"), current_step="coding", status=PipelineStatus.FAILED)
        selected_run = _make_run_record(
            run_id="selected-run",
            status="failed",
            context_json=ctx.model_dump_json(),
        )

        mock_mgr = MagicMock()
        mock_mgr.list_runs.return_value = [
            selected_run,
            _make_run_record(run_id="completed-1", status="completed"),
        ]
        mock_mgr.get_run.return_value = selected_run
        MockStateManager.return_value = mock_mgr
        mock_picker.return_value = selected_run

        with patch("levelup.config.loader.load_settings") as mock_load, \
             patch("levelup.core.orchestrator.Orchestrator") as MockOrch:
            mock_settings = MagicMock()
            mock_settings.llm.backend = "claude_code"
            mock_load.return_value = mock_settings
            mock_orch_inst = MagicMock()
            mock_orch_inst.resume.return_value = ctx
            MockOrch.return_value = mock_orch_inst

            result = runner.invoke(app, ["resume"])

        mock_picker.assert_called_once()
        picked_runs = mock_picker.call_args[0][0]
        assert len(picked_runs) == 1
        assert picked_runs[0].run_id == "selected-run"

    @patch("levelup.cli.app.print_banner")
    @patch("levelup.state.manager.StateManager")
    def test_resume_with_explicit_id_still_works(self, MockStateManager, _banner):
        """resume with explicit run_id still works as before."""
        mock_mgr = MagicMock()
        mock_mgr.get_run.return_value = None
        MockStateManager.return_value = mock_mgr

        result = runner.invoke(app, ["resume", "nonexistent-id"])

        assert result.exit_code == 1
        assert "not found" in result.output.lower()


class TestPickResumableRun:
    """Test the pick_resumable_run() prompt function directly."""

    @patch("levelup.cli.prompts.pt_prompt", return_value="1")
    def test_pick_first_run(self, _mock_prompt):
        """Typing '1' selects the first run."""
        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_resumable_run(runs)
        assert selected.run_id == "run-aaa"

    @patch("levelup.cli.prompts.pt_prompt", return_value="2")
    def test_pick_second_run(self, _mock_prompt):
        """Typing '2' selects the second run."""
        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_resumable_run(runs)
        assert selected.run_id == "run-bbb"

    @patch("levelup.cli.prompts.pt_prompt", return_value="q")
    def test_pick_quit_raises_keyboard_interrupt(self, _mock_prompt):
        """Typing 'q' raises KeyboardInterrupt."""
        runs = [_make_run_record()]
        with pytest.raises(KeyboardInterrupt):
            pick_resumable_run(runs)

    @patch("levelup.cli.prompts.pt_prompt", side_effect=["invalid", "0", "3", "2"])
    def test_pick_retries_on_invalid_input(self, _mock_prompt):
        """Invalid inputs are retried until valid."""
        runs = [
            _make_run_record(run_id="run-aaa"),
            _make_run_record(run_id="run-bbb"),
        ]
        selected = pick_resumable_run(runs)
        assert selected.run_id == "run-bbb"
        assert _mock_prompt.call_count == 4
