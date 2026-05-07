import asyncio

from opensprite.bus.message import AssistantMessage
from opensprite.evals.task_completion import (
    evaluate_task_completion_case,
    run_live_task_completion_eval,
    run_task_completion_smoke,
)
from opensprite.storage import MemoryStorage


def test_task_completion_case_passes_required_checks():
    payload = evaluate_task_completion_case(
        {
            "id": "answer",
            "label": "Answer case",
            "prompt": "How do I run the web smoke check?",
            "expected_completion_status": "complete",
            "must_include": ["apps/web", "npm run test:smoke"],
            "must_not_include": ["Playwright"],
            "require_no_tool_error": True,
        },
        {
            "response_text": "Run npm run test:smoke from apps/web.",
            "completion_status": "complete",
            "had_tool_error": False,
        },
    )

    assert payload["ok"] is True
    assert payload["score"] == {"passed": 6, "total": 6}
    assert all(check["ok"] for check in payload["checks"])


def test_task_completion_case_reports_failed_checks():
    payload = evaluate_task_completion_case(
        {
            "id": "answer",
            "expected_completion_status": "complete",
            "must_include": ["required fact"],
            "must_not_include": ["forbidden claim"],
            "require_no_tool_error": True,
        },
        {
            "response_text": "This includes a forbidden claim.",
            "completion_status": "incomplete",
            "had_tool_error": True,
        },
    )

    failed_check_ids = {check["id"] for check in payload["checks"] if not check["ok"]}
    assert payload["ok"] is False
    assert failed_check_ids == {
        "completion_status",
        "tool_errors",
        "must_include_required_fact",
        "must_not_include_forbidden_claim",
    }


def test_task_completion_smoke_runs_fixed_cases():
    payload = run_task_completion_smoke()

    assert payload["ok"] is True
    assert payload["live"] is False
    assert payload["summary"] == {
        "passed_cases": 2,
        "total_cases": 2,
        "passed_checks": 15,
        "total_checks": 15,
    }
    assert {case["id"] for case in payload["cases"]} == {"web_smoke_question", "task_completion_question"}


def test_live_task_completion_eval_scores_agent_result():
    asyncio.run(_run_live_task_completion_eval_scores_agent_result())


async def _run_live_task_completion_eval_scores_agent_result():
    storage = MemoryStorage()

    class LiveEvalAgent:
        def __init__(self):
            self.storage = storage
            self.seen_messages = []

        async def process(self, user_message):
            self.seen_messages.append(user_message)
            run_id = "run-live"
            await storage.create_run(user_message.session_id, run_id, status="running", created_at=1.0)
            await storage.add_run_event(
                user_message.session_id,
                run_id,
                "completion_gate.evaluated",
                payload={"status": "complete", "reason": "test"},
                created_at=2.0,
            )
            await storage.add_run_event(
                user_message.session_id,
                run_id,
                "run_finished",
                payload={"status": "completed", "had_tool_error": False},
                created_at=3.0,
            )
            await storage.update_run_status(
                user_message.session_id,
                run_id,
                "completed",
                metadata={"had_tool_error": False},
                finished_at=3.0,
            )
            return AssistantMessage(
                text="alpha beta gamma",
                channel=user_message.channel,
                external_chat_id=user_message.external_chat_id,
                session_id=user_message.session_id,
            )

    agent = LiveEvalAgent()
    payload = await run_live_task_completion_eval(agent=agent, storage=storage, channel="web", timeout_seconds=1)

    assert payload["ok"] is True
    assert payload["live"] is True
    assert payload["summary"]["passed_cases"] == payload["summary"]["total_cases"] == 1
    assert payload["summary"]["passed_checks"] == payload["summary"]["total_checks"]
    assert agent.seen_messages[0].metadata == {
        "eval_kind": "task_completion",
        "eval_case_id": "literal_instruction",
    }
    [case] = payload["cases"]
    assert case["id"] == "literal_instruction"
    assert case["run_id"] == "run-live"
    assert case["completion_status"] == "complete"
    assert case["response_preview"] == "alpha beta gamma"
