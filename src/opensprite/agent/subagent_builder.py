from pathlib import Path

from ..context.runtime import build_runtime_context
from ..llms import ChatMessage
from ..subagent_prompts import load_prompt


class SubagentMessageBuilder:
    """Build prompt/messages for delegated subagent work."""

    def __init__(self, prompt_loader=load_prompt):
        self.prompt_loader = prompt_loader

    def build_system_prompt(self, prompt_type: str = "writer", workspace: str | Path | None = None) -> str:
        prompt_body = self.prompt_loader(prompt_type)
        runtime_context = build_runtime_context(workspace=workspace)

        sections = []
        if prompt_body:
            sections.append(prompt_body)
        else:
            sections.append(
                "## 角色（Role）\n"
                f"你是專注於單一任務的 `{prompt_type}` 助手。\n\n"
                "## 任務（Task）\n"
                "1. 先理解目前任務。\n"
                "2. 根據已提供資訊完成內容。\n"
                "3. 若資訊不足，只提出必要問題。\n\n"
                "## 規範（Constraints）\n"
                "- 聚焦當前任務\n"
                "- 不要虛構事實\n"
                "- 直接輸出可交付內容\n\n"
                "## 輸出（Output）\n"
                "- 若資訊足夠：直接輸出完成內容。\n"
                "- 若資訊不足：列出需要補充的問題。"
            )

        sections.extend(["", runtime_context])
        return "\n".join(sections).strip()

    def build_messages(
        self,
        task: str,
        prompt_type: str = "writer",
        workspace: str | Path | None = None,
    ) -> list[ChatMessage]:
        system_prompt = self.build_system_prompt(prompt_type, workspace=workspace)
        return [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=task),
        ]
