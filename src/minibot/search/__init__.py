"""Search index providers."""

from minibot.search.base import SearchHit, SearchStore

__all__ = ["SearchHit", "SearchStore", "LanceDBSearchStore"]


def __getattr__(name: str):
    """Lazily import optional search backends."""
    if name == "LanceDBSearchStore":
        from minibot.search.lancedb_store import LanceDBSearchStore

        return LanceDBSearchStore
    raise AttributeError(f"module 'minibot.search' has no attribute {name!r}")
