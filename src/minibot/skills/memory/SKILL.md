---
name: memory
description: Two-layer memory system with automatic consolidation.
always: true
---

# Memory

## Structure

- `memory/{chat_id}/MEMORY.md` — Long-term facts (preferences, project context). Automatically loaded into context.
- `memory/{chat_id}/HISTORY.md` — Event log, not loaded into context.

## When to Update MEMORY.md

Use `edit_file` or `write_file` to immediately save important facts:
- User preferences ("I prefer dark mode")
- Project context ("API uses OAuth2")
- Important information (things the user tells you)

## Auto-consolidation

When conversation exceeds 30 messages, old messages are automatically summarized and written to MEMORY.md.
