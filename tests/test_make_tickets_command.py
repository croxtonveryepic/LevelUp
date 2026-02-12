"""Tests for the 'levelup make-tickets' CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from levelup.cli.app import app
from levelup.core.tickets import TicketStatus, add_ticket, read_tickets

runner = CliRunner()


class TestMakeTicketsFromExplicitFile:
    """Import tickets from an explicit filename argument."""

    def test_import_basic_tickets(self, tmp_path: Path):
        """Should import tickets from a specified markdown file."""
        md = tmp_path / "my-tickets.md"
        md.write_text(
            "## Add login page\n\nBuild the login UI.\n\n"
            "## Fix logout bug\n\nUsers can't log out.\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Imported 2 ticket(s)" in result.output

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 2
        assert tickets[0].title == "Add login page"
        assert tickets[1].title == "Fix logout bug"

    def test_explicit_file_not_deleted(self, tmp_path: Path):
        """Explicit file should NOT be deleted after import."""
        md = tmp_path / "custom.md"
        md.write_text("## Task one\n\nDescription.\n", encoding="utf-8")

        runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert md.exists(), "Explicit file should not be deleted"


class TestMakeTicketsFromDefaultPath:
    """Import from the default levelup/tickets.md location."""

    def test_import_from_default_path(self, tmp_path: Path):
        """Should use levelup/tickets.md when no filename argument given."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        md = tickets_dir / "tickets.md"
        md.write_text("## Default ticket\n\nBody.\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "Imported 1 ticket(s)" in result.output

        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].title == "Default ticket"

    def test_default_file_deleted_after_import(self, tmp_path: Path):
        """Default tickets.md should be deleted after successful import."""
        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        md = tickets_dir / "tickets.md"
        md.write_text("## Ticket A\n\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets",
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert not md.exists(), "Default file should be deleted after import"
        assert "Deleted" in result.output


class TestMakeTicketsErrorCases:
    """Error handling for missing/empty files."""

    def test_file_not_found(self, tmp_path: Path):
        """Should error if file does not exist."""
        result = runner.invoke(app, [
            "make-tickets", str(tmp_path / "nope.md"),
            "--path", str(tmp_path),
        ])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_default_file_not_found(self, tmp_path: Path):
        """Should error if default levelup/tickets.md does not exist."""
        result = runner.invoke(app, [
            "make-tickets",
            "--path", str(tmp_path),
        ])

        assert result.exit_code != 0

    def test_empty_file(self, tmp_path: Path):
        """Should handle a file with no tickets gracefully."""
        md = tmp_path / "empty.md"
        md.write_text("# Just a heading\n\nNo ## tickets here.\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        assert "No tickets found" in result.output


class TestMakeTicketsStatusPreservation:
    """Tickets with non-pending statuses should be preserved."""

    def test_in_progress_status(self, tmp_path: Path):
        """Should preserve [in progress] status from markdown."""
        md = tmp_path / "t.md"
        md.write_text("## [in progress] Active work\n\nDoing stuff.\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        assert tickets[0].status == TicketStatus.IN_PROGRESS

    def test_done_status(self, tmp_path: Path):
        """Should preserve [done] status from markdown."""
        md = tmp_path / "t.md"
        md.write_text("## [done] Finished task\n\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.DONE

    def test_merged_status(self, tmp_path: Path):
        """Should preserve [merged] status from markdown."""
        md = tmp_path / "t.md"
        md.write_text("## [merged] Old feature\n\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert tickets[0].status == TicketStatus.MERGED

    def test_mixed_statuses(self, tmp_path: Path):
        """Should handle a mix of statuses correctly."""
        md = tmp_path / "t.md"
        md.write_text(
            "## Pending one\n\n"
            "## [in progress] Active one\n\n"
            "## [done] Done one\n\n"
            "## Pending two\n\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 4
        assert tickets[0].status == TicketStatus.PENDING
        assert tickets[1].status == TicketStatus.IN_PROGRESS
        assert tickets[2].status == TicketStatus.DONE
        assert tickets[3].status == TicketStatus.PENDING


class TestMakeTicketsMetadata:
    """Tickets with metadata blocks should be preserved."""

    def test_metadata_preserved(self, tmp_path: Path):
        """Should import ticket metadata from HTML comment blocks."""
        md = tmp_path / "t.md"
        md.write_text(
            "## Task with meta\n\nDescription.\n\n"
            "<!--metadata\n"
            "priority: high\n"
            "-->\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 1
        # Note: _filter_run_options strips model/effort/skip_planning but not custom keys
        assert tickets[0].metadata is not None
        assert tickets[0].metadata.get("priority") == "high"


class TestMakeTicketsDbPath:
    """--db-path option should work."""

    def test_custom_db_path(self, tmp_path: Path):
        """Should use the specified DB path."""
        md = tmp_path / "t.md"
        md.write_text("## DB test ticket\n\n", encoding="utf-8")

        custom_db = tmp_path / "custom.db"

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
            "--db-path", str(custom_db),
        ])

        assert result.exit_code == 0
        assert "Imported 1 ticket(s)" in result.output

        # Verify ticket was stored in the custom DB
        tickets = read_tickets(tmp_path, db_path=custom_db)
        assert len(tickets) == 1
        assert tickets[0].title == "DB test ticket"


class TestMakeTicketsDescriptions:
    """Ticket descriptions should be imported correctly."""

    def test_multiline_description(self, tmp_path: Path):
        """Should preserve multi-line descriptions."""
        md = tmp_path / "t.md"
        md.write_text(
            "## Feature X\n\n"
            "Line one of description.\n"
            "Line two of description.\n\n"
            "Another paragraph.\n",
            encoding="utf-8",
        )

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert "Line one" in tickets[0].description
        assert "Line two" in tickets[0].description

    def test_empty_description(self, tmp_path: Path):
        """Should handle tickets with no description."""
        md = tmp_path / "t.md"
        md.write_text("## Title only\n\n## Another title only\n", encoding="utf-8")

        result = runner.invoke(app, [
            "make-tickets", str(md),
            "--path", str(tmp_path),
        ])

        assert result.exit_code == 0
        tickets = read_tickets(tmp_path)
        assert len(tickets) == 2
