"""Onboarding helpers for the OpenSprite CLI."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import dataclass, field
from getpass import getpass
from pathlib import Path
from typing import Any

from ..config import Config
from ..context.paths import (
    BOOTSTRAP_DIRNAME,
    MEMORY_DIRNAME,
    SKILLS_DIRNAME,
    WORKSPACE_DIRNAME,
    sync_templates,
)


LOGS_DIRNAME = "logs"
PROVIDER_CHOICES = ("openrouter", "openai", "minimax")
PROVIDER_MODEL_SUGGESTIONS = {
    "openrouter": "openai/gpt-4o-mini",
    "openai": "gpt-4.1-mini",
    "minimax": "MiniMax-M2.5",
}


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
    interactive: bool = False
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key_configured: bool = False
    telegram_enabled: bool = False
    telegram_token_configured: bool = False


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


def _prompt_choice(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Prompt the user to choose one item from a list."""
    labels = [str(choice) for choice in choices]
    mapping = {label.lower(): label for label in labels}

    while True:
        print(prompt)
        for index, label in enumerate(labels, start=1):
            marker = " (current)" if default == label else ""
            print(f"  {index}. {label}{marker}")

        suffix = f" [default: {default}]" if default else ""
        raw = input(f"> Select an option by number or name{suffix}: ").strip()
        if not raw and default:
            return default
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(labels):
                return labels[idx - 1]
        chosen = mapping.get(raw.lower())
        if chosen:
            return chosen
        print("Please choose one of the listed options.\n")


def _prompt_text(prompt: str, default: str | None = None, *, allow_empty: bool = True) -> str:
    """Prompt for plain text input."""
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"> {prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if allow_empty:
            return ""
        print("This value is required.\n")


def _prompt_secret(prompt: str, current_value: str = "", *, required: bool = False) -> str:
    """Prompt for a secret value without echoing it."""
    if current_value:
        print(f"{prompt}: currently configured. Press Enter to keep the current value.")
    elif not required:
        print(f"{prompt}: press Enter to leave it unset for now.")

    while True:
        value = getpass(f"> {prompt}: ").strip()
        if value:
            return value
        if current_value:
            return current_value
        if not required:
            return ""
        print("This value is required.\n")


def _prompt_yes_no(prompt: str, default: bool) -> bool:
    """Prompt for a yes/no answer."""
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        value = input(f"> {prompt} {suffix}: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer yes or no.\n")


def _require_tty() -> None:
    """Ensure interactive onboarding only runs on a real terminal."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError(
            "Interactive onboarding requires a TTY. Re-run with `opensprite onboard --no-input` for automation."
        )


def _prepare_config_data(result: OnboardResult, config_path: Path, force: bool) -> dict[str, Any]:
    """Create or refresh the config scaffold and return the working data."""
    defaults = Config.load_template_data()
    if config_path.exists():
        existing = _load_json(config_path)
        if force:
            data = copy.deepcopy(defaults)
            result.reset_config = True
        else:
            data = _merge_missing_defaults(existing, defaults)
            if data != existing:
                result.refreshed_config = True
    else:
        data = copy.deepcopy(defaults)
        result.created_config = True

    _write_json(config_path, data)
    return data


def _get_selected_provider(config_data: dict[str, Any]) -> str | None:
    """Return the currently selected provider, if valid."""
    llm = config_data.get("llm", {})
    providers = llm.get("providers", {})
    default = llm.get("default")
    if isinstance(default, str) and default in providers:
        return default

    for provider_name in PROVIDER_CHOICES:
        provider = providers.get(provider_name, {})
        if isinstance(provider, dict) and (provider.get("enabled") or provider.get("api_key")):
            return provider_name
    return None


def _show_summary(config_data: dict[str, Any]) -> None:
    """Print a short configuration summary before saving."""
    llm = config_data.get("llm", {})
    providers = llm.get("providers", {})
    provider_name = _get_selected_provider(config_data)
    provider = providers.get(provider_name, {}) if provider_name else {}
    telegram = config_data.get("channels", {}).get("telegram", {})

    print("\nOpenSprite configuration summary")
    print(f"- LLM provider: {provider_name or '<unset>'}")
    print(f"- Model: {provider.get('model') or '<unset>'}")
    print(f"- API key: {'configured' if provider.get('api_key') else 'not set'}")
    print(f"- Telegram: {'enabled' if telegram.get('enabled') else 'disabled'}")
    print(f"- Telegram token: {'configured' if telegram.get('token') else 'not set'}")
    print("")


def _run_interactive_setup(config_data: dict[str, Any]) -> dict[str, Any]:
    """Interactively collect the minimum required runtime settings."""
    updated = copy.deepcopy(config_data)
    llm = updated.setdefault("llm", {})
    providers = llm.setdefault("providers", {})
    for provider_name in PROVIDER_CHOICES:
        providers.setdefault(provider_name, {})

    current_provider = _get_selected_provider(updated)
    provider_name = _prompt_choice(
        "Choose the LLM provider you want OpenSprite to use:",
        list(PROVIDER_CHOICES),
        default=current_provider,
    )

    llm["default"] = provider_name
    for name, provider in providers.items():
        if isinstance(provider, dict):
            provider["enabled"] = name == provider_name

    selected = providers[provider_name]
    if not isinstance(selected, dict):
        raise ValueError(f"Invalid provider configuration for {provider_name}")

    default_model = selected.get("model") or PROVIDER_MODEL_SUGGESTIONS.get(provider_name)
    selected["model"] = _prompt_text("Model", default=default_model, allow_empty=False)
    selected["api_key"] = _prompt_secret("API key", str(selected.get("api_key", "")), required=True)

    channels = updated.setdefault("channels", {})
    telegram = channels.setdefault("telegram", {})
    enable_telegram = _prompt_yes_no(
        "Enable Telegram integration now?",
        bool(telegram.get("enabled", False)),
    )
    telegram["enabled"] = enable_telegram
    if enable_telegram:
        telegram["token"] = _prompt_secret(
            "Telegram bot token",
            str(telegram.get("token", "")),
            required=True,
        )

    _show_summary(updated)
    if not _prompt_yes_no("Save these settings?", True):
        print("Interactive changes discarded; keeping the current config file.\n")
        return config_data

    return updated


def _apply_result_snapshot(result: OnboardResult, config_data: dict[str, Any], interactive: bool) -> None:
    """Populate summary fields on the onboarding result."""
    llm = config_data.get("llm", {})
    providers = llm.get("providers", {})
    provider_name = _get_selected_provider(config_data)
    provider = providers.get(provider_name, {}) if provider_name else {}
    telegram = config_data.get("channels", {}).get("telegram", {})

    result.interactive = interactive
    result.llm_provider = provider_name
    if isinstance(provider, dict):
        result.llm_model = provider.get("model") or None
    else:
        result.llm_model = None
    result.llm_api_key_configured = bool(provider.get("api_key")) if isinstance(provider, dict) else False
    result.telegram_enabled = bool(telegram.get("enabled")) if isinstance(telegram, dict) else False
    result.telegram_token_configured = bool(telegram.get("token")) if isinstance(telegram, dict) else False


def run_onboard(
    config_path: str | Path | None = None,
    *,
    force: bool = False,
    interactive: bool = True,
) -> OnboardResult:
    """Initialize or refresh the default OpenSprite app directories and config."""
    resolved_config = _resolve_config_path(config_path)
    app_home = (Path.home() / ".opensprite").resolve()
    result = OnboardResult(config_path=resolved_config, app_home=app_home)

    _ensure_dir(app_home, result.created_dirs)
    _ensure_dir(app_home / LOGS_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / BOOTSTRAP_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / MEMORY_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / SKILLS_DIRNAME, result.created_dirs)
    _ensure_dir(app_home / WORKSPACE_DIRNAME, result.created_dirs)

    config_data = _prepare_config_data(result, resolved_config, force)
    result.template_files = sync_templates(app_home)

    if interactive:
        _require_tty()
        try:
            updated = _run_interactive_setup(config_data)
        except (EOFError, KeyboardInterrupt) as exc:
            raise RuntimeError("Interactive onboarding cancelled.") from exc
        if updated != config_data:
            _write_json(resolved_config, updated)
        config_data = updated

    _apply_result_snapshot(result, config_data, interactive=interactive)
    return result
