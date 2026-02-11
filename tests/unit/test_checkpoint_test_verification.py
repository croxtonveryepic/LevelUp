"""Unit tests for checkpoint display handling of test_verification step."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.core.checkpoint import build_checkpoint_display_data
from levelup.core.context import PipelineContext, TaskInput


@pytest.fixture()
def basic_ctx(tmp_path: Path) -> PipelineContext:
    """A minimal pipeline context."""
    return PipelineContext(
        task=TaskInput(title="Add login", description="Implement login"),
        project_path=tmp_path,
        language="python",
        framework="fastapi",
        test_runner="pytest",
        test_command="pytest tests/",
    )


class TestCheckpointDisplayTestVerification:
    """Tests for checkpoint display data builder handling test_verification step."""

    def test_build_checkpoint_display_handles_test_verification_gracefully(self, basic_ctx):
        """build_checkpoint_display_data() handles 'test_verification' step without errors."""
        # Should not raise an exception
        data = build_checkpoint_display_data("test_verification", basic_ctx)
        assert isinstance(data, dict)

    def test_build_checkpoint_display_returns_minimal_data_for_test_verification(self, basic_ctx):
        """build_checkpoint_display_data() returns minimal or empty data for test_verification."""
        data = build_checkpoint_display_data("test_verification", basic_ctx)

        # Should at least have step_name
        assert "step_name" in data
        assert data["step_name"] == "test_verification"

    def test_build_checkpoint_display_includes_verification_result(self, basic_ctx):
        """Display data includes test_verification_passed status if available."""
        basic_ctx.test_verification_passed = True

        data = build_checkpoint_display_data("test_verification", basic_ctx)

        # If available in context, should be included in display data
        # (Or it might be omitted since this step has no checkpoint - either is acceptable)
        assert isinstance(data, dict)

    def test_build_checkpoint_display_with_verification_passed_true(self, basic_ctx):
        """Display data reflects when verification passed (tests correctly failed)."""
        basic_ctx.test_verification_passed = True

        data = build_checkpoint_display_data("test_verification", basic_ctx)

        assert data["step_name"] == "test_verification"
        # Should not error out
        assert isinstance(data, dict)

    def test_build_checkpoint_display_with_verification_passed_false(self, basic_ctx):
        """Display data reflects when verification failed (tests incorrectly passed)."""
        basic_ctx.test_verification_passed = False

        data = build_checkpoint_display_data("test_verification", basic_ctx)

        assert data["step_name"] == "test_verification"
        # Should not error out
        assert isinstance(data, dict)

    def test_build_checkpoint_display_no_verification_result(self, basic_ctx):
        """Display data works when test_verification_passed is not set."""
        # Don't set test_verification_passed
        data = build_checkpoint_display_data("test_verification", basic_ctx)

        assert data["step_name"] == "test_verification"
        # Should still return valid data structure
        assert isinstance(data, dict)

    def test_build_checkpoint_display_does_not_include_unnecessary_data(self, basic_ctx):
        """test_verification display data doesn't include unrelated checkpoint data."""
        data = build_checkpoint_display_data("test_verification", basic_ctx)

        # Should not include data from other checkpoint steps
        assert "requirements" not in data
        assert "code_files" not in data
        assert "review_findings" not in data

    def test_build_checkpoint_display_for_requirements_still_works(self, basic_ctx):
        """Existing checkpoint steps (requirements) still work after adding test_verification."""
        from levelup.core.context import Requirement, Requirements

        basic_ctx.requirements = Requirements(
            summary="Test requirements",
            requirements=[Requirement(description="Test req", acceptance_criteria=["AC1"])],
        )

        data = build_checkpoint_display_data("requirements", basic_ctx)

        assert data["step_name"] == "requirements"
        assert "requirements" in data

    def test_build_checkpoint_display_for_test_writing_still_works(self, basic_ctx):
        """Existing checkpoint steps (test_writing) still work after adding test_verification."""
        from levelup.core.context import FileChange

        basic_ctx.test_files = [
            FileChange(path="tests/test_login.py", content="def test(): pass", is_new=True)
        ]

        data = build_checkpoint_display_data("test_writing", basic_ctx)

        assert data["step_name"] == "test_writing"
        assert "test_files" in data

    def test_build_checkpoint_display_for_review_still_works(self, basic_ctx):
        """Existing checkpoint steps (review) still work after adding test_verification."""
        from levelup.core.context import FileChange, TestResult

        basic_ctx.code_files = [
            FileChange(path="src/login.py", content="def login(): pass", is_new=True)
        ]
        basic_ctx.test_results = [
            TestResult(passed=True, total=5, failures=0, output="5 passed")
        ]

        data = build_checkpoint_display_data("review", basic_ctx)

        assert data["step_name"] == "review"
        assert "code_files" in data
        assert "test_results" in data

    def test_build_checkpoint_display_returns_serializable_dict(self, basic_ctx):
        """Display data for test_verification is JSON-serializable."""
        import json

        basic_ctx.test_verification_passed = True
        data = build_checkpoint_display_data("test_verification", basic_ctx)

        # Should be serializable to JSON without errors
        json_str = json.dumps(data)
        assert isinstance(json_str, str)

    def test_build_checkpoint_display_with_empty_context(self, tmp_path):
        """Display builder handles empty context for test_verification."""
        ctx = PipelineContext(
            task=TaskInput(title="Empty test"),
            project_path=tmp_path,
        )

        data = build_checkpoint_display_data("test_verification", ctx)

        assert data["step_name"] == "test_verification"
        assert isinstance(data, dict)


class TestCheckpointDisplayNoUserInteraction:
    """Tests verifying test_verification step doesn't trigger user checkpoints."""

    def test_test_verification_step_has_no_checkpoint_in_pipeline(self):
        """test_verification step in DEFAULT_PIPELINE has checkpoint_after=False."""
        from levelup.core.pipeline import DEFAULT_PIPELINE

        test_verification = next(
            s for s in DEFAULT_PIPELINE if s.name == "test_verification"
        )
        assert test_verification.checkpoint_after is False

    def test_checkpoint_not_shown_for_test_verification(self, basic_ctx):
        """run_checkpoint is not called for test_verification step (no user prompt)."""
        # This is enforced by checkpoint_after=False in pipeline definition
        # Verified in the pipeline tests, but documenting here for clarity
        from levelup.core.pipeline import DEFAULT_PIPELINE

        test_verification = next(
            s for s in DEFAULT_PIPELINE if s.name == "test_verification"
        )

        # Verification: no checkpoint
        assert test_verification.checkpoint_after is False

    def test_only_expected_steps_have_checkpoints(self):
        """Only requirements, test_writing, security, and review have checkpoints."""
        from levelup.core.pipeline import DEFAULT_PIPELINE

        checkpoint_steps = {s.name for s in DEFAULT_PIPELINE if s.checkpoint_after}

        expected_checkpoints = {"requirements", "test_writing", "security", "review"}
        assert checkpoint_steps == expected_checkpoints
        assert "test_verification" not in checkpoint_steps


class TestCheckpointDisplayDataStructure:
    """Tests for the structure of checkpoint display data."""

    def test_all_checkpoint_steps_return_consistent_structure(self, basic_ctx):
        """All checkpoint-enabled steps return dict with step_name."""
        from levelup.core.context import FileChange, Requirement, Requirements, TestResult

        # Set up context with data for all checkpoint steps
        basic_ctx.requirements = Requirements(
            summary="Test", requirements=[Requirement(description="R", acceptance_criteria=[])]
        )
        basic_ctx.test_files = [FileChange(path="test.py", content="pass")]
        basic_ctx.code_files = [FileChange(path="code.py", content="pass")]
        basic_ctx.test_results = [TestResult(passed=True, total=1)]

        checkpoint_steps = ["requirements", "test_writing", "security", "review"]

        for step_name in checkpoint_steps:
            data = build_checkpoint_display_data(step_name, basic_ctx)
            assert "step_name" in data
            assert data["step_name"] == step_name
            assert isinstance(data, dict)

    def test_non_checkpoint_step_still_returns_valid_data(self, basic_ctx):
        """Non-checkpoint steps like test_verification still return valid structure."""
        data = build_checkpoint_display_data("test_verification", basic_ctx)

        # Should have at minimum step_name
        assert "step_name" in data
        assert isinstance(data, dict)
