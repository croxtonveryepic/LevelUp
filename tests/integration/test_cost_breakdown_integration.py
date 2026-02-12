"""Integration tests for cost breakdown display in pipeline runs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import PipelineStatus, TaskInput
from levelup.core.orchestrator import Orchestrator


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal Python project for testing."""
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    # Source file
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").touch()
    (src / "main.py").write_text("def hello():\n    return 'hello'\n")
    # Tests dir
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").touch()
    return tmp_path


@pytest.fixture
def settings(sample_project):
    return LevelUpSettings(
        llm=LLMSettings(
            api_key="test-key",
            model="claude-sonnet-4-5-20250929",
            backend="anthropic_sdk",
        ),
        project=ProjectSettings(path=sample_project),
        pipeline=PipelineSettings(
            require_checkpoints=False,
            create_git_branch=False,
            max_code_iterations=1,
        ),
    )


def _make_mock_response(text: str, input_tokens: int = 100, output_tokens: int = 50):
    """Create a mock Anthropic response with text content and usage info."""
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = text
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"

    # Add usage info
    mock_usage = MagicMock()
    mock_usage.input_tokens = input_tokens
    mock_usage.output_tokens = output_tokens
    mock_response.usage = mock_usage

    return mock_response


class TestCostBreakdownPipelineIntegration:
    """Integration tests for cost tracking through pipeline execution."""

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_cost_tracked_across_pipeline_steps(self, mock_anthropic_cls, settings):
        """Cost should be calculated and accumulated across all pipeline steps."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Set up responses with different token counts for each step
        requirements_json = json.dumps({
            "summary": "Add greeting function",
            "requirements": [
                {
                    "description": "Create greet function",
                    "acceptance_criteria": ["Returns greeting"],
                }
            ],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Add a greet function to main.py",
            "steps": [
                {
                    "order": 1,
                    "description": "Add greet function",
                    "files_to_modify": ["src/main.py"],
                    "files_to_create": [],
                }
            ],
            "affected_files": ["src/main.py"],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_greet.py", "description": "Test greet"}]
        })

        review_json = json.dumps({
            "approved": True,
            "summary": "Implementation looks good",
            "issues": [],
            "suggestions": [],
        })

        # Mock responses with varying token usage
        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=10000, output_tokens=5000),
            _make_mock_response(plan_json, input_tokens=8000, output_tokens=4000),
            _make_mock_response(test_writer_json, input_tokens=12000, output_tokens=6000),
            _make_mock_response("# Code implementation", input_tokens=15000, output_tokens=8000),
            _make_mock_response(review_json, input_tokens=9000, output_tokens=4500),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Add greeting function"))

        # Pipeline should complete
        assert ctx.status == PipelineStatus.COMPLETED

        # Total cost should be calculated from all steps
        # Using Sonnet pricing: $3/M input, $15/M output
        # Requirements: (10000 * 3 + 5000 * 15) / 1M = $0.105
        # Planning: (8000 * 3 + 4000 * 15) / 1M = $0.084
        # Test writing: (12000 * 3 + 6000 * 15) / 1M = $0.126
        # Coding: (15000 * 3 + 8000 * 15) / 1M = $0.165
        # Review: (9000 * 3 + 4500 * 15) / 1M = $0.0945
        # Total: $0.5745
        assert ctx.total_cost_usd == pytest.approx(0.5745, abs=0.001)

        # Each step should have cost calculated
        assert "requirements" in ctx.step_usage
        assert ctx.step_usage["requirements"].cost_usd == pytest.approx(0.105, abs=0.001)

        assert "planning" in ctx.step_usage
        assert ctx.step_usage["planning"].cost_usd == pytest.approx(0.084, abs=0.001)

        assert "test_writing" in ctx.step_usage
        assert ctx.step_usage["test_writing"].cost_usd == pytest.approx(0.126, abs=0.001)

        assert "coding" in ctx.step_usage
        assert ctx.step_usage["coding"].cost_usd == pytest.approx(0.165, abs=0.001)

        assert "review" in ctx.step_usage
        assert ctx.step_usage["review"].cost_usd == pytest.approx(0.0945, abs=0.001)

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_cost_varies_by_model(self, mock_anthropic_cls, settings):
        """Cost should vary based on the model used (Sonnet vs Opus)."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Test task",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        # Same token usage for both runs
        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=100000, output_tokens=50000),
        ]

        # Run with Sonnet model
        settings.llm.model = "claude-sonnet-4-5-20250929"
        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Sonnet: (100000 * 3 + 50000 * 15) / 1M = $1.05
        sonnet_cost = ctx.step_usage["requirements"].cost_usd
        assert sonnet_cost == pytest.approx(1.05, abs=0.01)

        # Now test with Opus model
        settings.llm.model = "claude-opus-4-6"
        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=100000, output_tokens=50000),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Opus: (100000 * 5 + 50000 * 25) / 1M = $1.75
        opus_cost = ctx.step_usage["requirements"].cost_usd
        assert opus_cost == pytest.approx(1.75, abs=0.01)

        # Opus should cost more than Sonnet
        assert opus_cost > sonnet_cost

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_cost_breakdown_persists_to_state_manager(self, mock_anthropic_cls, settings, tmp_path):
        """Cost breakdown should be persisted to state database."""
        from levelup.state.manager import StateManager

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Test",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=10000, output_tokens=5000),
        ]

        # Create state manager with test database
        db_path = tmp_path / "test.db"
        state_mgr = StateManager(db_path=db_path)

        orchestrator = Orchestrator(settings=settings, state_manager=state_mgr)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Retrieve run from database
        record = state_mgr.get_run(ctx.run_id)
        assert record is not None

        # Total cost should be persisted
        # (10000 * 3 + 5000 * 15) / 1M = $0.105
        assert record.total_cost_usd == pytest.approx(0.105, abs=0.001)

        # Token counts should be persisted
        assert record.input_tokens == 10000
        assert record.output_tokens == 5000

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_zero_cost_when_no_tokens_used(self, mock_anthropic_cls, settings):
        """Cost should be zero when no tokens are consumed."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Test",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        # Response with zero tokens
        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=0, output_tokens=0),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Cost should be zero
        assert ctx.step_usage["requirements"].cost_usd == 0.0
        assert ctx.total_cost_usd == 0.0

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_step_usage_includes_all_metrics(self, mock_anthropic_cls, settings):
        """StepUsage should include cost, tokens, duration, and turns."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Test",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=5000, output_tokens=2500),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        usage = ctx.step_usage["requirements"]

        # All metrics should be populated
        assert usage.cost_usd > 0  # Should be calculated
        assert usage.input_tokens == 5000
        assert usage.output_tokens == 2500
        assert usage.duration_ms > 0  # Should be measured
        assert usage.num_turns >= 1  # At least one turn


class TestCostBreakdownDisplayOutput:
    """Tests for cost breakdown display in CLI output."""

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_cost_breakdown_appears_in_pipeline_summary(self, mock_anthropic_cls, settings):
        """Cost breakdown table should appear in pipeline summary output."""
        from io import StringIO

        from rich.console import Console

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Test",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=10000, output_tokens=5000),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Capture display output
        from levelup.cli.display import print_pipeline_summary

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # Should contain cost breakdown table
            assert "Cost Breakdown" in result

            # Should show requirements step
            assert "requirements" in result

            # Should show formatted cost
            assert "$0.0" in result or "$0.1" in result  # Some cost value

            # Should show token count
            assert "15,000" in result  # 10k + 5k tokens

        finally:
            display_module.console = original_console

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_cost_breakdown_shows_all_pipeline_steps(self, mock_anthropic_cls, settings):
        """Cost breakdown should show all steps that were executed."""
        from io import StringIO

        from rich.console import Console

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Mock responses for multiple steps
        requirements_json = json.dumps({
            "summary": "Test",
            "requirements": [{"description": "Test", "acceptance_criteria": ["Works"]}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Simple approach",
            "steps": [{"order": 1, "description": "Do it", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_it.py", "description": "Test"}]
        })

        mock_client.messages.create.side_effect = [
            _make_mock_response(requirements_json, input_tokens=1000, output_tokens=500),
            _make_mock_response(plan_json, input_tokens=800, output_tokens=400),
            _make_mock_response(test_writer_json, input_tokens=1200, output_tokens=600),
            _make_mock_response("# Code", input_tokens=1500, output_tokens=750),
            _make_mock_response(json.dumps({"approved": True, "summary": "OK", "issues": [], "suggestions": []}), input_tokens=900, output_tokens=450),
        ]

        orchestrator = Orchestrator(settings=settings)
        ctx = orchestrator.run(task_input=TaskInput(title="Test"))

        # Capture display output
        from levelup.cli.display import print_pipeline_summary

        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)

        import levelup.cli.display as display_module
        original_console = display_module.console
        display_module.console = console

        try:
            print_pipeline_summary(ctx)
            result = output.getvalue()

            # All pipeline steps should appear in cost breakdown
            assert "requirements" in result
            assert "planning" in result
            assert "test_writing" in result
            assert "coding" in result
            assert "review" in result

        finally:
            display_module.console = original_console


class TestUpdatedCostTrackingTest:
    """Test that the existing test_cost_usd_defaults_to_zero is updated."""

    def test_existing_test_needs_update(self):
        """The test_cost_usd_defaults_to_zero test should be updated to expect calculated cost."""
        # Read the existing test file
        test_file = Path(__file__).parent.parent / "unit" / "test_cost_tracking.py"
        content = test_file.read_text(encoding="utf-8")

        # The test at line 270 should be updated
        # Original test expects cost_usd == 0.0
        # After implementation, it should calculate cost from tokens

        # This test documents that the original test needs to be changed
        # The original test has:
        #   input_tokens=100, output_tokens=50
        # With Sonnet pricing: (100 * 3 + 50 * 15) / 1M = $0.00105

        assert "def test_cost_usd_defaults_to_zero" in content
        # The test exists and will need to be updated during implementation
