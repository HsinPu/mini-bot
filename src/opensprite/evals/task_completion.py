"""Deterministic task-completion evaluation helpers."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from ..bus.message import UserMessage


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

TASK_COMPLETION_LIVE_CASES: tuple[dict[str, Any], ...] = (
    {
        "id": "literal_instruction",
        "label": "Literal instruction answer",
        "prompt": "請只回覆這三個英文詞，且不要加入其他文字：alpha beta gamma",
        "expected_completion_status": "complete",
        "must_include": ("alpha", "beta", "gamma"),
        "must_not_include": ("抱歉", "sorry", "無法"),
        "require_no_tool_error": True,
        "require_run_trace": True,
        "max_response_chars": 120,
    },
)


def run_task_completion_smoke() -> dict[str, Any]:
    """Run deterministic task-completion smoke cases without calling an LLM."""
    cases = [evaluate_task_completion_case(case, case.get("sample_result")) for case in TASK_COMPLETION_SMOKE_CASES]
    return _summarize_cases(cases, live=False)


async def run_live_task_completion_eval(
    *,
    agent: Any,
    storage: Any,
    channel: str = "web",
    timeout_seconds: float = 45.0,
) -> dict[str, Any]:
    """Run fixed task-completion cases against the active agent."""
    cases = []
    for case in TASK_COMPLETION_LIVE_CASES:
        cases.append(
            await _run_live_task_completion_case(
                case,
                agent=agent,
                storage=storage,
                channel=channel,
                timeout_seconds=timeout_seconds,
            )
        )
    return _summarize_cases(cases, live=True)


def _summarize_cases(cases: list[dict[str, Any]], *, live: bool) -> dict[str, Any]:
    total_checks = sum(len(case["checks"]) for case in cases)
    passed_checks = sum(1 for case in cases for check in case["checks"] if check["ok"])
    passed_cases = sum(1 for case in cases if case["ok"])

    return {
        "ok": all(case["ok"] for case in cases),
        "live": live,
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

    if _bool(case.get("require_run_trace", False)):
        run_id = _string(result.get("run_id"))
        checks.append(
            _check(
                "run_trace",
                "Run trace is available",
                bool(run_id),
                f"Observed run {run_id}." if run_id else "Run trace was missing.",
            )
        )

    max_response_chars = _optional_int(case.get("max_response_chars"))
    if max_response_chars is not None:
        response_len = len(response_text.strip())
        checks.append(
            _check(
                "max_response_chars",
                f"Response is at most {max_response_chars} characters",
                response_len <= max_response_chars,
                f"Observed {response_len} response character(s).",
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
        "session_id": _string(result.get("session_id")),
        "run_id": _string(result.get("run_id")),
        "run_status": _string(result.get("run_status")),
        "error": _string(result.get("error")),
        "response_preview": _preview(response_text),
        "checks": checks,
    }


async def _run_live_task_completion_case(
    case: Mapping[str, Any],
    *,
    agent: Any,
    storage: Any,
    channel: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    case_id = _string(case.get("id"), default="case")
    external_chat_id = f"eval-task-completion-{case_id}-{uuid4().hex[:12]}"
    session_id = f"{channel}:{external_chat_id}"
    response_text = ""
    error = ""

    try:
        response = await asyncio.wait_for(
            agent.process(
                UserMessage(
                    text=_string(case.get("prompt")),
                    channel=channel,
                    external_chat_id=external_chat_id,
                    session_id=session_id,
                    sender_id="task-completion-eval",
                    sender_name="Task completion eval",
                    metadata={
                        "eval_kind": "task_completion",
                        "eval_case_id": case_id,
                    },
                )
            ),
            timeout=max(1.0, float(timeout_seconds or 1.0)),
        )
        response_text = _string(getattr(response, "text", ""))
    except asyncio.TimeoutError:
        error = f"Timed out after {timeout_seconds:.0f} seconds."
    except Exception as exc:  # pragma: no cover - exercised through integration error paths.
        error = f"{type(exc).__name__}: {exc}"

    result = await _live_result_from_storage(storage, session_id=session_id, response_text=response_text, error=error)
    evaluated = evaluate_task_completion_case(case, result)
    evaluated["live"] = True
    return evaluated


async def _live_result_from_storage(
    storage: Any,
    *,
    session_id: str,
    response_text: str,
    error: str,
) -> dict[str, Any]:
    run = None
    trace = None
    get_latest_run = getattr(storage, "get_latest_run", None)
    if callable(get_latest_run):
        run = await get_latest_run(session_id)
    if run is None:
        runs = await storage.get_runs(session_id, limit=1)
        run = runs[0] if runs else None
    if run is not None:
        get_run_trace = getattr(storage, "get_run_trace", None)
        trace = await get_run_trace(session_id, run.run_id) if callable(get_run_trace) else None

    events = list(getattr(trace, "events", []) or [])
    completion_payload = _latest_event_payload(events, "completion_gate.evaluated") or {}
    terminal_payload = (
        _latest_event_payload(events, "run_finished")
        or _latest_event_payload(events, "run_failed")
        or _latest_event_payload(events, "run_cancelled")
        or {}
    )
    run_metadata = dict(getattr(run, "metadata", {}) or {}) if run is not None else {}
    return {
        "session_id": session_id,
        "run_id": getattr(run, "run_id", "") if run is not None else "",
        "run_status": getattr(run, "status", "") if run is not None else "",
        "response_text": response_text,
        "completion_status": completion_payload.get("status") or "",
        "had_tool_error": _bool(run_metadata.get("had_tool_error")) or _bool(terminal_payload.get("had_tool_error")),
        "error": error,
    }


def _latest_event_payload(events: Sequence[Any], event_type: str) -> dict[str, Any] | None:
    for event in reversed(events):
        if getattr(event, "event_type", None) == event_type:
            payload = getattr(event, "payload", None)
            return dict(payload) if isinstance(payload, Mapping) else {}
    return None


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


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


__all__ = [
    "TASK_COMPLETION_LIVE_CASES",
    "TASK_COMPLETION_SMOKE_CASES",
    "evaluate_task_completion_case",
    "run_live_task_completion_eval",
    "run_task_completion_smoke",
]
