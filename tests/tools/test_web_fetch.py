import json
import asyncio

from opensprite.tools.web_fetch import WebFetchTool


class _FakeFetcher:
    timeout = 30
    prefer_trafilatura = True
    firecrawl_api_key = None

    def fetch(self, url: str):
        return {
            "url": url,
            "finalUrl": f"{url}?ref=1",
            "status": 200,
            "title": "SQLite FTS5",
            "extractor": "trafilatura",
            "contentType": "text/html",
            "truncated": False,
            "text": "SQLite FTS5 supports full text search.",
        }


def test_web_fetch_returns_unified_web_payload(monkeypatch):
    monkeypatch.setattr("opensprite.tools.web_fetch.WebFetcher", lambda *args, **kwargs: _FakeFetcher())
    tool = WebFetchTool()

    payload = json.loads(asyncio.run(tool._execute("https://sqlite.org/fts5.html")))

    assert payload == {
        "type": "web_fetch",
        "query": "https://sqlite.org/fts5.html",
        "url": "https://sqlite.org/fts5.html",
        "final_url": "https://sqlite.org/fts5.html?ref=1",
        "title": "SQLite FTS5",
        "content": "SQLite FTS5 supports full text search.",
        "summary": "SQLite FTS5",
        "provider": "web_fetch",
        "extractor": "trafilatura",
        "status": 200,
        "content_type": "text/html",
        "truncated": False,
        "items": [],
    }
