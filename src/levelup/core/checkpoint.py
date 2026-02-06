"""Checkpoint logic for user review points in the pipeline."""

from __future__ import annotations

import json

from levelup.cli.display import (
    console,
    print_file_changes,
    print_requirements,
    print_review_findings,
    print_test_results,
)
from levelup.cli.prompts import get_checkpoint_decision
from levelup.core.context import CheckpointDecision, PipelineContext


def run_checkpoint(step_name: str, ctx: PipelineContext) -> tuple[CheckpointDecision, str]:
    """Display step results and get user decision.

    Returns:
        Tuple of (decision, feedback).
    """
    _display_checkpoint_content(step_name, ctx)
    return get_checkpoint_decision(step_name)


def build_checkpoint_display_data(step_name: str, ctx: PipelineContext) -> dict:
    """Extract checkpoint content as a serializable dict.

    Used by both the interactive display path and the headless checkpoint builder.
    """
    data: dict = {"step_name": step_name}

    if step_name == "requirements":
        if ctx.requirements:
            data["requirements"] = ctx.requirements.model_dump()
        else:
            data["message"] = "No requirements produced."

    elif step_name == "test_writing":
        if ctx.test_files:
            data["test_files"] = [
                {"path": f.path, "content": f.content, "is_new": f.is_new}
                for f in ctx.test_files
            ]
        else:
            data["message"] = "No test files written."

    elif step_name == "review":
        if ctx.code_files:
            data["code_files"] = [
                {"path": f.path, "content": f.content, "is_new": f.is_new}
                for f in ctx.code_files
            ]
        if ctx.test_results:
            data["test_results"] = [r.model_dump() for r in ctx.test_results]
        if ctx.review_findings:
            data["review_findings"] = [f.model_dump() for f in ctx.review_findings]
        else:
            data["message"] = "No review findings."

    return data


def _display_checkpoint_content(step_name: str, ctx: PipelineContext) -> None:
    """Display the relevant content for a checkpoint."""
    if step_name == "requirements":
        if ctx.requirements:
            print_requirements(ctx.requirements)
        else:
            console.print("[dim]No requirements produced.[/dim]")

    elif step_name == "test_writing":
        if ctx.test_files:
            print_file_changes(ctx.test_files, title="Test Files")
        else:
            console.print("[dim]No test files written.[/dim]")

    elif step_name == "review":
        if ctx.code_files:
            print_file_changes(ctx.code_files, title="Implementation Files")
        if ctx.test_results:
            print_test_results(ctx.test_results)
        if ctx.review_findings:
            print_review_findings(ctx.review_findings)
        else:
            console.print("[green]No review findings.[/green]")
