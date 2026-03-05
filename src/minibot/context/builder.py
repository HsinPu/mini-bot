"""Context builder interface."""

from pathlib import Path
from typing import Protocol


class ContextBuilder(Protocol):
    """
    Context builder protocol.
    
    Implement this to create different ways of building context/prompts.
    """
    
    def build_system_prompt(self) -> str:
        """Build the system prompt."""
        ...
    
    def build_messages(
        self,
        history: list[dict],
        current_message: str,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict]:
        """
        Build complete message list for LLM call.
        
        Args:
            history: Conversation history
            current_message: Current user message
            channel: Channel name (e.g., "telegram", "discord")
            chat_id: Chat/room ID
            
        Returns:
            List of message dicts with "role" and "content"
        """
        ...
    
    def add_tool_result(
        self,
        messages: list[dict],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> list[dict]:
        """Add tool result to messages."""
        ...
    
    def add_assistant_message(
        self,
        messages: list[dict],
        content: str | None,
        tool_calls: list[dict] | None = None,
    ) -> list[dict]:
        """Add assistant message (with tool calls) to messages."""
        ...
