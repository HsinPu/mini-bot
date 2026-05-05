"""GitHub Copilot token helpers."""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from typing import Any


COPILOT_BASE_URL = "https://api.githubcopilot.com"
COPILOT_MODELS_URL = f"{COPILOT_BASE_URL}/models"
COPILOT_TOKEN_EXCHANGE_URL = "https://api.github.com/copilot_internal/v2/token"
COPILOT_EDITOR_VERSION = "vscode/1.104.1"
COPILOT_EXCHANGE_USER_AGENT = "GitHubCopilotChat/0.26.7"
COPILOT_REQUEST_USER_AGENT = "OpenSprite/0.1"
COPILOT_TOKEN_REFRESH_MARGIN_SECONDS = 120

_CLASSIC_PAT_PREFIX = "ghp_"
_SUPPORTED_PREFIXES = ("gho_", "github_pat_", "ghu_")
_TOKEN_CACHE: dict[str, tuple[str, float]] = {}


class CopilotAuthError(RuntimeError):
    """Raised when a GitHub token cannot be used for Copilot."""


def validate_copilot_token(token: str) -> None:
    normalized = str(token or "").strip()
    if not normalized:
        raise CopilotAuthError("GitHub Copilot token is required.")
    if normalized.startswith(_CLASSIC_PAT_PREFIX):
        raise CopilotAuthError(
            "Classic GitHub PATs (ghp_*) are not supported by the Copilot API. "
            "Use a GitHub OAuth token, GitHub App token, or fine-grained PAT with Copilot access."
        )


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def exchange_copilot_token(raw_token: str, *, timeout_seconds: float = 10.0) -> tuple[str, float]:
    """Exchange a GitHub token for a short-lived Copilot API token."""
    validate_copilot_token(raw_token)
    normalized = raw_token.strip()
    fingerprint = _token_fingerprint(normalized)
    cached = _TOKEN_CACHE.get(fingerprint)
    if cached:
        api_token, expires_at = cached
        if time.time() < expires_at - COPILOT_TOKEN_REFRESH_MARGIN_SECONDS:
            return api_token, expires_at

    request = urllib.request.Request(
        COPILOT_TOKEN_EXCHANGE_URL,
        method="GET",
        headers={
            "Authorization": f"token {normalized}",
            "User-Agent": COPILOT_EXCHANGE_USER_AGENT,
            "Accept": "application/json",
            "Editor-Version": COPILOT_EDITOR_VERSION,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=max(5.0, float(timeout_seconds))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise CopilotAuthError(f"GitHub Copilot token exchange failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise CopilotAuthError("GitHub Copilot token exchange returned invalid JSON.")
    api_token = str(payload.get("token") or "").strip()
    if not api_token:
        raise CopilotAuthError("GitHub Copilot token exchange returned no token.")
    try:
        expires_at = float(payload.get("expires_at") or 0)
    except (TypeError, ValueError):
        expires_at = 0
    if expires_at <= 0:
        expires_at = time.time() + 1800
    _TOKEN_CACHE[fingerprint] = (api_token, expires_at)
    return api_token, expires_at


def copilot_request_headers(*, is_vision: bool = False) -> dict[str, str]:
    headers = {
        "Editor-Version": COPILOT_EDITOR_VERSION,
        "User-Agent": COPILOT_REQUEST_USER_AGENT,
        "Copilot-Integration-Id": "vscode-chat",
        "Openai-Intent": "conversation-edits",
        "x-initiator": "agent",
    }
    if is_vision:
        headers["Copilot-Vision-Request"] = "true"
    return headers


def _copilot_catalog_item_is_text_model(item: dict[str, Any]) -> bool:
    model_id = str(item.get("id") or "").strip()
    if not model_id:
        return False
    if item.get("model_picker_enabled") is False:
        return False
    capabilities = item.get("capabilities")
    if isinstance(capabilities, dict):
        model_type = str(capabilities.get("type") or "").strip().lower()
        if model_type and model_type != "chat":
            return False
    endpoints = item.get("supported_endpoints")
    if isinstance(endpoints, list):
        normalized = {str(endpoint).strip() for endpoint in endpoints if str(endpoint).strip()}
        if normalized and not normalized.intersection({"/chat/completions", "/responses", "/v1/messages"}):
            return False
    return True


def fetch_copilot_models(api_key: str, *, timeout_seconds: float = 8.0) -> list[str]:
    """Fetch the live GitHub Copilot model catalog for this account."""
    token, _expires_at = exchange_copilot_token(api_key, timeout_seconds=timeout_seconds)
    request = urllib.request.Request(
        COPILOT_MODELS_URL,
        headers={**copilot_request_headers(), "Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(request, timeout=max(5.0, float(timeout_seconds))) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []
    items = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return []
    seen: set[str] = set()
    models: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not _copilot_catalog_item_is_text_model(item):
            continue
        model_id = str(item.get("id") or "").strip()
        if model_id and model_id not in seen:
            seen.add(model_id)
            models.append(model_id)
    return models
