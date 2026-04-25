# AGENTS.md

## Setup And Verification

- Use `pyproject.toml` as the dependency source; root `requirements.txt` is narrower than the current package dependencies.
- Python is 3.11+ with a setuptools `src` layout. Dev install from repo root: `python -m pip install -e ".[dev]"`.
- Use `python -m pip install -e ".[dev,vector]"` only when exercising the optional `sqlite-vec` vector backend.
- `tests/conftest.py` prepends `src` to `sys.path`, so focused tests can run without installing the package: `python -m pytest tests/channels/test_web.py::test_web_adapter_roundtrip`.
- Main Python verification is `python -m pytest`; no repo-configured ruff/black/mypy/pyright/pre-commit workflow was found.
- Web verification runs from `apps/web`: `npm ci`, `npm run build`, `npm run dev`, or `npm run preview`.

## Runtime Shape

- CLI entrypoint is `opensprite.cli.commands:app`; `python -m opensprite` imports the same Typer app.
- `opensprite gateway` runs `src/opensprite/runtime.py::gateway` as a foreground process; stop it with `Ctrl+C`.
- Gateway wiring is `Config -> Storage/Search/Media -> AgentLoop -> MessageQueue -> channel adapters`; built-in tools are registered in `src/opensprite/agent/tool_registration.py`.
- Registered channel adapters are `telegram` and `web` in `src/opensprite/channels/__init__.py`; `console` may be enabled in templates but has no adapter and only logs a warning.
- Trust channel registry/config code over older README prose that says only Telegram is implemented.

## Config Gotchas

- Default config lives under `~/.opensprite`, not this repo. Avoid committing runtime data, app-home files, API keys, or SQLite databases.
- `opensprite.json` uses sibling split files resolved relative to the main config: `llm.providers.json`, `channels.json`, `search.json`, `media.json`, `messages.json`, and `mcp_servers.json`.
- Validate split config with `opensprite config validate --config <path>` or add `--json` for machine-readable output.
- `search.backend="sqlite"` requires `storage.type="sqlite"`; enabling embeddings also requires `search.embedding.model` plus an embedding API key or active LLM provider fallback.

## Web App

- `apps/web` is an independent private Vue 3/Vite app with its own `package-lock.json`; there is no root JS workspace.
- Vite dev binds `127.0.0.1` and proxies `/ws` and `/healthz` to the gateway at `127.0.0.1:8765`.
- Default web channel config serves `http://127.0.0.1:8765/`, WebSocket `/ws`, and health `/healthz`.
- `WebAdapter` attempts `npm ci` if dependencies are missing and runs `npm run build` before gateway startup when `frontend_auto_install`/`frontend_auto_build` are enabled.
- Edit `apps/web/src/App.vue`, `apps/web/src/main.js`, and `apps/web/styles.css`; do not edit ignored outputs `apps/web/dist` or `apps/web/node_modules`.

## Packaged Prompts And Assets

- Bundled bootstrap prompts live in `src/opensprite/templates/{IDENTITY,SOUL,AGENTS,TOOLS,USER}.md` and sync to `~/.opensprite/bootstrap` only when missing.
- Bundled skills and subagent prompts are package data; update `[tool.setuptools.package-data]` in `pyproject.toml` when adding new runtime asset patterns.
