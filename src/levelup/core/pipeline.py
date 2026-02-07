"""Pipeline step definitions and configuration."""

from __future__ import annotations

import enum
from dataclasses import dataclass


class StepType(str, enum.Enum):
    DETECTION = "detection"
    AGENT = "agent"
    CHECKPOINT = "checkpoint"


@dataclass(frozen=True)
class PipelineStep:
    """Definition of a single pipeline step."""

    name: str
    step_type: StepType
    agent_name: str | None = None
    checkpoint_after: bool = False
    description: str = ""


# The default pipeline: detection -> requirements -> plan -> test -> code -> review
DEFAULT_PIPELINE: list[PipelineStep] = [
    PipelineStep(
        name="detect",
        step_type=StepType.DETECTION,
        description="Auto-detect project language, framework, and test runner",
    ),
    PipelineStep(
        name="requirements",
        step_type=StepType.AGENT,
        agent_name="requirements",
        checkpoint_after=True,
        description="Clarify and structure requirements",
    ),
    PipelineStep(
        name="planning",
        step_type=StepType.AGENT,
        agent_name="planning",
        description="Explore codebase and design implementation approach",
    ),
    PipelineStep(
        name="test_writing",
        step_type=StepType.AGENT,
        agent_name="test_writer",
        checkpoint_after=True,
        description="Write tests (TDD red phase)",
    ),
    PipelineStep(
        name="coding",
        step_type=StepType.AGENT,
        agent_name="coder",
        description="Implement code until tests pass (TDD green phase)",
    ),
    PipelineStep(
        name="security",
        step_type=StepType.AGENT,
        agent_name="security",
        checkpoint_after=True,
        description="Detect and patch security vulnerabilities",
    ),
    PipelineStep(
        name="review",
        step_type=StepType.AGENT,
        agent_name="reviewer",
        checkpoint_after=True,
        description="Review code quality, security, and best practices",
    ),
]
