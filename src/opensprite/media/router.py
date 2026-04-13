"""Routing helpers for media analysis providers."""

from __future__ import annotations

from .base import ImageAnalysisProvider, SpeechToTextProvider


class MediaRouter:
    """Route media analysis calls to configured providers."""

    IMAGE_PROVIDER_UNAVAILABLE = (
        "Error: image analysis is unavailable because no vision provider is configured."
    )
    SPEECH_PROVIDER_UNAVAILABLE = (
        "Error: audio transcription is unavailable because no speech provider is configured."
    )

    def __init__(
        self,
        *,
        image_provider: ImageAnalysisProvider | None = None,
        speech_provider: SpeechToTextProvider | None = None,
    ):
        self.image_provider = image_provider
        self.speech_provider = speech_provider

    async def analyze_image(
        self,
        instruction: str,
        images: list[str],
        *,
        image_index: int = 0,
        model: str | None = None,
        max_tokens: int = 2048,
    ) -> str:
        """Analyze one image from the current turn."""
        if self.image_provider is None:
            return self.IMAGE_PROVIDER_UNAVAILABLE
        if not images:
            return "Error: no images are available in the current turn."
        if image_index < 0 or image_index >= len(images):
            return f"Error: image_index {image_index} is out of range for {len(images)} image(s)."
        return await self.image_provider.analyze(
            instruction,
            [images[image_index]],
            model=model,
            max_tokens=max_tokens,
        )

    async def transcribe_audio(
        self,
        audios: list[str],
        *,
        audio_index: int = 0,
        model: str | None = None,
        language: str | None = None,
    ) -> str:
        """Transcribe one audio clip from the current turn."""
        if self.speech_provider is None:
            return self.SPEECH_PROVIDER_UNAVAILABLE
        if not audios:
            return "Error: no audio is available in the current turn."
        if audio_index < 0 or audio_index >= len(audios):
            return f"Error: audio_index {audio_index} is out of range for {len(audios)} audio clip(s)."
        return await self.speech_provider.transcribe(
            audios[audio_index],
            model=model,
            language=language,
        )
