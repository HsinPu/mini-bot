import asyncio
import json

from opensprite.skills import SkillsLoader
from opensprite.tools.skill_config import (
    MIN_SKILL_BODY_LEN,
    MIN_SKILL_DESCRIPTION_LEN,
    MIN_SKILL_DESCRIPTION_WORDS,
    PROTECTED_SKILL_IDS,
    ConfigureSkillTool,
)

# Meets fixed minimums for add/upsert validation.
_VALID_DESCRIPTION = (
    "Chat-scoped helper: applies a repeatable workflow for tasks tied to this conversation only. "
    "Use when the user asks for the same multi-step process within this chat workspace."
)
_VALID_BODY = (
    "# Instructions\n\n"
    "Do the thing with care. Follow project conventions and prefer small, focused edits.\n"
)


def test_configure_skill_lists_global_skills(tmp_path):
    skills_dir = tmp_path / "skills"
    (skills_dir / "alpha").mkdir(parents=True)
    (skills_dir / "alpha" / "SKILL.md").write_text(
        "---\nname: alpha\ndescription: First skill\n---\n\n# Alpha\n",
        encoding="utf-8",
    )

    loader = SkillsLoader(default_skills_dir=skills_dir)
    tool = ConfigureSkillTool(
        skills_loader=loader,
        workspace_resolver=lambda: tmp_path / "ws",
    )

    result = asyncio.run(tool.execute(action="list", scope="global"))
    payload = json.loads(result)

    assert payload["scope"] == "global"
    assert payload["skills_dir"] == str(skills_dir.resolve())
    assert "alpha" in payload["skills"]
    assert payload["skills"]["alpha"]["description"] == "First skill"


def test_configure_skill_add_upsert_and_get_chat_scope(tmp_path):
    ws = tmp_path / "workspace"
    loader = SkillsLoader(default_skills_dir=tmp_path / "global_skills")
    tool = ConfigureSkillTool(
        skills_loader=loader,
        workspace_resolver=lambda: ws,
    )

    created = asyncio.run(
        tool.execute(
            action="add",
            scope="chat",
            skill_name="my-skill",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "Added skill" in created

    duplicate = asyncio.run(
        tool.execute(
            action="add",
            scope="chat",
            skill_name="my-skill",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "already exists" in duplicate

    updated = asyncio.run(
        tool.execute(
            action="upsert",
            scope="chat",
            skill_name="my-skill",
            description=_VALID_DESCRIPTION,
            body=(
                "# Instructions\n\n"
                "Replaced body: follow conventions and verify results after each step in this chat.\n"
            ),
        )
    )
    assert "Updated skill" in updated

    skill_file = ws / "skills" / "my-skill" / "SKILL.md"
    assert skill_file.is_file()

    got = asyncio.run(tool.execute(action="get", scope="chat", skill_name="my-skill"))
    payload = json.loads(got)
    assert payload["skill_name"] == "my-skill"
    assert "Replaced body" in payload["content"]


def test_configure_skill_remove_global(tmp_path):
    skills_dir = tmp_path / "skills"
    skill_dir = skills_dir / "gone"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: gone\ndescription: x\n---\n\n# Gone\n",
        encoding="utf-8",
    )

    loader = SkillsLoader(default_skills_dir=skills_dir)
    tool = ConfigureSkillTool(
        skills_loader=loader,
        workspace_resolver=lambda: tmp_path / "ws",
    )

    result = asyncio.run(tool.execute(action="remove", scope="global", skill_name="gone"))
    assert "Removed skill" in result
    assert not skill_dir.exists()


def test_configure_skill_rejects_invalid_skill_id(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="My_Skill",
            description=_VALID_DESCRIPTION,
            body=_VALID_BODY,
        )
    )
    assert "lowercase ASCII" in out


def test_configure_skill_rejects_short_description(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="ok-skill",
            description="too short",
            body=_VALID_BODY,
        )
    )
    assert str(MIN_SKILL_DESCRIPTION_LEN) in out


def test_configure_skill_rejects_short_body(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="ok-skill",
            description=_VALID_DESCRIPTION,
            body="short",
        )
    )
    assert str(MIN_SKILL_BODY_LEN) in out


def test_configure_skill_rejects_too_few_english_words(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    # Long enough in characters but only 10 repeated tokens.
    padded = " ".join(["supercalifragilistic"] * 10)
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="ok-skill",
            description=padded,
            body=_VALID_BODY,
        )
    )
    assert str(MIN_SKILL_DESCRIPTION_WORDS) in out


def test_configure_skill_rejects_low_substance_glue_words(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    glue = " ".join(
        ["the", "a", "an", "of", "to", "in", "for", "on", "at", "by", "and", "or", "if", "so", "is", "are"]
        * 8
    )
    assert len(glue) >= MIN_SKILL_DESCRIPTION_LEN
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="ok-skill",
            description=glue,
            body=_VALID_BODY,
        )
    )
    assert "substantive" in out.lower()


def test_configure_skill_rejects_mutating_protected_spec_skill(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    for skill_name in sorted(PROTECTED_SKILL_IDS):
        for action in ("add", "upsert", "remove"):
            kwargs = {"action": action, "scope": "global", "skill_name": skill_name}
            if action in ("add", "upsert"):
                kwargs["description"] = _VALID_DESCRIPTION
                kwargs["body"] = _VALID_BODY
            out = asyncio.run(tool.execute(**kwargs))
            assert "bundled system skill" in out.lower()


def test_configure_skill_rejects_repetitive_description(tmp_path):
    tool = ConfigureSkillTool(
        skills_loader=SkillsLoader(default_skills_dir=tmp_path / "s"),
        workspace_resolver=lambda: tmp_path / "ws",
    )
    padded = " ".join(["foobar"] * 22)
    out = asyncio.run(
        tool.execute(
            action="add",
            scope="global",
            skill_name="ok-skill",
            description=padded,
            body=_VALID_BODY,
        )
    )
    assert "repetitive" in out.lower()
