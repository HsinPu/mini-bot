import json

import pytest

from opensprite.auth import copilot


def test_validate_copilot_token_rejects_classic_pat():
    with pytest.raises(copilot.CopilotAuthError, match="Classic GitHub PATs"):
        copilot.validate_copilot_token("ghp_classic")


def test_exchange_copilot_token_uses_cache(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"token": "copilot-api-token", "expires_at": 4_000_000_000}).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        calls.append((request.full_url, request.headers, timeout))
        return FakeResponse()

    monkeypatch.setattr(copilot.urllib.request, "urlopen", fake_urlopen)
    copilot._TOKEN_CACHE.clear()

    first = copilot.exchange_copilot_token("gho_raw")
    second = copilot.exchange_copilot_token("gho_raw")

    assert first == ("copilot-api-token", 4_000_000_000.0)
    assert second == first
    assert len(calls) == 1
    assert calls[0][0] == "https://api.github.com/copilot_internal/v2/token"
    assert calls[0][1]["Authorization"] == "token gho_raw"


def test_fetch_copilot_models_filters_catalog(monkeypatch):
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps(
                {
                    "data": [
                        {"id": "gpt-live", "capabilities": {"type": "chat"}},
                        {"id": "hidden", "model_picker_enabled": False},
                        {"id": "embed", "capabilities": {"type": "embedding"}},
                        {"id": "unsupported", "supported_endpoints": ["/embeddings"]},
                        {"id": "gpt-live", "capabilities": {"type": "chat"}},
                    ]
                }
            ).encode("utf-8")

    monkeypatch.setattr(copilot, "exchange_copilot_token", lambda api_key, timeout_seconds=8.0: ("api-token", 1_000))
    monkeypatch.setattr(copilot.urllib.request, "urlopen", lambda request, timeout=None: FakeResponse())

    assert copilot.fetch_copilot_models("gho_raw") == ["gpt-live"]
