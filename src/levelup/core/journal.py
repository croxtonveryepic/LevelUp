"""Run journal — writes an incremental Markdown log of pipeline activity."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from levelup.core.context import PipelineContext

logger = logging.getLogger(__name__)


def _slugify(text: str, max_length: int = 50) -> str:
    """Convert text to a URL-friendly slug.

    Lowercase, replace non-alphanumeric with dashes, strip leading/trailing
    dashes, truncate to *max_length* (no trailing dash after truncation).
    Falls back to ``"run-journal"`` if the result is empty.
    """
    slug = text.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")
    return slug or "run-journal"


def _build_filename(ctx: PipelineContext) -> str:
    """Build the journal filename from context metadata."""
    date = ctx.started_at.strftime("%Y%m%d")
    slug = _slugify(ctx.task.title)
    if ctx.task.source_id:
        return f"{date}-{ctx.task.source_id}-{slug}.md"
    return f"{date}-{slug}.md"


class RunJournal:
    """Incremental Markdown log written during a pipeline run."""

    def __init__(self, ctx: PipelineContext, base_path: Path | None = None) -> None:
        self._dir = (base_path or ctx.project_path) / "levelup"
        self._path = self._dir / _build_filename(ctx)

    @property
    def path(self) -> Path:
        return self._path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def write_header(self, ctx: PipelineContext) -> None:
        """Create dir, write title + run metadata + task description."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)

            lines = [
                f"# Run Journal: {ctx.task.title}",
                "",
                f"- **Run ID:** {ctx.run_id}",
                f"- **Started:** {ctx.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
                f"- **Task:** {ctx.task.title}",
            ]

            if ctx.task.source_id:
                lines.append(f"- **Ticket:** {ctx.task.source_id} ({ctx.task.source})")

            if ctx.task.description:
                lines.extend(["", "## Task Description", "", ctx.task.description])

            lines.append("")
            self._path.write_text("\n".join(lines), encoding="utf-8")
        except OSError:
            logger.warning("Failed to write journal header: %s", self._path)

    def log_step(self, step_name: str, ctx: PipelineContext) -> None:
        """Append a section for a completed pipeline step."""
        try:
            now = datetime.now(timezone.utc).strftime("%H:%M:%S")
            lines = [f"## Step: {step_name}  ({now})", ""]

            formatter = _STEP_FORMATTERS.get(step_name)
            if formatter:
                lines.extend(formatter(ctx))
            else:
                lines.append(f"Step `{step_name}` completed.")

            # Append usage info if available
            usage = ctx.step_usage.get(step_name)
            if usage:
                parts = []
                if usage.cost_usd:
                    parts.append(f"${usage.cost_usd:.4f}")
                tokens = usage.input_tokens + usage.output_tokens
                if tokens:
                    parts.append(f"{tokens:,} tokens")
                if usage.duration_ms:
                    parts.append(f"{usage.duration_ms / 1000:.1f}s")
                if parts:
                    lines.append(f"- **Usage:** {' | '.join(parts)}")

            lines.append("")
            self._append(lines)
        except OSError:
            logger.warning("Failed to write journal step %s: %s", step_name, self._path)

    def log_checkpoint(self, step_name: str, decision: str, feedback: str) -> None:
        """Append a checkpoint decision record."""
        try:
            lines = [
                f"### Checkpoint: {step_name}",
                "",
                f"- **Decision:** {decision}",
            ]
            if feedback:
                lines.append(f"- **Feedback:** {feedback}")
            lines.append("")
            self._append(lines)
        except OSError:
            logger.warning("Failed to write journal checkpoint: %s", self._path)

    def log_instruct(self, instruction: str, agent_result: object | None = None) -> None:
        """Append an instruct entry (instruction text + optional review cost)."""
        try:
            lines = [
                "### Instruct",
                "",
                f"- **Rule added:** {instruction}",
            ]
            if agent_result is not None:
                from levelup.agents.backend import AgentResult

                if isinstance(agent_result, AgentResult) and agent_result.cost_usd:
                    lines.append(f"- **Review cost:** ${agent_result.cost_usd:.4f}")
            lines.append("")
            self._append(lines)
        except OSError:
            logger.warning("Failed to write journal instruct: %s", self._path)

    def log_outcome(self, ctx: PipelineContext) -> None:
        """Append final status (completed/failed/aborted + error if any)."""
        try:
            lines = ["## Outcome", "", f"- **Status:** {ctx.status.value}"]
            if ctx.error_message:
                lines.append(f"- **Error:** {ctx.error_message}")
            if ctx.total_cost_usd:
                lines.append(f"- **Total cost:** ${ctx.total_cost_usd:.4f}")
            lines.append("")
            self._append(lines)
        except OSError:
            logger.warning("Failed to write journal outcome: %s", self._path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _append(self, lines: list[str]) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))


# ------------------------------------------------------------------
# Step content formatters
# ------------------------------------------------------------------


def _format_detect(ctx: PipelineContext) -> list[str]:
    return ["See `levelup/project_context.md` for project details."]


def _format_requirements(ctx: PipelineContext) -> list[str]:
    if ctx.requirements is None:
        return ["No requirements produced."]
    r = ctx.requirements
    lines = [f"**Summary:** {r.summary}"]
    lines.append(f"- {len(r.requirements)} requirement(s)")
    lines.append(f"- {len(r.assumptions)} assumption(s)")
    lines.append(f"- {len(r.out_of_scope)} out-of-scope item(s)")
    return lines


def _format_planning(ctx: PipelineContext) -> list[str]:
    if ctx.plan is None:
        return ["No plan produced."]
    p = ctx.plan
    lines = [f"**Approach:** {p.approach}"]
    lines.append(f"- {len(p.steps)} implementation step(s)")
    if p.affected_files:
        lines.append(f"- **Affected files:** {', '.join(p.affected_files)}")
    if p.risks:
        lines.append("- **Risks:**")
        for risk in p.risks:
            lines.append(f"  - {risk}")
    return lines


def _format_test_writing(ctx: PipelineContext) -> list[str]:
    if not ctx.test_files:
        return ["No test files written."]
    lines = [f"Wrote {len(ctx.test_files)} test file(s):"]
    for f in ctx.test_files:
        status = "new" if f.is_new else "modified"
        lines.append(f"- `{f.path}` ({status})")
    return lines


def _format_coding(ctx: PipelineContext) -> list[str]:
    lines: list[str] = []
    if ctx.code_files:
        lines.append(f"Wrote {len(ctx.code_files)} file(s):")
        for f in ctx.code_files:
            status = "new" if f.is_new else "modified"
            lines.append(f"- `{f.path}` ({status})")
    lines.append(f"- **Code iterations:** {ctx.code_iteration}")
    if ctx.test_results:
        latest = ctx.test_results[-1]
        status = "PASSED" if latest.passed else "FAILED"
        lines.append(
            f"- **Test results:** {latest.total} total, "
            f"{latest.failures} failures, {latest.errors} errors ({status})"
        )
    return lines


def _format_review(ctx: PipelineContext) -> list[str]:
    if not ctx.review_findings:
        return ["No review findings."]
    lines = [f"Found {len(ctx.review_findings)} issue(s):"]
    for finding in ctx.review_findings:
        lines.append(f"- [{finding.severity.value.upper()}] `{finding.file}`: {finding.message}")
    return lines


_STEP_FORMATTERS: dict[str, callable] = {
    "detect": _format_detect,
    "requirements": _format_requirements,
    "planning": _format_planning,
    "test_writing": _format_test_writing,
    "coding": _format_coding,
    "review": _format_review,
}
