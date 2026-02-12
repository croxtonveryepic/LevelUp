"""Unit tests for git diff generation helpers.

Tests the core diff generation logic that uses GitPython to create
diffs for display in the DiffViewWidget.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import git


def _init_git_repo(tmp_path: Path) -> git.Repo:
    """Create a git repo with an initial commit."""
    repo = git.Repo.init(tmp_path)
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()
    (tmp_path / "init.txt").write_text("initial content")
    repo.index.add(["init.txt"])
    repo.index.commit("initial commit")
    return repo


pytestmark = pytest.mark.regression


class TestGenerateDiffBetweenCommits:
    """Test generating diff between two commits."""

    def test_generate_diff_shows_additions(self, tmp_path):
        """Diff should show added lines with + prefix."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        # Add new file
        (tmp_path / "new_file.py").write_text("def hello():\n    print('hello')\n")
        repo.index.add(["new_file.py"])
        child_sha = repo.index.commit("Add new file").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        assert "new_file.py" in diff_output
        assert "+" in diff_output
        assert "hello" in diff_output

    def test_generate_diff_shows_deletions(self, tmp_path):
        """Diff should show deleted lines with - prefix."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)

        # Modify init.txt to delete content
        (tmp_path / "init.txt").write_text("")  # Empty file
        repo.index.add(["init.txt"])
        parent_sha = repo.index.commit("Remove content").hexsha

        # Restore content
        (tmp_path / "init.txt").write_text("restored content")
        repo.index.add(["init.txt"])
        child_sha = repo.index.commit("Restore content").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        assert "init.txt" in diff_output
        assert "+" in diff_output or "-" in diff_output

    def test_generate_diff_shows_modifications(self, tmp_path):
        """Diff should show modified lines."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        # Modify existing file
        (tmp_path / "init.txt").write_text("modified content")
        repo.index.add(["init.txt"])
        child_sha = repo.index.commit("Modify file").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        assert "init.txt" in diff_output
        assert "modified content" in diff_output or "initial content" in diff_output

    def test_generate_diff_empty_when_no_changes(self, tmp_path):
        """Diff should be empty when commits are identical."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        sha = repo.head.commit.hexsha

        diff_output = generate_diff(str(tmp_path), sha, sha)

        # Should be empty or minimal
        assert len(diff_output) < 100 or "no changes" in diff_output.lower()

    def test_generate_diff_handles_multiple_files(self, tmp_path):
        """Diff should show changes across multiple files."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        # Add multiple files
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "file3.py").write_text("content3")
        repo.index.add(["file1.py", "file2.py", "file3.py"])
        child_sha = repo.index.commit("Add multiple files").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        assert "file1.py" in diff_output
        assert "file2.py" in diff_output
        assert "file3.py" in diff_output

    def test_generate_diff_includes_file_headers(self, tmp_path):
        """Diff should include file path headers."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        (tmp_path / "test.py").write_text("test content")
        repo.index.add(["test.py"])
        child_sha = repo.index.commit("Add test").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        # Should have diff header with file path
        assert "diff --git" in diff_output or "test.py" in diff_output

    def test_generate_diff_includes_line_numbers(self, tmp_path):
        """Diff should include line number markers (@@)."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        (tmp_path / "code.py").write_text("line1\nline2\nline3\n")
        repo.index.add(["code.py"])
        child_sha = repo.index.commit("Add code").hexsha

        diff_output = generate_diff(str(tmp_path), parent_sha, child_sha)

        # Unified diff format includes @@ markers
        assert "@@" in diff_output


class TestGenerateDiffForStepCommit:
    """Test generating diff for a specific pipeline step."""

    def test_generate_step_diff_uses_parent_commit(self, tmp_path):
        """Step diff should compare with parent commit (previous step or pre_run_sha)."""
        from levelup.gui.diff_view_widget import generate_step_diff

        repo = _init_git_repo(tmp_path)
        initial_sha = repo.head.commit.hexsha

        # First step
        (tmp_path / "req.txt").write_text("requirements")
        repo.index.add(["req.txt"])
        step1_sha = repo.index.commit("levelup(requirements): Reqs").hexsha

        # Second step
        (tmp_path / "plan.txt").write_text("plan")
        repo.index.add(["plan.txt"])
        step2_sha = repo.index.commit("levelup(planning): Plan").hexsha

        # Diff for step2 should compare step1..step2
        diff_output = generate_step_diff(
            str(tmp_path),
            step2_sha,
            parent_sha=step1_sha,
        )

        assert "plan.txt" in diff_output
        assert "req.txt" not in diff_output  # Not in this step

    def test_generate_step_diff_first_step_uses_pre_run_sha(self, tmp_path):
        """First step diff should compare with pre_run_sha."""
        from levelup.gui.diff_view_widget import generate_step_diff

        repo = _init_git_repo(tmp_path)
        pre_run_sha = repo.head.commit.hexsha

        # First step
        (tmp_path / "req.txt").write_text("requirements")
        repo.index.add(["req.txt"])
        step_sha = repo.index.commit("levelup(requirements): Reqs").hexsha

        diff_output = generate_step_diff(
            str(tmp_path),
            step_sha,
            parent_sha=pre_run_sha,
        )

        assert "req.txt" in diff_output

    def test_generate_step_diff_extracts_commit_message(self, tmp_path):
        """Step diff should include commit message information."""
        from levelup.gui.diff_view_widget import get_commit_info

        repo = _init_git_repo(tmp_path)

        (tmp_path / "file.py").write_text("content")
        repo.index.add(["file.py"])
        commit_msg = "levelup(requirements): Add dependencies\n\nRun ID: test_123"
        step_sha = repo.index.commit(commit_msg).hexsha

        commit_info = get_commit_info(str(tmp_path), step_sha)

        assert "Add dependencies" in commit_info["message"]
        assert commit_info["sha"] == step_sha


class TestGenerateBranchDiff:
    """Test generating diff for entire branch."""

    def test_generate_branch_diff_from_pre_run_sha(self, tmp_path):
        """Branch diff should show all changes from pre_run_sha to HEAD."""
        from levelup.gui.diff_view_widget import generate_branch_diff

        repo = _init_git_repo(tmp_path)
        pre_run_sha = repo.head.commit.hexsha

        # Multiple commits
        (tmp_path / "file1.py").write_text("content1")
        repo.index.add(["file1.py"])
        repo.index.commit("levelup(requirements): Add file1")

        (tmp_path / "file2.py").write_text("content2")
        repo.index.add(["file2.py"])
        repo.index.commit("levelup(planning): Add file2")

        (tmp_path / "file3.py").write_text("content3")
        repo.index.add(["file3.py"])
        repo.index.commit("levelup(coding): Add file3")

        diff_output = generate_branch_diff(str(tmp_path), pre_run_sha)

        # Should show all files
        assert "file1.py" in diff_output
        assert "file2.py" in diff_output
        assert "file3.py" in diff_output

    def test_generate_branch_diff_to_specific_commit(self, tmp_path):
        """Branch diff should support specifying end commit."""
        from levelup.gui.diff_view_widget import generate_branch_diff

        repo = _init_git_repo(tmp_path)
        pre_run_sha = repo.head.commit.hexsha

        (tmp_path / "file1.py").write_text("content1")
        repo.index.add(["file1.py"])
        mid_sha = repo.index.commit("Add file1").hexsha

        (tmp_path / "file2.py").write_text("content2")
        repo.index.add(["file2.py"])
        repo.index.commit("Add file2")

        # Diff only to mid_sha
        diff_output = generate_branch_diff(
            str(tmp_path),
            pre_run_sha,
            to_sha=mid_sha,
        )

        assert "file1.py" in diff_output
        assert "file2.py" not in diff_output

    def test_generate_branch_diff_statistics(self, tmp_path):
        """Branch diff should provide statistics (files changed, insertions, deletions)."""
        from levelup.gui.diff_view_widget import get_diff_stats

        repo = _init_git_repo(tmp_path)
        pre_run_sha = repo.head.commit.hexsha

        # Add files with known line counts
        (tmp_path / "file1.py").write_text("line1\nline2\nline3\n")
        (tmp_path / "file2.py").write_text("lineA\nlineB\n")
        repo.index.add(["file1.py", "file2.py"])
        repo.index.commit("Add files")

        stats = get_diff_stats(str(tmp_path), pre_run_sha)

        assert stats["files_changed"] == 2
        assert stats["insertions"] == 5  # 3 + 2 lines
        assert stats["deletions"] == 0


class TestDiffFormatting:
    """Test diff output formatting for display."""

    def test_format_diff_for_html_escapes_special_chars(self):
        """Diff formatter should escape HTML special characters."""
        from levelup.gui.diff_view_widget import format_diff_html

        diff_text = "<script>alert('xss')</script>"
        html = format_diff_html(diff_text)

        assert "&lt;script&gt;" in html or "<" not in html

    def test_format_diff_for_html_adds_syntax_highlighting(self):
        """Diff formatter should add syntax highlighting for +/- lines."""
        from levelup.gui.diff_view_widget import format_diff_html

        diff_text = "+added line\n-deleted line\n unchanged line"
        html = format_diff_html(diff_text, theme="dark")

        # Should have color styling
        assert "color" in html.lower() or "style" in html.lower()

    def test_format_diff_for_html_dark_theme(self):
        """Dark theme should use appropriate colors."""
        from levelup.gui.diff_view_widget import format_diff_html

        diff_text = "+added\n-deleted"
        html = format_diff_html(diff_text, theme="dark")

        # Dark theme colors for additions/deletions
        assert "#a6e3a1" in html.lower() or "#2ecc71" in html.lower() or "green" in html.lower()

    def test_format_diff_for_html_light_theme(self):
        """Light theme should use appropriate colors."""
        from levelup.gui.diff_view_widget import format_diff_html

        diff_text = "+added\n-deleted"
        html = format_diff_html(diff_text, theme="light")

        # Should have styling appropriate for light theme
        assert "color" in html.lower() or "style" in html.lower()

    def test_format_diff_preserves_whitespace(self):
        """Diff formatter should preserve indentation and whitespace."""
        from levelup.gui.diff_view_widget import format_diff_html

        diff_text = "+    indented line\n+        more indented"
        html = format_diff_html(diff_text)

        # Should preserve spaces (via <pre> or &nbsp;)
        assert "<pre>" in html or "&nbsp;" in html or "white-space" in html


class TestDiffErrorHandling:
    """Test error handling in diff generation."""

    def test_generate_diff_invalid_sha_raises_error(self, tmp_path):
        """Invalid commit SHA should raise appropriate error."""
        from levelup.gui.diff_view_widget import generate_diff

        repo = _init_git_repo(tmp_path)

        with pytest.raises((git.exc.GitCommandError, ValueError, KeyError)):
            generate_diff(str(tmp_path), "invalid_sha_123", "invalid_sha_456")

    def test_generate_diff_non_git_repo_raises_error(self, tmp_path):
        """Non-git directory should raise appropriate error."""
        from levelup.gui.diff_view_widget import generate_diff

        non_git_dir = tmp_path / "not_a_repo"
        non_git_dir.mkdir()

        with pytest.raises((git.exc.InvalidGitRepositoryError, git.exc.GitCommandError)):
            generate_diff(str(non_git_dir), "sha1", "sha2")

    def test_generate_diff_handles_empty_repo(self, tmp_path):
        """Empty git repo (no commits) should be handled."""
        from levelup.gui.diff_view_widget import generate_diff

        # Create empty repo with no commits
        empty_repo = tmp_path / "empty"
        empty_repo.mkdir()
        git.Repo.init(empty_repo)

        with pytest.raises((git.exc.GitCommandError, ValueError)):
            generate_diff(str(empty_repo), "HEAD", "HEAD")

    def test_get_commit_info_invalid_sha(self, tmp_path):
        """Getting commit info with invalid SHA should raise error."""
        from levelup.gui.diff_view_widget import get_commit_info

        repo = _init_git_repo(tmp_path)

        with pytest.raises((git.exc.GitCommandError, ValueError)):
            get_commit_info(str(tmp_path), "nonexistent_sha")

    def test_get_diff_stats_handles_no_changes(self, tmp_path):
        """Diff stats should handle case with no changes."""
        from levelup.gui.diff_view_widget import get_diff_stats

        repo = _init_git_repo(tmp_path)
        sha = repo.head.commit.hexsha

        stats = get_diff_stats(str(tmp_path), sha, sha)

        assert stats["files_changed"] == 0
        assert stats["insertions"] == 0
        assert stats["deletions"] == 0


class TestDiffHelperFunctions:
    """Test utility functions for diff operations."""

    def test_get_parent_commit_sha(self, tmp_path):
        """Get parent SHA of a commit."""
        from levelup.gui.diff_view_widget import get_parent_sha

        repo = _init_git_repo(tmp_path)
        parent_sha = repo.head.commit.hexsha

        (tmp_path / "file.py").write_text("content")
        repo.index.add(["file.py"])
        child_sha = repo.index.commit("Add file").hexsha

        retrieved_parent = get_parent_sha(str(tmp_path), child_sha)

        assert retrieved_parent == parent_sha

    def test_get_parent_commit_sha_first_commit(self, tmp_path):
        """First commit has no parent."""
        from levelup.gui.diff_view_widget import get_parent_sha

        repo = _init_git_repo(tmp_path)
        first_sha = repo.head.commit.hexsha

        parent = get_parent_sha(str(tmp_path), first_sha)

        # First commit has no parent
        assert parent is None or parent == first_sha

    def test_find_step_parent_from_step_commits(self):
        """Find parent commit for a step from step_commits dict."""
        from levelup.gui.diff_view_widget import find_step_parent

        step_commits = {
            "requirements": "sha1",
            "planning": "sha2",
            "test_writing": "sha3",
            "coding": "sha4",
        }
        pre_run_sha = "sha0"

        # Requirements is first step
        parent = find_step_parent("requirements", step_commits, pre_run_sha)
        assert parent == pre_run_sha

        # Planning follows requirements
        parent = find_step_parent("planning", step_commits, pre_run_sha)
        assert parent == "sha1"

        # Coding follows test_writing
        parent = find_step_parent("coding", step_commits, pre_run_sha)
        assert parent == "sha3"

    def test_is_valid_commit_sha(self, tmp_path):
        """Check if a SHA is valid in the repository."""
        from levelup.gui.diff_view_widget import is_valid_sha

        repo = _init_git_repo(tmp_path)
        valid_sha = repo.head.commit.hexsha

        assert is_valid_sha(str(tmp_path), valid_sha) is True
        assert is_valid_sha(str(tmp_path), "invalid_sha_123") is False

    def test_get_branch_head_sha(self, tmp_path):
        """Get HEAD SHA of a branch."""
        from levelup.gui.diff_view_widget import get_branch_head

        repo = _init_git_repo(tmp_path)

        # Create a branch
        branch = repo.create_head("test_branch")
        branch.checkout()

        (tmp_path / "branch_file.py").write_text("branch content")
        repo.index.add(["branch_file.py"])
        branch_sha = repo.index.commit("Branch commit").hexsha

        retrieved_head = get_branch_head(str(tmp_path), "test_branch")

        assert retrieved_head == branch_sha
