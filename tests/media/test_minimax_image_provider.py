import asyncio

import httpx

from opensprite.media.image import MiniMaxImageProvider, create_image_analysis_provider


def test_minimax_image_provider_posts_to_coding_plan_vlm_endpoint():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"content": "a receipt"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    provider = MiniMaxImageProvider(
        api_key="secret-key",
        base_url="https://api.minimax.io/v1",
        client=client,
    )

    result = asyncio.run(provider.analyze("What is this?", ["data:image/jpeg;base64,abc"]))
    asyncio.run(client.aclose())

    assert result == "a receipt"
    assert len(requests) == 1
    request = requests[0]
    assert str(request.url) == "https://api.minimax.io/v1/coding_plan/vlm"
    assert request.headers["authorization"] == "Bearer secret-key"
    assert request.read().decode("utf-8") == '{"prompt":"What is this?","image_url":"data:image/jpeg;base64,abc"}'


def test_minimax_image_provider_normalizes_cn_base_url():
    provider = MiniMaxImageProvider(api_key="secret-key", base_url="https://api.minimaxi.com/v1")

    assert provider.endpoint == "https://api.minimaxi.com/v1/coding_plan/vlm"


def test_create_image_analysis_provider_uses_minimax_provider_for_minimax_ids():
    provider = create_image_analysis_provider(
        provider="minimax-cn",
        api_key="secret-key",
        default_model="MiniMax-VL-01",
        base_url="https://api.minimaxi.com/v1",
    )

    assert isinstance(provider, MiniMaxImageProvider)
