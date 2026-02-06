"""Language detection based on indicator files and file extensions."""

from __future__ import annotations

from pathlib import Path

# Indicator files -> language
INDICATOR_FILES: dict[str, str] = {
    "pyproject.toml": "python",
    "setup.py": "python",
    "setup.cfg": "python",
    "Pipfile": "python",
    "requirements.txt": "python",
    "package.json": "javascript",
    "tsconfig.json": "typescript",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "Gemfile": "ruby",
    "mix.exs": "elixir",
    "composer.json": "php",
    "Project.swift": "swift",
    "Package.swift": "swift",
    "*.csproj": "csharp",
    "*.sln": "csharp",
}

# Extension -> language (for counting source files)
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".ex": "elixir",
    ".exs": "elixir",
    ".php": "php",
    ".swift": "swift",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".c": "c",
}

SKIP_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    "target",
    "build",
    "dist",
    ".tox",
    "env",
}


def detect_language(project_path: Path) -> str | None:
    """Detect the primary language of a project."""
    # First pass: check indicator files
    for filename, language in INDICATOR_FILES.items():
        if "*" in filename:
            if list(project_path.glob(filename)):
                return language
        elif (project_path / filename).exists():
            return language

    # Second pass: count source files by extension
    counts: dict[str, int] = {}
    try:
        for p in project_path.rglob("*"):
            if any(skip in p.parts for skip in SKIP_DIRS):
                continue
            if p.is_file() and p.suffix in EXTENSION_MAP:
                lang = EXTENSION_MAP[p.suffix]
                counts[lang] = counts.get(lang, 0) + 1
    except PermissionError:
        pass

    if counts:
        return max(counts, key=lambda k: counts[k])

    return None
