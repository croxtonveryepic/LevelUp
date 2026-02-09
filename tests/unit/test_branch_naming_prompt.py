"""Tests for branch naming convention prompting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.cli.prompts import prompt_branch_naming_convention
from levelup.config.settings import LevelUpSettings, LLMSettings, PipelineSettings, ProjectSettings
from levelup.core.context import PipelineContext, TaskInput
from levelup.core.orchestrator import Orchestrator
from levelup.core.project_context import get_project_context_path


class TestPromptBranchNamingConvention:
    """Tests for prompt_branch_naming_convention() function."""

    @patch("levelup.cli.prompts.pt_prompt")
    def test_prompts_user_for_convention(self, mock_prompt, tmp_path: Path):
        """Prompts user interactively for branch naming convention."""
        mock_prompt.return_value = "1"

        result = prompt_branch_naming_convention()

        assert result is not None
        assert mock_prompt.called

    @patch("levelup.cli.prompts.pt_prompt")
    def test_returns_levelup_run_id_for_option_1(self, mock_prompt, tmp_path: Path):
        """Option 1 returns 'levelup/{run_id}' pattern."""
        mock_prompt.return_value = "1"

        result = prompt_branch_naming_convention()
        assert result == "levelup/{run_id}"

    @patch("levelup.cli.prompts.pt_prompt")
    def test_returns_feature_task_title_for_option_2(self, mock_prompt, tmp_path: Path):
        """Option 2 returns 'feature/{task_title}' pattern."""
        mock_prompt.return_value = "2"

        result = prompt_branch_naming_convention()
        assert result == "feature/{task_title}"

    @patch("levelup.cli.prompts.pt_prompt")
    def test_returns_ai_run_id_for_option_3(self, mock_prompt, tmp_path: Path):
        """Option 3 returns 'ai/{run_id}' pattern."""
        mock_prompt.return_value = "3"

        result = prompt_branch_naming_convention()
        assert result == "ai/{run_id}"

    @patch("levelup.cli.prompts.pt_prompt")
    def test_accepts_custom_format_for_option_4(self, mock_prompt, tmp_path: Path):
        """Option 4 prompts for custom format and returns it."""
        # First call returns "4", second call returns custom format
        mock_prompt.side_effect = ["4", "custom/{date}-{run_id}"]

        result = prompt_branch_naming_convention()
        assert result == "custom/{date}-{run_id}"
        assert mock_prompt.call_count == 2

    @patch("levelup.cli.prompts.pt_prompt")
    def test_reprompts_on_invalid_choice(self, mock_prompt, tmp_path: Path):
        """Re-prompts when user enters invalid option."""
        mock_prompt.side_effect = ["invalid", "5", "1"]

        result = prompt_branch_naming_convention()
        assert result == "levelup/{run_id}"
        assert mock_prompt.call_count == 3

    @patch("levelup.cli.prompts.pt_prompt")
    def test_displays_examples_in_prompt(self, mock_prompt, tmp_path: Path):
        """Prompt displays examples of branch naming patterns."""
        mock_prompt.return_value = "1"

        # We can't directly test console output, but we can verify the function runs
        result = prompt_branch_naming_convention()
        assert result is not None

    @patch("levelup.cli.prompts.pt_prompt")
    def test_accepts_custom_format_with_placeholders(self, mock_prompt, tmp_path: Path):
        """Custom format can include all valid placeholders."""
        mock_prompt.side_effect = ["4", "dev/{run_id}/{task_title}/{date}"]

        result = prompt_branch_naming_convention()
        assert result == "dev/{run_id}/{task_title}/{date}"
        assert "{run_id}" in result
        assert "{task_title}" in result
        assert "{date}" in result

    @patch("levelup.cli.prompts.pt_prompt")
    def test_accepts_custom_format_without_placeholders(self, mock_prompt, tmp_path: Path):
        """Custom format doesn't require placeholders."""
        mock_prompt.side_effect = ["4", "my-static-branch"]

        result = prompt_branch_naming_convention()
        assert result == "my-static-branch"


class TestOrchestratorPromptBranchNamingIfNeeded:
    """Tests for Orchestrator._prompt_branch_naming_if_needed() method."""

    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_prompts_when_convention_missing(self, mock_prompt, tmp_path: Path):
        """Prompts for convention when not present in project_context.md."""
        mock_prompt.return_value = "feature/{task_title}"

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._prompt_branch_naming_if_needed(ctx, tmp_path)

        assert result == "feature/{task_title}"
        mock_prompt.assert_called_once()

    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_skips_prompt_when_convention_exists(self, mock_prompt, tmp_path: Path):
        """Skips prompt when convention already exists in context."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"), branch_naming="ai/{run_id}")

        result = orch._prompt_branch_naming_if_needed(ctx, tmp_path)

        assert result == "ai/{run_id}"
        mock_prompt.assert_not_called()

    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_skips_prompt_when_create_git_branch_false(self, mock_prompt, tmp_path: Path):
        """Skips prompt when create_git_branch is False."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=False),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._prompt_branch_naming_if_needed(ctx, tmp_path)

        # Should return default without prompting
        assert result == "levelup/{run_id}"
        mock_prompt.assert_not_called()

    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_returns_default_when_prompt_returns_none(self, mock_prompt, tmp_path: Path):
        """Returns default convention when prompt returns None."""
        mock_prompt.return_value = None

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._prompt_branch_naming_if_needed(ctx, tmp_path)
        assert result == "levelup/{run_id}"

    @patch("levelup.cli.prompts.prompt_branch_naming_convention")
    def test_stores_convention_in_context(self, mock_prompt, tmp_path: Path):
        """Stores prompted convention in context.branch_naming."""
        mock_prompt.return_value = "custom/{run_id}"

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        ctx = PipelineContext(task=TaskInput(title="Test"))

        result = orch._prompt_branch_naming_if_needed(ctx, tmp_path)

        assert ctx.branch_naming == "custom/{run_id}"
        assert result == "custom/{run_id}"


class TestOrchestratorLoadBranchNamingFromContext:
    """Tests for Orchestrator._load_branch_naming_from_context() helper."""

    def test_loads_convention_from_project_context(self, tmp_path: Path):
        """Loads branch_naming from project_context.md header."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n"
            "- **Branch naming:** feature/{task_title}\n",
            encoding="utf-8",
        )

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        result = orch._load_branch_naming_from_context(tmp_path)
        assert result == "feature/{task_title}"

    def test_returns_default_when_field_missing(self, tmp_path: Path):
        """Returns default 'levelup/{run_id}' when field is missing."""
        path = get_project_context_path(tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "# Project Context\n\n"
            "- **Language:** Python\n"
            "- **Framework:** none\n"
            "- **Test runner:** pytest\n"
            "- **Test command:** pytest\n",
            encoding="utf-8",
        )

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        result = orch._load_branch_naming_from_context(tmp_path)
        assert result == "levelup/{run_id}"

    def test_returns_default_when_file_missing(self, tmp_path: Path):
        """Returns default when project_context.md doesn't exist."""
        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        result = orch._load_branch_naming_from_context(tmp_path)
        assert result == "levelup/{run_id}"

    def test_loads_various_conventions(self, tmp_path: Path):
        """Loads various branch naming conventions correctly."""
        conventions = [
            "levelup/{run_id}",
            "ai/{run_id}",
            "feature/{task_title}",
            "dev/{date}-{run_id}",
            "custom/{run_id}/{task_title}",
        ]

        settings = LevelUpSettings(
            llm=LLMSettings(api_key="test", model="test", backend="claude_code"),
            project=ProjectSettings(path=tmp_path),
            pipeline=PipelineSettings(create_git_branch=True),
        )
        orch = Orchestrator(settings=settings)

        for convention in conventions:
            path = get_project_context_path(tmp_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "# Project Context\n\n"
                "- **Language:** Python\n"
                "- **Framework:** none\n"
                "- **Test runner:** pytest\n"
                "- **Test command:** pytest\n"
                f"- **Branch naming:** {convention}\n",
                encoding="utf-8",
            )

            result = orch._load_branch_naming_from_context(tmp_path)
            assert result == convention
