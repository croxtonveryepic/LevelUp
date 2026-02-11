"""Shared test fixtures."""

import os

# Use Qt's offscreen platform plugin so GUI tests never create visible windows.
# This must be set before any PyQt6 import.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
