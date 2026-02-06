"""Framework detection based on language-specific indicators."""

from __future__ import annotations

from pathlib import Path

# (language, indicator_file_or_pattern, check_type) -> framework
# check_type: "file" = check file exists, "content" = check file content
FrameworkRule = tuple[str, str, str, str]  # (language, file, check, framework)

FRAMEWORK_RULES: list[FrameworkRule] = [
    # Python
    ("python", "manage.py", "file", "django"),
    ("python", "pyproject.toml", "content:fastapi", "fastapi"),
    ("python", "pyproject.toml", "content:flask", "flask"),
    ("python", "pyproject.toml", "content:starlette", "starlette"),
    ("python", "requirements.txt", "content:django", "django"),
    ("python", "requirements.txt", "content:fastapi", "fastapi"),
    ("python", "requirements.txt", "content:flask", "flask"),
    # JavaScript / TypeScript
    ("javascript", "next.config.js", "file", "nextjs"),
    ("javascript", "next.config.mjs", "file", "nextjs"),
    ("javascript", "next.config.ts", "file", "nextjs"),
    ("typescript", "next.config.js", "file", "nextjs"),
    ("typescript", "next.config.mjs", "file", "nextjs"),
    ("typescript", "next.config.ts", "file", "nextjs"),
    ("javascript", "nuxt.config.js", "file", "nuxt"),
    ("javascript", "nuxt.config.ts", "file", "nuxt"),
    ("typescript", "nuxt.config.ts", "file", "nuxt"),
    ("javascript", "angular.json", "file", "angular"),
    ("typescript", "angular.json", "file", "angular"),
    ("javascript", "vite.config.js", "file", "vite"),
    ("javascript", "vite.config.ts", "file", "vite"),
    ("typescript", "vite.config.ts", "file", "vite"),
    ("javascript", "package.json", "content:express", "express"),
    ("javascript", "package.json", "content:react", "react"),
    ("typescript", "package.json", "content:react", "react"),
    ("javascript", "package.json", "content:vue", "vue"),
    ("typescript", "package.json", "content:vue", "vue"),
    # Ruby
    ("ruby", "Gemfile", "content:rails", "rails"),
    ("ruby", "config/routes.rb", "file", "rails"),
    ("ruby", "Gemfile", "content:sinatra", "sinatra"),
    # Go
    ("go", "go.mod", "content:gin-gonic", "gin"),
    ("go", "go.mod", "content:gorilla/mux", "gorilla"),
    ("go", "go.mod", "content:labstack/echo", "echo"),
    # Rust
    ("rust", "Cargo.toml", "content:actix-web", "actix"),
    ("rust", "Cargo.toml", "content:axum", "axum"),
    ("rust", "Cargo.toml", "content:rocket", "rocket"),
    # Java / Kotlin
    ("java", "pom.xml", "content:spring-boot", "spring"),
    ("java", "build.gradle", "content:spring-boot", "spring"),
    ("kotlin", "build.gradle.kts", "content:spring-boot", "spring"),
]


def detect_framework(project_path: Path, language: str | None) -> str | None:
    """Detect the framework used in a project given its language."""
    if not language:
        return None

    for rule_lang, indicator, check, framework in FRAMEWORK_RULES:
        if rule_lang != language:
            continue

        filepath = project_path / indicator
        if check == "file":
            if filepath.exists():
                return framework
        elif check.startswith("content:"):
            search_term = check.split(":", 1)[1]
            if filepath.is_file():
                try:
                    content = filepath.read_text(encoding="utf-8", errors="ignore")
                    if search_term in content.lower():
                        return framework
                except Exception:
                    continue

    return None
