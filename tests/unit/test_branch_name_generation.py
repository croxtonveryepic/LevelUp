"""Tests for branch name generation with placeholder substitution."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, TaskInput
from levelup.core.orchestrator import Orchestrator


class TestSanitizeTaskTitle:
    """Tests for Orchestrator._sanitize_task_title() helper method."""

    def test_converts_to_lowercase(self, tmp_path: Path):
        """Task title is converted to lowercase."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Add User Authentication")
        assert result == "add-user-authentication"

    def test_replaces_spaces_with_hyphens(self, tmp_path: Path):
        """Spaces are replaced with hyphens."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("fix bug in login flow")
        assert result == "fix-bug-in-login-flow"

    def test_replaces_special_chars_with_hyphens(self, tmp_path: Path):
        """Special characters are replaced with hyphens."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Update API (v2.0) & tests!")
        assert "-" in result
        assert "(" not in result
        assert ")" not in result
        assert "&" not in result
        assert "!" not in result

    def test_limits_length_to_50_chars(self, tmp_path: Path):
        """Title is truncated to 50 characters."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        long_title = "This is a very long task title that exceeds fifty characters and should be truncated"
        result = orch._sanitize_task_title(long_title)
        assert len(result) <= 50

    def test_removes_consecutive_hyphens(self, tmp_path: Path):
        """Consecutive hyphens are collapsed to single hyphen."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Fix  bug---in   system")
        assert "--" not in result
        assert "---" not in result

    def test_strips_leading_trailing_hyphens(self, tmp_path: Path):
        """Leading and trailing hyphens are removed."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("---Fix bug---")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_handles_empty_string(self, tmp_path: Path):
        """Empty string returns sensible default."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("")
        assert result == "task" or result == ""  # Acceptable outcomes

    def test_handles_only_special_chars(self, tmp_path: Path):
        """String with only special characters returns sensible default."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("@#$%^&*()")
        assert result.replace("-", "") == "" or result == "task"


class TestBuildBranchName:
    """Tests for Orchestrator._build_branch_name() helper method."""

    def test_substitutes_run_id(self, tmp_path: Path):
        """Substitutes {run_id} placeholder with context run_id."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test task"),
            run_id="abc123def456",
        )

        result = orch._build_branch_name("levelup/{run_id}", ctx)
        assert result == "levelup/abc123def456"

    def test_substitutes_task_title(self, tmp_path: Path):
        """Substitutes {task_title} placeholder with sanitized task title."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Add User Login"),
        )

        result = orch._build_branch_name("feature/{task_title}", ctx)
        assert result == "feature/add-user-login"

    def test_substitutes_date(self, tmp_path: Path):
        """Substitutes {date} placeholder with current date in YYYYMMDD format."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._build_branch_name("ai/{date}", ctx)
        today = datetime.now().strftime("%Y%m%d")
        assert result == f"ai/{today}"

    def test_substitutes_multiple_placeholders(self, tmp_path: Path):
        """Substitutes multiple placeholders in single pattern."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Fix Bug"),
            run_id="xyz789",
        )

        result = orch._build_branch_name("dev/{date}/{run_id}/{task_title}", ctx)
        today = datetime.now().strftime("%Y%m%d")
        assert result == f"dev/{today}/xyz789/fix-bug"

    def test_handles_pattern_without_placeholders(self, tmp_path: Path):
        """Returns pattern as-is when no placeholders present."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._build_branch_name("custom-branch-name", ctx)
        assert result == "custom-branch-name"

    def test_falls_back_to_default_on_invalid_pattern(self, tmp_path: Path):
        """Falls back to 'levelup/{run_id}' when pattern substitution fails."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            run_id="abc123",
        )

        # Pattern with invalid placeholder
        result = orch._build_branch_name("branch/{invalid_placeholder}", ctx)
        # Should either keep the invalid pattern or fall back to default
        assert result == "branch/{invalid_placeholder}" or result == "levelup/abc123"

    def test_handles_empty_pattern(self, tmp_path: Path):
        """Falls back to default pattern when convention is empty."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            run_id="abc123",
        )

        result = orch._build_branch_name("", ctx)
        assert result == "levelup/abc123"


class TestBranchNameIntegration:
    """Integration tests for full branch name generation flow."""

    def test_default_convention_levelup_run_id(self, tmp_path: Path):
        """Default convention produces 'levelup/{run_id}' branch names."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Add feature"),
            run_id="testrun123",
        )

        # Simulate default convention
        result = orch._build_branch_name("levelup/{run_id}", ctx)
        assert result == "levelup/testrun123"

    def test_feature_task_title_convention(self, tmp_path: Path):
        """feature/{task_title} convention produces sanitized branch names."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Implement OAuth 2.0 Authentication"),
        )

        result = orch._build_branch_name("feature/{task_title}", ctx)
        assert result.startswith("feature/")
        assert "oauth" in result.lower()
        assert "authentication" in result.lower()
        assert " " not in result
        assert "." not in result

    def test_complex_convention_with_all_placeholders(self, tmp_path: Path):
        """Complex convention with all placeholders works correctly."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Fix critical bug"),
            run_id="urgent001",
        )

        result = orch._build_branch_name("hotfix/{date}-{run_id}-{task_title}", ctx)
        today = datetime.now().strftime("%Y%m%d")
        assert result == f"hotfix/{today}-urgent001-fix-critical-bug"

    def test_convention_persists_across_sanitization(self, tmp_path: Path):
        """Branch name convention structure preserved after sanitization."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Update API & Add Tests!!!"),
        )

        result = orch._build_branch_name("dev/{task_title}", ctx)
        assert result.startswith("dev/")
        assert "api" in result
        assert "tests" in result
        # Special chars should be sanitized
        assert "&" not in result
        assert "!" not in result
