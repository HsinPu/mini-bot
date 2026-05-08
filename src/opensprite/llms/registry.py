"""opensprite/llms/registry.py - LLM Provider Registry

用 Registry 模式管理所有 LLM Provider，方便擴充。
"""

from dataclasses import dataclass
from .base import LLMProvider
from .anthropic_messages import AnthropicMessagesLLM
from .openai import OpenAILLM
from .openai_responses import OpenAIResponsesLLM
from .openrouter import OpenRouterLLM
from .minimax import MiniMaxLLM
from ..auth.copilot import COPILOT_BASE_URL, copilot_request_headers


@dataclass(frozen=True)
class ProviderSpec:
    """單一 LLM Provider 的元數據"""
    name: str
    keywords: tuple[str, ...]
    detect_by_key_prefix: str = ""
    detect_by_base_keyword: str = ""
    default_base_url: str = ""


PROVIDERS = (
    ProviderSpec("openrouter", ("openrouter",), "sk-or-", "openrouter", "https://openrouter.ai/api/v1"),
    ProviderSpec("openai", ("gpt", "openai"), "", "", "https://api.openai.com/v1"),
    ProviderSpec("minimax", ("minimax",), "", "minimax", "https://api.minimax.io/v1"),
    ProviderSpec("copilot", ("copilot",), "", "githubcopilot", COPILOT_BASE_URL),
)


def find_provider(api_key: str = "", base_url: str = "", model: str = "", provider_name: str = "") -> ProviderSpec:
    """自動判斷要用哪個 Provider"""
    # 1. 直接指定
    for spec in PROVIDERS:
        if provider_name == spec.name:
            return spec
    # 2. API Key 前綴
    if api_key.startswith("sk-or-"):
        return PROVIDERS[0]  # openrouter
    # 3. base_url 關鍵字
    if "openrouter" in base_url:
        return PROVIDERS[0]
    if "minimax" in base_url:
        return PROVIDERS[2]  # minimax
    if "githubcopilot" in base_url:
        return PROVIDERS[3]  # copilot
    # 4. model 關鍵字
    if "gpt" in model.lower():
        return PROVIDERS[1]  # openai
    if "minimax" in model.lower():
        return PROVIDERS[2]  # minimax
    # 預設
    return PROVIDERS[1]  # openai


def create_llm(
    api_key: str,
    model: str,
    base_url: str = "",
    provider_name: str = "",
    enabled: bool = True,
    api_mode: str | None = None,
    auth_type: str = "api_key",
    reasoning_enabled: bool = False,
    reasoning_effort: str | None = None,
    reasoning_max_tokens: int | None = None,
    reasoning_exclude: bool = False,
    provider_sort: str | None = None,
    require_parameters: bool = False,
    request_options: tuple[str, ...] | None = None,
) -> LLMProvider:
    """建立 LLM Provider"""
    if not enabled:
        raise ValueError(f"Provider {provider_name} is disabled")

    if api_mode == "responses" or auth_type == "openai_codex_oauth":
        return OpenAIResponsesLLM(api_key=api_key, base_url=base_url, default_model=model)
    if api_mode == "anthropic_messages":
        return AnthropicMessagesLLM(
            api_key=api_key,
            base_url=base_url,
            default_model=model,
            reasoning_enabled=reasoning_enabled,
            reasoning_effort=reasoning_effort,
        )
    
    spec = find_provider(api_key, base_url, model, provider_name)
    
    if spec.name == "openrouter":
        effective_options = set(
            request_options if request_options is not None else ("reasoning", "provider_sort", "require_parameters")
        )
        return OpenRouterLLM(
            api_key=api_key,
            default_model=model,
            base_url=base_url,
            reasoning_enabled=reasoning_enabled if "reasoning" in effective_options else False,
            reasoning_effort=reasoning_effort if "reasoning" in effective_options else None,
            reasoning_max_tokens=reasoning_max_tokens if "reasoning" in effective_options else None,
            reasoning_exclude=reasoning_exclude if "reasoning" in effective_options else False,
            provider_sort=provider_sort if "provider_sort" in effective_options else None,
            require_parameters=require_parameters if "require_parameters" in effective_options else False,
        )
    
    if spec.name == "minimax":
        return MiniMaxLLM(api_key=api_key, default_model=model, base_url=base_url or spec.default_base_url)

    if spec.name == "copilot":
        return OpenAILLM(
            api_key=api_key,
            base_url=base_url or spec.default_base_url,
            default_model=model,
            default_headers=copilot_request_headers(),
        )
     
    return OpenAILLM(api_key=api_key, base_url=base_url or spec.default_base_url, default_model=model)
