"""TestAgent - writes tests (TDD red phase)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from levelup.agents.base import BaseAgent
from levelup.core.context import FileChange, PipelineContext

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior test engineer practicing TDD. Your job is to write comprehensive tests BEFORE any implementation code exists.

Project context:
- Language: {language}
- Framework: {framework}
- Test runner: {test_runner}
- Test command: {test_command}

Requirements:
{requirements}

Implementation plan:
{plan}

Write tests that:
1. Cover all requirements and acceptance criteria
2. Include edge cases and error conditions
3. Follow the project's existing test patterns and conventions
4. Are organized logically with clear test names
5. Will initially FAIL (this is the TDD red phase)

Use the available tools to:
1. Read existing test files to understand patterns
2. Write your test files
3. Optionally run the tests with `{test_command}` via Bash to confirm they fail (expected)

After writing all test files, produce a final JSON summary:
{{
  "test_files": [
    {{
      "path": "relative/path/to/test_file.py",
      "description": "What this test file covers"
    }}
  ]
}}

IMPORTANT: Write the actual test files using the Write tool, then produce the JSON summary as your final message."""


class TestWriterAgent(BaseAgent):
    name = "test_writer"
    description = "Write tests for TDD red phase"

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        req_text = ""
        if ctx.requirements:
            req_text = ctx.requirements.summary + "\n"
            for r in ctx.requirements.requirements:
                req_text += f"- {r.description}\n"
                for c in r.acceptance_criteria:
                    req_text += f"  - AC: {c}\n"

        plan_text = ""
        if ctx.plan:
            plan_text = ctx.plan.approach + "\n"
            for s in ctx.plan.steps:
                plan_text += f"{s.order}. {s.description}\n"

        return SYSTEM_PROMPT_TEMPLATE.format(
            language=ctx.language or "unknown",
            framework=ctx.framework or "none",
            test_runner=ctx.test_runner or "unknown",
            test_command=ctx.test_command or "unknown",
            requirements=req_text or "No structured requirements.",
            plan=plan_text or "No implementation plan.",
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system = self.get_system_prompt(ctx)
        user_prompt = (
            "Write comprehensive tests for the requirements. "
            "First explore existing test files to understand patterns, "
            "then write the test files using the Write tool. "
            "After writing, produce a JSON summary of what you wrote."
        )

        response = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        # Parse JSON summary to find written test files
        test_file_paths = _parse_test_file_paths(response)

        # Read back the files from disk
        for rel_path in test_file_paths:
            full_path = self.project_path / rel_path
            try:
                content = full_path.read_text(encoding="utf-8")
                ctx.test_files.append(
                    FileChange(path=rel_path, content=content, is_new=True)
                )
            except OSError as e:
                logger.warning("Could not read test file %s: %s", rel_path, e)

        return ctx


def _parse_test_file_paths(response: str) -> list[str]:
    """Extract test file paths from the agent's JSON summary."""
    text = response.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
        return [f["path"] for f in data.get("test_files", []) if "path" in f]
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse test file summary: %s", e)
        return []
