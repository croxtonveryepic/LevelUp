"""Integration test for the full pipeline flow with mocked LLM."""

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
        llm=LLMSettings(api_key="test-key", model="test-model", backend="anthropic_sdk"),
        project=ProjectSettings(path=sample_project),
        pipeline=PipelineSettings(
            require_checkpoints=False,
            create_git_branch=False,
            max_code_iterations=2,
        ),
    )


def _make_mock_response(text: str):
    """Create a mock Anthropic response with text content."""
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = text
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"
    return mock_response


class TestFullPipeline:
    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_completes_with_mocked_llm(self, mock_anthropic_cls, settings):
        """Test that the pipeline runs through all steps with mocked LLM responses."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Set up responses for each agent call
        requirements_json = json.dumps({
            "summary": "Add a greeting endpoint",
            "requirements": [
                {
                    "description": "Create GET /greet endpoint",
                    "acceptance_criteria": ["Returns greeting message"],
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

        coder_json = json.dumps({
            "files_written": ["src/main.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        review_json = json.dumps({
            "findings": [],
            "overall_assessment": "Code looks good",
        })

        # Each agent will get a text-only response (no tool use)
        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json),
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Add greeting endpoint", description="Add GET /greet")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert ctx.requirements is not None
        assert ctx.requirements.summary == "Add a greeting endpoint"
        assert ctx.plan is not None
        assert ctx.plan.approach == "Add a greet function to main.py"
        assert ctx.language == "python"

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_detects_python_project(self, mock_anthropic_cls, settings):
        """Test that detection correctly identifies the sample project."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Just return empty JSON for each agent so pipeline completes
        empty_responses = [
            _make_mock_response(json.dumps({
                "summary": "s", "requirements": [], "assumptions": [],
                "out_of_scope": [], "clarifications": [],
            })),
            _make_mock_response(json.dumps({
                "approach": "a", "steps": [], "affected_files": [], "risks": [],
            })),
            _make_mock_response(json.dumps({"test_files": []})),
            _make_mock_response(json.dumps({
                "files_written": [], "iterations": 0, "all_tests_passing": True,
            })),
            _make_mock_response(json.dumps({"findings": [], "overall_assessment": "ok"})),
        ]
        mock_client.messages.create.side_effect = empty_responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Test detection")
        ctx = orchestrator.run(task)

        assert ctx.language == "python"
        assert ctx.test_runner == "pytest"
        assert ctx.test_command == "pytest"
