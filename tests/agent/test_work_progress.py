from opensprite.agent.completion_gate import CompletionGateResult
from opensprite.agent.execution import ExecutionResult
from opensprite.agent.task_intent import TaskIntentService
from opensprite.agent.work_progress import WorkProgressService


def test_work_progress_creates_coding_plan_from_intent():
    intent = TaskIntentService().classify("Please implement the feature and run tests.")

    plan = WorkProgressService().create_plan(intent)

    assert plan is not None
    assert plan.coding_task is True
    assert plan.long_running is True
    assert plan.expects_code_change is True
    assert plan.expects_verification is True
    assert plan.steps == (
        "understand the request",
        "inspect relevant code",
        "make the smallest correct change",
        "verify the result",
    )
    assert "relevant tests or checks pass" in plan.done_criteria[2]


def test_work_progress_tracks_verification_and_next_action():
    intent = TaskIntentService().classify("Please refactor the agent and run tests.")
    completion = CompletionGateResult(
        status="needs_verification",
        reason="required verification was not recorded",
        verification_required=True,
    )

    update = WorkProgressService().evaluate(
        task_intent=intent,
        completion_result=completion,
        execution_result=ExecutionResult(
            content="Implemented.",
            executed_tool_calls=1,
            file_change_count=1,
            touched_paths=("src/agent.py",),
        ),
        auto_continue_attempts=0,
        pass_index=1,
    )

    assert update.status == "verifying"
    assert update.has_progress is True
    assert update.progress_signals == ("tool_calls", "file_changes")
    assert update.file_change_count == 1
    assert update.touched_paths == ("src/agent.py",)
    assert update.next_action == "continue_verification"
    assert update.continuation_budget == 3


def test_work_progress_stops_repeated_continuation_without_progress():
    intent = TaskIntentService().classify("Please refactor the agent and run tests.")
    completion = CompletionGateResult(status="needs_verification", reason="required verification was not recorded")

    update = WorkProgressService().evaluate(
        task_intent=intent,
        completion_result=completion,
        execution_result=ExecutionResult(content="Still done."),
        auto_continue_attempts=1,
        pass_index=2,
    )

    assert update.has_progress is False
    assert update.next_action == "stop_no_progress"
