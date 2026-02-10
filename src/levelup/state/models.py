"""Pydantic models for state DB rows."""

from __future__ import annotations

from pydantic import BaseModel


class RunRecord(BaseModel):
    """Represents a row in the runs table."""

    run_id: str
    task_title: str
    task_description: str = ""
    project_path: str
    status: str = "pending"
    current_step: str | None = None
    language: str | None = None
    framework: str | None = None
    test_runner: str | None = None
    error_message: str | None = None
    context_json: str | None = None
    started_at: str
    updated_at: str
    pid: int | None = None
    total_cost_usd: float = 0.0
    pause_requested: int = 0


class CheckpointRequestRecord(BaseModel):
    """Represents a row in the checkpoint_requests table."""

    id: int | None = None
    run_id: str
    step_name: str
    checkpoint_data: str | None = None
    status: str = "pending"
    decision: str | None = None
    feedback: str = ""
    created_at: str
    decided_at: str | None = None
