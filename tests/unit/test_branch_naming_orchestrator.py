"""Tests for branch naming integration in Orchestrator."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.core.project_context import get_project_context_path


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
        status=PipelineStatus.RUNNING,
    )
    defaults.update(overrides)
    return PipelineContext(**defaults)


# ---------------------------------------------------------------------------
# Context field tests
# ---------------------------------------------------------------------------


class TestPipelineContextBranchNaming:
    """Tests for branch_naming field on PipelineContext."""

    def test_branch_naming_defaults_to_none(self):
        """branch_naming field defaults to None."""
        ctx = PipelineContext(task=TaskInput(title="Test"))
        assert ctx.branch_naming is None

    def test_branch_naming_can_be_set(self):
        """branch_naming field can be set and read."""
        ctx = PipelineContext(task=TaskInput(title="Test"))
        ctx.branch_naming = "feature/{task_title}"
        assert ctx.branch_naming == "feature/{task_title}"

    def test_branch_naming_in_constructor(self):
        """branch_naming can be set via constructor."""
        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            branch_naming="ai/{run_id}",
        )
        assert ctx.branch_naming == "ai/{run_id}"

    def test_branch_naming_serialization_round_trip(self):
        """branch_naming survives JSON serialization."""
        import json

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            branch_naming="custom/{date}-{run_id}",
        )

        json_str = ctx.model_dump_json()
        data = json.loads(json_str)
        restored = PipelineContext(**data)

        assert restored.branch_naming == "custom/{date}-{run_id}"


# ---------------------------------------------------------------------------
# Detection step tests
# ---------------------------------------------------------------------------


class TestDetectionLoadsBranchNaming:
    """Tests for detection step loading branch_naming into context."""

    @patch("levelup.core.orchestrator.Orchestrator._run_project_detection")
    def test_detection_loads_branch_naming_from_project_context(
        self, mock_detect, tmp_path
    ):
        """Detection step loads branch_naming from project_context.md."""
        # Set up project_context.md with branch_naming
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** feature/{task_title}\n",
            encoding="utf-8",
        )

        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path)
        mock_detect.return_value = ("Python", "none", "pytest", "pytest")

        orch._run_detection(tmp_path, ctx)

        assert ctx.branch_naming == "feature/{task_title}"

    @patch("levelup.core.orchestrator.Orchestrator._run_project_detection")
    def test_detection_sets_default_when_field_missing(self, mock_detect, tmp_path):
        """Detection sets default 'levelup/{run_id}' when field is missing."""
        # Set up project_context.md without branch_naming
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n",
            encoding="utf-8",
        )

        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path)
        mock_detect.return_value = ("Python", "none", "pytest", "pytest")

        orch._run_detection(tmp_path, ctx)

        assert ctx.branch_naming == "levelup/{run_id}"

    @patch("levelup.core.orchestrator.Orchestrator._run_project_detection")
    def test_detection_writes_branch_naming_to_project_context(
        self, mock_detect, tmp_path
    ):
        """Detection writes branch_naming to project_context.md."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, branch_naming="ai/{run_id}")
        mock_detect.return_value = ("Python", "none", "pytest", "pytest")

        orch._run_detection(tmp_path, ctx)

        path = get_project_context_path(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** ai/{run_id}" in content


# ---------------------------------------------------------------------------
# _create_git_branch with custom conventions
# ---------------------------------------------------------------------------


class TestCreateGitBranchWithConvention:
    """Tests for Orchestrator._create_git_branch() using branch naming convention (worktree-based)."""

    def test_creates_branch_with_levelup_run_id_convention(self, tmp_path):
        """Creates worktree+branch using 'levelup/{run_id}' convention."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, run_id="abc123", branch_naming="levelup/{run_id}")

        orch._create_git_branch(tmp_path, ctx)

        # Branch exists in worktree, not as main repo active branch
        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == "levelup/abc123"
        # Cleanup
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_creates_branch_with_feature_task_title_convention(self, tmp_path):
        """Creates worktree+branch using 'feature/{task_title}' convention."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(
            tmp_path,
            task=TaskInput(title="Add User Login"),
            branch_naming="feature/{task_title}",
        )

        orch._create_git_branch(tmp_path, ctx)

        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == "feature/add-user-login"
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_creates_branch_with_date_convention(self, tmp_path):
        """Creates worktree+branch using convention with {date} placeholder."""
        from datetime import datetime

        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, branch_naming="ai/{date}")

        orch._create_git_branch(tmp_path, ctx)

        today = datetime.now().strftime("%Y%m%d")
        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == f"ai/{today}"
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_creates_branch_with_complex_convention(self, tmp_path):
        """Creates worktree+branch using complex convention with multiple placeholders."""
        from datetime import datetime

        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(
            tmp_path,
            task=TaskInput(title="Fix Bug"),
            run_id="xyz789",
            branch_naming="dev/{date}/{run_id}/{task_title}",
        )

        orch._create_git_branch(tmp_path, ctx)

        today = datetime.now().strftime("%Y%m%d")
        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == f"dev/{today}/xyz789/fix-bug"
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_falls_back_to_default_when_convention_missing(self, tmp_path):
        """Falls back to 'levelup/{run_id}' when convention is None."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, run_id="testrun", branch_naming=None)

        orch._create_git_branch(tmp_path, ctx)

        wt_repo = git.Repo(ctx.worktree_path)
        assert wt_repo.active_branch.name == "levelup/testrun"
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_sanitizes_task_title_in_branch_name(self, tmp_path):
        """Sanitizes task title when creating branch name."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(
            tmp_path,
            task=TaskInput(title="Update API (v2.0) & Tests!"),
            branch_naming="feature/{task_title}",
        )

        orch._create_git_branch(tmp_path, ctx)

        wt_repo = git.Repo(ctx.worktree_path)
        branch_name = wt_repo.active_branch.name
        assert branch_name.startswith("feature/")
        # Special chars should be sanitized
        assert "(" not in branch_name
        assert ")" not in branch_name
        assert "&" not in branch_name
        assert "!" not in branch_name
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_returns_pre_run_sha_with_custom_convention(self, tmp_path):
        """Returns pre_run_sha correctly with custom convention."""
        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, branch_naming="custom/{run_id}")

        orch._create_git_branch(tmp_path, ctx)

        assert ctx.pre_run_sha == initial_sha
        repo.git.worktree("remove", str(ctx.worktree_path), "--force")

    def test_noop_when_create_git_branch_false(self, tmp_path):
        """Does nothing when create_git_branch is False."""
        repo = _init_git_repo(tmp_path)
        initial_branch = repo.active_branch.name

        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = _make_context(tmp_path, branch_naming="feature/{task_title}")

        orch._create_git_branch(tmp_path, ctx)

        # Branch should not have changed
        assert repo.active_branch.name == initial_branch


# ---------------------------------------------------------------------------
# Orchestrator.run() prompting flow
# ---------------------------------------------------------------------------


class TestOrchestratorRunPromptsBranchNaming:
    """Tests for Orchestrator.run() prompting for branch naming on first run."""

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.Orchestrator._create_git_branch")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_prompts_before_creating_branch_on_first_run(
        self,
        mock_prompt,
        mock_create_branch,
        mock_detect,
        mock_agent,
        mock_subprocess,
        mock_which,
        tmp_path,
    ):
        """Prompts for branch naming before creating git branch on first run."""
        mock_prompt.return_value = "feature/{task_title}"
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Prompt should have been called
        mock_prompt.assert_called_once()
        # Branch creation should have been called
        mock_create_branch.assert_called_once()
        # Convention should be in context
        assert ctx.branch_naming == "feature/{task_title}"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.core.orchestrator.Orchestrator._create_git_branch")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_skips_prompt_when_convention_exists(
        self,
        mock_prompt,
        mock_create_branch,
        mock_detect,
        mock_agent,
        mock_subprocess,
        mock_which,
        tmp_path,
    ):
        """Skips prompt when branch_naming already exists in project_context.md."""
        # Set up existing convention
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

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Prompt should NOT have been called
        mock_prompt.assert_not_called()
        # Convention should be loaded from file
        assert ctx.branch_naming == "ai/{run_id}"

    @patch("shutil.which", return_value="/usr/bin/claude")
    @patch("levelup.core.orchestrator.subprocess.run")
    @patch("levelup.core.orchestrator.Orchestrator._run_agent_with_retry")
    @patch("levelup.core.orchestrator.Orchestrator._run_detection")
    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_skips_prompt_when_create_git_branch_false(
        self,
        mock_prompt,
        mock_detect,
        mock_agent,
        mock_subprocess,
        mock_which,
        tmp_path,
    ):
        """Skips prompt when create_git_branch is False."""
        mock_detect.return_value = None
        mock_agent.side_effect = lambda name, ctx: ctx

        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        task = TaskInput(title="Test task")
        ctx = orch.run(task)

        # Prompt should NOT have been called
        mock_prompt.assert_not_called()
