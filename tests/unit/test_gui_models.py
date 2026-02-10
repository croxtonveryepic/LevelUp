"""Tests for GUI helper logic (no Qt dependency needed)."""

from __future__ import annotations

import json

from levelup.gui.checkpoint_dialog import format_checkpoint_data
from levelup.gui.resources import STATUS_COLORS, STATUS_LABELS, status_display


class TestFormatCheckpointData:
    def test_none_input(self):
        result = format_checkpoint_data(None)
        assert "No checkpoint data" in result

    def test_empty_string(self):
        result = format_checkpoint_data("")
        assert "No checkpoint data" in result

    def test_invalid_json(self):
        result = format_checkpoint_data("not json at all")
        assert result == "not json at all"

    def test_requirements_step(self):
        data = {
            "step_name": "requirements",
            "requirements": {
                "summary": "Build a widget",
                "requirements": [
                    {
                        "id": "r1",
                        "description": "Widget renders",
                        "acceptance_criteria": ["Renders correctly"],
                    }
                ],
                "assumptions": ["User has modern browser"],
                "out_of_scope": ["Mobile support"],
            },
        }
        result = format_checkpoint_data(json.dumps(data))
        assert "requirements" in result
        assert "Build a widget" in result
        assert "Widget renders" in result
        assert "Renders correctly" in result
        assert "modern browser" in result
        assert "Mobile support" in result

    def test_test_writing_step(self):
        data = {
            "step_name": "test_writing",
            "test_files": [
                {"path": "tests/test_foo.py", "content": "def test_foo(): pass", "is_new": True}
            ],
        }
        result = format_checkpoint_data(json.dumps(data))
        assert "test_foo.py" in result
        assert "def test_foo" in result

    def test_review_step(self):
        data = {
            "step_name": "review",
            "code_files": [
                {"path": "src/foo.py", "content": "class Foo: ...", "is_new": True}
            ],
            "test_results": [
                {"passed": True, "total": 5, "failures": 0, "errors": 0, "output": "", "command": ""}
            ],
            "review_findings": [
                {
                    "severity": "warning",
                    "category": "style",
                    "file": "src/foo.py",
                    "line": 10,
                    "message": "Missing docstring",
                    "suggestion": "Add a docstring",
                }
            ],
        }
        result = format_checkpoint_data(json.dumps(data))
        assert "foo.py" in result
        assert "PASS" in result
        assert "Missing docstring" in result

    def test_message_field(self):
        data = {"step_name": "requirements", "message": "No requirements produced."}
        result = format_checkpoint_data(json.dumps(data))
        assert "No requirements produced." in result


class TestStatusDisplay:
    def test_known_statuses(self):
        for status in STATUS_COLORS:
            result = status_display(status)
            assert STATUS_LABELS[status] in result

    def test_unknown_status(self):
        result = status_display("unknown_status")
        assert "unknown_status" in result

    def test_all_statuses_have_colors(self):
        expected = {"running", "waiting_for_input", "paused", "completed", "failed", "aborted", "pending"}
        assert set(STATUS_COLORS.keys()) == expected

    def test_all_statuses_have_labels(self):
        assert set(STATUS_LABELS.keys()) == set(STATUS_COLORS.keys())
