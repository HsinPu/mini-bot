import asyncio
import uuid
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str
    content: str


class Subagent:
    """執行 LLM 呼叫的 worker"""

    def __init__(self, provider, model=None):
        self.provider = provider
        self.model = model

    async def run(self, task: str, system_prompt: str | None = None) -> str:
        if system_prompt is None:
            system_prompt = "You are a helpful assistant."
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=task),
        ]
        response = await self.provider.chat(model=self.model, messages=messages)
        return response.content


class SubagentManager:
    """管理背景子代理執行"""

    def __init__(self, provider):
        self.provider = provider
        self._running_tasks: dict[str, asyncio.Task[str]] = {}

    async def delegate(self, task: str, label: str | None = None) -> str:
        task_id = str(uuid.uuid4())[:8]
        display_label = label or "task"

        subagent = Subagent(self.provider)
        bg_task = asyncio.create_task(subagent.run(task))
        self._running_tasks[task_id] = bg_task

        def cleanup(t):
            self._running_tasks.pop(task_id, None)

        bg_task.add_done_callback(cleanup)

        return f"Delegate [{display_label}] started (id: {task_id})."

    async def get_result(self, task_id: str) -> str | None:
        task = self._running_tasks.get(task_id)
        if task is None:
            return None

        if task.done():
            try:
                return task.result()
            except Exception as e:
                return f"Error: {e}"
        return None

    async def cancel(self, task_id: str) -> bool:
        task = self._running_tasks.get(task_id)
        if task:
            task.cancel()
            return True
        return False

    @property
    def running_count(self) -> int:
        return len(self._running_tasks)