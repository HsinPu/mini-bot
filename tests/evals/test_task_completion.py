from opensprite.evals.task_completion import evaluate_task_completion_case, run_task_completion_smoke


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
    assert payload["summary"] == {
        "passed_cases": 2,
        "total_cases": 2,
        "passed_checks": 15,
        "total_checks": 15,
    }
    assert {case["id"] for case in payload["cases"]} == {"web_smoke_question", "task_completion_question"}
