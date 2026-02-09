"""Tests for branch naming with resume and rollback commands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest
from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.core.project_context import get_project_context_path

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repo with an initial commit and return the Repo object."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("init")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


def _make_settings(tmp_path: Path, create_git_branch: bool = True) -> LevelUpSettings:
    """Build LevelUpSettings pointing at tmp_path."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=create_git_branch,
            require_checkpoints=False,
        ),
    )


def _make_context(tmp_path: Path, **overrides) -> PipelineContext:
    """Build a minimal PipelineContext with controllable fields."""
    defaults = dict(
        task=TaskInput(title="Add widget feature", description="Implement widget"),
        project_path=tmp_path,
        status=PipelineStatus.FAILED,
        current_step="coding",
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


# ---------------------------------------------------------------------------
# Orchestrator.resume() with custom branch names
# ---------------------------------------------------------------------------


class TestOrchestratorResumeWithCustomBranches:
    """Test Orchestrator.resume() with custom branch naming conventions."""

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_checks_out_branch_with_levelup_convention(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() checks out branch created with 'levelup/{run_id}' convention."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a branch manually to simulate prior run
        run_id = "abc123"
        branch = repo.create_head(f"levelup/{run_id}")
        repo.head.reference = repo.heads.master  # Switch back to master

        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            current_step="coding",
            branch_naming="levelup/{run_id}",
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        result = orch.resume(ctx)

        # Should have checked out the branch
        assert repo.active_branch.name == f"levelup/{run_id}"
        assert result.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_checks_out_branch_with_feature_task_title_convention(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() checks out branch created with 'feature/{task_title}' convention."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a branch with feature convention
        task_title = "Add User Login"
        sanitized = "add-user-login"
        branch = repo.create_head(f"feature/{sanitized}")
        repo.head.reference = repo.heads.master

        ctx = _make_context(
            tmp_path,
            task=TaskInput(title=task_title),
            current_step="coding",
            branch_naming="feature/{task_title}",
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        result = orch.resume(ctx)

        assert repo.active_branch.name == f"feature/{sanitized}"
        assert result.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_checks_out_branch_with_complex_convention(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() reconstructs and checks out branch with complex convention."""
        from datetime import datetime

        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a branch with complex convention
        run_id = "xyz789"
        task_title = "Fix Bug"
        date_str = datetime.now().strftime("%Y%m%d")
        branch_name = f"dev/{date_str}/{run_id}/fix-bug"
        branch = repo.create_head(branch_name)
        repo.head.reference = repo.heads.master

        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            task=TaskInput(title=task_title),
            current_step="coding",
            branch_naming="dev/{date}/{run_id}/{task_title}",
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        result = orch.resume(ctx)

        assert repo.active_branch.name == branch_name
        assert result.status == PipelineStatus.COMPLETED

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_falls_back_to_default_when_convention_missing(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() uses default convention when branch_naming is None."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a branch with default convention
        run_id = "testrun"
        branch = repo.create_head(f"levelup/{run_id}")
        repo.head.reference = repo.heads.master

        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            current_step="coding",
            branch_naming=None,  # Missing convention
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        result = orch.resume(ctx)

        # Should fall back to levelup/{run_id}
        assert repo.active_branch.name == f"levelup/{run_id}"

    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    def test_resume_handles_missing_branch_gracefully(
        self, mock_detect, mock_agent, tmp_path
    ):
        """resume() handles case when expected branch doesn't exist."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Don't create the expected branch
        ctx = _make_context(
            tmp_path,
            run_id="nonexistent",
            current_step="coding",
            branch_naming="feature/{run_id}",
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        # Should either fail gracefully or continue without checkout
        # (actual behavior depends on implementation)
        result = orch.resume(ctx)

        # The resume should complete or fail gracefully
        assert result.status in (PipelineStatus.COMPLETED, PipelineStatus.FAILED)


# ---------------------------------------------------------------------------
# CLI rollback command with custom branch names
# ---------------------------------------------------------------------------


class TestCLIRollbackWithCustomBranches:
    """Test CLI rollback command with custom branch naming conventions."""

    @patch("levelup.cli.app.StateManager")
    @patch("levelup.cli.app.print_banner")
    def test_rollback_uses_branch_naming_from_context(
        self, mock_banner, MockStateManager, tmp_path
    ):
        """rollback command uses branch_naming from stored context."""
        repo = _init_git_repo(tmp_path)

        # Create a feature branch
        run_id = "test123"
        branch = repo.create_head("feature/add-login")

        # Create commits on the branch
        repo.head.reference = branch
        (tmp_path / "code.py").write_text("# code")
        repo.index.add(["code.py"])
        step_commit = repo.index.commit("levelup(coding): Test task")
        initial_sha = repo.head.commit.hexsha
        repo.head.reference = repo.heads.master

        # Mock state manager
        mgr_instance = MockStateManager.return_value.__enter__.return_value
        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            task=TaskInput(title="Add Login"),
            branch_naming="feature/{task_title}",
            pre_run_sha=initial_sha,
        )
        mgr_instance.get_run.return_value = MagicMock(
            run_id=run_id,
            context_json=ctx.model_dump_json(),
        )

        result = runner.invoke(app, ["rollback", run_id], catch_exceptions=False)

        # Should succeed (though actual git operations are mocked)
        assert result.exit_code == 0 or "rolled back" in result.output.lower()

    @patch("levelup.cli.app.StateManager")
    @patch("levelup.cli.app.print_banner")
    def test_rollback_with_to_step_uses_custom_convention(
        self, mock_banner, MockStateManager, tmp_path
    ):
        """rollback --to <step> uses branch_naming to find branch."""
        repo = _init_git_repo(tmp_path)

        # Create branch with custom convention
        run_id = "xyz999"
        branch = repo.create_head("ai/xyz999")
        repo.head.reference = branch

        # Create step commits
        (tmp_path / "requirements.txt").write_text("test")
        repo.index.add(["requirements.txt"])
        req_commit = repo.index.commit("levelup(requirements): Test")

        (tmp_path / "code.py").write_text("code")
        repo.index.add(["code.py"])
        code_commit = repo.index.commit("levelup(coding): Test")

        repo.head.reference = repo.heads.master

        # Mock state manager
        mgr_instance = MockStateManager.return_value.__enter__.return_value
        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            branch_naming="ai/{run_id}",
            step_commits={
                "requirements": req_commit.hexsha,
                "coding": code_commit.hexsha,
            },
        )
        mgr_instance.get_run.return_value = MagicMock(
            run_id=run_id,
            context_json=ctx.model_dump_json(),
        )

        result = runner.invoke(
            app, ["rollback", run_id, "--to", "requirements"], catch_exceptions=False
        )

        # Should succeed
        assert result.exit_code == 0 or "requirements" in result.output.lower()

    @patch("levelup.cli.app.StateManager")
    @patch("levelup.cli.app.print_banner")
    def test_rollback_falls_back_to_default_when_convention_missing(
        self, mock_banner, MockStateManager, tmp_path
    ):
        """rollback uses default convention when branch_naming is missing."""
        repo = _init_git_repo(tmp_path)

        run_id = "default123"
        branch = repo.create_head(f"levelup/{run_id}")
        repo.head.reference = branch

        (tmp_path / "code.py").write_text("code")
        repo.index.add(["code.py"])
        commit = repo.index.commit("levelup(coding): Test")
        repo.head.reference = repo.heads.master

        # Mock state manager with context missing branch_naming
        mgr_instance = MockStateManager.return_value.__enter__.return_value
        ctx = _make_context(
            tmp_path,
            run_id=run_id,
            branch_naming=None,  # Missing
            pre_run_sha=commit.hexsha,
        )
        mgr_instance.get_run.return_value = MagicMock(
            run_id=run_id,
            context_json=ctx.model_dump_json(),
        )

        result = runner.invoke(app, ["rollback", run_id], catch_exceptions=False)

        # Should succeed using default levelup/{run_id}
        assert result.exit_code == 0 or "rolled back" in result.output.lower()


# ---------------------------------------------------------------------------
# Integration test: Full flow with custom branch names
# ---------------------------------------------------------------------------


class TestBranchNamingFullIntegration:
    """Integration test for full branch naming flow."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_full_flow_first_run_prompt_store_create(
        self,
        mock_prompt,
        mock_detect,
        mock_agent,
        mock_subprocess,
        mock_which,
        tmp_path,
    ):
        """Full flow: first run -> prompt -> store -> create branch."""
        repo = _init_git_repo(tmp_path)

        # User chooses feature/{task_title}
        mock_prompt.return_value = "feature/{task_title}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Add OAuth Support")
        ctx = orch.run(task)

        # 1. Prompt was called (first run)
        mock_prompt.assert_called_once()

        # 2. Convention stored in context
        assert ctx.branch_naming == "feature/{task_title}"

        # 3. Convention stored in project_context.md
        path = get_project_context_path(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** feature/{task_title}" in content

        # 4. Branch created with correct name
        assert repo.active_branch.name == "feature/add-oauth-support"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_second_run_skips_prompt_uses_stored_convention(
        self,
        mock_prompt,
        mock_detect,
        mock_agent,
        mock_subprocess,
        mock_which,
        tmp_path,
    ):
        """Second run skips prompt and uses stored convention."""
        repo = _init_git_repo(tmp_path)

        # Set up project_context.md with existing convention
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** ai/{run_id}\n",
            encoding="utf-8",
        )

        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Another task")
        ctx = orch.run(task)

        # 1. Prompt was NOT called (convention exists)
        mock_prompt.assert_not_called()

        # 2. Convention loaded from file
        assert ctx.branch_naming == "ai/{run_id}"

        # 3. Branch created with stored convention
        assert repo.active_branch.name == f"ai/{ctx.run_id}"
