"""Structured work progress state for multi-step agent turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .completion_gate import CompletionGateResult
from .execution import ExecutionResult
from .task_intent import TaskIntent


_CODING_KINDS = {"debug", "implementation", "refactor", "review"}
_TERMINAL_STATUSES = {"blocked", "complete", "waiting_user"}


@dataclass(frozen=True)
class WorkPlan:
    """Small durable plan derived from the user intent."""

    objective: str
    kind: str
    steps: tuple[str, ...]
    done_criteria: tuple[str, ...]
    long_running: bool
    coding_task: bool
    expects_code_change: bool
    expects_verification: bool

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "objective": self.objective,
            "kind": self.kind,
            "steps": list(self.steps),
            "done_criteria": list(self.done_criteria),
            "long_running": self.long_running,
            "coding_task": self.coding_task,
            "expects_code_change": self.expects_code_change,
            "expects_verification": self.expects_verification,
        }


@dataclass(frozen=True)
class WorkProgressUpdate:
    """One pass worth of structured progress signals."""

    status: str
    pass_index: int
    auto_continue_attempts: int
    progress_signals: tuple[str, ...]
    has_progress: bool
    file_change_count: int
    touched_paths: tuple[str, ...]
    verification_required: bool
    verification_attempted: bool
    verification_passed: bool
    completion_status: str
    completion_reason: str
    next_action: str
    continuation_budget: int

    def to_metadata(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status,
            "pass_index": self.pass_index,
            "auto_continue_attempts": self.auto_continue_attempts,
            "progress_signals": list(self.progress_signals),
            "has_progress": self.has_progress,
            "file_change_count": self.file_change_count,
            "touched_paths": list(self.touched_paths),
            "verification_required": self.verification_required,
            "verification_attempted": self.verification_attempted,
            "verification_passed": self.verification_passed,
            "completion_status": self.completion_status,
            "completion_reason": self.completion_reason,
            "next_action": self.next_action,
            "continuation_budget": self.continuation_budget,
        }


class WorkProgressService:
    """Create a coherent work state from intent, execution, and completion signals."""

    def __init__(self, *, default_continuation_budget: int = 1, long_running_continuation_budget: int = 3):
        self.default_continuation_budget = max(0, default_continuation_budget)
        self.long_running_continuation_budget = max(self.default_continuation_budget, long_running_continuation_budget)

    def create_plan(self, task_intent: TaskIntent) -> WorkPlan | None:
        """Return a plan only for actionable tasks, not casual conversation."""
        if not task_intent.should_seed_active_task:
            return None

        steps = ["understand the request"]
        if task_intent.expects_code_change:
            steps.extend(
                [
                    "inspect relevant code",
                    "make the smallest correct change",
                    "verify the result" if task_intent.expects_verification else "review the result and finalize",
                ]
            )
        elif task_intent.kind == "debug":
            steps.extend(["inspect the relevant context", "identify the root cause", "state the diagnosis or blocker"])
        elif task_intent.kind in {"analysis", "review"}:
            steps.extend(["inspect the relevant context", "collect concrete evidence", "deliver the findings clearly"])
        elif task_intent.long_running:
            steps.extend(["make measurable progress", "verify or summarize remaining work"])
        else:
            steps.append("complete the requested task")

        return WorkPlan(
            objective=task_intent.objective,
            kind=task_intent.kind,
            steps=tuple(steps),
            done_criteria=tuple(task_intent.done_criteria),
            long_running=task_intent.long_running,
            coding_task=task_intent.kind in _CODING_KINDS,
            expects_code_change=task_intent.expects_code_change,
            expects_verification=task_intent.expects_verification,
        )

    def evaluate(
        self,
        *,
        task_intent: TaskIntent,
        completion_result: CompletionGateResult,
        execution_result: ExecutionResult,
        auto_continue_attempts: int,
        pass_index: int,
    ) -> WorkProgressUpdate:
        """Summarize the current pass and choose the next high-level action."""
        signals = self._progress_signals(execution_result)
        continuation_budget = self.continuation_budget(task_intent)
        status = self._status(completion_result)
        return WorkProgressUpdate(
            status=status,
            pass_index=max(1, pass_index),
            auto_continue_attempts=max(0, auto_continue_attempts),
            progress_signals=signals,
            has_progress=bool(signals),
            file_change_count=max(0, execution_result.file_change_count),
            touched_paths=tuple(execution_result.touched_paths),
            verification_required=completion_result.verification_required,
            verification_attempted=completion_result.verification_attempted,
            verification_passed=completion_result.verification_passed,
            completion_status=completion_result.status,
            completion_reason=completion_result.reason,
            next_action=self._next_action(completion_result, has_progress=bool(signals), attempts=auto_continue_attempts, budget=continuation_budget),
            continuation_budget=continuation_budget,
        )

    def continuation_budget(self, task_intent: TaskIntent) -> int:
        if task_intent.long_running or task_intent.kind in _CODING_KINDS:
            return self.long_running_continuation_budget
        return self.default_continuation_budget

    @staticmethod
    def _progress_signals(execution_result: ExecutionResult) -> tuple[str, ...]:
        signals: list[str] = []
        if execution_result.executed_tool_calls > 0:
            signals.append("tool_calls")
        if execution_result.file_change_count > 0:
            signals.append("file_changes")
        if execution_result.verification_attempted:
            signals.append("verification_attempted")
        if execution_result.verification_passed:
            signals.append("verification_passed")
        if execution_result.context_compactions > 0:
            signals.append("context_compaction")
        if execution_result.had_tool_error:
            signals.append("tool_error")
        return tuple(signals)

    @staticmethod
    def _status(completion_result: CompletionGateResult) -> str:
        if completion_result.status in _TERMINAL_STATUSES:
            return completion_result.status
        if completion_result.status == "needs_verification":
            return "verifying"
        return "working"

    @staticmethod
    def _next_action(
        completion_result: CompletionGateResult,
        *,
        has_progress: bool,
        attempts: int,
        budget: int,
    ) -> str:
        if completion_result.status == "complete":
            return "finalize"
        if completion_result.status in {"blocked", "waiting_user"}:
            return completion_result.status
        if attempts >= budget:
            return "stop_budget_exhausted"
        if attempts > 0 and not has_progress:
            return "stop_no_progress"
        if completion_result.status == "needs_verification":
            return "continue_verification"
        return "continue_work"
