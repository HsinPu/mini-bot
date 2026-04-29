"""Load packaged LLM provider presets for Web settings."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources
from typing import Any


@dataclass(frozen=True)
class ProviderPreset:
    """Preset fields for one LLM vendor."""

    default_base_url: str
    model_choices: tuple[str, ...]
    display_name: str | None = None


@dataclass(frozen=True)
class LLMPresets:
    """Bundled llm-presets.json content."""

    version: int
    provider_order: tuple[str, ...]
    providers: dict[str, ProviderPreset]


def _parse_providers(raw: dict[str, Any]) -> dict[str, ProviderPreset]:
    out: dict[str, ProviderPreset] = {}
    for name, entry in raw.items():
        if not isinstance(entry, dict):
            raise ValueError(f'llm-presets: providers["{name}"] must be an object')
        base = entry.get("default_base_url")
        if not isinstance(base, str) or not base.strip():
            raise ValueError(f'llm-presets: providers["{name}"].default_base_url is required')
        models = entry.get("model_choices", [])
        if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
            raise ValueError(f'llm-presets: providers["{name}"].model_choices must be a string array')
        dn = entry.get("display_name")
        display = str(dn).strip() if isinstance(dn, str) and dn.strip() else None
        out[name] = ProviderPreset(
            default_base_url=base.strip(),
            model_choices=tuple(models),
            display_name=display,
        )
    return out


def load_llm_presets() -> LLMPresets:
    """Read and validate ``llm-presets.json`` shipped inside ``opensprite.config``."""
    path = resources.files("opensprite.config").joinpath("llm-presets.json")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("llm-presets.json must contain a JSON object")

    version = data.get("version", 1)
    if not isinstance(version, int):
        raise ValueError("llm-presets.json: version must be an integer")

    order = data.get("provider_order", [])
    if not isinstance(order, list) or not order or not all(isinstance(x, str) for x in order):
        raise ValueError("llm-presets.json: provider_order must be a non-empty string array")

    raw_providers = data.get("providers", {})
    if not isinstance(raw_providers, dict):
        raise ValueError("llm-presets.json: providers must be an object")

    providers = _parse_providers(raw_providers)
    for name in order:
        if name not in providers:
            raise ValueError(f'llm-presets.json: provider_order entry "{name}" missing from providers')

    return LLMPresets(version=version, provider_order=tuple(order), providers=providers)
