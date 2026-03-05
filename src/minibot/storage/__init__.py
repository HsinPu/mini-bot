"""
minibot/storage/__init__.py - 儲存提供者

匯出所有 Storage Provider 實作
"""

from minibot.storage.base import StorageProvider, StoredMessage
from minibot.storage.memory import MemoryStorage

__all__ = [
    "StorageProvider",
    "StoredMessage", 
    "MemoryStorage"
]
