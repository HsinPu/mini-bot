import asyncio
from types import SimpleNamespace

from opensprite.channels.telegram import TelegramAdapter


class FakeFile:
    def __init__(self, payload: bytes):
        self._payload = payload

    async def download_as_bytearray(self):
        return bytearray(self._payload)


class FakeBot:
    async def get_file(self, file_id):
        return FakeFile(b"audio-bytes")


def test_telegram_adapter_downloads_voice_message_as_audio_data_url():
    async def scenario():
        adapter = TelegramAdapter("token")
        update = SimpleNamespace(
            update_id=1,
            bot=FakeBot(),
            message=SimpleNamespace(
                text=None,
                caption=None,
                from_user=SimpleNamespace(id=1, username="alice", full_name="Alice"),
                chat=SimpleNamespace(id=123, type="private"),
                message_id=7,
                photo=None,
                voice=SimpleNamespace(file_id="voice-1", mime_type="audio/ogg"),
                audio=None,
            ),
        )
        return await adapter.to_user_message(update)

    user_message = asyncio.run(scenario())

    assert user_message.audios is not None
    assert len(user_message.audios) == 1
    assert user_message.audios[0].startswith("data:audio/ogg;base64,")


def test_telegram_adapter_downloads_video_message_as_video_data_url():
    async def scenario():
        adapter = TelegramAdapter("token")
        update = SimpleNamespace(
            update_id=1,
            bot=FakeBot(),
            message=SimpleNamespace(
                text=None,
                caption=None,
                from_user=SimpleNamespace(id=1, username="alice", full_name="Alice"),
                chat=SimpleNamespace(id=123, type="private"),
                message_id=7,
                photo=None,
                voice=None,
                audio=None,
                video=SimpleNamespace(file_id="video-1", mime_type="video/mp4"),
                video_note=None,
                animation=None,
            ),
        )
        return await adapter.to_user_message(update)

    user_message = asyncio.run(scenario())

    assert user_message.videos is not None
    assert len(user_message.videos) == 1
    assert user_message.videos[0].startswith("data:video/mp4;base64,")
