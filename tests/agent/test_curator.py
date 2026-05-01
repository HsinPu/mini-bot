import asyncio

from opensprite.agent.curator import CuratorService
from opensprite.agent.execution import ExecutionResult


def test_curator_service_emits_summary_for_changed_jobs():
    async def scenario():
        state = {
            "memory": "",
            "recent_summary": "",
            "user_profile": "",
            "active_task": "",
            "skills": "",
        }
        events = []

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            events.append((session_id, run_id, event_type, payload, channel, external_chat_id))

        async def update_memory(_session_id):
            state["memory"] = "Remember this"

        async def update_skills(_session_id):
            state["skills"] = "skill-content"

        async def noop(_session_id):
            return None

        service = CuratorService(
            maybe_consolidate_memory=update_memory,
            maybe_update_recent_summary=noop,
            maybe_update_user_profile=noop,
            maybe_update_active_task=noop,
            run_skill_review=update_skills,
            should_run_skill_review=lambda result: result.executed_tool_calls >= 2,
            read_memory_snapshot=lambda _session_id: state["memory"],
            read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
            read_user_profile_snapshot=lambda _session_id: state["user_profile"],
            read_active_task_snapshot=lambda _session_id: state["active_task"],
            read_skill_snapshot=lambda _session_id: state["skills"],
            emit_run_event=emit_run_event,
        )

        service.schedule_after_turn(
            session_id="web:browser-1",
            run_id="run-1",
            channel="web",
            external_chat_id="browser-1",
            result=ExecutionResult(content="done", executed_tool_calls=3),
        )
        await service.wait()
        return events

    events = asyncio.run(scenario())

    assert [event[2] for event in events] == [
        "curator.started",
        "curator.job.started",
        "curator.job.completed",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.completed",
        "curator.completed",
    ]
    assert events[-1][3]["changed"] == ["memory", "skills"]
    assert events[-1][3]["summary"] == "Updated memory and skills."


def test_curator_service_emits_no_change_curator_trace():
    async def scenario():
        state = {"memory": "stable", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        events = []

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            events.append((session_id, run_id, event_type, payload, channel, external_chat_id))

        async def noop(_session_id):
            return None

        service = CuratorService(
            maybe_consolidate_memory=noop,
            maybe_update_recent_summary=noop,
            maybe_update_user_profile=noop,
            maybe_update_active_task=noop,
            run_skill_review=noop,
            should_run_skill_review=lambda result: False,
            read_memory_snapshot=lambda _session_id: state["memory"],
            read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
            read_user_profile_snapshot=lambda _session_id: state["user_profile"],
            read_active_task_snapshot=lambda _session_id: state["active_task"],
            read_skill_snapshot=lambda _session_id: state["skills"],
            emit_run_event=emit_run_event,
        )

        service.schedule_after_turn(
            session_id="web:browser-1",
            run_id="run-1",
            channel="web",
            external_chat_id="browser-1",
            result=ExecutionResult(content="done", executed_tool_calls=0),
        )
        await service.wait()
        return events

    events = asyncio.run(scenario())

    assert [event[2] for event in events] == [
        "curator.started",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.skipped",
        "curator.job.started",
        "curator.job.skipped",
        "curator.completed",
    ]
    assert events[-1][3]["changed"] == []
    assert events[-1][3]["summary"] == "No curator changes."


def test_curator_service_pause_blocks_future_scheduling():
    async def scenario():
        state = {"memory": "", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        runs = []

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            runs.append((session_id, run_id, event_type, payload, channel, external_chat_id))

        async def update_memory(_session_id):
            state["memory"] = "changed"

        async def noop(_session_id):
            return None

        service = CuratorService(
            maybe_consolidate_memory=update_memory,
            maybe_update_recent_summary=noop,
            maybe_update_user_profile=noop,
            maybe_update_active_task=noop,
            run_skill_review=noop,
            should_run_skill_review=lambda result: False,
            read_memory_snapshot=lambda _session_id: state["memory"],
            read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
            read_user_profile_snapshot=lambda _session_id: state["user_profile"],
            read_active_task_snapshot=lambda _session_id: state["active_task"],
            read_skill_snapshot=lambda _session_id: state["skills"],
            emit_run_event=emit_run_event,
        )

        paused_status = service.pause("web:browser-1")
        scheduled = service.schedule_manual_run(session_id="web:browser-1", run_id="run-1", channel="web", external_chat_id="browser-1")
        await service.wait()
        resumed_status = service.resume("web:browser-1")
        return paused_status, scheduled, resumed_status, runs

    paused_status, scheduled, resumed_status, runs = asyncio.run(scenario())

    assert paused_status["paused"] is True
    assert paused_status["state"] == "paused"
    assert scheduled is False
    assert resumed_status["paused"] is False
    assert resumed_status["state"] == "idle"
    assert runs == []


def test_curator_service_persists_pause_state(tmp_path):
    async def scenario():
        state = {"memory": "", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        state_path = tmp_path / "curator_state.json"

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            return None

        async def noop(_session_id):
            return None

        def make_service():
            return CuratorService(
                maybe_consolidate_memory=noop,
                maybe_update_recent_summary=noop,
                maybe_update_user_profile=noop,
                maybe_update_active_task=noop,
                run_skill_review=noop,
                should_run_skill_review=lambda result: False,
                read_memory_snapshot=lambda _session_id: state["memory"],
                read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
                read_user_profile_snapshot=lambda _session_id: state["user_profile"],
                read_active_task_snapshot=lambda _session_id: state["active_task"],
                read_skill_snapshot=lambda _session_id: state["skills"],
                emit_run_event=emit_run_event,
                state_path=state_path,
            )

        service = make_service()
        service.pause("web:browser-1")
        restored = make_service()
        scheduled = restored.schedule_manual_run(session_id="web:browser-1", run_id="run-1")
        await restored.wait()
        return restored.status("web:browser-1"), scheduled

    status, scheduled = asyncio.run(scenario())

    assert status["paused"] is True
    assert status["state"] == "paused"
    assert scheduled is False


def test_curator_service_persists_run_metadata(tmp_path):
    async def scenario():
        state = {"memory": "", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        state_path = tmp_path / "curator_state.json"

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            return None

        async def update_memory(_session_id):
            state["memory"] = "changed"

        async def noop(_session_id):
            return None

        def make_service():
            return CuratorService(
                maybe_consolidate_memory=update_memory,
                maybe_update_recent_summary=noop,
                maybe_update_user_profile=noop,
                maybe_update_active_task=noop,
                run_skill_review=noop,
                should_run_skill_review=lambda result: False,
                read_memory_snapshot=lambda _session_id: state["memory"],
                read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
                read_user_profile_snapshot=lambda _session_id: state["user_profile"],
                read_active_task_snapshot=lambda _session_id: state["active_task"],
                read_skill_snapshot=lambda _session_id: state["skills"],
                emit_run_event=emit_run_event,
                state_path=state_path,
            )

        service = make_service()
        service.schedule_manual_run(session_id="web:browser-1", run_id="run-1")
        await service.wait()
        restored = make_service()
        return restored.status("web:browser-1")

    status = asyncio.run(scenario())

    assert status["run_count"] == 1
    assert status["last_run_at"]
    assert status["last_run_summary"] == "Updated memory."
    assert status["last_run_jobs"] == ["memory", "recent_summary", "user_profile", "active_task", "skills"]
    assert status["last_run_changed"] == ["memory"]
    assert status["last_error"] is None


def test_curator_service_rerun_uses_pending_request_jobs_only():
    async def scenario():
        state = {"memory": "", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        calls = []
        skill_started = asyncio.Event()
        release_skill = asyncio.Event()

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            return None

        def maintenance_runner(key):
            async def run(_session_id):
                calls.append(key)

            return run

        async def run_skill(_session_id):
            calls.append("skills")
            skill_started.set()
            await release_skill.wait()

        service = CuratorService(
            maybe_consolidate_memory=maintenance_runner("memory"),
            maybe_update_recent_summary=maintenance_runner("recent_summary"),
            maybe_update_user_profile=maintenance_runner("user_profile"),
            maybe_update_active_task=maintenance_runner("active_task"),
            run_skill_review=run_skill,
            should_run_skill_review=lambda result: True,
            read_memory_snapshot=lambda _session_id: state["memory"],
            read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
            read_user_profile_snapshot=lambda _session_id: state["user_profile"],
            read_active_task_snapshot=lambda _session_id: state["active_task"],
            read_skill_snapshot=lambda _session_id: state["skills"],
            emit_run_event=emit_run_event,
        )

        service.schedule_skill_review(
            "web:browser-1",
            ExecutionResult(content="done", executed_tool_calls=3),
            run_id="run-skill",
        )
        await asyncio.wait_for(skill_started.wait(), timeout=2)
        scheduled = service.schedule_maintenance("web:browser-1", run_id="run-maintenance")
        status_while_running = service.status("web:browser-1")
        release_skill.set()
        await service.wait()
        return scheduled, status_while_running, calls

    scheduled, status_while_running, calls = asyncio.run(scenario())

    assert scheduled is False
    assert status_while_running["running"] is True
    assert status_while_running["rerun_pending"] is True
    assert status_while_running["current_job"] == "skills"
    assert status_while_running["current_job_label"] == "skills"
    assert status_while_running["active_jobs"] == ["skills"]
    assert calls == ["skills", "memory", "recent_summary", "user_profile", "active_task"]


def test_curator_service_emits_failed_event_and_records_error(tmp_path):
    async def scenario():
        state = {"memory": "", "recent_summary": "", "user_profile": "", "active_task": "", "skills": ""}
        state_path = tmp_path / "curator_state.json"
        events = []

        async def emit_run_event(session_id, run_id, event_type, payload, channel, external_chat_id):
            events.append((session_id, run_id, event_type, payload, channel, external_chat_id))

        async def fail_memory(_session_id):
            raise RuntimeError("memory broke")

        async def noop(_session_id):
            return None

        service = CuratorService(
            maybe_consolidate_memory=fail_memory,
            maybe_update_recent_summary=noop,
            maybe_update_user_profile=noop,
            maybe_update_active_task=noop,
            run_skill_review=noop,
            should_run_skill_review=lambda result: False,
            read_memory_snapshot=lambda _session_id: state["memory"],
            read_recent_summary_snapshot=lambda _session_id: state["recent_summary"],
            read_user_profile_snapshot=lambda _session_id: state["user_profile"],
            read_active_task_snapshot=lambda _session_id: state["active_task"],
            read_skill_snapshot=lambda _session_id: state["skills"],
            emit_run_event=emit_run_event,
            state_path=state_path,
        )

        service.schedule_manual_run(session_id="web:browser-1", run_id="run-1")
        await service.wait()
        return events, service.status("web:browser-1")

    events, status = asyncio.run(scenario())

    assert [event[2] for event in events] == ["curator.started", "curator.job.started", "curator.failed"]
    assert events[-1][3]["error"] == "memory broke"
    assert events[-1][3]["job"] == "memory"
    assert status["last_error"] == "memory broke"
