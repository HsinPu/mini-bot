"""Deterministic task-completion evaluation helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any


_RESPONSE_PREVIEW_CHARS = 240


TASK_COMPLETION_SMOKE_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "web_smoke_question",
        "label": "Web smoke check answer",
        "prompt": "OpenSprite 的 web smoke check 怎麼跑？",
        "expected_completion_status": "complete",
        "must_include": ("apps/web", "npm run test:smoke", "smoke check"),
        "must_not_include": ("Playwright", "Vitest"),
        "require_no_tool_error": True,
        "sample_result": {
            "response_text": "在 apps/web 執行 npm run test:smoke；這是 smoke check，不是完整前端測試。",
            "completion_status": "complete",
            "had_tool_error": False,
        },
    },
    {
        "id": "task_completion_question",
        "label": "Task completion criteria answer",
        "prompt": "如何小規模測試 LLM 是否完成使用者任務？",
        "expected_completion_status": "complete",
        "must_include": ("completion_gate", "final response", "must_include"),
        "must_not_include": ("只要有回答就一定正確",),
        "require_no_tool_error": True,
        "sample_result": {
            "response_text": (
                "小規模可以用固定 case：送 prompt 後讀 final response 和 completion_gate，"
                "再用 must_include / must_not_include 與 tool error 檢查打 pass/fail。"
            ),
            "completion_status": "complete",
            "had_tool_error": False,
        },
    },
)


def run_task_completion_smoke() -> dict[str, Any]:
    """Run deterministic task-completion smoke cases without calling an LLM."""
    cases = [evaluate_task_completion_case(case, case.get("sample_result")) for case in TASK_COMPLETION_SMOKE_CASES]
    total_checks = sum(len(case["checks"]) for case in cases)
    passed_checks = sum(1 for case in cases for check in case["checks"] if check["ok"])
    passed_cases = sum(1 for case in cases if case["ok"])

    return {
        "ok": all(case["ok"] for case in cases),
        "cases": cases,
        "summary": {
            "passed_cases": passed_cases,
            "total_cases": len(cases),
            "passed_checks": passed_checks,
            "total_checks": total_checks,
        },
    }


def evaluate_task_completion_case(case: Mapping[str, Any], result: Mapping[str, Any] | None) -> dict[str, Any]:
    """Evaluate one task-completion case against a captured run result."""
    result = result or {}
    case_id = _string(case.get("id"), default="case")
    response_text = _string(result.get("response_text"))
    completion_status = _string(result.get("completion_status") or result.get("status")).lower()
    expected_status = _string(case.get("expected_completion_status")).lower()
    had_tool_error = _bool(result.get("had_tool_error"))
    require_no_tool_error = _bool(case.get("require_no_tool_error", True))

    checks: list[dict[str, Any]] = []
    checks.append(
        _check(
            "response_present",
            "Final response is present",
            bool(response_text.strip()),
            f"Observed {len(response_text.strip())} response character(s).",
        )
    )

    if expected_status:
        checks.append(
            _check(
                "completion_status",
                "Completion gate status matches",
                completion_status == expected_status,
                f"Expected {expected_status or '-'}, observed {completion_status or '-'}.",
            )
        )

    if require_no_tool_error:
        checks.append(
            _check(
                "tool_errors",
                "No tool error was reported",
                not had_tool_error,
                "Tool errors were reported." if had_tool_error else "No tool errors reported.",
            )
        )

    for phrase in _string_sequence(case.get("must_include")):
        found = _contains(response_text, phrase)
        checks.append(
            _check(
                f"must_include_{_slug(phrase)}",
                f"Response includes `{phrase}`",
                found,
                "Required phrase was found." if found else "Required phrase was missing.",
            )
        )

    for phrase in _string_sequence(case.get("must_not_include")):
        found = _contains(response_text, phrase)
        checks.append(
            _check(
                f"must_not_include_{_slug(phrase)}",
                f"Response excludes `{phrase}`",
                not found,
                "Forbidden phrase was found." if found else "Forbidden phrase was absent.",
            )
        )

    passed_checks = sum(1 for check in checks if check["ok"])
    return {
        "id": case_id,
        "label": _string(case.get("label"), default=case_id),
        "prompt": _string(case.get("prompt")),
        "ok": passed_checks == len(checks),
        "score": {"passed": passed_checks, "total": len(checks)},
        "summary": f"{passed_checks}/{len(checks)} checks passed.",
        "completion_status": completion_status,
        "had_tool_error": had_tool_error,
        "response_preview": _preview(response_text),
        "checks": checks,
    }


def _check(check_id: str, label: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"id": check_id, "label": label, "ok": bool(ok), "detail": detail}


def _contains(text: str, phrase: str) -> bool:
    return _normalize(phrase) in _normalize(text)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _preview(text: str) -> str:
    value = str(text or "").strip()
    if len(value) <= _RESPONSE_PREVIEW_CHARS:
        return value
    return f"{value[: _RESPONSE_PREVIEW_CHARS - 1]}..."


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "_", _normalize(text)).strip("_")
    return value or "phrase"


def _string(value: Any, *, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _string_sequence(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (_string(value),) if _string(value) else ()
    if isinstance(value, Sequence) and not isinstance(value, bytes):
        return tuple(text for text in (_string(item) for item in value) if text)
    return ()


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


__all__ = ["TASK_COMPLETION_SMOKE_CASES", "evaluate_task_completion_case", "run_task_completion_smoke"]
