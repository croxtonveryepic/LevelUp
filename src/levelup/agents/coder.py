"""CodeAgent - implements code and iterates until tests pass (TDD green phase)."""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path

from levelup.agents.base import BaseAgent
from levelup.core.context import FileChange, PipelineContext, TestResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior software developer. Your job is to implement code that makes the tests pass (TDD green phase).

Start by reading `levelup/project_context.md` for project background (language, framework, test runner, test command, and any prior codebase insights).

Requirements:
{requirements}

Implementation plan:
{plan}

Test files that need to pass:
{test_files}

Your workflow:
1. Read the test files to understand what's expected
2. Read existing source files to understand the codebase
3. Implement the code using the Write tool
4. Run the tests using `{test_command}` via Bash
5. If tests fail, read the error output, fix the code, and run tests again
6. Repeat until ALL tests pass

Write clean, idiomatic code following the project's existing patterns.

After all tests pass, produce a final JSON summary:
{{
  "files_written": ["path/to/file.py"],
  "iterations": 3,
  "all_tests_passing": true
}}

IMPORTANT: Keep iterating until tests pass. Write files using the Write tool and run tests using `{test_command}` via Bash."""

MAX_CODE_ITERATIONS = 5


class CodeAgent(BaseAgent):
    name = "coder"
    description = "Implement code until tests pass (TDD green phase)"

    def __init__(self, *args, max_iterations: int = MAX_CODE_ITERATIONS, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._max_iterations = max_iterations

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        req_text = ""
        if ctx.requirements:
            req_text = ctx.requirements.summary + "\n"
            for r in ctx.requirements.requirements:
                req_text += f"- {r.description}\n"

        plan_text = ""
        if ctx.plan:
            plan_text = ctx.plan.approach + "\n"
            for s in ctx.plan.steps:
                plan_text += f"{s.order}. {s.description}\n"

        test_text = ""
        for tf in ctx.test_files:
            test_text += f"\n--- {tf.path} ---\n{tf.content}\n"

        return SYSTEM_PROMPT_TEMPLATE.format(
            test_command=ctx.test_command or "unknown",
            requirements=req_text or "No structured requirements.",
            plan=plan_text or "No implementation plan.",
            test_files=test_text or "No test files.",
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system = self.get_system_prompt(ctx)
        user_prompt = (
            "Implement the code to make all tests pass. "
            "Read the test files first, then implement the necessary code. "
            "Run tests after each change and iterate until they pass. "
            f"Maximum {self._max_iterations} iterations."
        )

        response = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        # Parse JSON summary to find written files and iteration count
        files_written, iterations = _parse_coder_summary(response)

        # Read back written files from disk
        for rel_path in files_written:
            full_path = self.project_path / rel_path
            try:
                content = full_path.read_text(encoding="utf-8")
                ctx.code_files.append(
                    FileChange(path=rel_path, content=content, is_new=True)
                )
            except OSError as e:
                logger.warning("Could not read code file %s: %s", rel_path, e)

        ctx.code_iteration = iterations

        # Run final test to get structured result
        if ctx.test_command:
            try:
                result = subprocess.run(
                    ctx.test_command,
                    shell=True,
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                output = result.stdout
                if result.stderr:
                    output += "\n" + result.stderr
                passed = result.returncode == 0
                ctx.test_results.append(
                    TestResult(
                        passed=passed,
                        output=output,
                        command=ctx.test_command,
                    )
                )
            except Exception as e:
                logger.warning("Failed to run final tests: %s", e)

        return ctx


def _parse_coder_summary(response: str) -> tuple[list[str], int]:
    """Extract files_written and iterations from the agent's JSON summary."""
    text = response.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
        files = data.get("files_written", [])
        iterations = data.get("iterations", 0)
        return files, iterations
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse coder summary: %s", e)
        return [], 0
