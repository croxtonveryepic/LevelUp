"""Tests for the `levelup tickets` CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.tickets import TicketStatus, read_tickets

runner = CliRunner()


def _write_tickets(tmp_path: Path, content: str) -> None:
    d = tmp_path / "levelup"
    d.mkdir(exist_ok=True)
    (d / "tickets.md").write_text(content, encoding="utf-8")


class TestTicketsCLI:
    def test_list_empty(self, tmp_path: Path):
        result = runner.invoke(app, ["tickets", "list", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No tickets" in result.output

    def test_list_shows_tickets(self, tmp_path: Path):
        _write_tickets(tmp_path, "## Task A\n\n## [done] Task B\n")
        result = runner.invoke(app, ["tickets", "list", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Task A" in result.output
        assert "Task B" in result.output

    def test_default_action_is_list(self, tmp_path: Path):
        result = runner.invoke(app, ["tickets", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No tickets" in result.output

    def test_next_shows_pending(self, tmp_path: Path):
        _write_tickets(tmp_path, "## [done] Done\n\n## Pending one\n")
        result = runner.invoke(app, ["tickets", "next", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "Pending one" in result.output

    def test_next_none_pending(self, tmp_path: Path):
        _write_tickets(tmp_path, "## [done] Done\n")
        result = runner.invoke(app, ["tickets", "next", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "No pending" in result.output

    def test_start_ticket(self, tmp_path: Path):
        _write_tickets(tmp_path, "## Task A\n")
        result = runner.invoke(app, ["tickets", "start", "1", "--path", str(tmp_path)])
        assert result.exit_code == 0
        assert "in progress" in result.output
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_done_ticket(self, tmp_path: Path):
        _write_tickets(tmp_path, "## [in progress] Task A\n")
        result = runner.invoke(app, ["tickets", "done", "1", "--path", str(tmp_path)])
        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE

    def test_merged_ticket(self, tmp_path: Path):
        _write_tickets(tmp_path, "## [done] Task A\n")
        result = runner.invoke(app, ["tickets", "merged", "1", "--path", str(tmp_path)])
        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.MERGED

    def test_action_without_number_fails(self, tmp_path: Path):
        _write_tickets(tmp_path, "## Task A\n")
        result = runner.invoke(app, ["tickets", "start", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_invalid_ticket_number(self, tmp_path: Path):
        _write_tickets(tmp_path, "## Task A\n")
        result = runner.invoke(app, ["tickets", "done", "99", "--path", str(tmp_path)])
        assert result.exit_code != 0

    def test_unknown_action(self, tmp_path: Path):
        result = runner.invoke(app, ["tickets", "nope", "--path", str(tmp_path)])
        assert result.exit_code != 0
