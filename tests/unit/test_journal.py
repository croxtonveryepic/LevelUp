"""Unit tests for src/levelup/core/journal.py."""

from __future__ import annotations

import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from levelup.core.context import (
    FileChange,
    PipelineContext,
    PipelineStatus,
    Plan,
    PlanStep,
    Requirements,
    Requirement,
    ReviewFinding,
    Severity,
    TaskInput,
    TestResult,
)
from levelup.core.journal import RunJournal, _build_filename, _sanitize_source_id, _slugify


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(
    tmp_path: Path,
    title: str = "Add auth",
    source_id: str | None = None,
    description: str = "",
    **overrides,
) -> PipelineContext:
    """Create a PipelineContext rooted at *tmp_path*."""
    return PipelineContext(
        task=TaskInput(
            title=title,
            description=description,
            source="jira" if source_id else "manual",
            source_id=source_id,
        ),
        project_path=tmp_path,
        started_at=datetime(2026, 2, 6, 14, 30, 0, tzinfo=timezone.utc),
        run_id="a1b2c3d4e5f6",
        status=PipelineStatus.RUNNING,
        **overrides,
    )


# ---------------------------------------------------------------------------
# TestSlugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_basic_title(self):
        assert _slugify("Add User Auth") == "add-user-auth"

    def test_special_characters(self):
        assert _slugify("Fix bug #123: crash!") == "fix-bug-123-crash"

    def test_long_title_truncated(self):
        long_title = "a" * 60
        result = _slugify(long_title, max_length=50)
        assert len(result) <= 50

    def test_truncation_no_trailing_dash(self):
        # Build a title that produces a dash right at the boundary
        title = "a" * 49 + " b"
        result = _slugify(title, max_length=50)
        assert not result.endswith("-")
        assert len(result) <= 50

    def test_empty_string_fallback(self):
        assert _slugify("") == "run-journal"

    def test_only_special_chars_fallback(self):
        assert _slugify("!!!@@@###") == "run-journal"


# ---------------------------------------------------------------------------
# TestBuildFilename
# ---------------------------------------------------------------------------


class TestSanitizeSourceId:
    def test_colon_replaced(self):
        assert _sanitize_source_id("ticket:1") == "ticket-1"

    def test_no_change_for_safe_id(self):
        assert _sanitize_source_id("PROJ-123") == "PROJ-123"

    def test_multiple_illegal_chars(self):
        assert _sanitize_source_id('a\\b/c:d*e?"f<g>h|i') == "a-b-c-d-e-f-g-h-i"

    def test_consecutive_illegal_chars_collapsed(self):
        assert _sanitize_source_id("a::b") == "a-b"

    def test_leading_trailing_illegal_stripped(self):
        assert _sanitize_source_id(":foo:") == "foo"


class TestBuildFilename:
    def test_with_ticket(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path, title="Add auth", source_id="PROJ-123")
        assert _build_filename(ctx) == "20260206-PROJ-123-add-auth.md"

    def test_without_ticket(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path, title="Fix bug")
        assert _build_filename(ctx) == "20260206-fix-bug.md"

    def test_with_ticket_colon_sanitized(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path, title="Light mode", source_id="ticket:1")
        assert _build_filename(ctx) == "20260206-ticket-1-light-mode.md"


# ---------------------------------------------------------------------------
# TestRunJournal
# ---------------------------------------------------------------------------


class TestRunJournal:
    def test_write_header_creates_dir_and_file(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        journal = RunJournal(ctx)
        journal.write_header(ctx)

        assert (tmp_path / "levelup").is_dir()
        content = journal.path.read_text(encoding="utf-8")
        assert "a1b2c3d4e5f6" in content
        assert "Add auth" in content

    def test_write_header_with_ticket(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path, source_id="PROJ-123")
        journal = RunJournal(ctx)
        journal.write_header(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "PROJ-123" in content
        assert "jira" in content

    def test_write_header_with_description(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path, description="Implement JWT auth")
        journal = RunJournal(ctx)
        journal.write_header(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Task Description" in content
        assert "Implement JWT auth" in content

    def test_log_step_detect(self, tmp_path: Path):
        ctx = _make_ctx(
            tmp_path,
            language="python",
            framework="fastapi",
            test_runner="pytest",
            test_command="pytest",
        )
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("detect", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: detect" in content
        assert "See `levelup/project_context.md` for project details." in content

    def test_log_step_requirements(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.requirements = Requirements(
            summary="Add JWT auth",
            requirements=[Requirement(description="Login endpoint")],
            assumptions=["DB exists", "HTTPS"],
            out_of_scope=["OAuth"],
        )
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("requirements", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: requirements" in content
        assert "Add JWT auth" in content
        assert "1 requirement(s)" in content
        assert "2 assumption(s)" in content
        assert "1 out-of-scope item(s)" in content

    def test_log_step_requirements_none(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("requirements", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "No requirements produced." in content

    def test_log_step_planning(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.plan = Plan(
            approach="Add auth module",
            steps=[PlanStep(order=1, description="Create model")],
            affected_files=["src/auth.py", "src/models/user.py"],
            risks=["Breaking middleware"],
        )
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("planning", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: planning" in content
        assert "Add auth module" in content
        assert "1 implementation step(s)" in content
        assert "src/auth.py" in content
        assert "Breaking middleware" in content

    def test_log_step_test_writing(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.test_files = [
            FileChange(path="tests/test_auth.py", content="...", is_new=True),
            FileChange(path="tests/test_user.py", content="...", is_new=False),
        ]
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("test_writing", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: test_writing" in content
        assert "2 test file(s)" in content
        assert "`tests/test_auth.py` (new)" in content
        assert "`tests/test_user.py` (modified)" in content

    def test_log_step_coding(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.code_files = [
            FileChange(path="src/auth.py", content="...", is_new=True),
        ]
        ctx.code_iteration = 3
        ctx.test_results = [
            TestResult(passed=True, total=12, failures=0, errors=0),
        ]
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("coding", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: coding" in content
        assert "`src/auth.py` (new)" in content
        assert "Code iterations:** 3" in content
        assert "12 total" in content
        assert "PASSED" in content

    def test_log_step_review(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.review_findings = [
            ReviewFinding(
                severity=Severity.WARNING,
                category="security",
                file="src/auth.py",
                message="Use constant-time comparison",
            ),
        ]
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_step("review", ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Step: review" in content
        assert "1 issue(s)" in content
        assert "[WARNING]" in content
        assert "Use constant-time comparison" in content

    def test_log_checkpoint(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_checkpoint("requirements", "approve", "")

        content = journal.path.read_text(encoding="utf-8")
        assert "### Checkpoint: requirements" in content
        assert "approve" in content

    def test_log_checkpoint_with_feedback(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_checkpoint("test_writing", "revise", "Add edge case tests")

        content = journal.path.read_text(encoding="utf-8")
        assert "revise" in content
        assert "Add edge case tests" in content

    def test_log_outcome(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.status = PipelineStatus.COMPLETED
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "## Outcome" in content
        assert "completed" in content

    def test_log_outcome_with_error(self, tmp_path: Path):
        ctx = _make_ctx(tmp_path)
        ctx.status = PipelineStatus.FAILED
        ctx.error_message = "Agent crashed"
        journal = RunJournal(ctx)
        journal.write_header(ctx)
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")
        assert "failed" in content
        assert "Agent crashed" in content

    def test_incremental_writing(self, tmp_path: Path):
        """Full sequence — all sections present in order."""
        ctx = _make_ctx(
            tmp_path,
            title="Add auth",
            source_id="PROJ-1",
            description="JWT auth",
            language="python",
            framework="fastapi",
            test_runner="pytest",
            test_command="pytest",
        )
        journal = RunJournal(ctx)
        journal.write_header(ctx)

        # detect
        journal.log_step("detect", ctx)

        # requirements
        ctx.requirements = Requirements(
            summary="Auth",
            requirements=[Requirement(description="Login")],
            assumptions=["DB"],
            out_of_scope=["OAuth"],
        )
        journal.log_step("requirements", ctx)
        journal.log_checkpoint("requirements", "approve", "")

        # planning
        ctx.plan = Plan(approach="Incremental", steps=[], affected_files=["a.py"])
        journal.log_step("planning", ctx)

        # test_writing
        ctx.test_files = [FileChange(path="test.py", content="", is_new=True)]
        journal.log_step("test_writing", ctx)
        journal.log_checkpoint("test_writing", "approve", "")

        # coding
        ctx.code_files = [FileChange(path="auth.py", content="", is_new=True)]
        ctx.code_iteration = 2
        ctx.test_results = [TestResult(passed=True, total=5, failures=0, errors=0)]
        journal.log_step("coding", ctx)

        # review
        ctx.review_findings = [
            ReviewFinding(
                severity=Severity.INFO, category="style", file="auth.py", message="OK"
            )
        ]
        journal.log_step("review", ctx)
        journal.log_checkpoint("review", "approve", "")

        # outcome
        ctx.status = PipelineStatus.COMPLETED
        journal.log_outcome(ctx)

        content = journal.path.read_text(encoding="utf-8")

        # Verify ordering
        sections = [
            "# Run Journal: Add auth",
            "## Task Description",
            "## Step: detect",
            "## Step: requirements",
            "### Checkpoint: requirements",
            "## Step: planning",
            "## Step: test_writing",
            "### Checkpoint: test_writing",
            "## Step: coding",
            "## Step: review",
            "### Checkpoint: review",
            "## Outcome",
        ]
        prev_idx = -1
        for section in sections:
            idx = content.index(section)
            assert idx > prev_idx, f"{section!r} not in order"
            prev_idx = idx

    @pytest.mark.skipif(sys.platform == "win32", reason="chmod not reliable on Windows")
    def test_write_failure_does_not_raise(self, tmp_path: Path):
        """Read-only dir doesn't propagate exception."""
        ctx = _make_ctx(tmp_path)
        journal = RunJournal(ctx)

        # Make the levelup dir read-only
        levelup_dir = tmp_path / "levelup"
        levelup_dir.mkdir()
        levelup_dir.chmod(stat.S_IRUSR | stat.S_IXUSR)

        try:
            # Should not raise
            journal.write_header(ctx)
            journal.log_step("detect", ctx)
            journal.log_checkpoint("detect", "approve", "")
            journal.log_outcome(ctx)
        finally:
            # Restore permissions for cleanup
            levelup_dir.chmod(stat.S_IRWXU)
