"""Unit tests for src/levelup/detection/ (languages, frameworks, test_runners, detector)."""

from __future__ import annotations

from pathlib import Path

import pytest

from levelup.detection.languages import detect_language
from levelup.detection.frameworks import detect_framework
from levelup.detection.test_runners import TestRunnerInfo, detect_test_runner
from levelup.detection.detector import ProjectDetector, ProjectInfo


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """Test detect_language() with various indicator files (uses tmp_path)."""

    def test_python_via_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text("[project]\nname='foo'\n")
        assert detect_language(tmp_path) == "python"

    def test_python_via_setup_py(self, tmp_path: Path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")
        assert detect_language(tmp_path) == "python"

    def test_python_via_requirements_txt(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("requests\n")
        assert detect_language(tmp_path) == "python"

    def test_python_via_pipfile(self, tmp_path: Path):
        (tmp_path / "Pipfile").write_text("[packages]\n")
        assert detect_language(tmp_path) == "python"

    def test_javascript_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"name":"app"}\n')
        assert detect_language(tmp_path) == "javascript"

    def test_typescript_via_tsconfig(self, tmp_path: Path):
        (tmp_path / "tsconfig.json").write_text("{}\n")
        assert detect_language(tmp_path) == "typescript"

    def test_rust_via_cargo(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        assert detect_language(tmp_path) == "rust"

    def test_go_via_go_mod(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/m\n")
        assert detect_language(tmp_path) == "go"

    def test_java_via_pom(self, tmp_path: Path):
        (tmp_path / "pom.xml").write_text("<project></project>\n")
        assert detect_language(tmp_path) == "java"

    def test_java_via_build_gradle(self, tmp_path: Path):
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'\n")
        assert detect_language(tmp_path) == "java"

    def test_kotlin_via_build_gradle_kts(self, tmp_path: Path):
        (tmp_path / "build.gradle.kts").write_text("plugins { kotlin(\"jvm\") }\n")
        assert detect_language(tmp_path) == "kotlin"

    def test_ruby_via_gemfile(self, tmp_path: Path):
        (tmp_path / "Gemfile").write_text("source 'https://rubygems.org'\n")
        assert detect_language(tmp_path) == "ruby"

    def test_elixir_via_mix(self, tmp_path: Path):
        (tmp_path / "mix.exs").write_text("defmodule MyApp do\nend\n")
        assert detect_language(tmp_path) == "elixir"

    def test_php_via_composer(self, tmp_path: Path):
        (tmp_path / "composer.json").write_text("{}\n")
        assert detect_language(tmp_path) == "php"

    def test_swift_via_package_swift(self, tmp_path: Path):
        (tmp_path / "Package.swift").write_text("// swift-tools-version:5.3\n")
        assert detect_language(tmp_path) == "swift"

    def test_csharp_via_csproj_glob(self, tmp_path: Path):
        (tmp_path / "MyApp.csproj").write_text("<Project></Project>\n")
        assert detect_language(tmp_path) == "csharp"

    def test_no_indicators_returns_none(self, tmp_path: Path):
        """Empty project directory with no indicators returns None."""
        assert detect_language(tmp_path) is None

    def test_fallback_to_extension_count(self, tmp_path: Path):
        """When no indicator files exist, falls back to counting source files."""
        # No indicator files, but create .go source files
        (tmp_path / "main.go").write_text("package main\n")
        (tmp_path / "util.go").write_text("package main\n")
        assert detect_language(tmp_path) == "go"

    def test_extension_count_picks_majority(self, tmp_path: Path):
        """The language with the most source files should win."""
        for i in range(3):
            (tmp_path / f"file{i}.py").write_text(f"# py {i}\n")
        (tmp_path / "one.js").write_text("// js\n")
        assert detect_language(tmp_path) == "python"

    def test_skips_known_dirs(self, tmp_path: Path):
        """Files in node_modules etc. should be ignored in extension counting."""
        nm = tmp_path / "node_modules" / "lib"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("// ignored\n")
        (nm / "util.js").write_text("// ignored\n")
        (nm / "extra.js").write_text("// ignored\n")
        (tmp_path / "app.py").write_text("# counted\n")
        assert detect_language(tmp_path) == "python"

    def test_indicator_takes_priority_over_extensions(self, tmp_path: Path):
        """Indicator file detection should take priority over extension counting."""
        (tmp_path / "pyproject.toml").write_text("[project]\n")
        for i in range(10):
            (tmp_path / f"file{i}.js").write_text("// js\n")
        assert detect_language(tmp_path) == "python"


# ---------------------------------------------------------------------------
# detect_framework
# ---------------------------------------------------------------------------


class TestDetectFramework:
    """Test detect_framework() for various languages."""

    def test_none_language_returns_none(self, tmp_path: Path):
        assert detect_framework(tmp_path, None) is None

    def test_unknown_language_returns_none(self, tmp_path: Path):
        assert detect_framework(tmp_path, "brainfuck") is None

    # --- Python ---

    def test_python_django_via_manage_py(self, tmp_path: Path):
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python\n")
        assert detect_framework(tmp_path, "python") == "django"

    def test_python_fastapi_via_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi>=0.100"]\n'
        )
        assert detect_framework(tmp_path, "python") == "fastapi"

    def test_python_flask_via_pyproject(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["flask>=2.0"]\n'
        )
        assert detect_framework(tmp_path, "python") == "flask"

    def test_python_django_via_requirements(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("Django>=4.0\n")
        assert detect_framework(tmp_path, "python") == "django"

    def test_python_fastapi_via_requirements(self, tmp_path: Path):
        (tmp_path / "requirements.txt").write_text("fastapi\nuvicorn\n")
        assert detect_framework(tmp_path, "python") == "fastapi"

    def test_python_no_framework(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "cli-tool"\n')
        assert detect_framework(tmp_path, "python") is None

    # --- JavaScript / TypeScript ---

    def test_js_nextjs_via_config(self, tmp_path: Path):
        (tmp_path / "next.config.js").write_text("module.exports = {}\n")
        assert detect_framework(tmp_path, "javascript") == "nextjs"

    def test_ts_nextjs_via_config(self, tmp_path: Path):
        (tmp_path / "next.config.ts").write_text("export default {}\n")
        assert detect_framework(tmp_path, "typescript") == "nextjs"

    def test_js_angular_via_config(self, tmp_path: Path):
        (tmp_path / "angular.json").write_text("{}\n")
        assert detect_framework(tmp_path, "javascript") == "angular"

    def test_js_express_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"dependencies":{"express":"^4.0"}}\n')
        assert detect_framework(tmp_path, "javascript") == "express"

    def test_js_react_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"dependencies":{"react":"^18.0"}}\n')
        assert detect_framework(tmp_path, "javascript") == "react"

    def test_ts_react_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text(
            '{"dependencies":{"react":"^18.0","@types/react":"^18.0"}}\n'
        )
        assert detect_framework(tmp_path, "typescript") == "react"

    def test_js_vue_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"dependencies":{"vue":"^3.0"}}\n')
        assert detect_framework(tmp_path, "javascript") == "vue"

    def test_js_no_framework(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"name":"plain"}\n')
        assert detect_framework(tmp_path, "javascript") is None


# ---------------------------------------------------------------------------
# detect_test_runner
# ---------------------------------------------------------------------------


class TestDetectTestRunner:
    """Test detect_test_runner() for various languages."""

    def test_none_language_returns_none(self, tmp_path: Path):
        assert detect_test_runner(tmp_path, None) is None

    # --- Python ---

    def test_python_pytest_via_pytest_ini(self, tmp_path: Path):
        (tmp_path / "pytest.ini").write_text("[pytest]\n")
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"
        assert result.command == "pytest"

    def test_python_pytest_via_conftest(self, tmp_path: Path):
        (tmp_path / "conftest.py").write_text("# conftest\n")
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"

    def test_python_pytest_via_pyproject_content(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        )
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"

    def test_python_pytest_via_tox_ini(self, tmp_path: Path):
        (tmp_path / "tox.ini").write_text("[tox]\n")
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"

    def test_python_pytest_via_tests_conftest(self, tmp_path: Path):
        tests = tmp_path / "tests"
        tests.mkdir()
        (tests / "conftest.py").write_text("# test conftest\n")
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"

    def test_python_default_fallback(self, tmp_path: Path):
        """Python with no test runner indicators still defaults to pytest."""
        result = detect_test_runner(tmp_path, "python")
        assert result is not None
        assert result.name == "pytest"
        assert result.command == "pytest"

    # --- JavaScript ---

    def test_js_jest_via_config_file(self, tmp_path: Path):
        (tmp_path / "jest.config.js").write_text("module.exports = {}\n")
        result = detect_test_runner(tmp_path, "javascript")
        assert result is not None
        assert result.name == "jest"
        assert result.command == "npx jest"

    def test_js_jest_via_package_json_content(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"devDependencies":{"jest":"^29.0"}}\n')
        result = detect_test_runner(tmp_path, "javascript")
        assert result is not None
        assert result.name == "jest"

    def test_ts_jest_via_config_ts(self, tmp_path: Path):
        (tmp_path / "jest.config.ts").write_text("export default {}\n")
        result = detect_test_runner(tmp_path, "typescript")
        assert result is not None
        assert result.name == "jest"

    def test_js_vitest_via_config(self, tmp_path: Path):
        (tmp_path / "vitest.config.js").write_text("export default {}\n")
        result = detect_test_runner(tmp_path, "javascript")
        assert result is not None
        assert result.name == "vitest"
        assert result.command == "npx vitest run"

    def test_ts_vitest_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"devDependencies":{"vitest":"^0.34"}}\n')
        result = detect_test_runner(tmp_path, "typescript")
        assert result is not None
        assert result.name == "vitest"

    def test_js_mocha_via_package_json(self, tmp_path: Path):
        (tmp_path / "package.json").write_text('{"devDependencies":{"mocha":"^10.0"}}\n')
        result = detect_test_runner(tmp_path, "javascript")
        assert result is not None
        assert result.name == "mocha"
        assert result.command == "npx mocha"

    def test_js_default_fallback(self, tmp_path: Path):
        """JS with no indicators defaults to jest."""
        result = detect_test_runner(tmp_path, "javascript")
        assert result is not None
        assert result.name == "jest"
        assert result.command == "npx jest"

    # --- Go ---

    def test_go_test_via_test_files(self, tmp_path: Path):
        (tmp_path / "main_test.go").write_text("package main\n")
        result = detect_test_runner(tmp_path, "go")
        assert result is not None
        assert result.name == "go_test"
        assert result.command == "go test ./..."

    def test_go_default_fallback(self, tmp_path: Path):
        result = detect_test_runner(tmp_path, "go")
        assert result is not None
        assert result.name == "go_test"

    # --- Rust ---

    def test_rust_cargo_test(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text("[package]\n")
        result = detect_test_runner(tmp_path, "rust")
        assert result is not None
        assert result.name == "cargo_test"
        assert result.command == "cargo test"

    # --- Ruby ---

    def test_ruby_rspec_via_gemfile(self, tmp_path: Path):
        (tmp_path / "Gemfile").write_text("gem 'rspec'\n")
        result = detect_test_runner(tmp_path, "ruby")
        assert result is not None
        assert result.name == "rspec"
        assert result.command == "bundle exec rspec"

    def test_ruby_rspec_via_spec_dir(self, tmp_path: Path):
        (tmp_path / "spec").mkdir()
        result = detect_test_runner(tmp_path, "ruby")
        assert result is not None
        assert result.name == "rspec"

    # --- Java ---

    def test_java_maven_via_pom(self, tmp_path: Path):
        (tmp_path / "pom.xml").write_text("<project></project>\n")
        result = detect_test_runner(tmp_path, "java")
        assert result is not None
        assert result.name == "maven"
        assert result.command == "mvn test"

    def test_java_gradle_via_build_gradle(self, tmp_path: Path):
        (tmp_path / "build.gradle").write_text("apply plugin: 'java'\n")
        result = detect_test_runner(tmp_path, "java")
        assert result is not None
        assert result.name == "gradle"
        assert result.command == "gradle test"

    # --- PHP ---

    def test_php_phpunit_via_xml(self, tmp_path: Path):
        (tmp_path / "phpunit.xml").write_text("<phpunit></phpunit>\n")
        result = detect_test_runner(tmp_path, "php")
        assert result is not None
        assert result.name == "phpunit"
        assert result.command == "vendor/bin/phpunit"

    # --- Unknown language ---

    def test_unknown_language_no_default(self, tmp_path: Path):
        result = detect_test_runner(tmp_path, "brainfuck")
        assert result is None

    # --- TestRunnerInfo ---

    def test_runner_info_dataclass(self):
        info = TestRunnerInfo(name="pytest", command="pytest")
        assert info.name == "pytest"
        assert info.command == "pytest"


# ---------------------------------------------------------------------------
# ProjectDetector.detect() integration
# ---------------------------------------------------------------------------


class TestProjectDetector:
    """Test ProjectDetector.detect() orchestration with real filesystem (tmp_path)."""

    def test_detect_python_fastapi_pytest(self, tmp_path: Path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi"]\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
        )
        (tmp_path / "conftest.py").write_text("# conftest\n")

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert isinstance(info, ProjectInfo)
        assert info.language == "python"
        assert info.framework == "fastapi"
        assert info.test_runner == "pytest"
        assert info.test_command == "pytest"

    def test_detect_javascript_react_jest(self, tmp_path: Path):
        (tmp_path / "package.json").write_text(
            '{"dependencies":{"react":"^18.0"},"devDependencies":{"jest":"^29.0"}}\n'
        )
        (tmp_path / "jest.config.js").write_text("module.exports = {}\n")

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language == "javascript"
        assert info.framework == "react"
        assert info.test_runner == "jest"
        assert info.test_command == "npx jest"

    def test_detect_typescript_nextjs_vitest(self, tmp_path: Path):
        (tmp_path / "tsconfig.json").write_text("{}\n")
        (tmp_path / "next.config.ts").write_text("export default {}\n")
        (tmp_path / "vitest.config.ts").write_text("export default {}\n")

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language == "typescript"
        assert info.framework == "nextjs"
        assert info.test_runner == "vitest"
        assert info.test_command == "npx vitest run"

    def test_detect_go_project(self, tmp_path: Path):
        (tmp_path / "go.mod").write_text("module example.com/m\n\ngo 1.21\n")
        (tmp_path / "main_test.go").write_text("package main\n")

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language == "go"
        assert info.framework is None
        assert info.test_runner == "go_test"
        assert info.test_command == "go test ./..."

    def test_detect_rust_axum_project(self, tmp_path: Path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "myapp"\n\n[dependencies]\naxum = "0.7"\n'
        )

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language == "rust"
        assert info.framework == "axum"
        assert info.test_runner == "cargo_test"
        assert info.test_command == "cargo test"

    def test_detect_empty_project(self, tmp_path: Path):
        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language is None
        assert info.framework is None
        assert info.test_runner is None
        assert info.test_command is None

    def test_detect_python_django_project(self, tmp_path: Path):
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python\n")
        (tmp_path / "requirements.txt").write_text("Django>=4.0\n")
        (tmp_path / "pytest.ini").write_text("[pytest]\n")

        detector = ProjectDetector()
        info = detector.detect(tmp_path)

        assert info.language == "python"
        assert info.framework == "django"
        assert info.test_runner == "pytest"

    def test_detect_returns_project_info(self, tmp_path: Path):
        detector = ProjectDetector()
        info = detector.detect(tmp_path)
        assert isinstance(info, ProjectInfo)
        assert hasattr(info, "language")
        assert hasattr(info, "framework")
        assert hasattr(info, "test_runner")
        assert hasattr(info, "test_command")
