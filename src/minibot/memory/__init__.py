"""Memory system for persistent agent memory (long-term)."""

import json
from pathlib import Path
from typing import Any

from minibot.utils.log import logger


# Tool definition for saving memory
_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save important information to long-term memory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_update": {
                        "type": "string",
                        "description": "Updated long-term memory as markdown. Include all existing facts plus new ones. Return unchanged if nothing new.",
                    },
                },
                "required": ["memory_update"],
            },
        },
    }
]


class MemoryStore:
    """
    Long-term memory stored in MEMORY.md.
    
    Reads/writes to a markdown file that gets included in system prompt.
    """

    def __init__(self, workspace: Path):
        self.memory_dir = workspace / "memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.memory_dir / "MEMORY.md"

    def read(self) -> str:
        """Read long-term memory."""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write(self, content: str) -> None:
        """Write long-term memory."""
        self.memory_file.write_text(content, encoding="utf-8")

    def get_context(self) -> str:
        """Get memory context for system prompt."""
        memory = self.read()
        if memory:
            return f"# Long-term Memory\n\n{memory}"
        return ""

    async def consolidate(
        self,
        messages: list[dict],
        provider: "LLMProvider",
        model: str,
    ) -> bool:
        """
        Consolidate old messages into memory via LLM.
        
        Args:
            messages: List of conversation messages to process
            provider: LLM provider
            model: Model to use
            
        Returns:
            True on success, False on failure
        """
        if not messages:
            return True

        # Build prompt with messages
        lines = []
        for m in messages:
            if not m.get("content"):
                continue
            role = m.get("role", "?").upper()
            content = m.get("content", "")
            lines.append(f"[{role}]: {content}")

        current_memory = self.read()
        prompt = f"""Process this conversation and call the save_memory tool with important information to remember.

Current memory:
{current_memory or "(empty)"}

Conversation:
{chr(10).join(lines[-20:])}  # Last 20 messages

Extract key facts, preferences, decisions, and important information. Update the memory accordingly."""

        try:
            response = await provider.chat(
                messages=[
                    {"role": "system", "content": "You are a memory consolidation agent. Call the save_memory tool to update long-term memory with important information from the conversation."},
                    {"role": "user", "content": prompt},
                ],
                tools=_SAVE_MEMORY_TOOL,
                model=model,
            )

            if not response.tool_calls:
                logger.warning("Memory consolidation: LLM did not call save_memory")
                return False

            args = response.tool_calls[0].arguments
            if isinstance(args, str):
                args = json.loads(args)

            if update := args.get("memory_update"):
                if update != current_memory:
                    self.write(update)
                    logger.info("Memory consolidated: {} chars", len(update))

            return True
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            return False
