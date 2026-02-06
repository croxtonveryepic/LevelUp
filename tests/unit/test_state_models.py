"""Tests for state Pydantic models."""

from __future__ import annotations

from levelup.state.models import CheckpointRequestRecord, RunRecord


class TestRunRecord:
    def test_construction_minimal(self):
        record = RunRecord(
            run_id="abc123",
            task_title="Test task",
            project_path="/tmp/proj",
            started_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        assert record.run_id == "abc123"
        assert record.status == "pending"
        assert record.current_step is None
        assert record.language is None
        assert record.pid is None

    def test_construction_full(self):
        record = RunRecord(
            run_id="abc123",
            task_title="Test task",
            task_description="A description",
            project_path="/tmp/proj",
            status="running",
            current_step="requirements",
            language="python",
            framework="pytest",
            test_runner="pytest",
            error_message=None,
            context_json='{"key": "value"}',
            started_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:01:00Z",
            pid=12345,
        )
        assert record.status == "running"
        assert record.language == "python"
        assert record.pid == 12345

    def test_serialization_roundtrip(self):
        record = RunRecord(
            run_id="abc123",
            task_title="Test",
            project_path="/tmp",
            started_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        data = record.model_dump()
        restored = RunRecord(**data)
        assert restored == record

    def test_json_roundtrip(self):
        record = RunRecord(
            run_id="abc123",
            task_title="Test",
            project_path="/tmp",
            started_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
        )
        json_str = record.model_dump_json()
        restored = RunRecord.model_validate_json(json_str)
        assert restored == record


class TestCheckpointRequestRecord:
    def test_construction_minimal(self):
        record = CheckpointRequestRecord(
            run_id="abc123",
            step_name="requirements",
            created_at="2025-01-01T00:00:00Z",
        )
        assert record.id is None
        assert record.status == "pending"
        assert record.decision is None
        assert record.feedback == ""
        assert record.decided_at is None

    def test_construction_decided(self):
        record = CheckpointRequestRecord(
            id=1,
            run_id="abc123",
            step_name="requirements",
            checkpoint_data='{"summary": "test"}',
            status="decided",
            decision="approve",
            feedback="",
            created_at="2025-01-01T00:00:00Z",
            decided_at="2025-01-01T00:01:00Z",
        )
        assert record.status == "decided"
        assert record.decision == "approve"

    def test_serialization_roundtrip(self):
        record = CheckpointRequestRecord(
            id=5,
            run_id="abc123",
            step_name="review",
            status="pending",
            created_at="2025-01-01T00:00:00Z",
        )
        data = record.model_dump()
        restored = CheckpointRequestRecord(**data)
        assert restored == record
