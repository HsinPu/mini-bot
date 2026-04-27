"""
opensprite/storage/memory.py - 記憶體 Storage 實作

把對話歷史存放在記憶體中（current implementation）

"""

import time
from collections import defaultdict
from typing import Any

from .base import StorageProvider, StoredMessage, StoredRun, StoredRunEvent, StoredRunFileChange, StoredRunPart, StoredWorkState


class MemoryStorage(StorageProvider):
    """
    記憶體 Storage 實作
    
    把對話歷史存在 dict 裡，重啟後會消失。
    適合開發測試用。
    """
    
    def __init__(self):
        """初始化"""
        self._messages: dict[str, list[StoredMessage]] = defaultdict(list)
        self._consolidated_index: dict[str, int] = {}  # Per-chat consolidation tracking
        self._runs: dict[str, StoredRun] = {}
        self._run_events: dict[tuple[str, str], list[StoredRunEvent]] = defaultdict(list)
        self._run_file_changes: dict[tuple[str, str], list[StoredRunFileChange]] = defaultdict(list)
        self._run_parts: dict[tuple[str, str], list[StoredRunPart]] = defaultdict(list)
        self._work_states: dict[str, StoredWorkState] = {}
    
    async def get_messages(self, chat_id: str, limit: int | None = None) -> list[StoredMessage]:
        """
        取得對話歷史
        """
        messages = self._messages.get(chat_id, [])
        if limit:
            return messages[-limit:]
        return messages
    
    async def add_message(self, chat_id: str, message: StoredMessage) -> None:
        """
        加入訊息
        """
        # 設定時間戳記（如果沒有的話）
        if message.timestamp == 0:
            message.timestamp = time.time()
        
        self._messages[chat_id].append(message)

    async def get_message_count(self, chat_id: str) -> int:
        """Return the total message count for one in-memory chat."""
        return len(self._messages.get(chat_id, []))

    async def get_messages_slice(
        self,
        chat_id: str,
        *,
        start_index: int = 0,
        end_index: int | None = None,
    ) -> list[StoredMessage]:
        """Return one message slice without copying the full chat history first."""
        messages = self._messages.get(chat_id, [])
        return list(messages[max(0, start_index):end_index])
    
    async def clear_messages(self, chat_id: str) -> None:
        """
        清除歷史
        """
        if chat_id in self._messages:
            self._messages[chat_id].clear()
        self._consolidated_index.pop(chat_id, None)
        for run_id, run in list(self._runs.items()):
            if run.chat_id == chat_id:
                self._runs.pop(run_id, None)
                self._run_events.pop((chat_id, run_id), None)
                self._run_file_changes.pop((chat_id, run_id), None)
                self._run_parts.pop((chat_id, run_id), None)
        self._work_states.pop(chat_id, None)
    
    async def get_consolidated_index(self, chat_id: str) -> int:
        """取得 consolidation 標記"""
        return self._consolidated_index.get(chat_id, 0)
    
    async def set_consolidated_index(self, chat_id: str, index: int) -> None:
        """設定 consolidation 標記"""
        self._consolidated_index[chat_id] = index
    
    async def get_all_chats(self) -> list[str]:
        """
        取得所有聊天室
        """
        chat_ids = set(self._messages.keys())
        chat_ids.update(run.chat_id for run in self._runs.values())
        chat_ids.update(self._work_states.keys())
        return sorted(chat_ids)

    async def create_run(
        self,
        chat_id: str,
        run_id: str,
        *,
        status: str = "running",
        metadata: dict | None = None,
        created_at: float | None = None,
    ) -> StoredRun:
        now = float(created_at or time.time())
        run = StoredRun(
            run_id=run_id,
            chat_id=chat_id,
            status=status,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        self._runs[run_id] = run
        return run

    async def update_run_status(
        self,
        chat_id: str,
        run_id: str,
        status: str,
        *,
        metadata: dict | None = None,
        finished_at: float | None = None,
    ) -> StoredRun | None:
        run = self._runs.get(run_id)
        if run is None:
            return None
        run.status = status
        run.updated_at = time.time()
        if finished_at is not None:
            run.finished_at = float(finished_at)
        if metadata:
            run.metadata.update(metadata)
        return run

    async def get_runs(self, chat_id: str, limit: int | None = None) -> list[StoredRun]:
        runs = [run for run in self._runs.values() if run.chat_id == chat_id]
        runs.sort(key=lambda run: (run.created_at, run.run_id), reverse=True)
        if limit is not None:
            return runs[:limit]
        return runs

    async def get_run(self, chat_id: str, run_id: str) -> StoredRun | None:
        run = self._runs.get(run_id)
        if run is None or run.chat_id != chat_id:
            return None
        return run

    async def get_work_state(self, chat_id: str) -> StoredWorkState | None:
        return self._work_states.get(chat_id)

    async def upsert_work_state(self, state: StoredWorkState) -> StoredWorkState:
        existing = self._work_states.get(state.chat_id)
        created_at = existing.created_at if existing is not None and existing.created_at else float(state.created_at or time.time())
        updated = StoredWorkState(
            chat_id=state.chat_id,
            objective=state.objective,
            kind=state.kind,
            status=state.status,
            steps=tuple(state.steps),
            constraints=tuple(state.constraints),
            done_criteria=tuple(state.done_criteria),
            long_running=bool(state.long_running),
            coding_task=bool(state.coding_task),
            expects_code_change=bool(state.expects_code_change),
            expects_verification=bool(state.expects_verification),
            current_step=state.current_step,
            next_step=state.next_step,
            completed_steps=tuple(state.completed_steps),
            file_change_count=int(state.file_change_count),
            touched_paths=tuple(state.touched_paths),
            verification_attempted=bool(state.verification_attempted),
            verification_passed=bool(state.verification_passed),
            last_next_action=state.last_next_action,
            active_delegate_task_id=state.active_delegate_task_id,
            active_delegate_prompt_type=state.active_delegate_prompt_type,
            metadata=dict(state.metadata or {}),
            created_at=created_at,
            updated_at=float(state.updated_at or time.time()),
        )
        self._work_states[state.chat_id] = updated
        return updated

    async def clear_work_state(self, chat_id: str) -> None:
        self._work_states.pop(chat_id, None)

    async def add_run_event(
        self,
        chat_id: str,
        run_id: str,
        event_type: str,
        *,
        payload: dict | None = None,
        created_at: float | None = None,
    ) -> StoredRunEvent:
        key = (chat_id, run_id)
        event = StoredRunEvent(
            run_id=run_id,
            chat_id=chat_id,
            event_type=event_type,
            payload=dict(payload or {}),
            created_at=float(created_at or time.time()),
            event_id=len(self._run_events[key]) + 1,
        )
        self._run_events[key].append(event)
        return event

    async def get_run_events(self, chat_id: str, run_id: str) -> list[StoredRunEvent]:
        return list(self._run_events.get((chat_id, run_id), []))

    async def add_run_part(
        self,
        chat_id: str,
        run_id: str,
        part_type: str,
        *,
        content: str = "",
        tool_name: str | None = None,
        metadata: dict | None = None,
        created_at: float | None = None,
    ) -> StoredRunPart:
        key = (chat_id, run_id)
        part = StoredRunPart(
            run_id=run_id,
            chat_id=chat_id,
            part_type=part_type,
            content=str(content or ""),
            tool_name=tool_name,
            metadata=dict(metadata or {}),
            created_at=float(created_at or time.time()),
            part_id=len(self._run_parts[key]) + 1,
        )
        self._run_parts[key].append(part)
        return part

    async def get_run_parts(self, chat_id: str, run_id: str) -> list[StoredRunPart]:
        return list(self._run_parts.get((chat_id, run_id), []))

    async def add_run_file_change(
        self,
        chat_id: str,
        run_id: str,
        tool_name: str,
        path: str,
        action: str,
        *,
        before_sha256: str | None = None,
        after_sha256: str | None = None,
        before_content: str | None = None,
        after_content: str | None = None,
        diff: str = "",
        metadata: dict[str, Any] | None = None,
        created_at: float | None = None,
    ) -> StoredRunFileChange:
        key = (chat_id, run_id)
        change = StoredRunFileChange(
            run_id=run_id,
            chat_id=chat_id,
            tool_name=tool_name,
            path=path,
            action=action,
            before_sha256=before_sha256,
            after_sha256=after_sha256,
            before_content=before_content,
            after_content=after_content,
            diff=str(diff or ""),
            metadata=dict(metadata or {}),
            created_at=float(created_at or time.time()),
            change_id=len(self._run_file_changes[key]) + 1,
        )
        self._run_file_changes[key].append(change)
        return change

    async def get_run_file_changes(self, chat_id: str, run_id: str) -> list[StoredRunFileChange]:
        return list(self._run_file_changes.get((chat_id, run_id), []))

    async def get_run_file_change(
        self,
        chat_id: str,
        run_id: str,
        change_id: int,
    ) -> StoredRunFileChange | None:
        for change in self._run_file_changes.get((chat_id, run_id), []):
            if change.change_id == change_id:
                return change
        return None
