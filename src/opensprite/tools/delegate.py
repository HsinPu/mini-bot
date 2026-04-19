"""Delegate Tool - 委派子代理執行任務"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from .base import Tool
from .validation import NON_EMPTY_STRING_PATTERN
from ..subagent_prompts import get_all_subagents


def _build_description(subagents: dict[str, str]) -> str:
    """動態生成 delegate tool 的 description"""
    subagent_list = "\n".join([f"- {name}: {desc}" for name, desc in subagents.items()])
    return f"""委派任務給子代理執行。

可用子代理類型（prompt_type 必須是下列其中一個已存在的 id）：
{subagent_list}

子代理會自行載入對應 prompt 並組合執行時 context。

若使用者要新增或改版子代理：請先用主代理的 `configure_subagent`（add／upsert）寫入 `~/.opensprite/subagent_prompts/<id>.md`，
新建前建議先 `read_skill` 讀取 `agent-creator-design`；完成後此清單會在下次載入工具描述時包含新 id，再呼叫 `delegate`。
不要要求使用者手動改該目錄的 markdown，也不要用 `write_file`／`edit_file` 繞過（與設定檔防護一致時應避免）。
"""


class DelegateTool(Tool):
    """Delegate tool - 同步等待子代理完成"""

    name = "delegate"

    def __init__(
        self,
        run_subagent: Callable[[str, str], Awaitable[str]],
        *,
        app_home: Path | None = None,
    ):
        self._run_subagent = run_subagent
        self._app_home = app_home

    @property
    def description(self) -> str:
        return _build_description(get_all_subagents(self._app_home))

    @property
    def parameters(self) -> dict[str, Any]:
        subs = get_all_subagents(self._app_home)
        return {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "要委派的工作描述", "pattern": NON_EMPTY_STRING_PATTERN},
                "prompt_type": {
                    "type": "string",
                    "description": (
                        f"子代理 id，必須是目前已存在的類型之一: {list(subs.keys())}。"
                        "若要新增類型，請先用 configure_subagent 建立 prompt，再使用新的 id 呼叫 delegate。"
                    ),
                    "default": "writer",
                },
            },
            "required": ["task"],
        }

    async def _execute(self, task: str, prompt_type: str = "writer", **kwargs: Any) -> str:
        return await self._run_subagent(task, prompt_type)
