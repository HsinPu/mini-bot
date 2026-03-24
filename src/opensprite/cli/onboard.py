"""Onboarding helpers for the OpenSprite CLI."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import Config
from ..context.paths import (
    BOOTSTRAP_DIRNAME,
    MEMORY_DIRNAME,
    OPENSPRITE_HOME,
    SKILLS_DIRNAME,
    WORKSPACE_DIRNAME,
    sync_templates,
)


LOGS_DIRNAME = "logs"


@dataclass
class OnboardResult:
    """Structured result for an onboarding run."""

    config_path: Path
    app_home: Path
    created_config: bool = False
    refreshed_config: bool = False
    reset_config: bool = False
    created_dirs: list[Path] = field(default_factory=list)
    template_files: list[str] = field(default_factory=list)


def _resolve_config_path(config_path: str | Path | None = None) -> Path:
    """Resolve a config path or fall back to the default app config."""
    if config_path is None:
        return (Path.home() / ".opensprite" / "opensprite.json").resolve()
    return Path(config_path).expanduser().resolve()


def _ensure_dir(path: Path, created_dirs: list[Path]) -> Path:
    """Ensure a directory exists while tracking newly created paths."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        created_dirs.append(path)
    return path


def _merge_missing_defaults(existing: Any, defaults: Any) -> Any:
    """Recursively fill missing keys from defaults without overwriting values."""
    if not isinstance(existing, dict) or not isinstance(defaults, dict):
        return existing

    merged = dict(existing)
    for key, value in defaults.items():
        if key not in merged:
            merged[key] = value
        else:
            merged[key] = _merge_missing_defaults(merged[key], value)
    return merged


def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file as a dictionary."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a JSON object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Write a JSON dictionary to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_onboard(
    config_path: str | Path | None = None,
    *,
    force: bool = False,
) -> OnboardResult:
    """Initialize or refresh the default OpenSprite app directories and config."""
    resolved_config = _resolve_config_path(config_path)
    app_home = OPENSPRITE_HOME.resolve()
    result = OnboardResult(config_path=resolved_config, app_home=app_home)

    _ensure_dir(app_home, result.created_dirs)
    _ensure_dir(app_home / LOGS_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / BOOTSTRAP_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / MEMORY_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / SKILLS_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / WORKSPACE_DIRNAME, result.created_dirs)

    defaults = Config.load_template_data()
    if resolved_config.exists():
        existing = _load_json(resolved_config)
        if force:
            _write_json(resolved_config, defaults)
            result.reset_config = True
        else:
            merged = _merge_missing_defaults(existing, defaults)
            if merged != existing:
                _write_json(resolved_config, merged)
                result.refreshed_config = True
    else:
        _write_json(resolved_config, defaults)
        result.created_config = True

    result.template_files = sync_templates(app_home)
    return result
