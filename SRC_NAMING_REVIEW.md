# Src Naming Review

Review scope: `src/minibot/**`

## Overall

- Status: mostly aligned
- Applied: the most obvious file rename candidates have been updated
- Recommendation: keep most folder names and revisit only the optional cleanup items later

## Looks Good

These folders and their main files match current responsibilities well:

- `src/minibot/agent/`
- `src/minibot/channels/`
- `src/minibot/llms/`
- `src/minibot/memory/`
- `src/minibot/search/`
- `src/minibot/storage/`
- `src/minibot/templates/`
- `src/minibot/config/`

## Applied Renames

| Previous path | Current path | Why |
| --- | --- | --- |
| `src/minibot/context/workspace.py` | `src/minibot/context/paths.py` | Now manages app home, bootstrap, memory, skills, tool workspace, and migration. It is no longer only a workspace helper. |
| `src/minibot/tools/webfetch.py` | `src/minibot/tools/web_fetch.py` | Better matches the naming style already used by `web_search.py`. |
| `src/minibot/bus/queue.py` | `src/minibot/bus/message_bus.py` | The file contains `MessageBus`, not a generic queue helper. This reduces confusion with `message_queue.py`. |
| `src/minibot/bus/message_queue.py` | `src/minibot/bus/dispatcher.py` | It is a higher-level coordinator, not the low-level bus queue itself. |

## Optional Cleanup

These are acceptable now, but could be improved later if the code grows more:

- `src/minibot/skills/__init__.py` -> `src/minibot/skills/loader.py`
  - Reason: `SkillsLoader` is now substantial enough to live in its own module.
- `src/minibot/context/file_builder.py`
  - Current name is still acceptable.
  - If more context sources are added later, consider `prompt_builder.py`.

## Non-Naming Hygiene Note

Tracked cache files were found under `src` and should not stay in git:

- `src/minibot/__pycache__/agent.cpython-312.pyc`
- `src/minibot/config/__pycache__/schema.cpython-312.pyc`
- `src/minibot/llms/__pycache__/__init__.cpython-312.pyc`
- `src/minibot/llms/__pycache__/base.cpython-312.pyc`
- `src/minibot/llms/__pycache__/openai.cpython-312.pyc`

Recommended follow-up:

1. Add `__pycache__/` and `*.pyc` to `.gitignore`
2. Remove tracked cache files from git

## Suggested Next Step

1. Decide whether `skills/__init__.py` should stay or move to `loader.py`
