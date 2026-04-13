import asyncio

from opensprite.media.router import MediaRouter
from opensprite.tools.audio import TranscribeAudioTool


class FakeSpeechProvider:
    def __init__(self):
        self.calls = []

    async def transcribe(self, audio_data_url, *, model=None, language=None):
        self.calls.append((audio_data_url, model, language))
        return "hello world"


def test_transcribe_audio_tool_uses_current_turn_audio():
    provider = FakeSpeechProvider()
    tool = TranscribeAudioTool(MediaRouter(speech_provider=provider), get_current_audios=lambda: ["aud-a"]) 

    result = asyncio.run(tool.execute(language="en"))

    assert result == "hello world"
    assert provider.calls == [("aud-a", None, "en")]


def test_transcribe_audio_tool_reports_when_provider_is_unavailable():
    tool = TranscribeAudioTool(MediaRouter(), get_current_audios=lambda: None)

    result = asyncio.run(tool.execute())

    assert result == MediaRouter.SPEECH_PROVIDER_UNAVAILABLE
