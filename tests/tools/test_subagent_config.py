import asyncio
import json
from pathlib import Path

from opensprite.tools.subagent_config import ConfigureSubagentTool

_VALID_DESCRIPTION = (
    "Chat-scoped helper: applies a repeatable workflow for tasks tied to this conversation only. "
    "Use when the user asks for the same multi-step process within this chat workspace."
)
_VALID_BODY = (
    "# Instructions\n\n"
    "Do the thing with care. Follow project conventions and prefer small, focused edits.\n"
)


def test_configure_subagent_list_and_add(tmp_path):
    app_home = tmp_path / "opensprite-home"
    tool = ConfigureSubagentTool(app_home=app_home)

    listed = asyncio.run(tool.execute(action="list"))
    payload = json.loads(listed)
    assert "subagent_prompts_dir" in payload
    assert "subagents" in payload
    assert Path(payload["subagent_prompts_dir"]).is_dir()

    out = asyncio.run(
        tool.execute(
            action="add",
            subagent_id="my-reviewer",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "Added subagent" in out

    dup = asyncio.run(
        tool.execute(
            action="add",
            subagent_id="my-reviewer",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "already exists" in dup.lower()

    got = asyncio.run(tool.execute(action="get", subagent_id="my-reviewer"))
    data = json.loads(got)
    assert data["subagent_id"] == "my-reviewer"
    assert "my-reviewer" in data["content"]
    assert "---" in data["content"]


def test_configure_subagent_upsert_then_remove(tmp_path):
    app_home = tmp_path / "oh"
    tool = ConfigureSubagentTool(app_home=app_home)

    asyncio.run(
        tool.execute(
            action="add",
            subagent_id="doc-writer",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    upsert_desc = (
        _VALID_DESCRIPTION
        + " Additional coverage for template reuse when migrating documents between environments "
        "and coordinating edits with upstream reviewers before publication."
    )
    up = asyncio.run(
        tool.execute(
            action="upsert",
            subagent_id="doc-writer",
            description=upsert_desc,
            body=_VALID_BODY + "\n\nSecond paragraph keeps the body substantive and long enough always.\n",
        )
    )
    assert "Updated" in up or "Added" in up

    rm = asyncio.run(tool.execute(action="remove", subagent_id="doc-writer"))
    assert "Removed" in rm

    again = asyncio.run(tool.execute(action="remove", subagent_id="doc-writer"))
    assert "no user-managed" in again.lower()


def test_configure_subagent_add_refuses_when_only_bundled_remains(tmp_path):
    """After removing the synced user copy, only the packaged writer remains; add must require upsert."""
    from opensprite.context.paths import get_subagent_prompts_dir

    app_home = tmp_path / "home-with-bundled"
    tool = ConfigureSubagentTool(app_home=app_home)
    asyncio.run(tool.execute(action="list"))
    writer_user = get_subagent_prompts_dir(app_home) / "writer.md"
    if writer_user.is_file():
        writer_user.unlink()

    out = asyncio.run(
        tool.execute(
            action="add",
            subagent_id="writer",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "bundled" in out.lower()
    assert "upsert" in out.lower()
