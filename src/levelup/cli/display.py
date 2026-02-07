"""Rich output helpers: panels, tables, syntax highlighting, spinners."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from levelup import __version__

if TYPE_CHECKING:
    from levelup.core.context import (
        FileChange,
        PipelineContext,
        Requirements,
        ReviewFinding,
        SecurityFinding,
        TestResult,
    )
    from levelup.detection.detector import ProjectInfo

console = Console()


def get_version_string() -> str:
    """Return a version string like 'levelup 0.1.0 (commit abc1234, clean)'."""
    base = f"levelup {__version__}"
    try:
        import git

        project_root = Path(__file__).resolve().parents[3]
        repo = git.Repo(project_root)
        sha7 = repo.head.commit.hexsha[:7]
        state = "dirty" if repo.is_dirty() else "clean"
        return f"{base} (commit {sha7}, {state})"
    except Exception:
        return base


def print_banner() -> None:
    """Print the LevelUp banner."""
    version_line = f"[dim]{get_version_string()}[/dim]"
    console.print(
        Panel(
            "[bold cyan]LevelUp[/bold cyan] - AI-Powered TDD Development Tool\n"
            + version_line,
            border_style="cyan",
        )
    )


def print_project_info(info: ProjectInfo) -> None:
    """Display detected project information."""
    table = Table(title="Project Detection", border_style="blue")
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Language", info.language or "[dim]not detected[/dim]")
    table.add_row("Framework", info.framework or "[dim]not detected[/dim]")
    table.add_row("Test Runner", info.test_runner or "[dim]not detected[/dim]")
    table.add_row("Test Command", info.test_command or "[dim]not detected[/dim]")
    console.print(table)


def print_requirements(requirements: Requirements) -> None:
    """Display structured requirements."""
    console.print(Panel(f"[bold]{requirements.summary}[/bold]", title="Requirements Summary"))

    if requirements.requirements:
        table = Table(title="Requirements", border_style="green")
        table.add_column("#", style="dim")
        table.add_column("Description")
        table.add_column("Acceptance Criteria")
        for i, req in enumerate(requirements.requirements, 1):
            criteria = "\n".join(f"- {c}" for c in req.acceptance_criteria) or "-"
            table.add_row(str(i), req.description, criteria)
        console.print(table)

    if requirements.assumptions:
        console.print(
            Panel("\n".join(f"- {a}" for a in requirements.assumptions), title="Assumptions")
        )

    if requirements.out_of_scope:
        console.print(
            Panel("\n".join(f"- {o}" for o in requirements.out_of_scope), title="Out of Scope")
        )


def print_file_changes(changes: list[FileChange], title: str = "File Changes") -> None:
    """Display file changes with syntax highlighting."""
    for change in changes:
        # Guess language from extension
        ext = change.path.rsplit(".", 1)[-1] if "." in change.path else ""
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "rs": "rust",
            "go": "go",
            "rb": "ruby",
            "java": "java",
        }
        lang = lang_map.get(ext, ext)

        label = "[green]NEW[/green]" if change.is_new else "[yellow]MODIFIED[/yellow]"
        console.print(f"\n{label} {change.path}")
        syntax = Syntax(change.content, lang, theme="monokai", line_numbers=True)
        console.print(syntax)


def print_test_results(results: list[TestResult]) -> None:
    """Display test results."""
    for result in results:
        status = "[green]PASSED[/green]" if result.passed else "[red]FAILED[/red]"
        console.print(
            Panel(
                f"Status: {status}\n"
                f"Total: {result.total} | Failures: {result.failures} | Errors: {result.errors}\n"
                f"Command: [dim]{result.command}[/dim]",
                title="Test Results",
                border_style="green" if result.passed else "red",
            )
        )


def print_security_findings(findings: list) -> None:
    """Display security findings in a formatted table."""
    from levelup.core.context import SecurityFinding

    if not findings:
        console.print("[green]✓ No security issues found[/green]")
        return

    table = Table(title="Security Findings", border_style="red")
    table.add_column("Severity", style="bold", width=10)
    table.add_column("Type", width=20)
    table.add_column("Location", width=30)
    table.add_column("Description", width=40)
    table.add_column("Status", width=15)

    severity_colors = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "critical": "bold red",
    }

    for f in findings:
        color = severity_colors.get(f.severity.value, "white")
        location = f.file
        if f.line:
            location += f":{f.line}"

        status = ""
        if f.patch_applied:
            status = "[green]✓ Patched[/green]"
        elif f.requires_manual_fix:
            status = "[red]⚠ Manual Fix Needed[/red]"
        else:
            status = "[yellow]Review Needed[/yellow]"

        vuln_type = f.vulnerability_type
        if f.cwe_id:
            vuln_type += f" ({f.cwe_id})"

        table.add_row(
            f"[{color}]{f.severity.value.upper()}[/{color}]",
            vuln_type,
            location,
            f.description[:80] + ("..." if len(f.description) > 80 else ""),
            status,
        )

    console.print(table)

    # Show recommendations for manual fix items
    manual_fixes = [f for f in findings if f.requires_manual_fix]
    if manual_fixes:
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for f in manual_fixes:
            console.print(f"• {f.file}:{f.line or '?'} - {f.recommendation}")


def print_review_findings(findings: list[ReviewFinding]) -> None:
    """Display review findings."""
    if not findings:
        console.print("[green]No issues found.[/green]")
        return

    table = Table(title="Review Findings", border_style="yellow")
    table.add_column("Severity", style="bold")
    table.add_column("Category")
    table.add_column("File")
    table.add_column("Message")
    table.add_column("Suggestion")

    severity_colors = {
        "info": "blue",
        "warning": "yellow",
        "error": "red",
        "critical": "bold red",
    }
    for f in findings:
        color = severity_colors.get(f.severity.value, "white")
        location = f.file
        if f.line:
            location += f":{f.line}"
        table.add_row(
            f"[{color}]{f.severity.value.upper()}[/{color}]",
            f.category,
            location,
            f.message,
            f.suggestion or "-",
        )
    console.print(table)


def print_pipeline_summary(ctx: PipelineContext) -> None:
    """Display final pipeline summary."""
    console.print(Panel("[bold green]Pipeline Complete[/bold green]", border_style="green"))

    table = Table(border_style="green")
    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_row("Status", ctx.status.value)
    table.add_row("Test files written", str(len(ctx.test_files)))
    table.add_row("Code files written", str(len(ctx.code_files)))
    table.add_row("Code iterations", str(ctx.code_iteration))
    if ctx.test_results:
        last = ctx.test_results[-1]
        table.add_row(
            "Final tests",
            f"{'PASSED' if last.passed else 'FAILED'} ({last.total} tests)",
        )
    # Security findings
    if ctx.security_findings:
        from levelup.core.context import Severity

        critical = len([f for f in ctx.security_findings if f.severity == Severity.CRITICAL])
        error = len([f for f in ctx.security_findings if f.severity == Severity.ERROR])
        warning = len([f for f in ctx.security_findings if f.severity == Severity.WARNING])

        security_summary = f"{critical} critical, {error} error, {warning} warning"
        table.add_row("Security findings", security_summary)

        if ctx.security_patches_applied > 0:
            table.add_row("Security patches applied", str(ctx.security_patches_applied))

    table.add_row("Review findings", str(len(ctx.review_findings)))

    # Cost/token summary
    if ctx.total_cost_usd > 0:
        table.add_row("Total cost", f"${ctx.total_cost_usd:.4f}")
    if ctx.step_usage:
        total_input = sum(u.input_tokens for u in ctx.step_usage.values())
        total_output = sum(u.output_tokens for u in ctx.step_usage.values())
        if total_input or total_output:
            table.add_row("Total tokens", f"{total_input + total_output:,} ({total_input:,} in / {total_output:,} out)")

    console.print(table)

    # Per-step cost breakdown
    if ctx.step_usage:
        cost_table = Table(title="Cost Breakdown", border_style="dim")
        cost_table.add_column("Step", style="bold")
        cost_table.add_column("Cost", justify="right")
        cost_table.add_column("Tokens", justify="right")
        cost_table.add_column("Duration", justify="right")
        cost_table.add_column("Turns", justify="right")
        for step_name, usage in ctx.step_usage.items():
            cost_str = f"${usage.cost_usd:.4f}" if usage.cost_usd else "-"
            tokens_str = f"{usage.input_tokens + usage.output_tokens:,}" if (usage.input_tokens or usage.output_tokens) else "-"
            dur_str = f"{usage.duration_ms / 1000:.1f}s" if usage.duration_ms else "-"
            cost_table.add_row(step_name, cost_str, tokens_str, dur_str, str(usage.num_turns))
        console.print(cost_table)


def print_step_header(step_name: str, description: str) -> None:
    """Print a step header."""
    console.print(f"\n[bold cyan]>>> {step_name}[/bold cyan]: {description}")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]{message}[/bold green]")
