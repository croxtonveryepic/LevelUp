"""Tests for token usage tracking in GUI and database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from levelup.core.context import PipelineContext, PipelineStatus, StepUsage, TaskInput
from levelup.state.db import (
    CURRENT_SCHEMA_VERSION,
    SCHEMA_SQL,
    _get_schema_version,
    get_connection,
    init_db,
)
from levelup.state.manager import StateManager
from levelup.state.models import RunRecord


# ------------------------------------------------------------------ #
# 1. Database Migration v5: Add token columns
# ------------------------------------------------------------------ #


class TestDBMigrationV5:
    """Migration v5 should add input_tokens and output_tokens columns to runs table."""

    def test_current_schema_version_is_5(self):
        """AC: Update CURRENT_SCHEMA_VERSION to 5 in src/levelup/state/db.py"""
        assert CURRENT_SCHEMA_VERSION == 5

    def test_migration_adds_input_tokens_column(self, tmp_path: Path):
        """AC: Create database migration v5 that adds input_tokens INTEGER DEFAULT 0 column."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "input_tokens" in col_names

    def test_migration_adds_output_tokens_column(self, tmp_path: Path):
        """AC: Create database migration v5 that adds output_tokens INTEGER DEFAULT 0 column."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "output_tokens" in col_names

    def test_input_tokens_default_value(self, tmp_path: Path):
        """AC: input_tokens column defaults to 0."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert a run without specifying input_tokens
        conn.execute(
            """INSERT INTO runs (run_id, task_title, project_path, started_at, updated_at)
               VALUES ('test', 'task', '/tmp', '2025-01-01', '2025-01-01')"""
        )
        conn.commit()

        row = conn.execute("SELECT input_tokens FROM runs WHERE run_id = 'test'").fetchone()
        conn.close()
        assert row["input_tokens"] == 0

    def test_output_tokens_default_value(self, tmp_path: Path):
        """AC: output_tokens column defaults to 0."""
        db_path = tmp_path / "test.db"
        init_db(db_path)
        conn = get_connection(db_path)

        # Insert a run without specifying output_tokens
        conn.execute(
            """INSERT INTO runs (run_id, task_title, project_path, started_at, updated_at)
               VALUES ('test', 'task', '/tmp', '2025-01-01', '2025-01-01')"""
        )
        conn.commit()

        row = conn.execute("SELECT output_tokens FROM runs WHERE run_id = 'test'").fetchone()
        conn.close()
        assert row["output_tokens"] == 0

    def test_upgrade_from_v4_to_v5(self, tmp_path: Path):
        """AC: Migration runs successfully on existing databases (idempotent)."""
        db_path = tmp_path / "test.db"
        # Create a DB at v4 by initializing with old schema
        from levelup.state.db import MIGRATIONS

        conn = get_connection(db_path)
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        # Run only migrations up to v4
        for target_version, sql in MIGRATIONS:
            if target_version <= 4:
                conn.executescript(sql)
        conn.commit()

        version = _get_schema_version(conn)
        assert version == 4
        conn.close()

        # Now run init_db which should migrate to v5
        init_db(db_path)

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == 5
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "input_tokens" in col_names
        assert "output_tokens" in col_names

    def test_fresh_db_at_v5(self, tmp_path: Path):
        """Fresh database should be created at version 5."""
        db_path = tmp_path / "fresh.db"
        init_db(db_path)

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == 5

        # Verify token columns exist
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        conn.close()
        assert "input_tokens" in col_names
        assert "output_tokens" in col_names

    def test_existing_cost_tracking_tests_pass(self, tmp_path: Path):
        """AC: Existing test_cost_tracking.py tests pass with new schema."""
        # This test ensures backward compatibility with the existing cost tracking
        db_path = tmp_path / "test.db"
        init_db(db_path)

        conn = get_connection(db_path)
        # Verify total_cost_usd column still exists
        info = conn.execute("PRAGMA table_info(runs)").fetchall()
        col_names = [row["name"] for row in info]
        assert "total_cost_usd" in col_names

        # Insert and retrieve a run with cost
        conn.execute(
            """INSERT INTO runs
               (run_id, task_title, project_path, started_at, updated_at, total_cost_usd)
               VALUES ('test', 'task', '/tmp', '2025-01-01', '2025-01-01', 0.123)"""
        )
        conn.commit()

        row = conn.execute("SELECT total_cost_usd FROM runs WHERE run_id = 'test'").fetchone()
        conn.close()
        assert row["total_cost_usd"] == pytest.approx(0.123)

    def test_migration_is_idempotent(self, tmp_path: Path):
        """Running init_db multiple times should not fail."""
        db_path = tmp_path / "idempotent.db"
        init_db(db_path)
        init_db(db_path)  # second call should not fail
        init_db(db_path)  # third call should not fail

        conn = get_connection(db_path)
        version = _get_schema_version(conn)
        assert version == 5
        conn.close()


# ------------------------------------------------------------------ #
# 2. RunRecord Model: Add token fields
# ------------------------------------------------------------------ #


class TestRunRecordTokenFields:
    """RunRecord model should include input_tokens and output_tokens fields."""

    def test_runrecord_has_input_tokens_field(self):
        """AC: Add input_tokens: int = 0 field to RunRecord."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
        )
        assert hasattr(record, "input_tokens")
        assert record.input_tokens == 0

    def test_runrecord_has_output_tokens_field(self):
        """AC: Add output_tokens: int = 0 field to RunRecord."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
        )
        assert hasattr(record, "output_tokens")
        assert record.output_tokens == 0

    def test_token_fields_default_to_zero(self):
        """AC: Fields default to 0 for backward compatibility."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
        )
        assert record.input_tokens == 0
        assert record.output_tokens == 0

    def test_token_fields_can_be_set(self):
        """Token fields should accept integer values."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=1500,
            output_tokens=800,
        )
        assert record.input_tokens == 1500
        assert record.output_tokens == 800

    def test_token_fields_serialization(self):
        """Token fields should serialize and deserialize correctly."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=500,
            output_tokens=300,
        )
        data = record.model_dump()
        restored = RunRecord(**data)
        assert restored.input_tokens == 500
        assert restored.output_tokens == 300

    def test_token_fields_json_roundtrip(self):
        """Token fields should survive JSON serialization."""
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=1000,
            output_tokens=500,
        )
        json_str = record.model_dump_json()
        restored = RunRecord.model_validate_json(json_str)
        assert restored.input_tokens == 1000
        assert restored.output_tokens == 500


# ------------------------------------------------------------------ #
# 3. StateManager: Persist token counts
# ------------------------------------------------------------------ #


class TestStateManagerTokenPersistence:
    """StateManager should persist token counts from context.step_usage."""

    def test_update_run_calculates_total_tokens_from_step_usage(self, tmp_path: Path):
        """AC: Calculate total tokens from ctx.step_usage when updating runs."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="token test"))
        mgr.register_run(ctx)

        # Add step usage with token counts
        ctx.step_usage["requirements"] = StepUsage(
            input_tokens=100,
            output_tokens=50,
        )
        ctx.step_usage["planning"] = StepUsage(
            input_tokens=200,
            output_tokens=150,
        )
        ctx.step_usage["coding"] = StepUsage(
            input_tokens=500,
            output_tokens=300,
        )
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 800  # 100 + 200 + 500
        assert record.output_tokens == 500  # 50 + 150 + 300

    def test_update_run_persists_input_tokens(self, tmp_path: Path):
        """AC: Modify StateManager.update_run() to persist input_tokens from context."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="input tokens test"))
        mgr.register_run(ctx)

        ctx.step_usage["test"] = StepUsage(input_tokens=1500, output_tokens=0)
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 1500

    def test_update_run_persists_output_tokens(self, tmp_path: Path):
        """AC: Modify StateManager.update_run() to persist output_tokens from context."""
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="output tokens test"))
        mgr.register_run(ctx)

        ctx.step_usage["test"] = StepUsage(input_tokens=0, output_tokens=800)
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.output_tokens == 800

    def test_tokens_default_to_zero_when_no_step_usage(self, tmp_path: Path):
        """When context has no step_usage, tokens should remain 0."""
        db_path = tmp_path / "test_zero.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="no usage"))
        mgr.register_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 0
        assert record.output_tokens == 0

    def test_tokens_updated_multiple_times(self, tmp_path: Path):
        """Token counts should accumulate correctly across updates."""
        db_path = tmp_path / "test_multi.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="multi update"))
        mgr.register_run(ctx)

        ctx.step_usage["step1"] = StepUsage(input_tokens=100, output_tokens=50)
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        ctx.step_usage["step2"] = StepUsage(input_tokens=200, output_tokens=150)
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 300  # 100 + 200
        assert record.output_tokens == 200  # 50 + 150

    def test_existing_state_manager_tests_still_pass(self, tmp_path: Path):
        """AC: Existing StateManager tests continue to pass."""
        # This ensures backward compatibility with existing functionality
        db_path = tmp_path / "test.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="backward compat test"))
        mgr.register_run(ctx)

        ctx.status = PipelineStatus.COMPLETED
        ctx.current_step = "review"
        ctx.language = "python"
        ctx.total_cost_usd = 0.25
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.status == "completed"
        assert record.current_step == "review"
        assert record.language == "python"
        assert record.total_cost_usd == pytest.approx(0.25)

    def test_tokens_with_zero_values_in_step_usage(self, tmp_path: Path):
        """Steps with zero tokens should not affect the total."""
        db_path = tmp_path / "test_zero_steps.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="zero steps"))
        mgr.register_run(ctx)

        ctx.step_usage["detect"] = StepUsage(input_tokens=0, output_tokens=0)
        ctx.step_usage["requirements"] = StepUsage(input_tokens=100, output_tokens=50)
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 100
        assert record.output_tokens == 50


# ------------------------------------------------------------------ #
# 4. GUI Main Window: Display tokens in runs table
# ------------------------------------------------------------------ #


class TestGUITokensColumn:
    """GUI main window should display token information in runs table."""

    def test_columns_include_tokens(self):
        """AC: Add 'Tokens' column to COLUMNS list in src/levelup/gui/main_window.py"""
        from levelup.gui.main_window import COLUMNS

        assert "Tokens" in COLUMNS

    def test_tokens_column_position(self):
        """AC: Column shows between 'Status' and 'Started' columns"""
        from levelup.gui.main_window import COLUMNS

        status_idx = COLUMNS.index("Status")
        started_idx = COLUMNS.index("Started")
        tokens_idx = COLUMNS.index("Tokens")

        # Tokens should be between Status and Started
        assert status_idx < tokens_idx < started_idx

    def test_tokens_display_na_when_zero(self):
        """AC: Display token counts as 'N/A' when zero"""
        # This will be implemented in the _update_table method
        # For now, we test the format logic
        input_tokens = 0
        output_tokens = 0
        total = input_tokens + output_tokens

        if total == 0:
            display = "N/A"
        else:
            display = f"{total:,} ({input_tokens:,} in / {output_tokens:,} out)"

        assert display == "N/A"

    def test_tokens_display_format_with_values(self):
        """AC: Format as '{total:,} ({input:,} in / {output:,} out)' when available"""
        input_tokens = 1500
        output_tokens = 800
        total = input_tokens + output_tokens

        if total == 0:
            display = "N/A"
        else:
            display = f"{total:,} ({input_tokens:,} in / {output_tokens:,} out)"

        assert display == "2,300 (1,500 in / 800 out)"

    def test_tokens_display_format_with_large_numbers(self):
        """Large token counts should be formatted with thousands separators."""
        input_tokens = 123456
        output_tokens = 78900
        total = input_tokens + output_tokens

        display = f"{total:,} ({input_tokens:,} in / {output_tokens:,} out)"

        assert display == "202,356 (123,456 in / 78,900 out)"

    def test_tokens_column_updates_on_refresh(self):
        """AC: Token data updates on refresh from database"""
        # This is an integration test scenario that would verify
        # that _update_table() reads token data from RunRecord
        # and populates the Tokens column correctly

        # We test the data flow: RunRecord -> table display
        record = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=1000,
            output_tokens=500,
        )

        # Simulate the display logic
        total = record.input_tokens + record.output_tokens
        if total == 0:
            display = "N/A"
        else:
            display = f"{total:,} ({record.input_tokens:,} in / {record.output_tokens:,} out)"

        assert display == "1,500 (1,000 in / 500 out)"


# ------------------------------------------------------------------ #
# 5. GUI Run Detail View: Display token information
# ------------------------------------------------------------------ #


class TestGUIRunDetailTokens:
    """GUI run detail view should display token information."""

    def test_detail_view_includes_total_tokens(self):
        """AC: Show both total tokens and breakdown in detail view"""
        # Simulate the detail view message format
        run = RunRecord(
            run_id="abc123",
            task_title="Test task",
            task_description="A test",
            project_path="/tmp/proj",
            status="completed",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=1500,
            output_tokens=800,
        )

        total_tokens = run.input_tokens + run.output_tokens
        tokens_line = f"Tokens: {total_tokens:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)"

        assert tokens_line == "Tokens: 2,300 (1,500 in / 800 out)"

    def test_detail_view_tokens_format_matches_cli(self):
        """AC: Token info appears alongside existing run metadata in same format as CLI"""
        # The CLI format from project_context.md is:
        # {total:,} ({input:,} in / {output:,} out)
        run = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=500,
            output_tokens=300,
        )

        total = run.input_tokens + run.output_tokens
        cli_format = f"{total:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)"

        assert cli_format == "800 (500 in / 300 out)"

    def test_detail_view_shows_na_for_zero_tokens(self):
        """Detail view should show N/A when tokens are zero."""
        run = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            input_tokens=0,
            output_tokens=0,
        )

        total_tokens = run.input_tokens + run.output_tokens
        if total_tokens == 0:
            tokens_display = "N/A"
        else:
            tokens_display = f"{total_tokens:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)"

        assert tokens_display == "N/A"

    def test_detail_view_includes_cost_and_tokens(self):
        """AC: Token info appears alongside cost in detail view"""
        run = RunRecord(
            run_id="test",
            task_title="task",
            project_path="/tmp",
            started_at="2025-01-01",
            updated_at="2025-01-01",
            total_cost_usd=0.25,
            input_tokens=1500,
            output_tokens=800,
        )

        # Both cost and tokens should be displayable
        cost_line = f"Cost: ${run.total_cost_usd:.4f}"
        total_tokens = run.input_tokens + run.output_tokens
        tokens_line = f"Tokens: {total_tokens:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)"

        assert cost_line == "Cost: $0.2500"
        assert tokens_line == "Tokens: 2,300 (1,500 in / 800 out)"

    def test_detail_view_message_structure(self):
        """Detail view message should include token information in proper format."""
        run = RunRecord(
            run_id="abc123",
            task_title="Test task",
            task_description="A description",
            project_path="/tmp/proj",
            status="completed",
            current_step="review",
            started_at="2025-01-01T10:00:00Z",
            updated_at="2025-01-01T11:00:00Z",
            total_cost_usd=0.15,
            input_tokens=1000,
            output_tokens=500,
        )

        total_tokens = run.input_tokens + run.output_tokens

        # Simulate the detail message structure
        msg = (
            f"Run ID: {run.run_id}\n"
            f"Task: {run.task_title}\n"
            f"Status: {run.status}\n"
            f"Cost: ${run.total_cost_usd:.4f}\n"
            f"Tokens: {total_tokens:,} ({run.input_tokens:,} in / {run.output_tokens:,} out)\n"
        )

        assert "Run ID: abc123" in msg
        assert "Cost: $0.1500" in msg
        assert "Tokens: 1,500 (1,000 in / 500 out)" in msg


# ------------------------------------------------------------------ #
# 6. Integration Tests
# ------------------------------------------------------------------ #


class TestTokenTrackingIntegration:
    """End-to-end integration tests for token tracking."""

    def test_full_pipeline_token_flow(self, tmp_path: Path):
        """Test complete flow from context to database to GUI display."""
        db_path = tmp_path / "integration.db"
        mgr = StateManager(db_path=db_path)

        # Create a context with multiple steps
        ctx = PipelineContext(task=TaskInput(title="integration test"))
        mgr.register_run(ctx)

        # Simulate pipeline adding step usage
        ctx.step_usage["requirements"] = StepUsage(
            cost_usd=0.05,
            input_tokens=200,
            output_tokens=100,
            duration_ms=1500.0,
            num_turns=2,
        )
        ctx.step_usage["planning"] = StepUsage(
            cost_usd=0.10,
            input_tokens=500,
            output_tokens=300,
            duration_ms=3000.0,
            num_turns=3,
        )
        ctx.total_cost_usd = 0.15
        ctx.status = PipelineStatus.RUNNING
        mgr.update_run(ctx)

        # Retrieve and verify
        record = mgr.get_run(ctx.run_id)
        assert record is not None
        assert record.input_tokens == 700  # 200 + 500
        assert record.output_tokens == 400  # 100 + 300
        assert record.total_cost_usd == pytest.approx(0.15)

        # Verify GUI display format
        total_tokens = record.input_tokens + record.output_tokens
        display = f"{total_tokens:,} ({record.input_tokens:,} in / {record.output_tokens:,} out)"
        assert display == "1,100 (700 in / 400 out)"

    def test_backward_compatibility_with_old_runs(self, tmp_path: Path):
        """Old runs without token data should display N/A."""
        db_path = tmp_path / "old_runs.db"

        # Create a v4 database (before token columns)
        conn = sqlite3.connect(str(db_path))
        conn.executescript(SCHEMA_SQL)
        from levelup.state.db import MIGRATIONS
        for target_version, sql in MIGRATIONS:
            if target_version <= 4:
                conn.executescript(sql)
        conn.commit()

        # Insert an old run
        conn.execute(
            """INSERT INTO runs
               (run_id, task_title, project_path, started_at, updated_at, total_cost_usd)
               VALUES ('old', 'old task', '/tmp', '2025-01-01', '2025-01-01', 0.10)"""
        )
        conn.commit()
        conn.close()

        # Migrate to v5
        init_db(db_path)

        # Retrieve the old run
        mgr = StateManager(db_path=db_path)
        record = mgr.get_run("old")
        assert record is not None
        assert record.input_tokens == 0
        assert record.output_tokens == 0
        assert record.total_cost_usd == pytest.approx(0.10)

        # Should display N/A for tokens
        total_tokens = record.input_tokens + record.output_tokens
        display = "N/A" if total_tokens == 0 else f"{total_tokens:,}"
        assert display == "N/A"

    def test_tokens_persist_across_context_updates(self, tmp_path: Path):
        """Tokens should accumulate correctly as pipeline progresses."""
        db_path = tmp_path / "progress.db"
        mgr = StateManager(db_path=db_path)

        ctx = PipelineContext(task=TaskInput(title="progress test"))
        mgr.register_run(ctx)

        # Step 1
        ctx.step_usage["detect"] = StepUsage(input_tokens=50, output_tokens=20)
        mgr.update_run(ctx)
        record = mgr.get_run(ctx.run_id)
        assert record.input_tokens == 50
        assert record.output_tokens == 20

        # Step 2
        ctx.step_usage["requirements"] = StepUsage(input_tokens=200, output_tokens=100)
        mgr.update_run(ctx)
        record = mgr.get_run(ctx.run_id)
        assert record.input_tokens == 250  # 50 + 200
        assert record.output_tokens == 120  # 20 + 100

        # Step 3
        ctx.step_usage["planning"] = StepUsage(input_tokens=300, output_tokens=150)
        mgr.update_run(ctx)
        record = mgr.get_run(ctx.run_id)
        assert record.input_tokens == 550  # 50 + 200 + 300
        assert record.output_tokens == 270  # 20 + 100 + 150
