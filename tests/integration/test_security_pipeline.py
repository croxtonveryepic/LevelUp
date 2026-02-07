"""Integration tests for security pipeline flow."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from levelup.config.settings import (
    LevelUpSettings,
    LLMSettings,
    PipelineSettings,
    ProjectSettings,
)
from levelup.core.context import PipelineStatus, Severity, TaskInput
from levelup.core.orchestrator import Orchestrator


@pytest.fixture
def sample_project(tmp_path):
    """Create a minimal Python project for testing."""
    # pyproject.toml
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "sample"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    )
    # Source file with potential vulnerability
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").touch()
    (src / "api.py").write_text(
        "def login(username, password):\n"
        "    query = f'SELECT * FROM users WHERE username={username}'\n"
        "    return db.execute(query)\n"
    )
    # Tests dir
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "__init__.py").touch()
    return tmp_path


@pytest.fixture
def settings(sample_project):
    return LevelUpSettings(
        llm=LLMSettings(api_key="test-key", model="test-model", backend="anthropic_sdk"),
        project=ProjectSettings(path=sample_project),
        pipeline=PipelineSettings(
            require_checkpoints=False,
            create_git_branch=False,
            max_code_iterations=2,
        ),
    )


def _make_mock_response(text: str, usage_in: int = 100, usage_out: int = 50):
    """Create a mock Anthropic response with text content and usage stats."""
    mock_response = MagicMock()
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = text
    mock_response.content = [mock_block]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = MagicMock()
    mock_response.usage.input_tokens = usage_in
    mock_response.usage.output_tokens = usage_out
    return mock_response


class TestSecurityPipelineCleanCode:
    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_with_no_security_issues(self, mock_anthropic_cls, settings):
        """Test security step when no vulnerabilities are found."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Add login endpoint",
            "requirements": [{"description": "Login endpoint", "acceptance_criteria": []}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Implement login",
            "steps": [{"order": 1, "description": "Add login", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_login.py", "description": "Test login"}]
        })

        coder_json = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        # Security agent finds no issues
        security_json = json.dumps({
            "findings": [],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        review_json = json.dumps({
            "findings": [],
            "overall_assessment": "Good",
        })

        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json),
            _make_mock_response(security_json),
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Add login", description="Implement login endpoint")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert ctx.security_findings == []
        assert ctx.security_patches_applied == 0
        assert ctx.requires_coding_rework is False


class TestSecurityPipelineMinorIssues:
    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_with_auto_patched_issues(self, mock_anthropic_cls, settings):
        """Test security step when minor issues are auto-patched."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Add login endpoint",
            "requirements": [{"description": "Login", "acceptance_criteria": []}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Implement",
            "steps": [{"order": 1, "description": "Code", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_api.py", "description": "Tests"}]
        })

        coder_json = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        # Security agent finds and patches minor issues
        security_json = json.dumps({
            "findings": [
                {
                    "severity": "warning",
                    "category": "input_validation",
                    "vulnerability_type": "Missing Input Validation",
                    "file": "src/api.py",
                    "line": 10,
                    "description": "No length limit on username",
                    "patch_applied": True,
                    "patch_description": "Added max length check",
                    "requires_manual_fix": False,
                    "recommendation": "Enforce length limits",
                },
                {
                    "severity": "info",
                    "category": "configuration",
                    "vulnerability_type": "Missing Type Hint",
                    "file": "src/api.py",
                    "line": 5,
                    "description": "No type annotation",
                    "patch_applied": True,
                    "patch_description": "Added type hints",
                    "requires_manual_fix": False,
                    "recommendation": "Use type hints",
                },
            ],
            "patches_applied": 2,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        review_json = json.dumps({
            "findings": [],
            "overall_assessment": "Good",
        })

        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json),
            _make_mock_response(security_json),
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Add login", description="Login endpoint")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        assert len(ctx.security_findings) == 2
        assert ctx.security_patches_applied == 2
        assert ctx.requires_coding_rework is False
        assert all(f.patch_applied for f in ctx.security_findings)


class TestSecurityPipelineLoopBack:
    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_loops_back_for_major_issues(self, mock_anthropic_cls, settings):
        """Test that major security issues trigger coding agent re-run."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Add login endpoint",
            "requirements": [{"description": "Login", "acceptance_criteria": []}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Implement",
            "steps": [{"order": 1, "description": "Code", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_api.py", "description": "Tests"}]
        })

        # First coding attempt
        coder_json_1 = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        # Security agent finds critical issue
        security_json_1 = json.dumps({
            "findings": [
                {
                    "severity": "critical",
                    "category": "injection",
                    "vulnerability_type": "SQL Injection",
                    "file": "src/api.py",
                    "line": 15,
                    "description": "User input directly in SQL query",
                    "cwe_id": "CWE-89",
                    "patch_applied": False,
                    "requires_manual_fix": True,
                    "recommendation": "Use parameterized queries",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": True,
            "feedback_for_coder": "Critical SQL injection found. Use parameterized queries.",
        })

        # Second coding attempt (after security feedback)
        coder_json_2 = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        # Second security check - issue fixed
        security_json_2 = json.dumps({
            "findings": [],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        review_json = json.dumps({
            "findings": [],
            "overall_assessment": "Good",
        })

        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json_1),  # First coding
            _make_mock_response(security_json_1),  # Security finds issue
            _make_mock_response(coder_json_2),  # Loop-back coding
            _make_mock_response(security_json_2),  # Security re-check (clean)
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Add login", description="Login endpoint")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # Final context should have no findings (fixed in second iteration)
        assert ctx.security_findings == []
        assert ctx.requires_coding_rework is False
        # Verify coding agent was called twice (initial + loop-back)
        assert mock_client.messages.create.call_count == 8

    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    def test_pipeline_continues_after_failed_retry(self, mock_anthropic_cls, settings):
        """Test that pipeline continues to checkpoint if issue remains after retry."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        requirements_json = json.dumps({
            "summary": "Add login",
            "requirements": [{"description": "Login", "acceptance_criteria": []}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Implement",
            "steps": [{"order": 1, "description": "Code", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({
            "test_files": [{"path": "tests/test_api.py", "description": "Tests"}]
        })

        coder_json = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        # Security finds critical issue (both times)
        security_json = json.dumps({
            "findings": [
                {
                    "severity": "critical",
                    "category": "injection",
                    "vulnerability_type": "SQL Injection",
                    "file": "src/api.py",
                    "line": 15,
                    "description": "SQL injection vulnerability",
                    "requires_manual_fix": True,
                    "recommendation": "Use parameterized queries",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": True,
            "feedback_for_coder": "SQL injection still present",
        })

        review_json = json.dumps({
            "findings": [],
            "overall_assessment": "Has security issues",
        })

        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json),  # First coding
            _make_mock_response(security_json),  # Security finds issue
            _make_mock_response(coder_json),  # Loop-back coding
            _make_mock_response(security_json),  # Security still finds issue
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Add login", description="Login endpoint")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # Issue remains but pipeline continues
        assert len(ctx.security_findings) == 1
        assert ctx.security_findings[0].severity == Severity.CRITICAL
        # requires_coding_rework should be False to prevent infinite loop
        assert ctx.requires_coding_rework is False


class TestSecurityPipelineGitCommits:
    @patch("levelup.agents.llm_client.anthropic.Anthropic")
    @patch("git.Repo")
    def test_security_loop_back_creates_revised_commits(
        self, mock_repo_cls, mock_anthropic_cls, settings
    ):
        """Test that loop-back creates revised git commits."""
        # Enable git commits
        settings.pipeline.create_git_branch = True

        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # Mock git repo
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.head.commit.hexsha = "abc123"
        mock_repo.is_dirty.return_value = False

        requirements_json = json.dumps({
            "summary": "Login",
            "requirements": [{"description": "Login", "acceptance_criteria": []}],
            "assumptions": [],
            "out_of_scope": [],
            "clarifications": [],
        })

        plan_json = json.dumps({
            "approach": "Impl",
            "steps": [{"order": 1, "description": "Code", "files_to_modify": [], "files_to_create": []}],
            "affected_files": [],
            "risks": [],
        })

        test_writer_json = json.dumps({"test_files": []})

        coder_json = json.dumps({
            "files_written": ["src/api.py"],
            "iterations": 1,
            "all_tests_passing": True,
        })

        security_json_bad = json.dumps({
            "findings": [
                {
                    "severity": "error",
                    "category": "injection",
                    "vulnerability_type": "SQL Injection",
                    "file": "src/api.py",
                    "description": "SQL injection",
                    "requires_manual_fix": True,
                    "recommendation": "Fix it",
                }
            ],
            "patches_applied": 0,
            "requires_coding_rework": True,
            "feedback_for_coder": "Fix SQL injection",
        })

        security_json_good = json.dumps({
            "findings": [],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        })

        review_json = json.dumps({"findings": [], "overall_assessment": "OK"})

        responses = [
            _make_mock_response(requirements_json),
            _make_mock_response(plan_json),
            _make_mock_response(test_writer_json),
            _make_mock_response(coder_json),
            _make_mock_response(security_json_bad),
            _make_mock_response(coder_json),
            _make_mock_response(security_json_good),
            _make_mock_response(review_json),
        ]
        mock_client.messages.create.side_effect = responses

        orchestrator = Orchestrator(settings=settings)
        task = TaskInput(title="Login", description="Login")
        ctx = orchestrator.run(task)

        assert ctx.status == PipelineStatus.COMPLETED
        # Verify git commits were made (initial + revised for both coding and security)
        # Should have commits for: detect, requirements, planning, test_writing,
        # coding (initial), coding (revised), security (initial), security (revised), review
        assert mock_repo.index.commit.call_count >= 4
