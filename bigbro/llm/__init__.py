"""LLM provider registry. BigBro's 'brain' is pluggable — swap providers via BIGBRO_PROVIDER in .env."""

import os

from .anthropic import AnthropicProvider
from .base import ChatResult, LLMProvider, ToolCall  # noqa: F401
from .gemini import GeminiProvider
from .mock import MockProvider
from .openai_compat import OpenAICompatProvider


def make_provider(cfg):
    provider = cfg.provider

    if provider == "openai":
        base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to .env, or switch BIGBRO_PROVIDER "
                "(anthropic / gemini / ollama / mock)."
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
                "(openai / gemini / ollama / mock)."
            )
        return AnthropicProvider(key, cfg.model_for_provider("anthropic"), cfg.temperature)

    if provider == "gemini":
        key = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set. Add it to .env, or switch "
                "BIGBRO_PROVIDER (openai / anthropic / ollama / mock)."
            )
        return GeminiProvider(key, cfg.model_for_provider("gemini"), cfg.temperature)

    if provider == "mock":
        return MockProvider()

    raise RuntimeError(f"Unknown BIGBRO_PROVIDER: '{provider}'. Valid: openai, anthropic, gemini, ollama, mock.")
