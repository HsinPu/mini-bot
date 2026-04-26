"""Conversation reset helpers across storage, documents, and search index."""

from __future__ import annotations

from typing import Callable

from ..search.base import SearchStore
from ..storage import StorageProvider
from ..utils.log import logger


class HistoryResetService:
    """Clears chat history and related per-chat derived state."""

    def __init__(
        self,
        *,
        storage: StorageProvider,
        search_store: SearchStore | None,
        clear_active_task: Callable[[str], None],
        clear_recent_summary: Callable[[str], None],
    ):
        self.storage = storage
        self.search_store = search_store
        self._clear_active_task = clear_active_task
        self._clear_recent_summary = clear_recent_summary

    async def reset(self, chat_id: str | None = None) -> None:
        """Clear one chat or all chats from storage and derived indexes."""
        if chat_id:
            await self._clear_one(chat_id)
            return

        all_chats = await self.storage.get_all_chats()
        for current_chat_id in all_chats:
            await self._clear_one(current_chat_id)

    async def _clear_one(self, chat_id: str) -> None:
        await self.storage.clear_messages(chat_id)
        self._clear_active_task(chat_id)
        self._clear_recent_summary(chat_id)
        if self.search_store is None:
            return
        try:
            await self.search_store.clear_chat(chat_id)
        except Exception as e:
            logger.warning("[{}] Failed to clear search index: {}", chat_id, e)
