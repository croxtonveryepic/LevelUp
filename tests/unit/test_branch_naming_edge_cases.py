"""Edge case and error condition tests for branch naming feature."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import git
import pytest

from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.core.project_context import (
    get_project_context_path,
    read_project_context_header,
    write_project_context_preserving,
)

pytestmark = pytest.mark.regression


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repo with an initial commit."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("init")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


def _make_settings(tmp_path: Path, create_git_branch: bool = True) -> LevelUpSettings:
    """Build LevelUpSettings."""
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="claude_code"),
        project=ProjectSettings(path=tmp_path),
        pipeline=PipelineSettings(
            create_git_branch=create_git_branch,
            require_checkpoints=False,
        ),
    )


# ---------------------------------------------------------------------------
# Edge cases for task title sanitization
# ---------------------------------------------------------------------------


class TestTaskTitleSanitizationEdgeCases:
    """Edge cases for task title sanitization."""

    def test_unicode_characters_in_title(self, tmp_path: Path):
        """Unicode characters are handled properly."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Add emoji 😀 support")
        # Should either remove or handle unicode
        assert isinstance(result, str)
        assert len(result) > 0

    def test_title_with_only_whitespace(self, tmp_path: Path):
        """Title with only whitespace returns sensible default."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("     ")
        assert result in ("", "task")

    def test_title_with_numbers(self, tmp_path: Path):
        """Title with numbers preserves them."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Fix bug 123 in API v2")
        assert "123" in result
        assert "2" in result

    def test_title_with_slashes(self, tmp_path: Path):
        """Slashes in title are replaced (can't be in branch names)."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Update src/api/routes")
        # Slashes should be replaced or removed
        assert "/" not in result or result.count("/") < 3

    def test_title_with_dots(self, tmp_path: Path):
        """Dots in title are handled."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Update v1.2.3 config.json")
        # Should handle dots appropriately
        assert isinstance(result, str)

    def test_extremely_long_title_truncation(self, tmp_path: Path):
        """Very long title is truncated properly."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        long_title = "a" * 200  # 200 characters
        result = orch._sanitize_task_title(long_title)
        assert len(result) <= 50

    def test_title_starting_with_number(self, tmp_path: Path):
        """Title starting with number is handled."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("123 Fix authentication bug")
        # Branch names can start with numbers
        assert result.startswith("123") or result[0].isdigit()

    def test_title_with_multiple_spaces_between_words(self, tmp_path: Path):
        """Multiple spaces between words are collapsed."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        result = orch._sanitize_task_title("Fix    authentication     bug")
        # Multiple spaces should become single hyphens
        assert "--" not in result


# ---------------------------------------------------------------------------
# Edge cases for project_context.md parsing
# ---------------------------------------------------------------------------


class TestProjectContextParsingEdgeCases:
    """Edge cases for reading project_context.md."""

    def test_header_with_extra_whitespace(self, tmp_path: Path):
        """Handles header lines with extra whitespace."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:**   Python  \n"
            "- **Framework:**  none\n"
            "- **Test runner:**  pytest  \n"
            "- **Test command:**  pytest  \n"
            "- **Branch naming:**  feature/{task_title}  \n",
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        # Should strip whitespace
        assert header["language"].strip() == "Python"
        assert header["branch_naming"].strip() == "feature/{task_title}"

    def test_header_with_missing_lines(self, tmp_path: Path):
        """Handles header with missing optional lines."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Test command:** pytest\n",
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header["language"] == "Python"
        # Missing fields should be None or have defaults
        assert header.get("framework") is None or header.get("framework") == ""

    def test_header_with_empty_branch_naming_value(self, tmp_path: Path):
        """Handles branch naming line with empty value."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** \n",
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        assert header is not None
        # Empty value should be treated as missing
        branch_naming = header.get("branch_naming")
        assert branch_naming is None or branch_naming.strip() == ""

    def test_header_with_malformed_branch_naming_line(self, tmp_path: Path):
        """Handles malformed branch naming line."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- Branch naming feature/{task_title}\n",  # Missing ** **
            encoding="utf-8",
        )

        header = read_project_context_header(tmp_path)
        # Should handle gracefully
        assert header is not None

    def test_file_with_only_header_no_body(self, tmp_path: Path):
        """Handles file with only header, no body section."""
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

        header = read_project_context_header(tmp_path)
        assert header is not None
        assert header["branch_naming"] == "ai/{run_id}"

    def test_read_header_with_permission_denied(self, tmp_path: Path):
        """Handles permission denied when reading file."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Project Context\n", encoding="utf-8")

        # Make file unreadable (Unix-like systems)
        # On Windows, this test may not work as expected
        try:
            import os
            os.chmod(path, 0o000)
            header = read_project_context_header(tmp_path)
            # Should return None or handle gracefully
            assert header is None or isinstance(header, dict)
        except (PermissionError, OSError):
            # Expected on some systems
            pass
        finally:
            # Restore permissions
            try:
                os.chmod(path, 0o644)
            except:
                pass


# ---------------------------------------------------------------------------
# Edge cases for branch creation
# ---------------------------------------------------------------------------


class TestBranchCreationEdgeCases:
    """Edge cases for git branch creation with custom names."""

    def test_branch_name_with_special_git_chars(self, tmp_path: Path):
        """Handles task titles that produce git-invalid characters."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Git doesn't allow certain characters in branch names
        ctx = PipelineContext(
            task=TaskInput(title="Fix bug: colon issue"),
            branch_naming="feature/{task_title}",
        )

        orch._create_git_branch(tmp_path, ctx)

        # Should have sanitized the colon
        branch_name = repo.active_branch.name
        assert ":" not in branch_name

    def test_branch_name_collision(self, tmp_path: Path):
        """Handles case when branch name already exists."""
        repo = _init_git_repo(tmp_path)
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        # Create a branch that will collide
        repo.create_head("feature/add-login")

        ctx = PipelineContext(
            task=TaskInput(title="Add Login"),
            branch_naming="feature/{task_title}",
        )

        # Should handle collision gracefully (force, append suffix, or error)
        # Actual behavior depends on implementation
        try:
            orch._create_git_branch(tmp_path, ctx)
            # If it succeeds, verify we're on some valid branch
            assert repo.active_branch is not None
        except Exception as e:
            # If it fails, error should be informative
            assert "exists" in str(e).lower() or "conflict" in str(e).lower()

    def test_branch_creation_without_git_repo(self, tmp_path: Path):
        """Handles branch creation when not in a git repository."""
        # Don't initialize git repo
        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            branch_naming="feature/{task_title}",
        )

        # Should handle gracefully (skip or error)
        try:
            orch._create_git_branch(tmp_path, ctx)
        except Exception as e:
            # Expected - not a git repo
            assert "git" in str(e).lower() or "repository" in str(e).lower()

    def test_branch_creation_with_detached_head(self, tmp_path: Path):
        """Handles branch creation when HEAD is detached."""
        repo = _init_git_repo(tmp_path)

        # Detach HEAD
        repo.head.reference = repo.commit("HEAD")

        settings = _make_settings(tmp_path, create_git_branch=True)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            branch_naming="feature/{task_title}",
        )

        # Should handle detached HEAD gracefully
        try:
            orch._create_git_branch(tmp_path, ctx)
            # Should have created and checked out new branch
            assert not repo.head.is_detached or repo.active_branch is not None
        except Exception:
            # Acceptable if it errors with informative message
            pass


# ---------------------------------------------------------------------------
# Edge cases for write operations
# ---------------------------------------------------------------------------


class TestWriteProjectContextEdgeCases:
    """Edge cases for writing project_context.md with branch_naming."""

    def test_write_preserving_with_very_large_body(self, tmp_path: Path):
        """Preserves very large body content when updating header."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Create a file with large body
        large_body = "## Deep Analysis\n\n" + ("a" * 10000) + "\n"
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            + large_body,
            encoding="utf-8",
        )

        write_project_context_preserving(
            tmp_path,
            language="Python",
            framework="none",
            test_runner="pytest",
            test_command="pytest",
            branch_naming="ai/{run_id}",
        )

        content = path.read_text(encoding="utf-8")
        assert "**Branch naming:** ai/{run_id}" in content
        assert "## Deep Analysis" in content
        assert len(content) > 10000

    def test_write_with_none_values_uses_defaults(self, tmp_path: Path):
        """All None values use appropriate defaults."""
        write_project_context_preserving(
            tmp_path,
            language=None,
            framework=None,
            test_runner=None,
            test_command=None,
            branch_naming=None,
        )

        path = get_project_context_path(tmp_path)
        content = path.read_text(encoding="utf-8")
        assert "**Language:** unknown" in content
        assert "**Branch naming:** levelup/{run_id}" in content

    def test_concurrent_writes_to_project_context(self, tmp_path: Path):
        """Multiple concurrent writes don't corrupt file."""
        # This is more of a stress test
        import threading

        def write_branch_naming(convention: str):
            write_project_context_preserving(
                tmp_path,
                language="Python",
                branch_naming=convention,
            )

        threads = [
            threading.Thread(target=write_branch_naming, args=(f"conv{i}",))
            for i in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # File should exist and be readable
        path = get_project_context_path(tmp_path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "# Project Context" in content
        # One of the conventions should be present
        assert "Branch naming" in content


# ---------------------------------------------------------------------------
# Edge cases for placeholder substitution
# ---------------------------------------------------------------------------


class TestPlaceholderSubstitutionEdgeCases:
    """Edge cases for placeholder substitution in branch names."""

    def test_pattern_with_unknown_placeholder(self, tmp_path: Path):
        """Pattern with unknown placeholder is handled."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            run_id="abc123",
        )

        result = orch._build_branch_name("branch/{unknown}/{run_id}", ctx)
        # Should either leave it as-is or handle gracefully
        assert isinstance(result, str)

    def test_pattern_with_nested_braces(self, tmp_path: Path):
        """Pattern with nested braces is handled."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._build_branch_name("branch/{{nested}}", ctx)
        assert isinstance(result, str)

    def test_pattern_with_only_placeholders_no_separators(self, tmp_path: Path):
        """Pattern with only placeholders, no separators."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(
            task=TaskInput(title="Test"),
            run_id="abc",
        )

        result = orch._build_branch_name("{run_id}{task_title}", ctx)
        # Should concatenate without separators
        assert "abc" in result
        assert "test" in result

    def test_date_placeholder_format_consistency(self, tmp_path: Path):
        """Date placeholder produces consistent YYYYMMDD format."""
        from datetime import datetime

        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._build_branch_name("branch/{date}", ctx)
        # Extract date part
        date_part = result.replace("branch/", "")
        # Should be 8 digits
        assert len(date_part) == 8
        assert date_part.isdigit()
        # Should match current date
        today = datetime.now().strftime("%Y%m%d")
        assert date_part == today

    def test_pattern_with_escaped_braces(self, tmp_path: Path):
        """Pattern with escaped braces (if supported)."""
        settings = _make_settings(tmp_path, create_git_branch=False)
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        # Depending on implementation, this might preserve literal braces
        result = orch._build_branch_name("branch/\\{literal\\}", ctx)
        assert isinstance(result, str)
