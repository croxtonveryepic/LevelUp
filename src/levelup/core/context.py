"""PipelineContext and all data models that flow through the pipeline."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field


# --- Enums ---


class PipelineStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_INPUT = "waiting_for_input"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class CheckpointDecision(str, enum.Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT = "reject"
    INSTRUCT = "instruct"


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# --- Data Models ---


class TaskInput(BaseModel):
    """Raw task input from user or ticket system."""

    title: str
    description: str = ""
    source: str = "manual"
    source_id: str | None = None


class Requirement(BaseModel):
    """A single requirement extracted by the RequirementsAgent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str
    acceptance_criteria: list[str] = Field(default_factory=list)


class Requirements(BaseModel):
    """Structured output from the RequirementsAgent."""

    summary: str
    requirements: list[Requirement] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    """A single step in the implementation plan."""

    order: int
    description: str
    files_to_modify: list[str] = Field(default_factory=list)
    files_to_create: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """Structured output from the PlanningAgent."""

    approach: str
    steps: list[PlanStep] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class FileChange(BaseModel):
    """A file that was created or modified by an agent."""

    path: str
    content: str
    original_content: str | None = None
    is_new: bool = False


class TestResult(BaseModel):
    """Result from running a test suite."""

    passed: bool
    total: int = 0
    failures: int = 0
    errors: int = 0
    output: str = ""
    command: str = ""


class ReviewFinding(BaseModel):
    """A single finding from the ReviewAgent."""

    severity: Severity
    category: str
    file: str
    line: int | None = None
    message: str
    suggestion: str = ""


class SecurityFinding(BaseModel):
    """A security vulnerability detected by the SecurityAgent."""

    severity: Severity  # INFO, WARNING, ERROR, CRITICAL
    category: str  # e.g., "injection", "authentication", "crypto", "input_validation"
    vulnerability_type: str  # e.g., "SQL Injection", "XSS", "Hardcoded Secret"
    file: str
    line: int | None = None
    description: str
    cwe_id: str | None = None  # Common Weakness Enumeration reference
    patch_applied: bool = False
    patch_description: str = ""
    requires_manual_fix: bool = False
    recommendation: str = ""


# --- Usage Tracking ---


class StepUsage(BaseModel):
    """Usage metrics from a single pipeline step."""

    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    duration_ms: float = 0.0
    num_turns: int = 0


# --- Pipeline Context ---


class PipelineContext(BaseModel):
    """Single mutable state object that flows through all agents."""

    # Run metadata
    run_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Input
    task: TaskInput

    # Project info (from detection)
    project_path: Path = Field(default_factory=Path.cwd)
    language: str | None = None
    framework: str | None = None
    test_runner: str | None = None
    test_command: str | None = None
    branch_naming: str | None = None

    # Agent outputs (populated sequentially)
    requirements: Requirements | None = None
    plan: Plan | None = None
    test_files: list[FileChange] = Field(default_factory=list)
    code_files: list[FileChange] = Field(default_factory=list)
    test_results: list[TestResult] = Field(default_factory=list)
    review_findings: list[ReviewFinding] = Field(default_factory=list)

    # Security outputs
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    security_patches_applied: int = 0
    requires_coding_rework: bool = False
    security_feedback: str = ""

    # Pipeline state
    status: PipelineStatus = PipelineStatus.PENDING
    current_step: str | None = None
    code_iteration: int = 0
    error_message: str | None = None

    # Cost/token tracking
    step_usage: dict[str, StepUsage] = Field(default_factory=dict)
    total_cost_usd: float = 0.0

    # Git tracking
    pre_run_sha: str | None = None
    step_commits: dict[str, str] = Field(default_factory=dict)
    worktree_path: Path | None = None

    @property
    def effective_path(self) -> Path:
        """Worktree path if set, otherwise project_path."""
        return self.worktree_path or self.project_path
