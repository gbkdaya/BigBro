"""LLM provider registry. BigBro's 'brain' is pluggable — swap providers via BIGBRO_PROVIDER in .env.

Provider modes:
- free       (default) newest FREE tool-capable model on OpenRouter, auto-picked daily
- openrouter any specific OpenRouter model (set BIGBRO_MODEL)
- openai     OpenAI (or any OpenAI-compatible API via OPENAI_BASE_URL)
- anthropic  Claude
- gemini     Google Gemini
- ollama     fully local, offline
- mock       deterministic, for tests/demos
"""

import os

from .anthropic import AnthropicProvider
from .base import ChatResult, LLMProvider, ToolCall  # noqa: F401
from .gemini import GeminiProvider
from .mock import MockProvider
from .openai_compat import OpenAICompatProvider

OPENROUTER_KEY_HELP = (
    "OPENROUTER_API_KEY is not set. BigBro's free mode needs a FREE OpenRouter account "
    "(no credit card): create a key at https://openrouter.ai/keys and add OPENROUTER_API_KEY "
    "to .env — or use BIGBRO_PROVIDER=ollama for a fully local, zero-account brain."
)


def make_provider(cfg):
    provider = cfg.provider

    if provider in ("free", "openrouter"):
        base = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError(OPENROUTER_KEY_HELP)
        if provider == "free":
            from .free_model import resolve_free_model

            model, source = resolve_free_model()
            p = OpenAICompatProvider(base, key, model, cfg.temperature)
            p.model_source = "auto: latest free model (%s)" % source
            return p
        return OpenAICompatProvider(base, key, cfg.model_for_provider("openrouter"), cfg.temperature)

    if provider == "openai":
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env, or switch BIGBRO_PROVIDER "
                "(free / openrouter / anthropic / gemini / ollama / mock)."
            )
        return OpenAICompatProvider(base, key, cfg.model_for_provider("openai"), cfg.temperature)

    if provider == "ollama":
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        model = cfg.model_for_provider("ollama")
        return OpenAICompatProvider(base, "ollama", model, cfg.temperature, key_required=False)

    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env, or switch BIGBRO_PROVIDER "
                "(free / openai / gemini / ollama / mock)."
            )
        return AnthropicProvider(key, cfg.model_for_provider("anthropic"), cfg.temperature)

    if provider == "gemini":
        key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. Add it to .env, or switch "
                "BIGBRO_PROVIDER (free / openai / anthropic / ollama / mock)."
            )
        return GeminiProvider(key, cfg.model_for_provider("gemini"), cfg.temperature)

    if provider == "mock":
        return MockProvider()

    raise RuntimeError(
        f"Unknown BIGBRO_PROVIDER: '{provider}'. Valid: free, openrouter, openai, anthropic, gemini, ollama, mock."
    )
