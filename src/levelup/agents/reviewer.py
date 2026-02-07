"""ReviewAgent - checks code quality, security, and best practices."""

from __future__ import annotations

import json
import logging

from levelup.agents.base import BaseAgent
from levelup.core.context import PipelineContext, ReviewFinding, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior code reviewer. Your job is to review code changes for quality, security, and best practices.

Start by reading `levelup/project_context.md` for project background (language, framework, test runner, test command, and any prior codebase insights).

Files changed (tests):
{test_files}

Files changed (implementation):
{code_files}

Test results:
{test_results}

Review the code for:
1. **Correctness**: Logic errors, edge cases, off-by-one errors
2. **Security**: Injection vulnerabilities, unsafe operations, hardcoded secrets
3. **Best practices**: Code style, naming conventions, SOLID principles
4. **Performance**: Obvious inefficiencies, N+1 queries, unnecessary allocations
5. **Maintainability**: Code clarity, documentation needs, test coverage gaps

Use Read, Glob, and Grep tools to examine the code in context.

Produce your final output as a JSON array of findings:
{{
  "findings": [
    {{
      "severity": "info|warning|error|critical",
      "category": "correctness|security|best_practices|performance|maintainability",
      "file": "path/to/file.py",
      "line": 42,
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }}
  ],
  "overall_assessment": "Brief overall assessment"
}}

If the code looks good, return an empty findings array with a positive assessment.

IMPORTANT: Your final message MUST contain ONLY the JSON object."""


class ReviewAgent(BaseAgent):
    name = "reviewer"
    description = "Review code quality, security, and best practices"

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        test_text = ""
        for tf in ctx.test_files:
            test_text += f"\n--- {tf.path} ---\n{tf.content}\n"

        code_text = ""
        for cf in ctx.code_files:
            code_text += f"\n--- {cf.path} ---\n{cf.content}\n"

        test_results_text = ""
        for tr in ctx.test_results:
            test_results_text += (
                f"{'PASSED' if tr.passed else 'FAILED'}: "
                f"{tr.total} tests, {tr.failures} failures\n"
            )

        return SYSTEM_PROMPT_TEMPLATE.format(
            test_files=test_text or "No test files.",
            code_files=code_text or "No code files.",
            test_results=test_results_text or "No test results.",
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Glob", "Grep"]

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system = self.get_system_prompt(ctx)
        user_prompt = (
            "Review all the code changes described in the system prompt. "
            "Use Read to examine files in their full context. "
            "Produce your findings as a JSON object."
        )

        response = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        ctx.review_findings = _parse_findings(response)
        return ctx


def _parse_findings(response: str) -> list[ReviewFinding]:
    """Parse the agent's response into ReviewFinding models."""
    text = response.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
        findings = []
        for f in data.get("findings", []):
            try:
                severity = Severity(f.get("severity", "info"))
            except ValueError:
                severity = Severity.INFO
            findings.append(
                ReviewFinding(
                    severity=severity,
                    category=f.get("category", "general"),
                    file=f.get("file", "unknown"),
                    line=f.get("line"),
                    message=f.get("message", ""),
                    suggestion=f.get("suggestion", ""),
                )
            )
        return findings
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse review findings JSON: %s", e)
        return []
