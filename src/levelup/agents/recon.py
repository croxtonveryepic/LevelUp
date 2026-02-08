"""ReconAgent - one-time project reconnaissance before the TDD pipeline."""

from __future__ import annotations

import logging
from pathlib import Path

from levelup.agents.backend import AgentResult, Backend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior software architect performing a one-time reconnaissance of a project codebase.

The project has been detected as:
- **Language:** {language}
- **Framework:** {framework}
- **Test runner:** {test_runner}
- **Test command:** {test_command}

Your goal is to deeply explore the codebase and write a comprehensive project context file at `levelup/project_context.md`. Use `Read`, `Glob`, and `Grep` to explore, then `Write` to produce the final file.

The file MUST start with this exact detection header:

```
# Project Context

- **Language:** {language}
- **Framework:** {framework}
- **Test runner:** {test_runner}
- **Test command:** {test_command}
```

Then add these structured sections with your findings:

## Directory Structure
A brief outline of the top-level directory layout and what each directory contains.

## Architecture & Key Modules
The main architectural patterns (MVC, layered, microservices, etc.), key entry points, and important modules/classes.

## Coding Conventions
Naming conventions, formatting style, import ordering, error handling patterns, logging approach.

## Dependencies
Key third-party dependencies and what they're used for.

## Test Patterns
How tests are organized, naming conventions, fixture patterns, mocking approach.

## Codebase Insights
Any other notable patterns, configuration approaches, or things a developer should know.

Be thorough but concise. Focus on information that would help an AI agent write correct, idiomatic code for this project."""

USER_PROMPT_TEMPLATE = """Explore this project codebase and write a comprehensive project context file to `levelup/project_context.md`.

Use Glob to discover the directory structure, Read to examine key files (entry points, config, tests), and Grep to find patterns.

Write the complete file using the Write tool when done."""


class ReconAgent:
    """Standalone recon agent that explores a project and writes project_context.md.

    Does not inherit BaseAgent since it has no PipelineContext.
    """

    def __init__(
        self,
        backend: Backend,
        project_path: Path,
        *,
        language: str | None = None,
        framework: str | None = None,
        test_runner: str | None = None,
        test_command: str | None = None,
    ) -> None:
        self.backend = backend
        self.project_path = project_path
        self.language = language or "unknown"
        self.framework = framework or "none"
        self.test_runner = test_runner or "unknown"
        self.test_command = test_command or "unknown"

    def run(self) -> AgentResult:
        """Run the recon agent and return usage metrics."""
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            language=self.language,
            framework=self.framework,
            test_runner=self.test_runner,
            test_command=self.test_command,
        )
        user_prompt = USER_PROMPT_TEMPLATE

        result = self.backend.run_agent(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            allowed_tools=["Read", "Write", "Glob", "Grep"],
            working_directory=str(self.project_path),
        )
        return result
