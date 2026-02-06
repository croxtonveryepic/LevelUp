"""PlanningAgent - explores codebase and designs implementation approach."""

from __future__ import annotations

import json
import logging

from levelup.agents.base import BaseAgent
from levelup.core.context import PipelineContext, Plan, PlanStep

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are a senior software architect. Your job is to explore the codebase and design an implementation plan.

Project context:
- Language: {language}
- Framework: {framework}
- Test runner: {test_runner}
- Test command: {test_command}

Requirements:
{requirements}

You have access to tools to read files and search the codebase. Use them extensively to understand:
1. The project structure and directory layout
2. Existing code patterns and conventions
3. Related files that will need to be modified
4. Where new code should be placed

After thorough exploration, produce your final output as a JSON object with this exact structure:
{{
  "approach": "High-level description of the implementation approach",
  "steps": [
    {{
      "order": 1,
      "description": "What to do in this step",
      "files_to_modify": ["path/to/existing/file.py"],
      "files_to_create": ["path/to/new/file.py"]
    }}
  ],
  "affected_files": ["all/files/that/will/change.py"],
  "risks": ["Potential risk or concern"]
}}

IMPORTANT: Your final message MUST contain ONLY the JSON object, no other text."""


class PlanningAgent(BaseAgent):
    name = "planning"
    description = "Explore codebase and design implementation approach"

    def get_system_prompt(self, ctx: PipelineContext) -> str:
        req_text = ""
        if ctx.requirements:
            req_text = ctx.requirements.summary + "\n"
            for r in ctx.requirements.requirements:
                req_text += f"- {r.description}\n"
                for c in r.acceptance_criteria:
                    req_text += f"  - AC: {c}\n"

        return SYSTEM_PROMPT_TEMPLATE.format(
            language=ctx.language or "unknown",
            framework=ctx.framework or "none",
            test_runner=ctx.test_runner or "unknown",
            test_command=ctx.test_command or "unknown",
            requirements=req_text or "No structured requirements available.",
        )

    def get_allowed_tools(self) -> list[str]:
        return ["Read", "Glob", "Grep"]

    def run(self, ctx: PipelineContext) -> PipelineContext:
        system = self.get_system_prompt(ctx)
        user_prompt = (
            "Please explore the codebase thoroughly and design an implementation plan "
            "for the requirements described in the system prompt. "
            "Start by searching for the project structure and relevant files."
        )

        response = self.backend.run_agent(
            system_prompt=system,
            user_prompt=user_prompt,
            allowed_tools=self.get_allowed_tools(),
            working_directory=str(self.project_path),
        )

        ctx.plan = _parse_plan(response)
        return ctx


def _parse_plan(response: str) -> Plan:
    """Parse the agent's response into a Plan model."""
    text = response.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    try:
        data = json.loads(text)
        steps = [
            PlanStep(
                order=s.get("order", i + 1),
                description=s["description"],
                files_to_modify=s.get("files_to_modify", []),
                files_to_create=s.get("files_to_create", []),
            )
            for i, s in enumerate(data.get("steps", []))
        ]
        return Plan(
            approach=data.get("approach", ""),
            steps=steps,
            affected_files=data.get("affected_files", []),
            risks=data.get("risks", []),
        )
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning("Failed to parse plan JSON: %s", e)
        return Plan(
            approach=response[:500],
            steps=[PlanStep(order=1, description=response)],
        )
