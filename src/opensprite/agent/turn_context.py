"""Current-turn ContextVar lifecycle helpers for AgentLoop."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator


class TurnContextService:
    """Activates task-local context for one user message turn."""

    def __init__(
        self,
        *,
        current_chat_id: ContextVar[str | None],
        current_channel: ContextVar[str | None],
        current_transport_chat_id: ContextVar[str | None],
        current_images: ContextVar[list[str] | None],
        current_audios: ContextVar[list[str] | None],
        current_videos: ContextVar[list[str] | None],
        current_outbound_media: ContextVar[dict[str, list[str]] | None],
        current_run_id: ContextVar[str | None],
    ):
        self._current_chat_id = current_chat_id
        self._current_channel = current_channel
        self._current_transport_chat_id = current_transport_chat_id
        self._current_images = current_images
        self._current_audios = current_audios
        self._current_videos = current_videos
        self._current_outbound_media = current_outbound_media
        self._current_run_id = current_run_id

    @contextmanager
    def activate(
        self,
        *,
        chat_id: str,
        channel: str | None,
        transport_chat_id: str | None,
        images: list[str] | None,
        audios: list[str] | None,
        videos: list[str] | None,
        run_id: str,
    ) -> Iterator[None]:
        """Set per-turn context values and reset them in reverse order."""
        token = self._current_chat_id.set(chat_id)
        channel_token = self._current_channel.set(channel)
        transport_chat_id_token = self._current_transport_chat_id.set(transport_chat_id)
        images_token = self._current_images.set(list(images or []))
        audios_token = self._current_audios.set(list(audios or []))
        videos_token = self._current_videos.set(list(videos or []))
        outbound_media_token = self._current_outbound_media.set(
            {"images": [], "voices": [], "audios": [], "videos": []}
        )
        run_token = self._current_run_id.set(run_id)
        try:
            yield
        finally:
            self._current_run_id.reset(run_token)
            self._current_outbound_media.reset(outbound_media_token)
            self._current_videos.reset(videos_token)
            self._current_audios.reset(audios_token)
            self._current_images.reset(images_token)
            self._current_transport_chat_id.reset(transport_chat_id_token)
            self._current_channel.reset(channel_token)
            self._current_chat_id.reset(token)
