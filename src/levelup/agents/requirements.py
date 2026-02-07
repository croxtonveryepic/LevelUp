"""RequirementsAgent - interactive conversation loop to clarify and structure requirements."""

from __future__ import annotations

import json
import logging

from levelup.agents.base import BaseAgent
from levelup.core.context import PipelineContext, Requirement, Requirements

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior software requirements analyst. Your job is to take a raw task description and produce clear, structured requirements.

Start by reading `levelup/project_context.md` for project background (language, framework, test runner, etc.).

The user has provided this task:
Title: {title}
Description: {description}

You have access to tools to read files and search the codebase. Use them to understand the existing code before finalizing requirements.

After exploring the codebase, update the "Codebase Insights" section of `levelup/project_context.md` with general project discoveries (directory structure, key modules, conventions) using the Write tool.

Then produce your final output as a JSON object with this exact structure:
{{
  "summary": "Brief summary of what needs to be done",
  "requirements": [
    {{
      "description": "What needs to be implemented",
      "acceptance_criteria": ["Criterion 1", "Criterion 2"]
    }}
  ],
  "assumptions": ["Assumption 1"],
  "out_of_scope": ["Thing that is out of scope"],
  "clarifications": ["Any questions or things that were clarified"]
}}

IMPORTANT: Your final message MUST contain ONLY the JSON object, no other text."""


class RequirementsAgent(BaseAgent):
    name = "requirements"
    description = "Clarify and structure requirements through codebase exploration"

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(
            title=ctx.task.title,
            description=ctx.task.description,
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Write", "Glob", "Grep"]

    def run(self, ctx: PipelineContext) -> tuple[PipelineContext, "AgentResult"]:
        from levelup.agents.backend import AgentResult

        system = self.get_system_prompt(ctx)
        user_prompt = (
            f"Please analyze this task and produce structured requirements.\n\n"
            f"Task: {ctx.task.title}\n"
            f"Description: {ctx.task.description}\n\n"
            f"Explore the codebase first to understand the project structure, "
            f"then produce your requirements as JSON."
        )

        result = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        # Parse the JSON response
        ctx.requirements = _parse_requirements(result.text)
        return ctx, result


def _parse_requirements(response: str) -> Requirements:
    """Parse the agent's response into a Requirements model."""
    # Try to extract JSON from the response
    text = response.strip()

    # Find JSON object in the response
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
        reqs = [
            Requirement(
                description=r["description"],
                acceptance_criteria=r.get("acceptance_criteria", []),
            )
            for r in data.get("requirements", [])
        ]
        return Requirements(
            summary=data.get("summary", ""),
            requirements=reqs,
            assumptions=data.get("assumptions", []),
            out_of_scope=data.get("out_of_scope", []),
            clarifications=data.get("clarifications", []),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse requirements JSON: %s", e)
        # Fallback: treat the entire response as the summary
        return Requirements(
            summary=response[:500],
            requirements=[Requirement(description=response)],
        )
