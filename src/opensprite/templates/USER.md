# USER.md - Durable User Context

This file lives at this chat session's workspace root, beside `skills/` and `subagent_prompts/`.
It stores durable user-focused context for this session: stable preferences, recurring constraints, and background that improve future collaboration in the same session.
It should not contain assistant-wide rules, one-off tasks, or private secrets.

## Purpose

Use this file for information that should remain useful across multiple turns in this session, especially when it helps OpenSprite collaborate more effectively without asking the same thing again.

## What Belongs Here

- stable preferences
- recurring work context
- long-lived constraints
- repeated habits or goals likely to matter again
- durable language or formatting preferences

## What Does Not Belong Here

- one-off requests
- transient task details
- temporary session noise
- secrets, passwords, API keys, or access tokens
- assistant operating rules that belong in bootstrap files

## Response language

This section is maintained by OpenSprite.
Use a short durable preference when one is clear, such as `- Traditional Chinese (Taiwan)` or `- English`.
Use `- not set` when response language should follow the user's current message.

<!-- OPENSPRITE:RESPONSE_LANGUAGE:START -->
- not set
<!-- OPENSPRITE:RESPONSE_LANGUAGE:END -->

## Auto-managed Profile

This section is maintained by OpenSprite and should stay concise, factual, and durable.
Store only user-focused details that are stable enough to help future turns in this same session.

<!-- OPENSPRITE:USER_PROFILE:START -->
- No learned user profile details yet.
<!-- OPENSPRITE:USER_PROFILE:END -->
