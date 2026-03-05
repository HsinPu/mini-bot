"""
minibot/channels/__init__.py - 訊息頻道適配器

匯出各平台的訊息適配器
"""

from minibot.channels.telegram import TelegramAdapter

__all__ = ["TelegramAdapter"]
