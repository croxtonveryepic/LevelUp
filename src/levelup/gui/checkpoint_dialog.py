"""Checkpoint review dialog for approving/revising/rejecting from the GUI."""

from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from levelup.state.manager import StateManager
from levelup.state.models import CheckpointRequestRecord


def format_checkpoint_data(checkpoint_data: str | None) -> str:
    """Format raw checkpoint JSON into readable text."""
    if not checkpoint_data:
        return "(No checkpoint data)"
    try:
        data = json.loads(checkpoint_data)
    except (json.JSONDecodeError, TypeError):
        return checkpoint_data

    lines: list[str] = []
    step_name = data.get("step_name", "unknown")
    lines.append(f"Step: {step_name}\n")

    if "requirements" in data:
        reqs = data["requirements"]
        lines.append(f"Summary: {reqs.get('summary', '')}\n")
        for req in reqs.get("requirements", []):
            lines.append(f"  - [{req.get('id', '?')}] {req.get('description', '')}")
            for ac in req.get("acceptance_criteria", []):
                lines.append(f"    * {ac}")
        if reqs.get("assumptions"):
            lines.append("\nAssumptions:")
            for a in reqs["assumptions"]:
                lines.append(f"  - {a}")
        if reqs.get("out_of_scope"):
            lines.append("\nOut of scope:")
            for o in reqs["out_of_scope"]:
                lines.append(f"  - {o}")

    if "test_files" in data:
        lines.append("Test Files:")
        for tf in data["test_files"]:
            lines.append(f"\n--- {tf.get('path', '?')} ---")
            lines.append(tf.get("content", ""))

    if "code_files" in data:
        lines.append("Implementation Files:")
        for cf in data["code_files"]:
            lines.append(f"\n--- {cf.get('path', '?')} ---")
            lines.append(cf.get("content", ""))

    if "test_results" in data:
        lines.append("\nTest Results:")
        for tr in data["test_results"]:
            status = "PASS" if tr.get("passed") else "FAIL"
            lines.append(f"  {status}: {tr.get('total', 0)} total, {tr.get('failures', 0)} failures")

    if "review_findings" in data:
        lines.append("\nReview Findings:")
        for rf in data["review_findings"]:
            lines.append(
                f"  [{rf.get('severity', '?')}] {rf.get('category', '')}: "
                f"{rf.get('message', '')} ({rf.get('file', '')}:{rf.get('line', '?')})"
            )

    if "message" in data:
        lines.append(data["message"])

    return "\n".join(lines)


class CheckpointDialog(QDialog):
    """Dialog for reviewing and deciding on a checkpoint request."""

    def __init__(
        self,
        checkpoint: CheckpointRequestRecord,
        state_manager: StateManager,
        parent: object | None = None,
    ) -> None:
        super().__init__(parent)  # type: ignore[arg-type]
        self._checkpoint = checkpoint
        self._state_manager = state_manager
        self._decision: str | None = None

        self.setWindowTitle(
            f"Checkpoint: {checkpoint.step_name}  (run {checkpoint.run_id[:12]})"
        )
        self.setMinimumSize(700, 500)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(
            f"<b>Step:</b> {self._checkpoint.step_name} &nbsp; "
            f"<b>Run:</b> {self._checkpoint.run_id[:12]}"
        )
        layout.addWidget(header)

        # Checkpoint content (read-only)
        self._content_view = QTextEdit()
        self._content_view.setReadOnly(True)
        self._content_view.setPlainText(
            format_checkpoint_data(self._checkpoint.checkpoint_data)
        )
        layout.addWidget(self._content_view, stretch=3)

        # Feedback label + text input
        feedback_label = QLabel("Feedback (required for Revise):")
        layout.addWidget(feedback_label)

        self._feedback_input = QPlainTextEdit()
        self._feedback_input.setMaximumHeight(100)
        self._feedback_input.setPlaceholderText("Enter feedback for revision...")
        layout.addWidget(self._feedback_input, stretch=1)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        approve_btn = QPushButton("Approve")
        approve_btn.setObjectName("approveBtn")
        approve_btn.clicked.connect(self._on_approve)
        btn_layout.addWidget(approve_btn)

        revise_btn = QPushButton("Revise")
        revise_btn.setObjectName("reviseBtn")
        revise_btn.clicked.connect(self._on_revise)
        btn_layout.addWidget(revise_btn)

        reject_btn = QPushButton("Reject")
        reject_btn.setObjectName("rejectBtn")
        reject_btn.clicked.connect(self._on_reject)
        btn_layout.addWidget(reject_btn)

        layout.addLayout(btn_layout)

    def _on_approve(self) -> None:
        self._submit("approve", "")

    def _on_revise(self) -> None:
        feedback = self._feedback_input.toPlainText().strip()
        if not feedback:
            QMessageBox.warning(
                self, "Feedback Required",
                "Please enter feedback when requesting a revision.",
            )
            return
        self._submit("revise", feedback)

    def _on_reject(self) -> None:
        reply = QMessageBox.question(
            self, "Confirm Reject",
            "Are you sure you want to reject and abort this pipeline run?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._submit("reject", "")

    def _submit(self, decision: str, feedback: str) -> None:
        assert self._checkpoint.id is not None
        self._state_manager.submit_checkpoint_decision(
            self._checkpoint.id, decision, feedback
        )
        self._decision = decision
        self.accept()
