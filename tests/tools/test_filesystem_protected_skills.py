"""write_file / edit_file refuse paths under skills/<bundled_system_skill_id>/."""

import asyncio

from opensprite.tools.filesystem import EditFileTool, WriteFileTool
from opensprite.tools.skill_config import PROTECTED_SKILL_IDS


def test_write_file_allows_non_protected_skill_subdir(tmp_path):
    tool = WriteFileTool(workspace=tmp_path)
    out = asyncio.run(
        tool.execute(path="skills/custom-skill/notes.md", content="hello")
    )
    assert "Successfully wrote" in out
    assert (tmp_path / "skills" / "custom-skill" / "notes.md").read_text() == "hello"


def test_write_file_blocks_protected_skill_paths(tmp_path):
    tool = WriteFileTool(workspace=tmp_path)
    for sid in PROTECTED_SKILL_IDS:
        out = asyncio.run(
            tool.execute(path=f"skills/{sid}/SKILL.md", content="x")
        )
        assert "bundled system skill" in out.lower()
        assert not (tmp_path / "skills" / sid / "SKILL.md").exists()


def test_edit_file_blocks_protected_skill_paths(tmp_path):
    sid = next(iter(sorted(PROTECTED_SKILL_IDS)))
    skill_dir = tmp_path / "skills" / sid
    skill_dir.mkdir(parents=True)
    f = skill_dir / "SKILL.md"
    f.write_text("old", encoding="utf-8")

    tool = EditFileTool(workspace=tmp_path)
    out = asyncio.run(
        tool.execute(path=f"skills/{sid}/SKILL.md", old_text="old", new_text="new")
    )
    assert "bundled system skill" in out.lower()
    assert f.read_text() == "old"
