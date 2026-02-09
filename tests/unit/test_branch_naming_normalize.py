"""Tests for branch naming normalization logic."""

from __future__ import annotations

import pytest

from levelup.core.branch_naming import normalize_branch_convention


class TestPassthrough:
    """Existing {placeholder} patterns return unchanged."""

    def test_levelup_run_id(self):
        assert normalize_branch_convention("levelup/{run_id}") == "levelup/{run_id}"

    def test_feature_task_title(self):
        assert normalize_branch_convention("feature/{task_title}") == "feature/{task_title}"

    def test_ai_run_id(self):
        assert normalize_branch_convention("ai/{run_id}") == "ai/{run_id}"

    def test_custom_all_placeholders(self):
        pattern = "dev/{date}-{run_id}/{task_title}"
        assert normalize_branch_convention(pattern) == pattern

    def test_date_placeholder(self):
        assert normalize_branch_convention("{date}/fix") == "{date}/fix"


class TestNaturalLanguage:
    """Natural-language aliases are converted to canonical placeholders."""

    def test_task_title_alias(self):
        assert normalize_branch_convention("feature/task-title") == "feature/{task_title}"

    def test_task_title_underscore(self):
        assert normalize_branch_convention("feature/task_title") == "feature/{task_title}"

    def test_run_id_alias(self):
        assert normalize_branch_convention("levelup/run-id") == "levelup/{run_id}"

    def test_run_id_underscore(self):
        assert normalize_branch_convention("levelup/run_id") == "levelup/{run_id}"

    def test_runid_alias(self):
        assert normalize_branch_convention("levelup/runid") == "levelup/{run_id}"

    def test_date_alias(self):
        assert normalize_branch_convention("fix/date") == "fix/{date}"

    def test_title_alias(self):
        assert normalize_branch_convention("feature/title") == "feature/{task_title}"

    def test_task_alias(self):
        assert normalize_branch_convention("feature/task") == "feature/{task_title}"

    def test_id_alias(self):
        assert normalize_branch_convention("levelup/id") == "levelup/{run_id}"

    def test_multiple_aliases(self):
        assert normalize_branch_convention("dev/date-run-id") == "dev/{date}-{run_id}"

    def test_date_task_title(self):
        assert normalize_branch_convention("dev/date-task-title") == "dev/{date}-{task_title}"


class TestUserExample:
    """The canonical user example from the plan."""

    def test_levelup_task_title_in_kebab_case(self):
        result = normalize_branch_convention("levelup/task-title-in-kebab-case")
        assert result == "levelup/{task_title}"


class TestFormatDescriptorStripping:
    """Format descriptors are stripped from segments containing placeholders."""

    def test_kebab_case_descriptor(self):
        result = normalize_branch_convention("feature/task-title-in-kebab-case")
        assert result == "feature/{task_title}"

    def test_snake_case_descriptor(self):
        result = normalize_branch_convention("feature/task_title-in-snake-case")
        assert result == "feature/{task_title}"

    def test_no_stripping_without_placeholder(self):
        """Descriptors are NOT stripped from segments without placeholders."""
        result = normalize_branch_convention("feature-in-kebab-case/task-title")
        assert result == "feature-in-kebab-case/{task_title}"


class TestWordBoundary:
    """Aliases only match at word boundaries, not inside other words."""

    def test_id_not_in_valid(self):
        result = normalize_branch_convention("valid/task-title")
        assert result == "valid/{task_title}"

    def test_id_not_in_android(self):
        result = normalize_branch_convention("android/task-title")
        assert result == "android/{task_title}"

    def test_date_not_in_update(self):
        result = normalize_branch_convention("update/run-id")
        assert result == "update/{run_id}"

    def test_task_not_in_multitask(self):
        """'task' inside 'multitask' should not be replaced."""
        result = normalize_branch_convention("multitask/run-id")
        assert result == "multitask/{run_id}"


class TestEdgeCases:
    """Edge cases and unusual inputs."""

    def test_empty_string(self):
        assert normalize_branch_convention("") == ""

    def test_whitespace_only(self):
        assert normalize_branch_convention("   ") == ""

    def test_leading_trailing_whitespace(self):
        assert normalize_branch_convention("  levelup/run-id  ") == "levelup/{run_id}"

    def test_no_aliases_found(self):
        """Input with no recognizable aliases returns unchanged."""
        assert normalize_branch_convention("mybranch/something") == "mybranch/something"

    def test_single_segment_no_slash(self):
        assert normalize_branch_convention("task-title") == "{task_title}"

    def test_static_prefix(self):
        """Static prefix before a slash is preserved."""
        result = normalize_branch_convention("my-prefix/task-title")
        assert result == "my-prefix/{task_title}"

    def test_multiple_slashes(self):
        result = normalize_branch_convention("org/repo/task-title")
        assert result == "org/repo/{task_title}"

    def test_case_insensitive(self):
        """Aliases match case-insensitively."""
        result = normalize_branch_convention("feature/Task-Title")
        assert result == "feature/{task_title}"

    def test_case_insensitive_run_id(self):
        result = normalize_branch_convention("levelup/Run-ID")
        assert result == "levelup/{run_id}"


class TestBackwardCompatibility:
    """All three presets and custom {placeholder} patterns remain unchanged."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "levelup/{run_id}",
            "feature/{task_title}",
            "ai/{run_id}",
            "custom/{date}-{run_id}",
            "dev/{run_id}/{task_title}/{date}",
            "my-static-branch",
        ],
    )
    def test_preset_and_custom_patterns_unchanged(self, pattern: str):
        result = normalize_branch_convention(pattern)
        # Patterns with placeholders pass through; static patterns stay static.
        assert result == pattern
