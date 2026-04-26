"""Conversation history load/save helpers for AgentLoop."""

from __future__ import annotations

import time
from typing import Any, Callable

from ..llms import ChatMessage
from ..search.base import SearchStore
from ..storage import StorageProvider, StoredMessage
from ..utils.log import logger


class MessageHistoryService:
    """Loads chat history and persists messages with optional search indexing."""

    def __init__(
        self,
        *,
        storage: StorageProvider,
        search_store: SearchStore | None,
        max_history_getter: Callable[[], int],
    ):
        self.storage = storage
        self.search_store = search_store
        self._max_history_getter = max_history_getter

    async def load_history(self, chat_id: str) -> list[ChatMessage]:
        """Load conversation history as ChatMessage objects for LLM consumption."""
        stored_messages = await self.storage.get_messages(
            chat_id,
            limit=self._max_history_getter(),
        )

        chat_messages = []
        for message in stored_messages:
            if isinstance(message, dict):
                chat_messages.append(ChatMessage(role=message.get("role", "?"), content=message.get("content", "")))
            else:
                chat_messages.append(ChatMessage(role=message.role, content=message.content))

        return chat_messages

    async def save_message(
        self,
        chat_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Save one message to storage and index it when search is configured."""
        created_at = time.time()
        await self.storage.add_message(
            chat_id,
            StoredMessage(
                role=role,
                content=content,
                timestamp=created_at,
                tool_name=tool_name,
                metadata=dict(metadata or {}),
            ),
        )
        if self.search_store is None:
            return

        try:
            await self.search_store.index_message(
                chat_id=chat_id,
                role=role,
                content=content,
                tool_name=tool_name,
                created_at=created_at,
            )
        except Exception as e:
            logger.warning("[{}] Failed to index message for search: {}", chat_id, e)
