import asyncio

from opensprite.media.router import MediaRouter
from opensprite.tools.video import AnalyzeVideoTool


class FakeVideoProvider:
    def __init__(self):
        self.calls = []

    async def analyze(self, instruction, video_data_url, *, model=None, max_tokens=2048):
        self.calls.append((instruction, video_data_url))
        return "video result"


def test_analyze_video_tool_uses_current_turn_videos():
    provider = FakeVideoProvider()
    tool = AnalyzeVideoTool(MediaRouter(video_provider=provider), get_current_videos=lambda: ["vid-a"])

    result = asyncio.run(tool.execute(instruction="describe the clip"))

    assert result == "video result"
    assert provider.calls == [("describe the clip", "vid-a")]


def test_analyze_video_tool_reports_when_provider_is_unavailable():
    tool = AnalyzeVideoTool(MediaRouter(), get_current_videos=lambda: None)

    result = asyncio.run(tool.execute(instruction="describe the clip"))

    assert result == MediaRouter.VIDEO_PROVIDER_UNAVAILABLE
