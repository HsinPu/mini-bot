"""
opensprite/storage/base.py - Storage 介面定義

設計理念：
- Agent 只認得「統一的 Storage 介面」
- 不同存放方式（記憶體、檔案、資料庫、Redis）都實作這個介面
- 以後要換存放方式 Agent 不用改

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StoredMessage:
    """
    已儲存的訊息格式
    """
    role: str      # "user" / "assistant" / "tool"
    content: str   # 訊息內容
    timestamp: float  # 時間戳記
    tool_name: str | None = None  # 如果是 tool，記錄用了什麼工具
    is_consolidated: bool = False  # 是否已被 consolidate 過
    metadata: dict[str, Any] = field(default_factory=dict)  # 額外欄位（channel、sender、transport chat id...）


class StorageProvider(ABC):
    """
    Storage Provider 的抽象基底類別
    
    每種存放方式都應該實作這個類別。
    
    抽象方法：
        - get_messages(): 取得對話歷史
        - add_message(): 加入訊息
        - clear_messages(): 清除歷史
        - get_consolidated_index(): 取得 consolidation 標記
        - set_consolidated_index(): 設定 consolidation 標記
    """
    
    @abstractmethod
    async def get_messages(self, chat_id: str, limit: int | None = None) -> list[StoredMessage]:
        """
        取得對話歷史
        
        參數：
            chat_id: 聊天室 ID
            limit: 最多取幾筆（可選）
        
        回傳：
            list[StoredMessage]: 訊息清單
        """
        pass

    async def get_message_count(self, chat_id: str) -> int:
        """Return the total persisted message count for one chat."""
        return len(await self.get_messages(chat_id))

    async def get_messages_slice(
        self,
        chat_id: str,
        *,
        start_index: int = 0,
        end_index: int | None = None,
    ) -> list[StoredMessage]:
        """Return one contiguous message slice using Python slice semantics."""
        messages = await self.get_messages(chat_id)
        return messages[max(0, start_index):end_index]
    
    @abstractmethod
    async def add_message(self, chat_id: str, message: StoredMessage) -> None:
        """
        加入訊息到歷史
        
        參數：
            chat_id: 聊天室 ID
            message: StoredMessage 訊息
        """
        pass
    
    @abstractmethod
    async def clear_messages(self, chat_id: str) -> None:
        """
        清除指定聊天室的歷史
        
        參數：
            chat_id: 聊天室 ID
        """
        pass

    @abstractmethod
    async def get_consolidated_index(self, chat_id: str) -> int:
        """Get the last consolidated message index for a chat."""
        pass

    @abstractmethod
    async def set_consolidated_index(self, chat_id: str, index: int) -> None:
        """Persist the last consolidated message index for a chat."""
        pass
    
    @abstractmethod
    async def get_all_chats(self) -> list[str]:
        """
        取得所有聊天室 ID
        
        回傳：
            list[str]: 聊天室 ID 清單
        """
        pass


async def get_storage_message_count(storage: Any, chat_id: str) -> int:
    """Compatibility helper for storages that may not implement get_message_count yet."""
    getter = getattr(storage, "get_message_count", None)
    if callable(getter):
        return int(await getter(chat_id))
    return len(await storage.get_messages(chat_id))


async def get_storage_messages_slice(
    storage: Any,
    chat_id: str,
    *,
    start_index: int = 0,
    end_index: int | None = None,
) -> list[StoredMessage]:
    """Compatibility helper for storages that may not implement get_messages_slice yet."""
    getter = getattr(storage, "get_messages_slice", None)
    if callable(getter):
        return list(await getter(chat_id, start_index=max(0, start_index), end_index=end_index))
    messages = await storage.get_messages(chat_id)
    return list(messages[max(0, start_index):end_index])
