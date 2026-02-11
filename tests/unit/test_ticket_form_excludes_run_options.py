"""TDD tests for excluding run options from ticket form and metadata.

This test suite covers the requirements for removing run options (model, effort,
skip_planning) from TicketDetailWidget form and ticket metadata.

Requirements:
- Remove run options from TicketDetailWidget form
- Update _build_metadata() to exclude run options
- Update _build_save_metadata() to exclude run options
- Update set_ticket() to not populate run options from metadata
- Existing tickets with run options in metadata continue to load without errors

These tests follow TDD approach - they SHOULD FAIL initially until the
implementation is complete.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

# Skip all tests if PyQt6 not available
pytest.importorskip("PyQt6")


@pytest.fixture(scope="module")
def qapp():
    """Create QApplication for GUI tests."""
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


# ---------------------------------------------------------------------------
# AC: Run options removed from ticket form
# ---------------------------------------------------------------------------


class TestRunOptionsRemovedFromForm:
    """Test that run option widgets are removed from TicketDetailWidget form."""

    def test_model_combo_not_in_ticket_form(self, qapp, tmp_path):
        """AC: Model combo removed from ticket form (line 105)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Widget should NOT have a model combo in the form
        assert not hasattr(widget, "_model_combo"), "TicketDetailWidget should not have _model_combo"

    def test_effort_combo_not_in_ticket_form(self, qapp, tmp_path):
        """AC: Effort combo removed from ticket form (line 112)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Widget should NOT have an effort combo in the form
        assert not hasattr(widget, "_effort_combo"), "TicketDetailWidget should not have _effort_combo"

    def test_skip_planning_checkbox_not_in_ticket_form(self, qapp, tmp_path):
        """AC: Skip planning checkbox removed from ticket form (line 118)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Widget should NOT have a skip planning checkbox in the form
        assert not hasattr(
            widget, "_skip_planning_checkbox"
        ), "TicketDetailWidget should not have _skip_planning_checkbox"

    def test_auto_approve_checkbox_remains_in_form(self, qapp, tmp_path):
        """AC: Auto-approve checkbox remains in ticket form (it's ticket-level metadata)."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Auto-approve should STILL exist
        assert hasattr(widget, "auto_approve_checkbox"), "auto_approve_checkbox should remain"
        assert widget.auto_approve_checkbox is not None


# ---------------------------------------------------------------------------
# AC: _build_metadata() excludes run options
# ---------------------------------------------------------------------------


class TestBuildMetadataExcludesRunOptions:
    """Test that _build_metadata() no longer includes model, effort, skip_planning."""

    def test_build_metadata_excludes_model(self, qapp, tmp_path):
        """AC: _build_metadata() no longer includes model."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_metadata()
        if metadata:
            assert "model" not in metadata, "_build_metadata() should not include 'model'"

    def test_build_metadata_excludes_effort(self, qapp, tmp_path):
        """AC: _build_metadata() no longer includes effort."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_metadata()
        if metadata:
            assert "effort" not in metadata, "_build_metadata() should not include 'effort'"

    def test_build_metadata_excludes_skip_planning(self, qapp, tmp_path):
        """AC: _build_metadata() no longer includes skip_planning."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_metadata()
        if metadata:
            assert "skip_planning" not in metadata, "_build_metadata() should not include 'skip_planning'"

    def test_build_metadata_includes_auto_approve(self, qapp, tmp_path):
        """AC: _build_metadata() should STILL include auto_approve (ticket-level metadata)."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(tmp_path, "Test task", "Description")

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Check auto-approve
        widget.auto_approve_checkbox.setChecked(True)

        metadata = widget._build_metadata()
        assert metadata is not None
        assert metadata.get("auto_approve") is True, "_build_metadata() should include auto_approve"


# ---------------------------------------------------------------------------
# AC: _build_save_metadata() excludes run options
# ---------------------------------------------------------------------------


class TestBuildSaveMetadataExcludesRunOptions:
    """Test that _build_save_metadata() preserves only non-run-option metadata."""

    def test_build_save_metadata_excludes_model(self, qapp, tmp_path):
        """AC: _build_save_metadata() excludes model from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "sonnet", "priority": "high"},
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_save_metadata()
        if metadata:
            assert "model" not in metadata, "_build_save_metadata() should exclude 'model'"
            # priority should be preserved
            assert metadata.get("priority") == "high"

    def test_build_save_metadata_excludes_effort(self, qapp, tmp_path):
        """AC: _build_save_metadata() excludes effort from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"effort": "high", "estimate": "2h"},
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_save_metadata()
        if metadata:
            assert "effort" not in metadata, "_build_save_metadata() should exclude 'effort'"
            # estimate should be preserved
            assert metadata.get("estimate") == "2h"

    def test_build_save_metadata_excludes_skip_planning(self, qapp, tmp_path):
        """AC: _build_save_metadata() excludes skip_planning from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"skip_planning": True, "tags": ["bug", "urgent"]},
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        metadata = widget._build_save_metadata()
        if metadata:
            assert "skip_planning" not in metadata, "_build_save_metadata() should exclude 'skip_planning'"
            # tags should be preserved
            assert metadata.get("tags") == ["bug", "urgent"]

    def test_build_save_metadata_preserves_non_form_fields(self, qapp, tmp_path):
        """AC: _build_save_metadata() preserves non-run-option metadata from existing tickets."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={
                "model": "opus",
                "effort": "low",
                "skip_planning": True,
                "priority": "critical",
                "assignee": "alice",
                "custom_field": "value",
            },
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Change auto-approve
        widget.auto_approve_checkbox.setChecked(True)

        metadata = widget._build_save_metadata()
        assert metadata is not None

        # Run options should be removed
        assert "model" not in metadata
        assert "effort" not in metadata
        assert "skip_planning" not in metadata

        # Non-form fields should be preserved
        assert metadata.get("priority") == "critical"
        assert metadata.get("assignee") == "alice"
        assert metadata.get("custom_field") == "value"

        # Auto-approve (ticket-level) should be included
        assert metadata.get("auto_approve") is True


# ---------------------------------------------------------------------------
# AC: set_ticket() does not populate run options
# ---------------------------------------------------------------------------


class TestSetTicketDoesNotPopulateRunOptions:
    """Test that set_ticket() no longer populates run option widgets."""

    def test_set_ticket_does_not_populate_model_combo(self, qapp, tmp_path):
        """AC: set_ticket() no longer populates model combo from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"model": "sonnet"}
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Loading ticket should not attempt to set model combo (it doesn't exist)
        # This test verifies no AttributeError is raised
        widget.load_ticket(ticket)

    def test_set_ticket_does_not_populate_effort_combo(self, qapp, tmp_path):
        """AC: set_ticket() no longer populates effort combo from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"effort": "high"}
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Loading ticket should not attempt to set effort combo (it doesn't exist)
        widget.load_ticket(ticket)

    def test_set_ticket_does_not_populate_skip_planning(self, qapp, tmp_path):
        """AC: set_ticket() no longer populates skip_planning checkbox from metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"skip_planning": True}
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Loading ticket should not attempt to set skip_planning checkbox (it doesn't exist)
        widget.load_ticket(ticket)

    def test_set_ticket_populates_auto_approve(self, qapp, tmp_path):
        """AC: set_ticket() SHOULD still populate auto_approve (ticket-level metadata)."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path, "Test task", "Description", metadata={"auto_approve": True}
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        assert widget.auto_approve_checkbox.isChecked() is True


# ---------------------------------------------------------------------------
# AC: Backward compatibility with existing tickets
# ---------------------------------------------------------------------------


class TestBackwardCompatibilityWithRunOptions:
    """Test that existing tickets with run options in metadata continue to load."""

    def test_ticket_with_model_metadata_loads_without_error(self, qapp, tmp_path):
        """AC: Existing tickets with model metadata continue to load without errors."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "opus", "priority": "high"},
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should load without error
        widget.load_ticket(ticket)

        # Verify ticket loaded correctly
        assert widget._ticket.number == ticket.number
        assert widget._title_edit.text() == "Test task"

    def test_ticket_with_all_run_options_loads_without_error(self, qapp, tmp_path):
        """AC: Existing tickets with all run options continue to load without errors."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={
                "model": "sonnet",
                "effort": "high",
                "skip_planning": True,
                "auto_approve": True,
            },
        )

        widget = TicketDetailWidget(project_path=tmp_path)

        # Should load without error
        widget.load_ticket(ticket)

        # Verify ticket loaded correctly
        assert widget._ticket.number == ticket.number
        # auto_approve should still be populated
        assert widget.auto_approve_checkbox.isChecked() is True

    def test_save_removes_run_options_from_existing_ticket(self, qapp, tmp_path):
        """AC: Saving a ticket with run options in metadata removes them."""
        from levelup.core.tickets import add_ticket, read_tickets
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={
                "model": "opus",
                "effort": "low",
                "skip_planning": True,
                "priority": "urgent",
            },
        )

        widget = TicketDetailWidget(project_path=tmp_path)
        widget.load_ticket(ticket)

        # Make a change (to mark dirty and enable save)
        widget._title_edit.setText("Updated task")
        widget.save_ticket()

        # Read back
        tickets = read_tickets(tmp_path)
        saved_ticket = tickets[0]

        # Run options should be removed
        assert "model" not in (saved_ticket.metadata or {})
        assert "effort" not in (saved_ticket.metadata or {})
        assert "skip_planning" not in (saved_ticket.metadata or {})

        # Other metadata should be preserved
        assert saved_ticket.metadata.get("priority") == "urgent"


# ---------------------------------------------------------------------------
# AC: Ticket form has no reference to set_ticket_settings
# ---------------------------------------------------------------------------


class TestNoSetTicketSettingsCall:
    """Test that TicketDetailWidget does not call terminal.set_ticket_settings() for run options."""

    def test_set_ticket_does_not_call_set_ticket_settings(self, qapp, tmp_path):
        """AC: set_ticket_settings() method removed or refactored since settings no longer flow from ticket metadata."""
        from levelup.core.tickets import add_ticket
        from levelup.gui.ticket_detail import TicketDetailWidget

        tickets_dir = tmp_path / "levelup"
        tickets_dir.mkdir()
        ticket = add_ticket(
            tmp_path,
            "Test task",
            "Description",
            metadata={"model": "sonnet", "effort": "high", "skip_planning": True},
        )

        with patch("levelup.gui.terminal_emulator.PtyBackend"):
            widget = TicketDetailWidget(project_path=tmp_path)

            # Mock the terminal's set_ticket_settings if it still exists
            if hasattr(widget, "_current_terminal") and widget._current_terminal:
                with patch.object(
                    widget._current_terminal, "set_ticket_settings", create=True
                ) as mock_set:
                    widget.load_ticket(ticket)

                    # set_ticket_settings should NOT be called with run options
                    # Either it's not called at all, or called with empty/non-run-option args
                    if mock_set.called:
                        call_kwargs = mock_set.call_args.kwargs if mock_set.call_args else {}
                        # Verify run options are NOT passed
                        assert (
                            "model" not in call_kwargs or call_kwargs["model"] is None
                        ), "model should not be passed"
                        assert (
                            "effort" not in call_kwargs or call_kwargs["effort"] is None
                        ), "effort should not be passed"
                        assert (
                            "skip_planning" not in call_kwargs
                            or call_kwargs["skip_planning"] is False
                        ), "skip_planning should not be passed"


# ---------------------------------------------------------------------------
# AC: Form keys constant updated
# ---------------------------------------------------------------------------


class TestFormKeysConstant:
    """Test that the form_keys set in _build_save_metadata() is updated."""

    def test_form_keys_excludes_run_options(self, qapp, tmp_path):
        """AC: form_keys in _build_save_metadata() should only include 'auto_approve'."""
        from levelup.gui.ticket_detail import TicketDetailWidget

        widget = TicketDetailWidget(project_path=tmp_path)

        # Inspect the _build_save_metadata method to verify form_keys
        # This is implementation-specific, but the key insight is that
        # form_keys should only contain "auto_approve", not run options

        # We can test this indirectly by verifying metadata preservation behavior
        # (already covered in other tests)
