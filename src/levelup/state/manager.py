"""StateManager: all DB read/write operations for multi-instance coordination."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from levelup.state.db import DEFAULT_DB_PATH, get_connection, init_db
from levelup.state.models import CheckpointRequestRecord, RunRecord


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    if pid <= 0:
        return False
    try:
        if os.name == "nt":
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


class StateManager:
    """Manages pipeline run state in SQLite for multi-instance coordination."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        init_db(self._db_path)

    def _conn(self) -> sqlite3.Connection:
        return get_connection(self._db_path)

    @staticmethod
    def _extract_ticket_number(ctx: object) -> int | None:
        """Extract ticket number from ctx.task.source_id (format 'ticket:N')."""
        from levelup.core.context import PipelineContext

        assert isinstance(ctx, PipelineContext)
        sid = ctx.task.source_id
        if sid and sid.startswith("ticket:"):
            try:
                return int(sid.split(":")[1])
            except (IndexError, ValueError):
                pass
        return None

    def register_run(self, ctx: object) -> None:
        """INSERT a new run from a PipelineContext."""
        from levelup.core.context import PipelineContext

        assert isinstance(ctx, PipelineContext)
        ticket_number = self._extract_ticket_number(ctx)
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO runs
                   (run_id, task_title, task_description, project_path, status,
                    current_step, language, framework, test_runner, started_at,
                    updated_at, pid, ticket_number)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ctx.run_id,
                    ctx.task.title,
                    ctx.task.description,
                    str(ctx.project_path),
                    ctx.status.value,
                    ctx.current_step,
                    ctx.language,
                    ctx.framework,
                    ctx.test_runner,
                    ctx.started_at.isoformat(),
                    _now_iso(),
                    os.getpid(),
                    ticket_number,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_run(self, ctx: object) -> None:
        """UPDATE status, current_step, context_json, updated_at for an existing run."""
        from levelup.core.context import PipelineContext

        assert isinstance(ctx, PipelineContext)
        context_json = ctx.model_dump_json()

        # Calculate total tokens from step_usage
        total_input_tokens = sum(usage.input_tokens for usage in ctx.step_usage.values())
        total_output_tokens = sum(usage.output_tokens for usage in ctx.step_usage.values())

        conn = self._conn()
        try:
            conn.execute(
                """UPDATE runs SET
                       status = ?, current_step = ?, language = ?, framework = ?,
                       test_runner = ?, error_message = ?, context_json = ?,
                       total_cost_usd = ?, input_tokens = ?, output_tokens = ?, updated_at = ?
                   WHERE run_id = ?""",
                (
                    ctx.status.value,
                    ctx.current_step,
                    ctx.language,
                    ctx.framework,
                    ctx.test_runner,
                    ctx.error_message,
                    context_json,
                    ctx.total_cost_usd,
                    total_input_tokens,
                    total_output_tokens,
                    _now_iso(),
                    ctx.run_id,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_run(self, run_id: str) -> RunRecord | None:
        """Get a single run by ID."""
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            return RunRecord(**dict(row))
        finally:
            conn.close()

    def list_runs(
        self, status_filter: str | None = None, limit: int = 50
    ) -> list[RunRecord]:
        """List runs, optionally filtered by status."""
        conn = self._conn()
        try:
            if status_filter:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE status = ? ORDER BY updated_at DESC LIMIT ?",
                    (status_filter, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runs ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [RunRecord(**dict(r)) for r in rows]
        finally:
            conn.close()

    def delete_run(self, run_id: str) -> None:
        """Delete a run and its checkpoint requests."""
        conn = self._conn()
        try:
            conn.execute("DELETE FROM checkpoint_requests WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM runs WHERE run_id = ?", (run_id,))
            conn.commit()
        finally:
            conn.close()

    def get_run_for_ticket(
        self, project_path: str, ticket_number: int
    ) -> RunRecord | None:
        """Return the most recent run for a given project + ticket number."""
        conn = self._conn()
        try:
            row = conn.execute(
                """SELECT * FROM runs
                   WHERE project_path = ? AND ticket_number = ?
                   ORDER BY updated_at DESC LIMIT 1""",
                (project_path, ticket_number),
            ).fetchone()
            if row is None:
                return None
            return RunRecord(**dict(row))
        finally:
            conn.close()

    def has_active_run_for_ticket(
        self, project_path: str, ticket_number: int
    ) -> RunRecord | None:
        """Return a non-completed run for the ticket, or None."""
        conn = self._conn()
        try:
            row = conn.execute(
                """SELECT * FROM runs
                   WHERE project_path = ? AND ticket_number = ?
                     AND status NOT IN ('completed', 'failed', 'aborted')
                   ORDER BY updated_at DESC LIMIT 1""",
                (project_path, ticket_number),
            ).fetchone()
            if row is None:
                return None
            return RunRecord(**dict(row))
        finally:
            conn.close()

    def create_checkpoint_request(
        self, run_id: str, step_name: str, checkpoint_data: str | None = None
    ) -> int:
        """Create a new checkpoint request, returns the request ID."""
        conn = self._conn()
        try:
            cursor = conn.execute(
                """INSERT INTO checkpoint_requests
                   (run_id, step_name, checkpoint_data, status, created_at)
                   VALUES (?, ?, ?, 'pending', ?)""",
                (run_id, step_name, checkpoint_data, _now_iso()),
            )
            conn.commit()
            return cursor.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def get_pending_checkpoints(self) -> list[CheckpointRequestRecord]:
        """Get all pending checkpoint requests across all runs."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM checkpoint_requests WHERE status = 'pending' ORDER BY created_at"
            ).fetchall()
            return [CheckpointRequestRecord(**dict(r)) for r in rows]
        finally:
            conn.close()

    def get_checkpoint_decision(
        self, run_id: str, step_name: str
    ) -> tuple[str, str] | None:
        """Get the decision for the latest checkpoint of a run+step if decided."""
        conn = self._conn()
        try:
            row = conn.execute(
                """SELECT decision, feedback FROM checkpoint_requests
                   WHERE run_id = ? AND step_name = ? AND status = 'decided'
                   ORDER BY decided_at DESC LIMIT 1""",
                (run_id, step_name),
            ).fetchone()
            if row is None:
                return None
            return (row["decision"], row["feedback"] or "")
        finally:
            conn.close()

    def submit_checkpoint_decision(
        self, request_id: int, decision: str, feedback: str = ""
    ) -> None:
        """GUI writes a decision for a checkpoint request."""
        conn = self._conn()
        try:
            conn.execute(
                """UPDATE checkpoint_requests
                   SET status = 'decided', decision = ?, feedback = ?, decided_at = ?
                   WHERE id = ?""",
                (decision, feedback, _now_iso(), request_id),
            )
            conn.commit()
        finally:
            conn.close()

    def request_pause(self, run_id: str) -> None:
        """Set the pause_requested flag for a run."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE runs SET pause_requested = 1, updated_at = ? WHERE run_id = ?",
                (_now_iso(), run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def is_pause_requested(self, run_id: str) -> bool:
        """Check if a pause has been requested for a run."""
        conn = self._conn()
        try:
            row = conn.execute(
                "SELECT pause_requested FROM runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None:
                return False
            return bool(row["pause_requested"])
        finally:
            conn.close()

    def clear_pause_request(self, run_id: str) -> None:
        """Clear the pause_requested flag for a run."""
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE runs SET pause_requested = 0, updated_at = ? WHERE run_id = ?",
                (_now_iso(), run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_dead_runs(self) -> int:
        """Check PIDs of active runs; mark dead processes as failed. Returns count."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT run_id, pid FROM runs WHERE status IN ('running', 'pending', 'waiting_for_input')"
            ).fetchall()
            count = 0
            for row in rows:
                pid = row["pid"]
                if pid and not _is_pid_alive(pid):
                    conn.execute(
                        "UPDATE runs SET status = 'failed', error_message = 'Process died', updated_at = ? WHERE run_id = ?",
                        (_now_iso(), row["run_id"]),
                    )
                    count += 1
            conn.commit()
            return count
        finally:
            conn.close()
