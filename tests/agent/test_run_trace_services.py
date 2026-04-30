import asyncio
from types import SimpleNamespace

from opensprite.agent.run_trace import RUN_PART_CONTENT_MAX_CHARS, RunEventSink, RunTraceRecorder, truncate_run_part_content
from opensprite.bus import MessageBus
from opensprite.run_schema import serialize_file_change, serialize_run_artifacts, serialize_run_event, serialize_run_part
from opensprite.storage import MemoryStorage


def test_truncate_run_part_content_bounds_large_payloads():
    long_content = "a" * (RUN_PART_CONTENT_MAX_CHARS + 1000) + "THE-END"

    content, metadata = truncate_run_part_content(long_content)

    assert len(content) <= RUN_PART_CONTENT_MAX_CHARS
    assert "run part content truncated" in content
    assert content.endswith("THE-END")
    assert metadata["content_truncated"] is True
    assert metadata["content_original_len"] == RUN_PART_CONTENT_MAX_CHARS + 1007


def test_run_trace_recorder_persists_bounded_parts():
    async def scenario():
        storage = MemoryStorage()
        recorder = RunTraceRecorder(storage=storage, message_bus_getter=lambda: None)
        await storage.create_run("web:browser-1", "run-1")
        await recorder.add_part(
            "web:browser-1",
            "run-1",
            "tool_result",
            content="a" * (RUN_PART_CONTENT_MAX_CHARS + 1000) + "THE-END",
            tool_name="dummy",
        )
        return await storage.get_run_parts("web:browser-1", "run-1")

    parts = asyncio.run(scenario())

    assert len(parts) == 1
    assert len(parts[0].content) <= RUN_PART_CONTENT_MAX_CHARS
    assert parts[0].content.endswith("THE-END")
    assert parts[0].metadata["content_truncated"] is True


def test_run_event_sink_persists_and_publishes_safe_payloads():
    async def scenario():
        storage = MemoryStorage()
        bus = MessageBus()
        sink = RunEventSink(storage=storage, message_bus_getter=lambda: bus)
        await storage.create_run("web:browser-1", "run-1")
        await sink.emit(
            "web:browser-1",
            "run-1",
            "tool_result",
            {"tool_name": "demo", "value": object()},
            channel="web",
            external_chat_id="browser-1",
        )
        return (
            await storage.get_run_events("web:browser-1", "run-1"),
            await bus.consume_run_event(),
        )

    stored_events, bus_event = asyncio.run(scenario())

    assert len(stored_events) == 1
    assert stored_events[0].event_type == "tool_result"
    assert stored_events[0].payload["tool_name"] == "demo"
    assert isinstance(stored_events[0].payload["value"], str)
    assert bus_event.event_type == "tool_result"
    assert bus_event.payload == stored_events[0].payload
    assert bus_event.channel == "web"
    assert bus_event.external_chat_id == "browser-1"


def test_serialize_run_event_builds_stable_envelope():
    event = SimpleNamespace(
        event_id=42,
        run_id="run-1",
        session_id="web:browser-1",
        event_type="tool_result",
        payload={"tool_name": "demo", "tool_call_id": "call-1", "ok": False, "result_preview": "failed"},
        created_at=12.5,
    )

    payload = serialize_run_event(event)

    assert payload == {
        "schema_version": 1,
        "event_id": 42,
        "run_id": "run-1",
        "session_id": "web:browser-1",
        "event_type": "tool_result",
        "kind": "tool",
        "status": "error",
        "payload": {"tool_name": "demo", "tool_call_id": "call-1", "ok": False, "result_preview": "failed"},
        "artifact": {
            "schema_version": 1,
            "artifact_id": "tool:call-1",
            "artifact_type": "tool",
            "kind": "tool",
            "status": "error",
            "phase": "result",
            "tool_name": "demo",
            "tool_call_id": "call-1",
            "iteration": None,
            "title": "demo",
            "detail": "failed",
        },
        "created_at": 12.5,
    }


def test_serialize_run_part_builds_stable_artifact_shape():
    part = SimpleNamespace(
        part_id=7,
        run_id="run-1",
        session_id="web:browser-1",
        part_type="tool_result",
        tool_name="demo",
        content="failed",
        metadata={"tool_call_id": "call-1", "ok": False, "result_preview": "failed"},
        created_at=13.0,
    )

    payload = serialize_run_part(part)

    assert payload["schema_version"] == 1
    assert payload["part_id"] == 7
    assert payload["kind"] == "tool"
    assert payload["state"] == "error"
    assert payload["metadata"] == {"tool_call_id": "call-1", "ok": False, "result_preview": "failed"}
    assert payload["artifact"]["artifact_id"] == "tool:call-1"
    assert payload["artifact"]["phase"] == "tool_result"
    assert payload["artifact"]["status"] == "error"


def test_serialize_file_change_builds_stable_snapshot_shape():
    change = SimpleNamespace(
        change_id=3,
        run_id="run-1",
        session_id="web:browser-1",
        tool_name="apply_patch",
        path="notes.txt",
        action="modify",
        before_sha256="before",
        after_sha256="after",
        before_content="old",
        after_content="new",
        diff="-old\n+new",
        metadata={"diff_len": 9},
        created_at=14.0,
    )

    payload = serialize_file_change(change)

    assert payload["schema_version"] == 1
    assert payload["change_id"] == 3
    assert payload["kind"] == "file"
    assert payload["state"] == "completed"
    assert payload["path"] == "notes.txt"
    assert payload["before_content"] == "old"
    assert payload["after_content"] == "new"
    assert payload["artifact"] == {
        "schema_version": 1,
        "artifact_id": "file_change:3",
        "artifact_type": "file_change",
        "kind": "file",
        "status": "completed",
        "path": "notes.txt",
        "action": "modify",
        "tool_name": "apply_patch",
        "diff_len": 9,
        "snapshots_available": {"before": True, "after": True},
        "metadata": {"diff_len": 9},
    }


def test_serialize_run_artifacts_merges_tool_event_and_part_by_call_id():
    trace = SimpleNamespace(
        events=[
            SimpleNamespace(
                event_id=1,
                run_id="run-1",
                session_id="web:browser-1",
                event_type="tool_started",
                payload={"tool_name": "demo", "tool_call_id": "call-1", "args_preview": "{}"},
                created_at=10.0,
            ),
            SimpleNamespace(
                event_id=2,
                run_id="run-1",
                session_id="web:browser-1",
                event_type="tool_result",
                payload={"tool_name": "demo", "tool_call_id": "call-1", "ok": True, "result_preview": "done"},
                created_at=11.0,
            ),
        ],
        parts=[
            SimpleNamespace(
                part_id=7,
                run_id="run-1",
                session_id="web:browser-1",
                part_type="tool_result",
                tool_name="demo",
                content="done",
                metadata={"tool_call_id": "call-1", "ok": True, "result_preview": "done"},
                created_at=12.0,
            )
        ],
        file_changes=[],
    )

    artifacts = serialize_run_artifacts(trace)

    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact["artifact_id"] == "tool:call-1"
    assert artifact["kind"] == "tool"
    assert artifact["status"] == "completed"
    assert artifact["phase"] == "tool_result"
    assert artifact["tool_call_id"] == "call-1"
    assert artifact["source"] == "part"
    assert artifact["sources"] == ["event", "part"]
