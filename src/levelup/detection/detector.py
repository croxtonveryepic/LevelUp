"""ProjectDetector orchestrator - combines language, framework, and test runner detection."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from levelup.detection.frameworks import detect_framework
from levelup.detection.languages import detect_language
from levelup.detection.test_runners import TestRunnerInfo, detect_test_runner


@dataclass
class ProjectInfo:
    """Aggregated project detection results."""

    language: str | None = None
    framework: str | None = None
    test_runner: str | None = None
    test_command: str | None = None


class ProjectDetector:
    """Orchestrates project detection by running language, framework, and test runner detection."""

    def detect(self, project_path: Path) -> ProjectInfo:
        """Detect project language, framework, and test runner."""
        project_path = project_path.resolve()

        language = detect_language(project_path)
        framework = detect_framework(project_path, language)
        runner_info: TestRunnerInfo | None = detect_test_runner(project_path, language)

        return ProjectInfo(
            language=language,
            framework=framework,
            test_runner=runner_info.name if runner_info else None,
            test_command=runner_info.command if runner_info else None,
        )
