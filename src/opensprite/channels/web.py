"""
opensprite/channels/web.py - WebSocket chat adapter

Expose a lightweight WebSocket endpoint that feeds browser messages into
MessageQueue and routes assistant replies back to the same web session.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import uuid4

from aiohttp import WSMsgType, web

from ..bus.message import AssistantMessage, MessageAdapter, UserMessage
from ..config import MessagesConfig
from ..utils.log import logger


class WebAdapter(MessageAdapter):
    """WebSocket adapter for browser-based chat clients."""

    DEFAULT_CONFIG = {
        "host": "127.0.0.1",
        "port": 8765,
        "path": "/ws",
        "health_path": "/healthz",
        "max_message_size": 1024 * 1024,
    }

    def __init__(self, mq=None, config: dict[str, Any] | None = None):
        self.mq = mq
        self.messages = getattr(mq, "messages", None) or MessagesConfig()
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.app: web.Application | None = None
        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None
        self._shutdown_event = asyncio.Event()
        self._started_event = asyncio.Event()
        self._session_connections: dict[str, web.WebSocketResponse] = {}
        self._socket_sessions: dict[web.WebSocketResponse, set[str]] = {}

    def _get_host(self) -> str:
        return str(self.config.get("host", self.DEFAULT_CONFIG["host"]))

    def _get_port(self) -> int:
        return int(self.config.get("port", self.DEFAULT_CONFIG["port"]))

    def _get_max_message_size(self) -> int:
        return int(self.config.get("max_message_size", self.DEFAULT_CONFIG["max_message_size"]))

    def _get_path(self, key: str) -> str:
        raw = str(self.config.get(key, self.DEFAULT_CONFIG[key]) or self.DEFAULT_CONFIG[key]).strip() or "/"
        return raw if raw.startswith("/") else f"/{raw}"

    def _build_session_chat_id(self, chat_id: str | None) -> str:
        normalized_chat_id = self._coerce_optional_text(chat_id, default="default") or "default"
        if self.mq is not None:
            return self.mq.build_session_chat_id("web", normalized_chat_id)
        return f"web:{normalized_chat_id}"

    @property
    def bound_port(self) -> int | None:
        if self.site is None:
            return None
        server = getattr(self.site, "_server", None)
        sockets = getattr(server, "sockets", None) or []
        if not sockets:
            return None
        return int(sockets[0].getsockname()[1])

    async def wait_until_started(self, timeout: float = 5.0) -> None:
        """Wait until the HTTP server starts listening."""
        await asyncio.wait_for(self._started_event.wait(), timeout=timeout)

    def _bind_session(self, session_chat_id: str, ws: web.WebSocketResponse) -> None:
        self._session_connections[session_chat_id] = ws
        self._socket_sessions.setdefault(ws, set()).add(session_chat_id)

    def _unbind_socket(self, ws: web.WebSocketResponse) -> None:
        for session_chat_id in self._socket_sessions.pop(ws, set()):
            if self._session_connections.get(session_chat_id) is ws:
                self._session_connections.pop(session_chat_id, None)

    @staticmethod
    def _coerce_metadata(value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    @staticmethod
    def _coerce_media_list(value: Any) -> list[str] | None:
        if not isinstance(value, list):
            return None
        items = [str(item) for item in value if isinstance(item, str) and item.strip()]
        return items or None

    @staticmethod
    def _coerce_optional_text(value: Any, *, default: str | None = None) -> str | None:
        if value is None:
            return default
        text = str(value).strip()
        return text or default

    def _parse_incoming_payload(self, raw_text: str) -> dict[str, Any]:
        stripped = raw_text.strip()
        if not stripped:
            raise ValueError("Message text cannot be empty")

        if stripped.startswith("{"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON payload: {exc.msg}") from exc
            if not isinstance(payload, dict):
                raise ValueError("JSON payload must be an object")
            return payload

        return {"text": raw_text}

    async def to_user_message(self, raw_message: Any) -> UserMessage:
        payload = dict(raw_message) if isinstance(raw_message, dict) else {}
        chat_id = self._coerce_optional_text(payload.get("chat_id"))
        session_chat_id = self._coerce_optional_text(payload.get("session_chat_id"))
        if session_chat_id is None:
            session_chat_id = self._build_session_chat_id(chat_id)

        return UserMessage(
            text=self._coerce_optional_text(payload.get("text"), default="") or "",
            channel="web",
            chat_id=chat_id,
            session_chat_id=session_chat_id,
            sender_id=self._coerce_optional_text(payload.get("sender_id"), default="web-user"),
            sender_name=self._coerce_optional_text(payload.get("sender_name")),
            images=self._coerce_media_list(payload.get("images")),
            audios=self._coerce_media_list(payload.get("audios")),
            videos=self._coerce_media_list(payload.get("videos")),
            metadata=self._coerce_metadata(payload.get("metadata")),
            raw=payload,
        )

    async def send(self, message: AssistantMessage) -> None:
        session_chat_id = message.session_chat_id or self._build_session_chat_id(message.chat_id)
        ws = self._session_connections.get(session_chat_id)
        if ws is None or ws.closed:
            logger.warning("Web reply dropped because no active socket is bound to session {}", session_chat_id)
            return

        await ws.send_json(
            {
                "type": "message",
                "channel": "web",
                "chat_id": message.chat_id,
                "session_chat_id": session_chat_id,
                "text": message.text,
                "metadata": dict(message.metadata or {}),
            }
        )

    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({"ok": True, "channel": "web"})

    async def _handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        if self.mq is None:
            raise RuntimeError("WebAdapter requires a MessageQueue instance")

        ws = web.WebSocketResponse(max_msg_size=self._get_max_message_size())
        await ws.prepare(request)

        default_chat_id = (request.query.get("chat_id") or uuid4().hex).strip() or uuid4().hex
        default_session_chat_id = self._build_session_chat_id(default_chat_id)
        self._bind_session(default_session_chat_id, ws)

        await ws.send_json(
            {
                "type": "session",
                "channel": "web",
                "chat_id": default_chat_id,
                "session_chat_id": default_session_chat_id,
            }
        )

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        payload = self._parse_incoming_payload(msg.data)
                        payload_chat_id = self._coerce_optional_text(payload.get("chat_id"), default=default_chat_id)
                        payload["chat_id"] = payload_chat_id
                        payload.setdefault("session_chat_id", self._build_session_chat_id(payload_chat_id))
                        user_message = await self.to_user_message(payload)
                    except ValueError as exc:
                        await ws.send_json({"type": "error", "error": str(exc)})
                        continue

                    self._bind_session(user_message.session_chat_id or default_session_chat_id, ws)
                    await self.mq.enqueue(user_message)
                    continue

                if msg.type == WSMsgType.ERROR:
                    logger.warning("WebSocket connection closed with error: {}", ws.exception())
        finally:
            self._unbind_socket(ws)

        return ws

    async def _on_response(self, response: AssistantMessage, channel: str, chat_id: str | None) -> None:
        await self.send(response)

    async def _shutdown(self) -> None:
        for ws in list(self._socket_sessions):
            self._unbind_socket(ws)
            if not ws.closed:
                await ws.close()

        if self.mq is not None:
            self.mq.unregister_response_handler("web")

        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None

        self.site = None
        self.app = None

    async def run(self) -> None:
        if self.mq is None:
            raise RuntimeError("WebAdapter requires a MessageQueue instance")

        host = self._get_host()
        port = self._get_port()
        ws_path = self._get_path("path")
        health_path = self._get_path("health_path")

        self.app = web.Application()
        self.app.router.add_get(ws_path, self._handle_websocket)
        self.app.router.add_get(health_path, self._handle_health)

        self.mq.register_response_handler("web", self._on_response)
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host=host, port=port)
        await self.site.start()
        self._started_event.set()

        logger.info(
            "Web adapter listening on ws://{}:{}{} (health=http://{}:{}{})",
            host,
            self.bound_port,
            ws_path,
            host,
            self.bound_port,
            health_path,
        )

        try:
            await self._shutdown_event.wait()
        finally:
            await self._shutdown()
