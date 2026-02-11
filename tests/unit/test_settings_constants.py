"""Tests for adaptive pipeline constants in settings."""

from __future__ import annotations

from levelup.config.settings import EFFORT_THINKING_BUDGETS, MODEL_SHORT_NAMES


class TestModelShortNames:
    def test_contains_sonnet(self):
        assert "sonnet" in MODEL_SHORT_NAMES

    def test_contains_opus(self):
        assert "opus" in MODEL_SHORT_NAMES

    def test_sonnet_value_is_full_model_id(self):
        assert "claude-sonnet" in MODEL_SHORT_NAMES["sonnet"]

    def test_opus_value_is_full_model_id(self):
        assert "claude-opus" in MODEL_SHORT_NAMES["opus"]


class TestEffortThinkingBudgets:
    def test_contains_low(self):
        assert "low" in EFFORT_THINKING_BUDGETS

    def test_contains_medium(self):
        assert "medium" in EFFORT_THINKING_BUDGETS

    def test_contains_high(self):
        assert "high" in EFFORT_THINKING_BUDGETS

    def test_low_less_than_medium(self):
        assert EFFORT_THINKING_BUDGETS["low"] < EFFORT_THINKING_BUDGETS["medium"]

    def test_medium_less_than_high(self):
        assert EFFORT_THINKING_BUDGETS["medium"] < EFFORT_THINKING_BUDGETS["high"]

    def test_all_positive(self):
        for key, val in EFFORT_THINKING_BUDGETS.items():
            assert val > 0, f"{key} should be positive"
