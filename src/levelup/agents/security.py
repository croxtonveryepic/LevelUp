"""SecurityAgent - detects and patches security vulnerabilities."""

from __future__ import annotations

import json
import logging

from levelup.agents.base import BaseAgent
from levelup.core.context import PipelineContext, SecurityFinding, Severity

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a security expert performing vulnerability assessment and remediation. Your job is to detect security vulnerabilities, automatically patch minor issues, and identify major issues requiring manual fixes.

Start by reading `levelup/project_context.md` for project background (language, framework, test runner, test command, and any prior codebase insights).

Files changed (tests):
{test_files}

Files changed (implementation):
{code_files}

Test results:
{test_results}

## Your Mission

1. **Detect vulnerabilities** using Read, Glob, and Grep tools to examine code
2. **Auto-patch MINOR issues** (INFO/WARNING severity) using Write/Edit tools:
   - Missing input validation
   - Lack of output escaping
   - Insecure default configurations
   - Missing type hints that could prevent bugs
   - Use of deprecated insecure functions

3. **Flag MAJOR issues** (ERROR/CRITICAL severity) for manual fix:
   - SQL/NoSQL/Command injection vulnerabilities
   - Authentication/authorization flaws
   - Cryptographic weaknesses (weak algorithms, hardcoded keys)
   - XSS vulnerabilities
   - Path traversal
   - Insecure deserialization
   - Sensitive data exposure

## Security Checks (OWASP Top 10 Coverage)

**Injection Attacks:**
- SQL injection: Check for string concatenation in queries
- Command injection: Check for unsanitized input to shell commands
- NoSQL injection: Check for unvalidated query parameters
- XSS: Check for unescaped user input in HTML/templates
- Path traversal: Check for unchecked file paths

**Authentication & Crypto:**
- Hardcoded credentials, API keys, secrets
- Weak password hashing (MD5, SHA1, plain text)
- Insecure random number generation
- Weak crypto algorithms
- Missing authentication checks

**Input Validation:**
- Missing type validation
- No length limits
- Unsafe deserialization (pickle, eval)
- Missing sanitization

**Configuration:**
- Debug mode enabled in production
- Verbose error messages exposing internals
- Overly permissive CORS
- Insecure defaults

## Severity Classification

- **CRITICAL**: Remote code execution, authentication bypass, data breach
- **ERROR**: SQL injection, XSS, command injection, crypto flaws
- **WARNING**: Missing validation, weak config, deprecated functions
- **INFO**: Missing type hints, minor improvements

## Output Format

Produce your final output as JSON:

```json
{{
  "findings": [
    {{
      "severity": "critical|error|warning|info",
      "category": "injection|authentication|crypto|input_validation|configuration|other",
      "vulnerability_type": "SQL Injection",
      "file": "path/to/file.py",
      "line": 42,
      "description": "User input directly interpolated into SQL query",
      "cwe_id": "CWE-89",
      "patch_applied": false,
      "patch_description": "",
      "requires_manual_fix": true,
      "recommendation": "Use parameterized queries or ORM methods"
    }}
  ],
  "patches_applied": 0,
  "requires_coding_rework": false,
  "feedback_for_coder": ""
}}
```

**Rules:**
- Set `patch_applied: true` and provide `patch_description` for issues you fixed
- Set `requires_manual_fix: true` for ERROR/CRITICAL issues
- Set `requires_coding_rework: true` if any MAJOR issues found (will trigger coding agent re-run)
- Provide detailed `feedback_for_coder` explaining what needs to be fixed
- If no vulnerabilities found, return empty findings array

IMPORTANT: Your final message MUST contain ONLY the JSON object."""


class SecurityAgent(BaseAgent):
    name = "security"
    description = "Detect and patch security vulnerabilities"

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
        """Security agent needs Read/Write/Edit for patching."""
        return ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]

    def run(self, ctx: PipelineContext) -> tuple[PipelineContext, "AgentResult"]:
        from levelup.agents.backend import AgentResult

        system = self.get_system_prompt(ctx)
        user_prompt = (
            "Perform security review of all code changes described in the system prompt. "
            "Use Read, Glob, and Grep to examine files in context. "
            "Auto-patch minor issues using Write/Edit tools. "
            "Flag major issues for manual fix. "
            "Produce your findings as a JSON object."
        )

        result = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        # Parse JSON response and update context
        parsed = _parse_security_findings(result.text)
        ctx.security_findings = parsed["findings"]
        ctx.security_patches_applied = parsed["patches_applied"]
        ctx.requires_coding_rework = parsed["requires_coding_rework"]
        ctx.security_feedback = parsed["feedback_for_coder"]

        return ctx, result


def _parse_security_findings(response: str) -> dict:
    """Parse the agent's response into SecurityFinding models."""
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
                SecurityFinding(
                    severity=severity,
                    category=f.get("category", "other"),
                    vulnerability_type=f.get("vulnerability_type", "Unknown"),
                    file=f.get("file", "unknown"),
                    line=f.get("line"),
                    description=f.get("description", ""),
                    cwe_id=f.get("cwe_id"),
                    patch_applied=f.get("patch_applied", False),
                    patch_description=f.get("patch_description", ""),
                    requires_manual_fix=f.get("requires_manual_fix", False),
                    recommendation=f.get("recommendation", ""),
                )
            )

        return {
            "findings": findings,
            "patches_applied": data.get("patches_applied", 0),
            "requires_coding_rework": data.get("requires_coding_rework", False),
            "feedback_for_coder": data.get("feedback_for_coder", ""),
        }
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse security findings JSON: %s", e)
        return {
            "findings": [],
            "patches_applied": 0,
            "requires_coding_rework": False,
            "feedback_for_coder": "",
        }
