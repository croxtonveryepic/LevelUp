"""Shared test fixtures."""

import os

import pytest

# Use Qt's offscreen platform plugin so GUI tests never create visible windows.
# This must be set before any PyQt6 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Auto-apply 'smoke' marker to any test not marked 'regression'."""
    smoke = pytest.mark.smoke
    for item in items:
        if not any(m.name == "regression" for m in item.iter_markers()):
            item.add_marker(smoke)
