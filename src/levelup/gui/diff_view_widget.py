"""Diff view widget for displaying git changes from pipeline runs."""

from __future__ import annotations

import html
from pathlib import Path

import git
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from levelup.core.context import PipelineContext, PipelineStatus
from levelup.state.manager import StateManager


# Theme CSS for diff display
_DARK_CSS = """
body {
    color: #CDD6F4;
    background: #181825;
    font-family: Consolas, 'Courier New', monospace;
    padding: 16px;
    line-height: 1.4;
    font-size: 13px;
}
h2, h3 {
    color: #89B4FA;
    margin: 16px 0 8px 0;
}
.commit-info {
    background: #313244;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
}
.diff-stats {
    color: #A6ADC8;
    margin-bottom: 16px;
    font-weight: bold;
}
.diff-file {
    color: #F9E2AF;
    font-weight: bold;
    margin-top: 16px;
}
.diff-hunk {
    color: #89DCEB;
}
.diff-add {
    color: #A6E3A1;
    background: #1e3a1e;
}
.diff-del {
    color: #F38BA8;
    background: #3a1e1e;
}
.diff-context {
    color: #BAC2DE;
}
.error-message {
    color: #F38BA8;
    background: #3a1e1e;
    padding: 12px;
    border-radius: 6px;
    margin: 16px 0;
}
.info-message {
    color: #89B4FA;
    background: #1e2a3a;
    padding: 12px;
    border-radius: 6px;
    margin: 16px 0;
}
"""

_LIGHT_CSS = """
body {
    color: #2E3440;
    background: #FFFFFF;
    font-family: Consolas, 'Courier New', monospace;
    padding: 16px;
    line-height: 1.4;
    font-size: 13px;
}
h2, h3 {
    color: #5E81AC;
    margin: 16px 0 8px 0;
}
.commit-info {
    background: #E5E9F0;
    padding: 12px;
    border-radius: 6px;
    margin-bottom: 16px;
}
.diff-stats {
    color: #4C566A;
    margin-bottom: 16px;
    font-weight: bold;
}
.diff-file {
    color: #D08770;
    font-weight: bold;
    margin-top: 16px;
}
.diff-hunk {
    color: #5E81AC;
}
.diff-add {
    color: #2E7D32;
    background: #e8f5e9;
}
.diff-del {
    color: #C62828;
    background: #ffebee;
}
.diff-context {
    color: #2E3440;
}
.error-message {
    color: #C62828;
    background: #ffebee;
    padding: 12px;
    border-radius: 6px;
    margin: 16px 0;
}
.info-message {
    color: #5E81AC;
    background: #e3f2fd;
    padding: 12px;
    border-radius: 6px;
    margin: 16px 0;
}
"""


# ============================================================================
# Diff Generation Helper Functions
# ============================================================================


def generate_diff(project_path: str, from_sha: str, to_sha: str) -> str:
    """Generate unified diff between two commits.

    Args:
        project_path: Path to git repository
        from_sha: Starting commit SHA
        to_sha: Ending commit SHA

    Returns:
        Unified diff output as string

    Raises:
        git.exc.GitCommandError: If git command fails
        git.exc.InvalidGitRepositoryError: If not a git repo
    """
    try:
        repo = git.Repo(project_path)
        # Generate unified diff
        diff_output = repo.git.diff(from_sha, to_sha)
        return diff_output
    except Exception as e:
        raise


def generate_step_diff(project_path: str, step_sha: str, parent_sha: str) -> str:
    """Generate diff for a specific pipeline step.

    Args:
        project_path: Path to git repository
        step_sha: Commit SHA for the step
        parent_sha: Parent commit SHA (previous step or pre_run_sha)

    Returns:
        Unified diff output as string
    """
    return generate_diff(project_path, parent_sha, step_sha)


def generate_branch_diff(project_path: str, pre_run_sha: str, to_sha: str | None = None) -> str:
    """Generate diff for entire branch from pre_run_sha to HEAD or specified commit.

    Args:
        project_path: Path to git repository
        pre_run_sha: Starting commit SHA (before run began)
        to_sha: Optional ending commit SHA (defaults to HEAD)

    Returns:
        Unified diff output as string
    """
    if to_sha is None:
        repo = git.Repo(project_path)
        to_sha = repo.head.commit.hexsha
    return generate_diff(project_path, pre_run_sha, to_sha)


def get_commit_info(project_path: str, sha: str) -> dict[str, str]:
    """Get commit information (message, author, date).

    Args:
        project_path: Path to git repository
        sha: Commit SHA

    Returns:
        Dict with commit info: message, sha, author, date

    Raises:
        ValueError: If commit SHA is invalid
    """
    try:
        repo = git.Repo(project_path)
        commit = repo.commit(sha)
        return {
            "sha": sha,
            "message": commit.message.strip(),
            "author": str(commit.author),
            "date": commit.committed_datetime.isoformat(),
        }
    except Exception as e:
        raise ValueError(f"Invalid commit SHA: {sha}") from e


def get_parent_sha(project_path: str, sha: str) -> str | None:
    """Get parent commit SHA.

    Args:
        project_path: Path to git repository
        sha: Commit SHA

    Returns:
        Parent commit SHA or None if no parent (first commit)
    """
    repo = git.Repo(project_path)
    commit = repo.commit(sha)
    if commit.parents:
        return commit.parents[0].hexsha
    return None


def get_diff_stats(project_path: str, from_sha: str, to_sha: str | None = None) -> dict[str, int]:
    """Get diff statistics (files changed, insertions, deletions).

    Args:
        project_path: Path to git repository
        from_sha: Starting commit SHA
        to_sha: Optional ending commit SHA (defaults to HEAD)

    Returns:
        Dict with stats: files_changed, insertions, deletions
    """
    try:
        repo = git.Repo(project_path)
        if to_sha is None:
            to_sha = repo.head.commit.hexsha

        if from_sha == to_sha:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}
    except Exception:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}

    try:
        repo = git.Repo(project_path)
        # Get stats using --numstat format
        stats_output = repo.git.diff(from_sha, to_sha, numstat=True)

        if not stats_output:
            return {"files_changed": 0, "insertions": 0, "deletions": 0}

        files_changed = 0
        insertions = 0
        deletions = 0

        for line in stats_output.splitlines():
            if line.strip():
                parts = line.split('\t')
                if len(parts) >= 2:
                    try:
                        add = int(parts[0]) if parts[0] != '-' else 0
                        delete = int(parts[1]) if parts[1] != '-' else 0
                        insertions += add
                        deletions += delete
                        files_changed += 1
                    except ValueError:
                        pass

        return {
            "files_changed": files_changed,
            "insertions": insertions,
            "deletions": deletions,
        }
    except Exception:
        return {"files_changed": 0, "insertions": 0, "deletions": 0}


def find_step_parent(step_name: str, step_commits: dict[str, str], pre_run_sha: str) -> str:
    """Find parent commit SHA for a given step.

    Args:
        step_name: Name of the pipeline step
        step_commits: Dict mapping step names to commit SHAs
        pre_run_sha: Initial commit SHA before run began

    Returns:
        Parent commit SHA for the step
    """
    # Pipeline step order
    step_order = [
        "requirements",
        "planning",
        "test_writing",
        "test_verification",
        "coding",
        "security",
        "review",
    ]

    if step_name not in step_order:
        # Unknown step, try to find any previous step
        for s in reversed(list(step_commits.keys())):
            if s != step_name:
                return step_commits[s]
        return pre_run_sha

    # Find the previous step in order
    step_idx = step_order.index(step_name)
    for i in range(step_idx - 1, -1, -1):
        prev_step = step_order[i]
        if prev_step in step_commits:
            return step_commits[prev_step]

    # No previous step found, use pre_run_sha
    return pre_run_sha


def is_valid_sha(project_path: str, sha: str) -> bool:
    """Check if a commit SHA is valid in the repository.

    Args:
        project_path: Path to git repository
        sha: Commit SHA to check

    Returns:
        True if SHA is valid, False otherwise
    """
    try:
        repo = git.Repo(project_path)
        repo.commit(sha)
        return True
    except Exception:
        return False


def get_branch_head(project_path: str, branch_name: str) -> str:
    """Get HEAD SHA of a branch.

    Args:
        project_path: Path to git repository
        branch_name: Name of the branch

    Returns:
        HEAD commit SHA of the branch
    """
    repo = git.Repo(project_path)
    branch = repo.heads[branch_name]
    return branch.commit.hexsha


def format_diff_html(diff_text: str, theme: str = "dark") -> str:
    """Format diff text as HTML with syntax highlighting.

    Args:
        diff_text: Raw diff output
        theme: Color theme ("dark" or "light")

    Returns:
        HTML-formatted diff
    """
    if not diff_text:
        return '<div class="info-message">No changes to display.</div>'

    # Define colors based on theme
    if theme == "dark":
        colors = {
            "file": "#F9E2AF",
            "hunk": "#89DCEB",
            "add": "#A6E3A1",
            "add_bg": "#1e3a1e",
            "del": "#F38BA8",
            "del_bg": "#3a1e1e",
            "context": "#BAC2DE",
        }
    else:  # light
        colors = {
            "file": "#D08770",
            "hunk": "#5E81AC",
            "add": "#2E7D32",
            "add_bg": "#e8f5e9",
            "del": "#C62828",
            "del_bg": "#ffebee",
            "context": "#2E3440",
        }

    lines = diff_text.splitlines()
    html_lines = []

    for line in lines:
        escaped = html.escape(line)

        if line.startswith('+++') or line.startswith('---'):
            html_lines.append(f'<div class="diff-file" style="color: {colors["file"]}; font-weight: bold;">{escaped}</div>')
        elif line.startswith('@@'):
            html_lines.append(f'<div class="diff-hunk" style="color: {colors["hunk"]};">{escaped}</div>')
        elif line.startswith('+'):
            html_lines.append(f'<div class="diff-add" style="color: {colors["add"]}; background: {colors["add_bg"]};">{escaped}</div>')
        elif line.startswith('-'):
            html_lines.append(f'<div class="diff-del" style="color: {colors["del"]}; background: {colors["del_bg"]};">{escaped}</div>')
        elif line.startswith('diff --git'):
            html_lines.append(f'<div class="diff-file" style="color: {colors["file"]}; font-weight: bold;">{escaped}</div>')
        else:
            html_lines.append(f'<div class="diff-context" style="color: {colors["context"]};">{escaped}</div>')

    return '<pre style="margin: 0; white-space: pre-wrap; word-wrap: break-word;">' + '\n'.join(html_lines) + '</pre>'


def _wrap_html(body: str, theme: str = "dark") -> str:
    """Wrap HTML body with theme CSS."""
    css = _DARK_CSS if theme == "dark" else _LIGHT_CSS
    return f"<!DOCTYPE html><html><head><style>{css}</style></head><body>{body}</body></html>"


# ============================================================================
# DiffViewWidget
# ============================================================================


class DiffViewWidget(QWidget):
    """Widget for displaying git diffs from pipeline runs."""

    back_clicked = pyqtSignal()

    def __init__(
        self,
        run_id: str | None = None,
        step_name: str | None = None,
        state_manager: StateManager | None = None,
        theme: str = "dark",
        project_path: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._run_id = run_id
        self._step_name = step_name
        self._state_manager = state_manager
        self._theme = theme
        self._project_path = project_path
        self._context: PipelineContext | None = None
        self._pre_run_sha: str | None = None
        self._last_diff_text: str = ""
        self._last_diff_title: str = "Diff"

        self._build_ui()

        # Load context and display diff if run_id provided
        if run_id and state_manager:
            self._load_context()
            if self._context:
                self._display_diff()

    def _build_ui(self) -> None:
        """Build the widget UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top bar: back button + title + step selector
        top_bar = QHBoxLayout()

        self._back_btn = QPushButton("\u2190 Back")
        self._back_btn.setObjectName("backBtn")
        self._back_btn.clicked.connect(self.back_clicked.emit)
        top_bar.addWidget(self._back_btn)

        self._title_label = QLabel("Changes")
        self._title_label.setStyleSheet("font-size: 14pt; font-weight: bold;")
        top_bar.addWidget(self._title_label)

        top_bar.addStretch()

        # Step selector
        step_label = QLabel("View:")
        top_bar.addWidget(step_label)

        self._step_selector = QComboBox()
        self._step_selector.setObjectName("stepSelector")
        self._step_selector.setMinimumWidth(200)
        self._step_selector.currentTextChanged.connect(self._on_step_changed)
        top_bar.addWidget(self._step_selector)

        layout.addLayout(top_bar)

        # Diff display browser
        self._browser = QTextBrowser()
        self._browser.setObjectName("diffBrowser")
        self._browser.setOpenExternalLinks(False)
        layout.addWidget(self._browser)

    def _load_context(self) -> None:
        """Load PipelineContext from state manager."""
        if not self._run_id or not self._state_manager:
            # Still populate empty selector if context is None
            self._populate_step_selector()
            return

        try:
            record = self._state_manager.get_run(self._run_id)
            if not record:
                self._show_error("Run not found")
                self._populate_step_selector()
                return

            # Check if context_json is available
            if not record.context_json:
                self._show_info("Run context not yet available for diff view")
                self._populate_step_selector()
                return

            # Deserialize context from JSON
            self._context = PipelineContext.model_validate_json(record.context_json)
            self._pre_run_sha = self._context.pre_run_sha

            # Use project path from context if not provided
            if not self._project_path:
                self._project_path = str(self._context.project_path)

            # Populate step selector
            self._populate_step_selector()

        except Exception as e:
            self._show_error(f"Error loading run context: {e}")
            self._populate_step_selector()

    def _populate_step_selector(self) -> None:
        """Populate the step selector with available steps."""
        self._step_selector.clear()

        # Add "All Changes" option
        self._step_selector.addItem("All Changes", None)

        # Add individual steps
        if self._context and self._context.step_commits:
            for step_name in self._context.step_commits.keys():
                display_name = step_name.replace("_", " ").title()
                self._step_selector.addItem(display_name, step_name)

        # Select current step if specified
        if self._step_name:
            for i in range(self._step_selector.count()):
                if self._step_selector.itemData(i) == self._step_name:
                    self._step_selector.setCurrentIndex(i)
                    break

    def _on_step_changed(self, text: str) -> None:
        """Handle step selector change."""
        idx = self._step_selector.currentIndex()
        if idx >= 0:
            step_data = self._step_selector.itemData(idx)
            self._step_name = step_data
            self._display_diff()

    def _display_diff(self) -> None:
        """Display the appropriate diff based on current selection."""
        if not self._context:
            # Don't show error if not initialized yet
            return

        if not self._project_path:
            self._show_error("No project path available")
            return

        if not self._pre_run_sha:
            self._show_info("No git tracking available for this run")
            return

        try:
            # Check if project path is a valid git repo
            try:
                repo = git.Repo(self._project_path)
            except git.exc.InvalidGitRepositoryError:
                self._show_error("Project path is not a git repository")
                return

            # Generate appropriate diff
            if self._step_name is None:
                # All changes view
                self._display_branch_diff()
            else:
                # Per-step view
                self._display_step_diff()

        except Exception as e:
            self._show_error(f"Error generating diff: {e}")

    def _display_step_diff(self) -> None:
        """Display diff for a specific step."""
        if not self._step_name or not self._context:
            return

        # Update title
        step_title = self._step_name.replace('_', ' ').title()
        self._title_label.setText(f"Changes - {step_title}")

        # Get step commit SHA
        if self._step_name not in self._context.step_commits:
            self._show_error(f"No commit found for step: {self._step_name}")
            return

        step_sha = self._context.step_commits[self._step_name]

        # Validate SHA
        if not is_valid_sha(self._project_path, step_sha):  # type: ignore
            self._show_error(f"Commit not found: {step_sha}")
            return

        # Find parent SHA
        parent_sha = find_step_parent(
            self._step_name,
            self._context.step_commits,
            self._pre_run_sha or ""
        )

        if not is_valid_sha(self._project_path, parent_sha):  # type: ignore
            self._show_error(f"Parent commit not found: {parent_sha}")
            return

        # Generate diff
        try:
            diff_text = generate_step_diff(self._project_path, step_sha, parent_sha)  # type: ignore

            # Get commit info
            commit_info = get_commit_info(self._project_path, step_sha)  # type: ignore

            # Build HTML
            html_parts = []
            html_parts.append(f"<h2>{step_title}</h2>")
            html_parts.append('<div class="commit-info">')
            html_parts.append(f"<strong>Commit:</strong> {commit_info['sha'][:8]}<br>")
            html_parts.append(f"<strong>Message:</strong> {html.escape(commit_info['message'])}<br>")
            html_parts.append("</div>")

            if diff_text:
                html_parts.append(format_diff_html(diff_text, self._theme))
            else:
                html_parts.append('<div class="info-message">No changes in this step.</div>')

            full_html = _wrap_html('\n'.join(html_parts), self._theme)
            self._browser.setHtml(full_html)

        except Exception as e:
            self._show_error(f"Error generating step diff: {e}")

    def _display_branch_diff(self) -> None:
        """Display diff for entire branch."""
        if not self._context or not self._pre_run_sha:
            return

        # Update title
        self._title_label.setText("Changes - All")

        try:
            # Get current HEAD
            repo = git.Repo(self._project_path)

            # Try to find the run's branch if it still exists
            branch_name = f"levelup/{self._run_id}"
            try:
                branch = repo.heads[branch_name]
                to_sha = branch.commit.hexsha
            except (IndexError, AttributeError):
                # Branch might not exist, use current HEAD
                to_sha = repo.head.commit.hexsha

            # Generate diff
            diff_text = generate_branch_diff(self._project_path, self._pre_run_sha, to_sha)  # type: ignore

            # Get stats
            stats = get_diff_stats(self._project_path, self._pre_run_sha, to_sha)  # type: ignore

            # Build HTML
            html_parts = []
            html_parts.append("<h2>All Changes</h2>")
            html_parts.append('<div class="diff-stats">')
            html_parts.append(f"{stats['files_changed']} file(s) changed, ")
            html_parts.append(f"{stats['insertions']} insertion(s)(+), ")
            html_parts.append(f"{stats['deletions']} deletion(s)(-)")
            html_parts.append("</div>")

            if diff_text:
                html_parts.append(format_diff_html(diff_text, self._theme))
            else:
                html_parts.append('<div class="info-message">No changes to display.</div>')

            full_html = _wrap_html('\n'.join(html_parts), self._theme)
            self._browser.setHtml(full_html)

        except Exception as e:
            self._show_error(f"Error generating branch diff: {e}")

    def _show_error(self, message: str) -> None:
        """Show an error message in the browser."""
        html_content = f'<div class="error-message"><strong>Error:</strong> {html.escape(message)}</div>'
        full_html = _wrap_html(html_content, self._theme)
        self._browser.setHtml(full_html)

    def _show_info(self, message: str) -> None:
        """Show an info message in the browser."""
        html_content = f'<div class="info-message">{html.escape(message)}</div>'
        full_html = _wrap_html(html_content, self._theme)
        self._browser.setHtml(full_html)

    def set_diff_content(self, diff_text: str, title: str = "Diff") -> None:
        """Set raw diff content for display (for testing)."""
        # Store for theme updates
        self._last_diff_text = diff_text
        self._last_diff_title = title

        html_parts = []
        html_parts.append(f"<h2>{html.escape(title)}</h2>")
        if diff_text:
            html_parts.append(format_diff_html(diff_text, self._theme))
        else:
            html_parts.append('<div class="info-message">No changes to display.</div>')

        full_html = _wrap_html('\n'.join(html_parts), self._theme)
        self._browser.setHtml(full_html)

    def update_theme(self, theme: str) -> None:
        """Update the widget theme."""
        self._theme = theme
        # Re-display current diff with new theme
        if self._context:
            self._display_diff()
        elif hasattr(self, '_last_diff_text'):
            # Re-display raw diff content with new theme
            self.set_diff_content(self._last_diff_text, self._last_diff_title)

    def refresh(self) -> None:
        """Refresh the diff view (reload context and redisplay)."""
        if self._run_id and self._state_manager:
            self._load_context()
            self._display_diff()

    def update_diff(self) -> None:
        """Alias for refresh() for compatibility."""
        self.refresh()
