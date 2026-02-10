"""Unit tests for src/levelup/core/context.py data models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from levelup.core.context import (
    CheckpointDecision,
    FileChange,
    Severity,
    PipelineContext,
    PipelineStatus,
    Plan,
    PlanStep,
    Requirements,
    Requirement,
    ReviewFinding,
    TaskInput,
    TestResult,
)


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestPipelineStatus:
    """Test PipelineStatus enum values and str behaviour."""

    def test_values(self):
        assert PipelineStatus.PENDING == "pending"
        assert PipelineStatus.RUNNING == "running"
        assert PipelineStatus.WAITING_FOR_INPUT == "waiting_for_input"
        assert PipelineStatus.COMPLETED == "completed"
        assert PipelineStatus.FAILED == "failed"
        assert PipelineStatus.ABORTED == "aborted"

    def test_is_str(self):
        assert isinstance(PipelineStatus.RUNNING, str)

    def test_member_count(self):
        assert len(PipelineStatus) == 6


class TestCheckpointDecision:
    """Test CheckpointDecision enum values."""

    def test_values(self):
        assert CheckpointDecision.APPROVE == "approve"
        assert CheckpointDecision.REVISE == "revise"
        assert CheckpointDecision.REJECT == "reject"

    def test_is_str(self):
        assert isinstance(CheckpointDecision.APPROVE, str)

    def test_member_count(self):
        assert len(CheckpointDecision) == 4


class TestSeverity:
    """Test Severity enum values."""

    def test_values(self):
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"
        assert Severity.CRITICAL == "critical"

    def test_is_str(self):
        assert isinstance(Severity.ERROR, str)

    def test_member_count(self):
        assert len(Severity) == 4


# ---------------------------------------------------------------------------
# TaskInput
# ---------------------------------------------------------------------------


class TestTaskInput:
    """Test TaskInput model."""

    def test_minimal_creation(self):
        task = TaskInput(title="Fix bug")
        assert task.title == "Fix bug"
        assert task.description == ""
        assert task.source == "manual"
        assert task.source_id is None

    def test_full_creation(self):
        task = TaskInput(
            title="Add feature",
            description="Implement user auth",
            source="jira",
            source_id="PROJ-123",
        )
        assert task.title == "Add feature"
        assert task.description == "Implement user auth"
        assert task.source == "jira"
        assert task.source_id == "PROJ-123"

    def test_json_round_trip(self):
        task = TaskInput(title="roundtrip", description="test", source="cli", source_id="42")
        data = json.loads(task.model_dump_json())
        restored = TaskInput(**data)
        assert restored == task


# ---------------------------------------------------------------------------
# Requirement / Requirements
# ---------------------------------------------------------------------------


class TestRequirement:
    """Test Requirement model."""

    def test_auto_generated_id(self):
        req = Requirement(description="Must do X")
        assert len(req.id) == 8
        assert req.description == "Must do X"
        assert req.acceptance_criteria == []

    def test_explicit_id(self):
        req = Requirement(id="custom-id", description="Y")
        assert req.id == "custom-id"

    def test_with_acceptance_criteria(self):
        req = Requirement(
            description="Z",
            acceptance_criteria=["crit-1", "crit-2"],
        )
        assert len(req.acceptance_criteria) == 2


class TestRequirements:
    """Test Requirements model."""

    def test_minimal(self):
        reqs = Requirements(summary="Add login page")
        assert reqs.summary == "Add login page"
        assert reqs.requirements == []
        assert reqs.assumptions == []
        assert reqs.out_of_scope == []
        assert reqs.clarifications == []

    def test_full(self):
        reqs = Requirements(
            summary="Auth feature",
            requirements=[Requirement(description="Login endpoint")],
            assumptions=["DB exists"],
            out_of_scope=["OAuth"],
            clarifications=["Password policy?"],
        )
        assert len(reqs.requirements) == 1
        assert reqs.assumptions == ["DB exists"]
        assert reqs.out_of_scope == ["OAuth"]
        assert reqs.clarifications == ["Password policy?"]

    def test_json_round_trip(self):
        reqs = Requirements(
            summary="s",
            requirements=[Requirement(id="r1", description="d1", acceptance_criteria=["a"])],
            assumptions=["a1"],
        )
        data = json.loads(reqs.model_dump_json())
        restored = Requirements(**data)
        assert restored == reqs


# ---------------------------------------------------------------------------
# PlanStep / Plan
# ---------------------------------------------------------------------------


class TestPlanStep:
    """Test PlanStep model."""

    def test_creation(self):
        step = PlanStep(order=1, description="Create models")
        assert step.order == 1
        assert step.description == "Create models"
        assert step.files_to_modify == []
        assert step.files_to_create == []

    def test_with_files(self):
        step = PlanStep(
            order=2,
            description="Add routes",
            files_to_modify=["routes.py"],
            files_to_create=["auth.py"],
        )
        assert step.files_to_modify == ["routes.py"]
        assert step.files_to_create == ["auth.py"]


class TestPlan:
    """Test Plan model."""

    def test_minimal(self):
        plan = Plan(approach="TDD")
        assert plan.approach == "TDD"
        assert plan.steps == []
        assert plan.affected_files == []
        assert plan.risks == []

    def test_full(self):
        plan = Plan(
            approach="Incremental",
            steps=[PlanStep(order=1, description="step 1")],
            affected_files=["main.py"],
            risks=["Breaking change"],
        )
        assert len(plan.steps) == 1
        assert plan.affected_files == ["main.py"]
        assert plan.risks == ["Breaking change"]

    def test_json_round_trip(self):
        plan = Plan(
            approach="a",
            steps=[PlanStep(order=1, description="s")],
            affected_files=["f.py"],
            risks=["r"],
        )
        data = json.loads(plan.model_dump_json())
        restored = Plan(**data)
        assert restored == plan


# ---------------------------------------------------------------------------
# FileChange
# ---------------------------------------------------------------------------


class TestFileChange:
    """Test FileChange model."""

    def test_minimal(self):
        fc = FileChange(path="src/main.py", content="print('hi')")
        assert fc.path == "src/main.py"
        assert fc.content == "print('hi')"
        assert fc.original_content is None
        assert fc.is_new is False

    def test_new_file(self):
        fc = FileChange(path="new.py", content="# new", is_new=True)
        assert fc.is_new is True

    def test_with_original(self):
        fc = FileChange(path="f.py", content="new", original_content="old")
        assert fc.original_content == "old"

    def test_json_round_trip(self):
        fc = FileChange(path="a.py", content="c", original_content="o", is_new=True)
        data = json.loads(fc.model_dump_json())
        restored = FileChange(**data)
        assert restored == fc


# ---------------------------------------------------------------------------
# TestResult
# ---------------------------------------------------------------------------


class TestTestResult:
    """Test TestResult model."""

    def test_minimal(self):
        tr = TestResult(passed=True)
        assert tr.passed is True
        assert tr.total == 0
        assert tr.failures == 0
        assert tr.errors == 0
        assert tr.output == ""
        assert tr.command == ""

    def test_full(self):
        tr = TestResult(
            passed=False,
            total=10,
            failures=2,
            errors=1,
            output="FAILED",
            command="pytest",
        )
        assert tr.passed is False
        assert tr.total == 10
        assert tr.failures == 2
        assert tr.errors == 1

    def test_json_round_trip(self):
        tr = TestResult(passed=False, total=5, failures=1, errors=0, output="x", command="c")
        data = json.loads(tr.model_dump_json())
        restored = TestResult(**data)
        assert restored == tr


# ---------------------------------------------------------------------------
# ReviewFinding
# ---------------------------------------------------------------------------


class TestReviewFinding:
    """Test ReviewFinding model."""

    def test_minimal(self):
        rf = ReviewFinding(
            severity=Severity.WARNING,
            category="style",
            file="main.py",
            message="Unused import",
        )
        assert rf.severity == Severity.WARNING
        assert rf.category == "style"
        assert rf.file == "main.py"
        assert rf.line is None
        assert rf.message == "Unused import"
        assert rf.suggestion == ""

    def test_full(self):
        rf = ReviewFinding(
            severity=Severity.ERROR,
            category="security",
            file="auth.py",
            line=42,
            message="SQL injection",
            suggestion="Use parameterized queries",
        )
        assert rf.line == 42
        assert rf.suggestion == "Use parameterized queries"

    def test_json_round_trip(self):
        rf = ReviewFinding(
            severity=Severity.CRITICAL,
            category="bug",
            file="x.py",
            line=10,
            message="m",
            suggestion="s",
        )
        data = json.loads(rf.model_dump_json())
        restored = ReviewFinding(**data)
        assert restored == rf


# ---------------------------------------------------------------------------
# PipelineContext
# ---------------------------------------------------------------------------


class TestPipelineContext:
    """Test PipelineContext model."""

    def test_creation_with_defaults(self):
        task = TaskInput(title="Test task")
        ctx = PipelineContext(task=task)

        assert ctx.task == task
        assert len(ctx.run_id) == 12
        assert isinstance(ctx.started_at, datetime)
        assert ctx.started_at.tzinfo is not None
        assert ctx.language is None
        assert ctx.framework is None
        assert ctx.test_runner is None
        assert ctx.test_command is None
        assert ctx.requirements is None
        assert ctx.plan is None
        assert ctx.test_files == []
        assert ctx.code_files == []
        assert ctx.test_results == []
        assert ctx.review_findings == []
        assert ctx.status == PipelineStatus.PENDING
        assert ctx.current_step is None
        assert ctx.code_iteration == 0
        assert ctx.error_message is None

    def test_creation_with_full_data(self):
        task = TaskInput(title="Full", description="desc", source="jira", source_id="J-1")
        reqs = Requirements(summary="s", requirements=[Requirement(description="r")])
        plan = Plan(approach="TDD", steps=[PlanStep(order=1, description="step")])
        fc = FileChange(path="f.py", content="c")
        tr = TestResult(passed=True, total=1)
        rf = ReviewFinding(
            severity=Severity.INFO, category="cat", file="f.py", message="msg"
        )

        ctx = PipelineContext(
            run_id="abc123def456",
            task=task,
            project_path=Path("/tmp/proj"),
            language="python",
            framework="fastapi",
            test_runner="pytest",
            test_command="pytest",
            requirements=reqs,
            plan=plan,
            test_files=[fc],
            code_files=[fc],
            test_results=[tr],
            review_findings=[rf],
            status=PipelineStatus.RUNNING,
            current_step="coding",
            code_iteration=2,
            error_message=None,
        )

        assert ctx.run_id == "abc123def456"
        assert ctx.language == "python"
        assert ctx.framework == "fastapi"
        assert ctx.test_runner == "pytest"
        assert ctx.requirements is not None
        assert ctx.plan is not None
        assert len(ctx.test_files) == 1
        assert len(ctx.code_files) == 1
        assert len(ctx.test_results) == 1
        assert len(ctx.review_findings) == 1
        assert ctx.status == PipelineStatus.RUNNING
        assert ctx.current_step == "coding"
        assert ctx.code_iteration == 2

    def test_unique_run_ids(self):
        task = TaskInput(title="t")
        ctx1 = PipelineContext(task=task)
        ctx2 = PipelineContext(task=task)
        assert ctx1.run_id != ctx2.run_id

    def test_status_default_is_pending(self):
        ctx = PipelineContext(task=TaskInput(title="t"))
        assert ctx.status == PipelineStatus.PENDING

    def test_json_round_trip(self):
        task = TaskInput(title="rt")
        ctx = PipelineContext(
            task=task,
            language="python",
            status=PipelineStatus.COMPLETED,
            code_iteration=3,
        )
        json_str = ctx.model_dump_json()
        data = json.loads(json_str)
        restored = PipelineContext(**data)

        assert restored.task.title == "rt"
        assert restored.language == "python"
        assert restored.status == PipelineStatus.COMPLETED
        assert restored.code_iteration == 3

    def test_project_path_serializes(self):
        ctx = PipelineContext(
            task=TaskInput(title="t"),
            project_path=Path("/some/path"),
        )
        data = json.loads(ctx.model_dump_json())
        # Normalize separators for cross-platform compatibility
        normalized = data["project_path"].replace("\\", "/")
        assert "some/path" in normalized

    def test_mutable_status_update(self):
        ctx = PipelineContext(task=TaskInput(title="t"))
        ctx.status = PipelineStatus.RUNNING
        ctx.current_step = "requirements"
        ctx.code_iteration = 1
        assert ctx.status == PipelineStatus.RUNNING
        assert ctx.current_step == "requirements"
        assert ctx.code_iteration == 1

    def test_append_to_lists(self):
        ctx = PipelineContext(task=TaskInput(title="t"))
        ctx.test_files.append(FileChange(path="t.py", content="c"))
        ctx.code_files.append(FileChange(path="m.py", content="c"))
        ctx.test_results.append(TestResult(passed=True))
        ctx.review_findings.append(
            ReviewFinding(
                severity=Severity.INFO, category="c", file="f.py", message="m"
            )
        )
        assert len(ctx.test_files) == 1
        assert len(ctx.code_files) == 1
        assert len(ctx.test_results) == 1
        assert len(ctx.review_findings) == 1
