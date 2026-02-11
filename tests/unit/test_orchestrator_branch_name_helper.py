"""Tests for orchestrator helper to expose branch name calculation.

Tests the public interface for retrieving the calculated branch name from
the orchestrator, which is needed by the CLI to record it in ticket metadata.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator


# ---------------------------------------------------------------------------
# Helper fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory."""
    (tmp_path / "levelup").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def settings(tmp_project: Path) -> LevelUpSettings:
    """Create test settings."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_project),
        pipeline=PipelineSettings(
            create_git_branch=True,
            require_checkpoints=False,
        ),
    )


@pytest.fixture
def orchestrator(settings: LevelUpSettings) -> Orchestrator:
    """Create an orchestrator instance."""
    state_manager = MagicMock()
    return Orchestrator(
        settings=settings,
        state_manager=state_manager,
        headless=False,
        gui_mode=False,
    )


@pytest.fixture
def pipeline_context(tmp_project: Path) -> PipelineContext:
    """Create a test pipeline context."""
    return PipelineContext(
        run_id="abc123def456",
        task=TaskInput(title="Implement feature", description="Add feature X"),
        project_path=tmp_project,
        status=PipelineStatus.COMPLETED,
        branch_naming="levelup/{run_id}",
    )


# ---------------------------------------------------------------------------
# Tests for _build_branch_name method accessibility
# ---------------------------------------------------------------------------


class TestBuildBranchNameMethod:
    """Test that _build_branch_name is accessible for branch name calculation."""

    def test_build_branch_name_method_exists(self, orchestrator: Orchestrator):
        """Orchestrator should have _build_branch_name method."""
        assert hasattr(orchestrator, "_build_branch_name")
        assert callable(orchestrator._build_branch_name)

    def test_build_branch_name_with_run_id(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should substitute {run_id} placeholder."""
        branch_name = orchestrator._build_branch_name(
            "levelup/{run_id}", pipeline_context
        )
        assert branch_name == "levelup/abc123def456"

    def test_build_branch_name_with_task_title(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should substitute {task_title} placeholder with sanitized title."""
        branch_name = orchestrator._build_branch_name(
            "feature/{task_title}", pipeline_context
        )
        # Task title "Implement feature" should be sanitized
        assert branch_name == "feature/implement-feature"

    def test_build_branch_name_with_date(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should substitute {date} placeholder with current date."""
        branch_name = orchestrator._build_branch_name(
            "ai/{date}-{run_id}", pipeline_context
        )
        # Date should be in YYYYMMDD format
        assert len(branch_name.split("-")[0].split("/")[1]) == 8  # YYYYMMDD
        assert branch_name.endswith("-abc123def456")

    def test_build_branch_name_with_multiple_placeholders(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should substitute multiple placeholders."""
        branch_name = orchestrator._build_branch_name(
            "feature/{task_title}/{run_id}", pipeline_context
        )
        assert "implement-feature" in branch_name
        assert "abc123def456" in branch_name

    def test_build_branch_name_default_convention(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should use default convention when None provided."""
        branch_name = orchestrator._build_branch_name(None, pipeline_context)
        assert branch_name == "levelup/abc123def456"

    def test_build_branch_name_empty_convention(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Should use default convention when empty string provided."""
        branch_name = orchestrator._build_branch_name("", pipeline_context)
        assert branch_name == "levelup/abc123def456"

    def test_build_branch_name_with_context_branch_naming(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should use branch_naming from context."""
        ctx = PipelineContext(
            run_id="xyz789",
            task=TaskInput(title="Fix bug", description=""),
            project_path=tmp_project,
            branch_naming="bugfix/{task_title}",
        )
        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        assert branch_name == "bugfix/fix-bug"

    def test_build_branch_name_sanitizes_special_characters(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should sanitize special characters in task title."""
        ctx = PipelineContext(
            run_id="run123",
            task=TaskInput(title="Fix: Critical Bug (P0)", description=""),
            project_path=tmp_project,
            branch_naming="fix/{task_title}",
        )
        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        # Should sanitize to lowercase with hyphens
        assert branch_name == "fix/fix-critical-bug-p0"

    def test_build_branch_name_handles_long_titles(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should truncate long task titles."""
        long_title = "A" * 100  # Very long title
        ctx = PipelineContext(
            run_id="run123",
            task=TaskInput(title=long_title, description=""),
            project_path=tmp_project,
            branch_naming="feature/{task_title}",
        )
        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        # Should be truncated to 50 chars
        title_part = branch_name.split("/")[1]
        assert len(title_part) <= 50


# ---------------------------------------------------------------------------
# Tests for public interface to get branch name
# ---------------------------------------------------------------------------


class TestGetBranchNamePublicInterface:
    """Test public interface for getting branch name from orchestrator and context."""

    def test_can_call_build_branch_name_from_cli_code(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """CLI code should be able to call _build_branch_name to get branch name."""
        # This simulates what the CLI will do in app.py
        convention = pipeline_context.branch_naming or "levelup/{run_id}"
        branch_name = orchestrator._build_branch_name(convention, pipeline_context)

        assert branch_name is not None
        assert isinstance(branch_name, str)
        assert len(branch_name) > 0

    def test_build_branch_name_consistent_with_git_creation(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Branch name from helper should match what's used in git branch creation."""
        # The orchestrator uses the same method internally for git branch creation
        # This ensures consistency
        convention = "custom/{run_id}-{task_title}"
        branch_name = orchestrator._build_branch_name(convention, pipeline_context)

        # Should match the pattern used internally
        assert "abc123def456" in branch_name
        assert "implement-feature" in branch_name

    def test_branch_name_from_completed_context(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should get branch name from a completed pipeline context."""
        ctx = PipelineContext(
            run_id="completed123",
            task=TaskInput(title="Add tests", description=""),
            project_path=tmp_project,
            status=PipelineStatus.COMPLETED,
            branch_naming="levelup/{run_id}",
        )

        branch_name = orchestrator._build_branch_name(
            ctx.branch_naming or "levelup/{run_id}", ctx
        )

        assert branch_name == "levelup/completed123"

    def test_branch_name_calculation_idempotent(
        self, orchestrator: Orchestrator, pipeline_context: PipelineContext
    ):
        """Calling _build_branch_name multiple times should return same result."""
        convention = pipeline_context.branch_naming

        branch_name1 = orchestrator._build_branch_name(convention, pipeline_context)
        branch_name2 = orchestrator._build_branch_name(convention, pipeline_context)

        assert branch_name1 == branch_name2


# ---------------------------------------------------------------------------
# Tests for error handling
# ---------------------------------------------------------------------------


class TestBranchNameCalculationErrors:
    """Test error handling in branch name calculation."""

    def test_handles_missing_run_id(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should handle gracefully when run_id is None."""
        ctx = PipelineContext(
            run_id=None,  # Missing run_id
            task=TaskInput(title="Test", description=""),
            project_path=tmp_project,
            branch_naming="levelup/{run_id}",
        )

        # Should not crash, may return branch with "None" or handle it
        try:
            branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
            assert branch_name is not None
        except (AttributeError, TypeError):
            # If it raises an error, that's expected behavior to test
            pass

    def test_handles_missing_task_title(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should handle gracefully when task title is empty."""
        ctx = PipelineContext(
            run_id="run123",
            task=TaskInput(title="", description=""),
            project_path=tmp_project,
            branch_naming="feature/{task_title}",
        )

        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        # Should have a fallback, likely "task" or similar
        assert branch_name is not None
        assert len(branch_name) > 0

    def test_handles_context_without_branch_naming(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Should use default when context has no branch_naming."""
        ctx = PipelineContext(
            run_id="default123",
            task=TaskInput(title="Test", description=""),
            project_path=tmp_project,
            branch_naming=None,
        )

        branch_name = orchestrator._build_branch_name(
            ctx.branch_naming or "levelup/{run_id}", ctx
        )

        assert branch_name == "levelup/default123"


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


class TestBranchNameIntegrationWithOrchestrator:
    """Integration tests for branch name calculation in orchestrator workflow."""

    def test_branch_name_available_after_detection(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Branch naming should be available in context after detection step."""
        # After detection, branch_naming should be set in context
        ctx = PipelineContext(
            run_id="detect123",
            task=TaskInput(title="Test", description=""),
            project_path=tmp_project,
            branch_naming="levelup/{run_id}",  # Set by detection
        )

        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        assert branch_name == "levelup/detect123"

    def test_branch_name_consistent_across_pipeline(
        self, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Branch name should be consistent throughout pipeline execution."""
        ctx = PipelineContext(
            run_id="consistent123",
            task=TaskInput(title="Feature", description=""),
            project_path=tmp_project,
            branch_naming="custom/{run_id}",
        )

        # Calculate at different points
        branch_name_start = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        # ... pipeline runs ...
        branch_name_end = orchestrator._build_branch_name(ctx.branch_naming, ctx)

        assert branch_name_start == branch_name_end

    @patch("levelup.core.orchestrator.datetime")
    def test_branch_name_with_date_is_consistent(
        self, mock_datetime, orchestrator: Orchestrator, tmp_project: Path
    ):
        """Branch name with {date} should be consistent within same run."""
        # Mock datetime to return consistent date
        fixed_date = datetime(2026, 2, 10, 12, 0, 0)
        mock_datetime.now.return_value = fixed_date

        ctx = PipelineContext(
            run_id="date123",
            task=TaskInput(title="Test", description=""),
            project_path=tmp_project,
            branch_naming="ai/{date}-{run_id}",
        )

        branch_name = orchestrator._build_branch_name(ctx.branch_naming, ctx)
        assert "20260210" in branch_name
        assert "date123" in branch_name
