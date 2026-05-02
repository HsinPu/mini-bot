import asyncio

from agent_test_helpers import make_agent_loop
from opensprite.agent.learning_ledger import LearningLedger


def test_learning_ledger_records_and_ranks_relevant_entries():
    ledger = LearningLedger()
    ledger.record_learning(
        "telegram:room-1",
        kind="skill",
        target_id="pytest-helper",
        summary="Reusable pytest workflow for updating assertions and running focused tests.",
        source_run_id="run-1",
    )
    ledger.record_learning(
        "telegram:room-1",
        kind="memory",
        target_id="memory",
        summary="Updated session memory.",
        source_run_id="run-2",
    )

    entries = ledger.relevant_entries("telegram:room-1", "Please update pytest assertions")

    assert entries
    assert entries[0]["kind"] == "skill"
    assert entries[0]["target_id"] == "pytest-helper"
    context = ledger.build_relevant_context("telegram:room-1", "Please update pytest assertions")
    assert "# Relevant Learned Context" in context
    assert "pytest-helper" in context


def test_agent_loop_marks_read_skill_reuse_in_learning_ledger(tmp_path):
    async def scenario():
        agent = make_agent_loop(tmp_path)
        hook = agent._make_tool_result_hook(
            channel="telegram",
            external_chat_id="room-1",
            session_id="telegram:room-1",
            run_id="run-1",
            enabled=False,
        )
        assert hook is not None
        await hook("read_skill", {"skill_name": "pytest-helper"}, "Skill body")
        agent._finalize_learning_reuse("telegram:room-1", "run-1", True)
        return agent.learning_ledger.recent_entries("telegram:room-1", limit=1)

    entries = asyncio.run(scenario())

    assert entries[0]["kind"] == "skill"
    assert entries[0]["target_id"] == "pytest-helper"
    assert entries[0]["use_count"] == 1
    assert entries[0]["last_outcome"] == "success"
