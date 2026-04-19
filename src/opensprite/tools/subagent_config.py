"""Tool for safely creating and updating subagent prompt markdown files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..context.paths import get_app_home, get_subagent_prompts_dir
from ..subagent_prompts import (
    BUNDLED_PROMPTS_DIR,
    load_all_metadata,
    read_prompt_document,
    sync_subagent_prompts_from_package,
)
from .base import Tool
from .skill_config import (
    _validate_body_for_write,
    _validate_description_for_write,
    _validate_skill_id,
)

# Bundled skill in ~/.opensprite/skills — same design discipline as configure_skill + skill-creator-design.
AGENT_PROMPT_GUIDE_SKILL_NAME = "agent-creator-design"

_CONFIGURE_SUBAGENT_RULES_SUMMARY = (
    "Each subagent is one file: ~/.opensprite/subagent_prompts/<subagent_id>.md with YAML frontmatter "
    "(name must match subagent_id, description required) and a markdown body used as the subagent system prompt. "
    "Follow the bundled skill read_skill + "
    f"skill_name '{AGENT_PROMPT_GUIDE_SKILL_NAME}' for structure (Role, Task, Constraints, Output) and metadata rules. "
    "Use action=add only when no prompt exists yet (neither user nor bundled); if a bundled prompt exists, use upsert "
    "to write a user override. remove deletes only the user-managed file in subagent_prompts, not bundled package files."
)


def _build_subagent_prompt_md(subagent_id: str, description: str, body: str) -> str:
    desc = (description or "").strip().replace("\n", " ").replace("\r", "")
    body_text = (body or "").strip()
    return f"---\nname: {subagent_id}\ndescription: {desc}\n---\n\n{body_text}\n"


def _classify_subagent_storage(subagent_id: str, *, app_home: Path | None) -> str | None:
    """Return 'user' if a user overlay exists, 'bundled' if only bundled exists, None if neither."""
    home = get_app_home(app_home)
    sync_subagent_prompts_from_package(home)
    user_path = get_subagent_prompts_dir(home) / f"{subagent_id}.md"
    if user_path.is_file():
        return "user"

    bundled = BUNDLED_PROMPTS_DIR / f"{subagent_id}.md"
    if bundled.is_file():
        return "bundled"
    return None


class ConfigureSubagentTool(Tool):
    """Read and update subagent prompt files under ~/.opensprite/subagent_prompts/."""

    name = "configure_subagent"
    description = (
        "Inspect, add, update, or remove subagent prompt definitions (one markdown file per subagent id). "
        "Use this when the user wants a new delegate target or to change an existing subagent prompt instead of "
        "editing files manually. "
        + _CONFIGURE_SUBAGENT_RULES_SUMMARY
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["list", "get", "add", "upsert", "remove"],
                "description": (
                    "list: enumerate known subagent ids and descriptions; get: read one prompt file; "
                    "add: create a user prompt only when none exists (no user file and no bundled file); "
                    "upsert: create or replace the user overlay file (overrides bundled when present); "
                    "remove: delete the user overlay file only (cannot remove bundled-only prompts)."
                ),
            },
            "subagent_id": {
                "type": "string",
                "description": (
                    "Subagent id: must match the markdown filename without .md and the frontmatter name field. "
                    "Same format as skill_name (lowercase ASCII, letter-first, hyphens between segments). "
                    "Required for get, add, upsert, and remove."
                ),
            },
            "description": {
                "type": "string",
                "description": (
                    "YAML frontmatter description for add and upsert: same quality rules as configure_skill "
                    f"(read_skill '{AGENT_PROMPT_GUIDE_SKILL_NAME}' for narrative structure; tool enforces length and English word counts)."
                ),
            },
            "body": {
                "type": "string",
                "description": (
                    "Markdown body for add and upsert (system prompt after frontmatter). "
                    "Same minimum length rules as configure_skill body."
                ),
            },
        },
        "required": ["action"],
    }

    def __init__(self, *, app_home: Path | None = None):
        self._app_home = app_home

    def _prompts_dir(self) -> Path:
        return get_subagent_prompts_dir(self._app_home)

    def _user_prompt_path(self, subagent_id: str) -> Path:
        return self._prompts_dir() / f"{subagent_id}.md"

    async def _execute(self, action: str, **kwargs: Any) -> str:
        home = get_app_home(self._app_home)
        sync_subagent_prompts_from_package(home)
        prompts_dir = self._prompts_dir()

        if action == "list":
            meta = load_all_metadata(app_home=self._app_home)
            payload = {"subagent_prompts_dir": str(prompts_dir), "subagents": meta}
            return json.dumps(payload, ensure_ascii=False, indent=2)

        subagent_id = str(kwargs.get("subagent_id", "") or "").strip()
        err = _validate_skill_id(subagent_id)
        if err:
            return (
                err.replace("skill_name", "subagent_id")
                .replace("Skill name", "Subagent id")
                .replace("skill name", "subagent id")
            )

        if action == "get":
            path, text = read_prompt_document(subagent_id, app_home=self._app_home)
            if not text:
                return f"Error: no prompt found for subagent_id '{subagent_id}'"
            payload = {
                "subagent_id": subagent_id,
                "resolved_path": str(path) if path else "",
                "content": text,
            }
            return json.dumps(payload, ensure_ascii=False, indent=2)

        user_path = self._user_prompt_path(subagent_id)

        if action == "remove":
            if not user_path.is_file():
                return (
                    f"Error: no user-managed prompt at {user_path}. "
                    "Bundled prompts cannot be removed via configure_subagent; delete a user overlay only."
                )
            user_path.unlink()
            return f"Removed user subagent prompt '{subagent_id}' at {user_path}."

        if action in {"add", "upsert"}:
            description = kwargs.get("description")
            body = kwargs.get("body")
            desc_err = _validate_description_for_write(description, action=action)
            if desc_err:
                return desc_err
            body_err = _validate_body_for_write(body, action=action)
            if body_err:
                return body_err

            where = _classify_subagent_storage(subagent_id, app_home=self._app_home)
            if action == "add":
                if where == "user":
                    return (
                        f"Error: subagent '{subagent_id}' already exists at {user_path}. "
                        "Use action=upsert to replace it, or remove it first."
                    )
                if where == "bundled":
                    return (
                        f"Error: subagent '{subagent_id}' already exists as a bundled prompt. "
                        "Use action=upsert to create a user override in ~/.opensprite/subagent_prompts/."
                    )

            existed_user = user_path.is_file()
            prompts_dir.mkdir(parents=True, exist_ok=True)
            content = _build_subagent_prompt_md(subagent_id, str(description), str(body))
            user_path.write_text(content, encoding="utf-8")
            guide = (
                f" Next: ensure read_skill '{AGENT_PROMPT_GUIDE_SKILL_NAME}' was applied for structure and metadata; "
                "delegate will pick up this id after the next tool description refresh."
            )
            if action == "add":
                return f"Added subagent prompt '{subagent_id}' at {user_path}.{guide}"
            label = "Updated" if existed_user or where == "bundled" else "Added"
            return f"{label} subagent prompt '{subagent_id}' at {user_path}.{guide}"

        return f"Error: unsupported action '{action}'"
