"""Unit tests for levelup tools (src/levelup/tools/)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from levelup.tools.base import BaseTool, ToolRegistry
from levelup.tools.file_read import FileReadTool
from levelup.tools.file_write import FileWriteTool
from levelup.tools.file_search import FileSearchTool
from levelup.tools.shell import ShellTool
from levelup.tools.test_runner import TestRunnerTool, _parse_test_output


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _DummyTool(BaseTool):
    """Minimal concrete tool for testing the registry."""

    name = "dummy"
    description = "A dummy tool"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def execute(self, **kwargs: Any) -> str:
        return "ok"


class _OtherTool(BaseTool):
    name = "other"
    description = "Another tool"

    def get_input_schema(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"x": {"type": "string"}}}

    def execute(self, **kwargs: Any) -> str:
        return kwargs.get("x", "")


# ===========================================================================
# ToolRegistry
# ===========================================================================


class TestToolRegistry:
    def test_register_and_get(self):
        reg = ToolRegistry()
        tool = _DummyTool()
        reg.register(tool)
        assert reg.get("dummy") is tool

    def test_get_raises_key_error_for_missing_tool(self):
        reg = ToolRegistry()
        with pytest.raises(KeyError, match="Tool not found: nope"):
            reg.get("nope")

    def test_get_tools_returns_all_when_names_is_none(self):
        reg = ToolRegistry()
        t1 = _DummyTool()
        t2 = _OtherTool()
        reg.register(t1)
        reg.register(t2)
        tools = reg.get_tools()
        assert len(tools) == 2
        assert t1 in tools
        assert t2 in tools

    def test_get_tools_returns_selected_by_name(self):
        reg = ToolRegistry()
        t1 = _DummyTool()
        t2 = _OtherTool()
        reg.register(t1)
        reg.register(t2)
        tools = reg.get_tools(["other"])
        assert tools == [t2]

    def test_get_tools_raises_key_error_for_missing_name(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        with pytest.raises(KeyError):
            reg.get_tools(["nonexistent"])

    def test_get_anthropic_schemas(self):
        reg = ToolRegistry()
        t1 = _DummyTool()
        reg.register(t1)
        schemas = reg.get_anthropic_schemas()
        assert len(schemas) == 1
        schema = schemas[0]
        assert schema["name"] == "dummy"
        assert schema["description"] == "A dummy tool"
        assert "input_schema" in schema

    def test_get_anthropic_schemas_with_filter(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        reg.register(_OtherTool())
        schemas = reg.get_anthropic_schemas(["other"])
        assert len(schemas) == 1
        assert schemas[0]["name"] == "other"

    def test_tool_names_property(self):
        reg = ToolRegistry()
        reg.register(_DummyTool())
        reg.register(_OtherTool())
        assert set(reg.tool_names) == {"dummy", "other"}


# ===========================================================================
# FileReadTool
# ===========================================================================


class TestFileReadTool:
    def test_read_existing_file(self, tmp_path: Path):
        (tmp_path / "hello.txt").write_text("world", encoding="utf-8")
        tool = FileReadTool(project_root=tmp_path)
        result = tool.execute(path="hello.txt")
        assert result == "world"

    def test_read_file_in_subdirectory(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "data.txt").write_text("content", encoding="utf-8")
        tool = FileReadTool(project_root=tmp_path)
        result = tool.execute(path="sub/data.txt")
        assert result == "content"

    def test_file_not_found(self, tmp_path: Path):
        tool = FileReadTool(project_root=tmp_path)
        result = tool.execute(path="missing.txt")
        assert result.startswith("Error: file not found")

    def test_path_escape_prevention(self, tmp_path: Path):
        tool = FileReadTool(project_root=tmp_path)
        result = tool.execute(path="../../etc/passwd")
        assert "Error" in result

    def test_path_escape_with_absolute_style(self, tmp_path: Path):
        # Even sneaky relative paths that resolve outside root should be blocked
        tool = FileReadTool(project_root=tmp_path)
        result = tool.execute(path="../../../tmp/secret")
        assert "Error" in result

    def test_get_input_schema(self, tmp_path: Path):
        tool = FileReadTool(project_root=tmp_path)
        schema = tool.get_input_schema()
        assert schema["type"] == "object"
        assert "path" in schema["properties"]
        assert "path" in schema["required"]

    def test_to_anthropic_schema(self, tmp_path: Path):
        tool = FileReadTool(project_root=tmp_path)
        schema = tool.to_anthropic_schema()
        assert schema["name"] == "file_read"
        assert "description" in schema
        assert "input_schema" in schema


# ===========================================================================
# FileWriteTool
# ===========================================================================


class TestFileWriteTool:
    def test_write_new_file(self, tmp_path: Path):
        tool = FileWriteTool(project_root=tmp_path)
        result = tool.execute(path="output.txt", content="hello")
        assert "Successfully wrote" in result
        assert (tmp_path / "output.txt").read_text(encoding="utf-8") == "hello"

    def test_write_creates_parent_directories(self, tmp_path: Path):
        tool = FileWriteTool(project_root=tmp_path)
        result = tool.execute(path="a/b/c/deep.txt", content="deep content")
        assert "Successfully wrote" in result
        assert (tmp_path / "a" / "b" / "c" / "deep.txt").exists()
        assert (tmp_path / "a" / "b" / "c" / "deep.txt").read_text(encoding="utf-8") == "deep content"

    def test_overwrite_existing_file(self, tmp_path: Path):
        (tmp_path / "existing.txt").write_text("old", encoding="utf-8")
        tool = FileWriteTool(project_root=tmp_path)
        result = tool.execute(path="existing.txt", content="new")
        assert "Successfully wrote" in result
        assert (tmp_path / "existing.txt").read_text(encoding="utf-8") == "new"

    def test_path_escape_prevention(self, tmp_path: Path):
        tool = FileWriteTool(project_root=tmp_path)
        result = tool.execute(path="../../evil.txt", content="bad stuff")
        assert result == "Error: path escapes project root"
        # Ensure the file was NOT created outside the project root
        assert not (tmp_path.parent.parent / "evil.txt").exists()

    def test_reports_byte_count(self, tmp_path: Path):
        tool = FileWriteTool(project_root=tmp_path)
        content = "12345"
        result = tool.execute(path="count.txt", content=content)
        assert f"{len(content)} bytes" in result

    def test_get_input_schema(self, tmp_path: Path):
        tool = FileWriteTool(project_root=tmp_path)
        schema = tool.get_input_schema()
        assert "path" in schema["properties"]
        assert "content" in schema["properties"]
        assert set(schema["required"]) == {"path", "content"}


# ===========================================================================
# FileSearchTool
# ===========================================================================


class TestFileSearchTool:
    def _setup_project(self, tmp_path: Path) -> None:
        """Create a small project tree for search tests."""
        (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (tmp_path / "util.py").write_text("def helper():\n    return 42\n", encoding="utf-8")
        sub = tmp_path / "pkg"
        sub.mkdir()
        (sub / "module.py").write_text("import os\nclass Foo:\n    pass\n", encoding="utf-8")
        (sub / "data.json").write_text('{"key": "value"}\n', encoding="utf-8")

    def test_glob_matching_all_py(self, tmp_path: Path):
        self._setup_project(tmp_path)
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.py")
        assert "main.py" in result
        assert "util.py" in result
        assert "pkg/module.py" in result
        # json should not match
        assert "data.json" not in result

    def test_glob_matching_specific_dir(self, tmp_path: Path):
        self._setup_project(tmp_path)
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="pkg/*.py")
        assert "pkg/module.py" in result
        assert "main.py" not in result

    def test_content_search(self, tmp_path: Path):
        self._setup_project(tmp_path)
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.py", content_pattern="helper")
        assert "util.py" in result
        assert "L1:" in result  # should show line reference
        # Files without the pattern should not appear
        assert "main.py" not in result

    def test_content_search_no_match(self, tmp_path: Path):
        self._setup_project(tmp_path)
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.py", content_pattern="zzz_no_match_zzz")
        assert result == "No files matched."

    def test_no_files_match_glob(self, tmp_path: Path):
        self._setup_project(tmp_path)
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.rs")
        assert result == "No files matched."

    def test_max_results_limits_output(self, tmp_path: Path):
        # Create many files
        for i in range(10):
            (tmp_path / f"f{i}.txt").write_text(f"file {i}", encoding="utf-8")
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="*.txt", max_results=3)
        lines = [line for line in result.strip().split("\n") if line]
        assert len(lines) == 3

    def test_skips_hidden_directories(self, tmp_path: Path):
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.py").write_text("secret", encoding="utf-8")
        (tmp_path / "visible.py").write_text("visible", encoding="utf-8")
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.py")
        assert "visible.py" in result
        assert "secret.py" not in result

    def test_skips_node_modules(self, tmp_path: Path):
        nm = tmp_path / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = {}", encoding="utf-8")
        (tmp_path / "app.js").write_text("console.log('hi')", encoding="utf-8")
        tool = FileSearchTool(project_root=tmp_path)
        result = tool.execute(pattern="**/*.js")
        assert "app.js" in result
        assert "node_modules" not in result


# ===========================================================================
# ShellTool
# ===========================================================================


class TestShellTool:
    @patch("levelup.tools.shell.subprocess.run")
    def test_execute_successful_command(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="echo hello",
            returncode=0,
            stdout="hello\n",
            stderr="",
        )
        tool = ShellTool(project_root=tmp_path)
        result = tool.execute(command="echo hello")
        assert "hello" in result
        assert "Exit code: 0" in result
        mock_run.assert_called_once_with(
            "echo hello",
            shell=True,
            cwd=str(tmp_path.resolve()),
            capture_output=True,
            text=True,
            timeout=60,
        )

    @patch("levelup.tools.shell.subprocess.run")
    def test_execute_with_stderr(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="badcmd",
            returncode=1,
            stdout="",
            stderr="command not found\n",
        )
        tool = ShellTool(project_root=tmp_path)
        result = tool.execute(command="badcmd")
        assert "STDERR:" in result
        assert "command not found" in result
        assert "Exit code: 1" in result

    @patch("levelup.tools.shell.subprocess.run")
    def test_timeout(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=5)
        tool = ShellTool(project_root=tmp_path, timeout=5)
        result = tool.execute(command="sleep 100")
        assert "timed out" in result
        assert "5s" in result

    @patch("levelup.tools.shell.subprocess.run")
    def test_custom_timeout_in_kwargs(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="long_task", timeout=10)
        tool = ShellTool(project_root=tmp_path)
        result = tool.execute(command="long_task", timeout=10)
        assert "timed out" in result
        mock_run.assert_called_once_with(
            "long_task",
            shell=True,
            cwd=str(tmp_path.resolve()),
            capture_output=True,
            text=True,
            timeout=10,
        )

    @patch("levelup.tools.shell.subprocess.run")
    def test_output_truncation(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="big",
            returncode=0,
            stdout="x" * 20000,
            stderr="",
        )
        tool = ShellTool(project_root=tmp_path)
        result = tool.execute(command="big")
        assert len(result) <= 10100  # 10000 + some small tail
        assert "truncated" in result

    @patch("levelup.tools.shell.subprocess.run")
    def test_generic_exception(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = OSError("permission denied")
        tool = ShellTool(project_root=tmp_path)
        result = tool.execute(command="forbidden")
        assert "Error executing command" in result
        assert "permission denied" in result

    def test_get_input_schema(self, tmp_path: Path):
        tool = ShellTool(project_root=tmp_path)
        schema = tool.get_input_schema()
        assert "command" in schema["properties"]
        assert "command" in schema["required"]


# ===========================================================================
# TestRunnerTool
# ===========================================================================


class TestTestRunnerTool:
    @patch("levelup.tools.test_runner.subprocess.run")
    def test_execute_with_explicit_command(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="pytest",
            returncode=0,
            stdout="===== 3 passed in 0.5s =====\n",
            stderr="",
        )
        tool = TestRunnerTool(project_root=tmp_path)
        result = tool.execute(command="pytest")
        assert "PASSED" in result
        assert "3 passed" in result

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_execute_with_configured_command(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="pytest --verbose",
            returncode=0,
            stdout="===== 5 passed in 1.0s =====\n",
            stderr="",
        )
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest --verbose")
        result = tool.execute()
        assert "PASSED" in result
        mock_run.assert_called_once()

    def test_execute_no_command_configured(self, tmp_path: Path):
        tool = TestRunnerTool(project_root=tmp_path)
        result = tool.execute()
        assert "Error" in result
        assert "no test command" in result.lower()

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_execute_timeout(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest")
        result = tool.execute()
        assert "timed out" in result

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_run_and_parse_returns_test_result(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="pytest",
            returncode=0,
            stdout="===== 5 passed in 0.3s =====\n",
            stderr="",
        )
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest")
        tr = tool.run_and_parse()
        assert tr.passed is True
        assert tr.total == 5
        assert tr.failures == 0
        assert tr.command == "pytest"

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_run_and_parse_with_failures(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.return_value = subprocess.CompletedProcess(
            args="pytest",
            returncode=1,
            stdout="===== 3 passed, 2 failed in 1.0s =====\n",
            stderr="",
        )
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest")
        tr = tool.run_and_parse()
        assert tr.passed is False
        assert tr.failures == 2
        assert tr.total == 3 + 2  # passed + failures

    def test_run_and_parse_no_command(self, tmp_path: Path):
        tool = TestRunnerTool(project_root=tmp_path)
        tr = tool.run_and_parse()
        assert tr.passed is False
        assert "No test command" in tr.output

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_run_and_parse_timeout(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=120)
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest")
        tr = tool.run_and_parse()
        assert tr.passed is False
        assert "Timed out" in tr.output

    @patch("levelup.tools.test_runner.subprocess.run")
    def test_run_and_parse_generic_exception(self, mock_run: MagicMock, tmp_path: Path):
        mock_run.side_effect = RuntimeError("boom")
        tool = TestRunnerTool(project_root=tmp_path, test_command="pytest")
        tr = tool.run_and_parse()
        assert tr.passed is False
        assert "boom" in tr.output


# ===========================================================================
# _parse_test_output() helper
# ===========================================================================


class TestParseTestOutput:
    def test_pytest_all_passed(self):
        output = "===== 10 passed in 2.5s ====="
        result = _parse_test_output(output, returncode=0, command="pytest")
        assert result.passed is True
        assert result.total == 10
        assert result.failures == 0
        assert result.errors == 0

    def test_pytest_with_failures(self):
        output = "===== 3 passed, 2 failed in 1.5s ====="
        result = _parse_test_output(output, returncode=1, command="pytest")
        assert result.passed is False
        assert result.failures == 2
        # total should account for passed + failed
        assert result.total == 3 + 2

    def test_pytest_with_errors(self):
        output = "===== 4 passed, 1 failed, 2 error in 3.0s ====="
        result = _parse_test_output(output, returncode=1, command="pytest")
        assert result.passed is False
        assert result.failures == 1
        assert result.errors == 2
        # total = passed (4) + failures (1) + errors (2)
        assert result.total == 4 + 1 + 2

    def test_jest_style_output(self):
        output = "Tests:  2 failed, 8 passed, 10 total\nTime:   3.5s"
        result = _parse_test_output(output, returncode=1, command="npx jest")
        assert result.passed is False
        assert result.total == 10
        assert result.failures == 2

    def test_jest_all_passed(self):
        output = "Tests:  5 passed, 5 total\nTime:   1.2s"
        result = _parse_test_output(output, returncode=0, command="npx jest")
        assert result.passed is True
        assert result.total == 5

    def test_returncode_zero_means_passed(self):
        output = "All good"  # no parseable pattern
        result = _parse_test_output(output, returncode=0, command="custom")
        assert result.passed is True

    def test_returncode_nonzero_means_failed(self):
        output = "Something went wrong"
        result = _parse_test_output(output, returncode=1, command="custom")
        assert result.passed is False

    def test_empty_output(self):
        result = _parse_test_output("", returncode=0, command="pytest")
        assert result.passed is True
        assert result.total == 0

    def test_output_and_command_stored(self):
        output = "===== 1 passed in 0.1s ====="
        result = _parse_test_output(output, returncode=0, command="pytest tests/")
        assert result.output == output
        assert result.command == "pytest tests/"
