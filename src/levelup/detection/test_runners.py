"""Test runner detection based on config files and language conventions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestRunnerInfo:
    name: str
    command: str


# (language, config_file_or_check, runner_name, command)
TestRunnerRule = tuple[str, str, str, str]

TEST_RUNNER_RULES: list[TestRunnerRule] = [
    # Python
    ("python", "pytest.ini", "pytest", "pytest"),
    ("python", "pyproject.toml:pytest", "pytest", "pytest"),
    ("python", "setup.cfg:pytest", "pytest", "pytest"),
    ("python", "tox.ini", "pytest", "pytest"),
    ("python", "conftest.py", "pytest", "pytest"),
    ("python", "tests/conftest.py", "pytest", "pytest"),
    # JavaScript / TypeScript
    ("javascript", "jest.config.js", "jest", "npx jest"),
    ("javascript", "jest.config.ts", "jest", "npx jest"),
    ("typescript", "jest.config.js", "jest", "npx jest"),
    ("typescript", "jest.config.ts", "jest", "npx jest"),
    ("javascript", "package.json:jest", "jest", "npx jest"),
    ("typescript", "package.json:jest", "jest", "npx jest"),
    ("javascript", "vitest.config.js", "vitest", "npx vitest run"),
    ("javascript", "vitest.config.ts", "vitest", "npx vitest run"),
    ("typescript", "vitest.config.ts", "vitest", "npx vitest run"),
    ("javascript", "package.json:vitest", "vitest", "npx vitest run"),
    ("typescript", "package.json:vitest", "vitest", "npx vitest run"),
    ("javascript", "package.json:mocha", "mocha", "npx mocha"),
    # Go
    ("go", "*_test.go", "go_test", "go test ./..."),
    # Rust
    ("rust", "Cargo.toml", "cargo_test", "cargo test"),
    # Ruby
    ("ruby", "Gemfile:rspec", "rspec", "bundle exec rspec"),
    ("ruby", "spec/", "rspec", "bundle exec rspec"),
    # Java / Kotlin
    ("java", "pom.xml", "maven", "mvn test"),
    ("java", "build.gradle", "gradle", "gradle test"),
    ("kotlin", "build.gradle.kts", "gradle", "gradle test"),
    # PHP
    ("php", "phpunit.xml", "phpunit", "vendor/bin/phpunit"),
    ("php", "phpunit.xml.dist", "phpunit", "vendor/bin/phpunit"),
]

# Default test commands per language if no runner detected
DEFAULT_COMMANDS: dict[str, tuple[str, str]] = {
    "python": ("pytest", "pytest"),
    "javascript": ("jest", "npx jest"),
    "typescript": ("jest", "npx jest"),
    "go": ("go_test", "go test ./..."),
    "rust": ("cargo_test", "cargo test"),
    "java": ("maven", "mvn test"),
    "ruby": ("rspec", "bundle exec rspec"),
}


def detect_test_runner(project_path: Path, language: str | None) -> TestRunnerInfo | None:
    """Detect the test runner used in a project given its language."""
    if not language:
        return None

    for rule_lang, check, runner_name, command in TEST_RUNNER_RULES:
        if rule_lang != language:
            continue

        if ":" in check:
            # Check file contains content
            filename, search_term = check.split(":", 1)
            filepath = project_path / filename
            if filepath.is_file():
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    if search_term in content.lower():
                        return TestRunnerInfo(name=runner_name, command=command)
                except Exception:
                    continue
        elif "*" in check:
            # Glob check
            if list(project_path.rglob(check)):
                return TestRunnerInfo(name=runner_name, command=command)
        elif check.endswith("/"):
            # Directory check
            if (project_path / check.rstrip("/")).is_dir():
                return TestRunnerInfo(name=runner_name, command=command)
        else:
            # File existence check
            if (project_path / check).exists():
                return TestRunnerInfo(name=runner_name, command=command)

    # Fall back to default for language
    if language in DEFAULT_COMMANDS:
        name, cmd = DEFAULT_COMMANDS[language]
        return TestRunnerInfo(name=name, command=cmd)

    return None
