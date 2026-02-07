"""Unit tests for SecurityAgent (src/levelup/agents/security.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from levelup.agents.backend import AgentResult, Backend
from levelup.agents.security import SecurityAgent, _parse_security_findings
from levelup.core.context import (
    PipelineContext,
    SecurityFinding,
    Severity,
    TaskInput,
    FileChange,
    TestResult,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def task_input() -> TaskInput:
    return TaskInput(
        title="Add user registration endpoint",
        description="Implement POST /register with password hashing"
    )


@pytest.fixture()
def basic_ctx(task_input: TaskInput, tmp_path: Path) -> PipelineContext:
    """A minimal pipeline context suitable for security agent tests."""
    return PipelineContext(
        task=task_input,
        project_path=tmp_path,
        language="python",
        framework="fastapi",
        test_runner="pytest",
        test_command="pytest tests/",
    )


@pytest.fixture()
def rich_ctx(basic_ctx: PipelineContext) -> PipelineContext:
    """Context with test files, code files, and test results populated."""
    basic_ctx.test_files = [
        FileChange(
            path="tests/test_register.py",
            content="def test_register(): pass",
            is_new=True
        )
    ]
    basic_ctx.code_files = [
        FileChange(
            path="routes/register.py",
            content="def register(password): db.query(f'INSERT INTO users VALUES ({password})')",
            is_new=True
        )
    ]
    basic_ctx.test_results = [
        TestResult(passed=True, total=1, failures=0, output="1 passed", command="pytest")
    ]
    return basic_ctx


@pytest.fixture()
def mock_backend() -> MagicMock:
    """A MagicMock standing in for Backend."""
    backend = MagicMock(spec=Backend)
    return backend


@pytest.fixture()
def project_path(tmp_path: Path) -> Path:
    return tmp_path


# ===========================================================================
# SecurityAgent
# ===========================================================================


class TestSecurityAgent:
    def test_get_system_prompt_contains_context(
        self, mock_backend: MagicMock, project_path: Path, rich_ctx: PipelineContext
    ):
        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(rich_ctx)
        assert isinstance(prompt, str)
        assert "project_context.md" in prompt
        assert "security expert" in prompt.lower()
        assert "tests/test_register.py" in prompt
        assert "routes/register.py" in prompt
        assert "PASSED" in prompt

    def test_get_system_prompt_empty_context(
        self, mock_backend: MagicMock, project_path: Path, basic_ctx: PipelineContext
    ):
        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        prompt = agent.get_system_prompt(basic_ctx)
        assert "No test files" in prompt
        assert "No code files" in prompt
        assert "No test results" in prompt

    def test_get_allowed_tools(self, mock_backend: MagicMock, project_path: Path):
        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        tools = agent.get_allowed_tools()
        # Security agent needs write/edit access for patching
        assert "Read" in tools
        assert "Write" in tools
        assert "Edit" in tools
        assert "Bash" in tools
        assert "Glob" in tools
        assert "Grep" in tools

    def test_run_parses_security_findings(
        self, mock_backend: MagicMock, project_path: Path, rich_ctx: PipelineContext
    ):
        response_json = json.dumps({
            "findings": [
                {
                    "severity": "critical",
                    "category": "injection",
                    "vulnerability_type": "SQL Injection",
                    "file": "routes/register.py",
                    "line": 15,
                    "description": "User input directly interpolated into SQL query",
                    "cwe_id": "CWE-89",
                    "patch_applied": False,
                    "patch_description": "",
                    "requires_manual_fix": True,
                    "recommendation": "Use parameterized queries or ORM methods",
                },
                {
                    "severity": "warning",
                    "category": "input_validation",
                    "vulnerability_type": "Missing Input Validation",
                    "file": "routes/register.py",
                    "line": 10,
                    "description": "No length limit on password field",
                    "cwe_id": "CWE-20",
                    "patch_applied": True,
                    "patch_description": "Added max length check",
                    "requires_manual_fix": False,
                    "recommendation": "Enforce reasonable length limits",
                },
            ],
            "patches_applied": 1,
            "requires_coding_rework": True,
            "feedback_for_coder": "Found critical SQL injection vulnerability in register endpoint. Use parameterized queries.",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        assert len(ctx.security_findings) == 2

        # Check critical finding
        assert ctx.security_findings[0].severity == Severity.CRITICAL
        assert ctx.security_findings[0].category == "injection"
        assert ctx.security_findings[0].vulnerability_type == "SQL Injection"
        assert ctx.security_findings[0].file == "routes/register.py"
        assert ctx.security_findings[0].line == 15
        assert ctx.security_findings[0].cwe_id == "CWE-89"
        assert ctx.security_findings[0].patch_applied is False
        assert ctx.security_findings[0].requires_manual_fix is True
        assert "parameterized queries" in ctx.security_findings[0].recommendation

        # Check warning finding
        assert ctx.security_findings[1].severity == Severity.WARNING
        assert ctx.security_findings[1].category == "input_validation"
        assert ctx.security_findings[1].patch_applied is True
        assert ctx.security_findings[1].patch_description == "Added max length check"
        assert ctx.security_findings[1].requires_manual_fix is False

        # Check context flags
        assert ctx.security_patches_applied == 1
        assert ctx.requires_coding_rework is True
        assert "SQL injection" in ctx.security_feedback

    def test_run_handles_empty_findings(
        self, mock_backend: MagicMock, project_path: Path, rich_ctx: PipelineContext
    ):
        response_json = json.dumps({
            "findings": [],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        assert ctx.security_findings == []
        assert ctx.security_patches_applied == 0
        assert ctx.requires_coding_rework is False
        assert ctx.security_feedback == ""

    def test_run_handles_malformed_json(
        self, mock_backend: MagicMock, project_path: Path, rich_ctx: PipelineContext
    ):
        mock_backend.run_agent.return_value = AgentResult(text="not json at all")

        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        # Should return empty findings on parse failure
        assert ctx.security_findings == []
        assert ctx.security_patches_applied == 0
        assert ctx.requires_coding_rework is False
        assert ctx.security_feedback == ""

    def test_run_handles_invalid_severity(
        self, mock_backend: MagicMock, project_path: Path, rich_ctx: PipelineContext
    ):
        response_json = json.dumps({
            "findings": [
                {
                    "severity": "bogus_level",
                    "category": "other",
                    "vulnerability_type": "Unknown",
                    "file": "x.py",
                    "description": "Something",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })
        mock_backend.run_agent.return_value = AgentResult(text=response_json)

        agent = SecurityAgent(backend=mock_backend, project_path=project_path)
        ctx, result = agent.run(rich_ctx)

        # Should fall back to INFO for invalid severity
        assert len(ctx.security_findings) == 1
        assert ctx.security_findings[0].severity == Severity.INFO


# ===========================================================================
# _parse_security_findings helper
# ===========================================================================


class TestParseSecurityFindings:
    def test_parses_valid_json(self):
        response = json.dumps({
            "findings": [
                {
                    "severity": "error",
                    "category": "authentication",
                    "vulnerability_type": "Hardcoded Secret",
                    "file": "config.py",
                    "line": 5,
                    "description": "API key hardcoded in source",
                    "cwe_id": "CWE-798",
                    "patch_applied": False,
                    "patch_description": "",
                    "requires_manual_fix": True,
                    "recommendation": "Use environment variables",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": True,
            "feedback_for_coder": "Remove hardcoded secrets",
        })

        result = _parse_security_findings(response)

        assert len(result["findings"]) == 1
        finding = result["findings"][0]
        assert isinstance(finding, SecurityFinding)
        assert finding.severity == Severity.ERROR
        assert finding.category == "authentication"
        assert finding.vulnerability_type == "Hardcoded Secret"
        assert finding.file == "config.py"
        assert finding.line == 5
        assert finding.cwe_id == "CWE-798"
        assert finding.requires_manual_fix is True
        assert result["patches_applied"] == 0
        assert result["requires_coding_rework"] is True
        assert result["feedback_for_coder"] == "Remove hardcoded secrets"

    def test_handles_json_with_extra_text(self):
        response = "Here's the analysis:\n" + json.dumps({
            "findings": [],
            "patches_applied": 2,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        }) + "\nEnd of report"

        result = _parse_security_findings(response)

        assert result["findings"] == []
        assert result["patches_applied"] == 2
        assert result["requires_coding_rework"] is False

    def test_handles_missing_optional_fields(self):
        response = json.dumps({
            "findings": [
                {
                    "severity": "info",
                    "category": "configuration",
                    "vulnerability_type": "Debug Mode",
                    "file": "settings.py",
                    "description": "Debug mode enabled",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        result = _parse_security_findings(response)

        assert len(result["findings"]) == 1
        finding = result["findings"][0]
        assert finding.line is None
        assert finding.cwe_id is None
        assert finding.patch_applied is False
        assert finding.patch_description == ""
        assert finding.requires_manual_fix is False
        assert finding.recommendation == ""

    def test_handles_invalid_json(self):
        response = "This is definitely not JSON"

        result = _parse_security_findings(response)

        assert result["findings"] == []
        assert result["patches_applied"] == 0
        assert result["requires_coding_rework"] is False
        assert result["feedback_for_coder"] == ""

    def test_handles_invalid_severity_falls_back_to_info(self):
        response = json.dumps({
            "findings": [
                {
                    "severity": "super_critical",  # invalid
                    "category": "other",
                    "vulnerability_type": "Test",
                    "file": "test.py",
                    "description": "Test",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        result = _parse_security_findings(response)

        assert len(result["findings"]) == 1
        assert result["findings"][0].severity == Severity.INFO

    def test_handles_multiple_findings_mixed_severities(self):
        response = json.dumps({
            "findings": [
                {
                    "severity": "critical",
                    "category": "injection",
                    "vulnerability_type": "Command Injection",
                    "file": "exec.py",
                    "line": 20,
                    "description": "Unsanitized input to shell",
                    "requires_manual_fix": True,
                    "recommendation": "Use subprocess with args list",
                },
                {
                    "severity": "warning",
                    "category": "crypto",
                    "vulnerability_type": "Weak Algorithm",
                    "file": "hash.py",
                    "line": 10,
                    "description": "Using MD5",
                    "patch_applied": True,
                    "patch_description": "Replaced with SHA256",
                },
                {
                    "severity": "info",
                    "category": "input_validation",
                    "vulnerability_type": "Missing Type Hint",
                    "file": "api.py",
                    "line": 5,
                    "description": "No type validation",
                },
            ],
            "patches_applied": 1,
            "requires_coding_rework": True,
            "feedback_for_coder": "Critical command injection found",
        })

        result = _parse_security_findings(response)

        assert len(result["findings"]) == 3
        assert result["findings"][0].severity == Severity.CRITICAL
        assert result["findings"][1].severity == Severity.WARNING
        assert result["findings"][2].severity == Severity.INFO
        assert result["patches_applied"] == 1
        assert result["requires_coding_rework"] is True
