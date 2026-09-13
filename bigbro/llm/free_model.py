"""'free' model mode — always use the newest free models that support tool calling.

Source: OpenRouter's public model list (no auth needed to read it). Free models
carry zero pricing; we additionally require 'tools' in supported_parameters
because BigBro drives everything through tool calls.

Resolution order at startup:
1. Fresh cache (last 24h)            → use it
2. Live fetch of the model list      → newest free + tool-capable models, write cache
3. Fallback constant (kept current)  → used when offline

If the newest free model is rate-limited, FreeModelProvider automatically
fails over to the next-newest free model for the rest of the session.
"""

import json
import time

import requests

from ..config import PROJECT_ROOT
from .base import LLMProvider
from .openai_compat import OpenAICompatProvider, ProviderTransientError, RateLimitedError

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
CACHE_FILE = PROJECT_ROOT / ".free_model_cache.json"
CACHE_TTL = 86400  # re-check "what's the latest free model" once a day
CANDIDATE_LIMIT = 5  # how many newest free models to keep on standby
# Newest free + tool-capable model as of 2026-09-13 (offline fallback; keep updated)
FALLBACK_FREE_MODEL = "inclusionai/ling-3.0-flash-vl:free"


def _is_free(model: dict) -> bool:
    pricing = model.get("pricing", {})
    try:
        return float(pricing.get("prompt", 1) or 1) == 0 and float(pricing.get("completion", 1) or 1) == 0
    except (TypeError, ValueError):
        return False


def _fetch_candidates(timeout: int = 20, limit: int = CANDIDATE_LIMIT):
    r = requests.get(OPENROUTER_MODELS_URL, timeout=timeout)
    r.raise_for_status()
    picked = []
    for m in r.json().get("data", []):
        if not _is_free(m):
            continue
        if "tools" not in (m.get("supported_parameters") or []):
            continue
        picked.append((m.get("created", 0), m["id"]))
    picked.sort(reverse=True)
    return [mid for _, mid in picked][:limit]


def pick_latest_free_model(timeout: int = 20) -> str | None:
    """Return the newest free model with tools support (or None)."""
    cands = _fetch_candidates(timeout=timeout, limit=1)
    return cands[0] if cands else None


def resolve_free_candidates(cache_file=CACHE_FILE, max_age: int = CACHE_TTL,
                            limit: int = CANDIDATE_LIMIT):
    """Return (candidates, source) — candidates newest-first. source: cache|live|fallback."""
    if cache_file is not None and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if data.get("candidates") and time.time() - data.get("ts", 0) < max_age:
                return data["candidates"], "cache"
        except (json.JSONDecodeError, OSError):
            pass
    try:
        cands = _fetch_candidates(limit=limit)
        if cands:
            if cache_file is not None:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps({"ts": time.time(), "model": cands[0], "candidates": cands}))
                except OSError:
                    pass
            return cands, "live"
    except Exception:
        pass
    return [FALLBACK_FREE_MODEL], "fallback"


def resolve_free_model(cache_file=CACHE_FILE, max_age: int = CACHE_TTL):
    """Return (model_id, source) for the newest free model."""
    cands, source = resolve_free_candidates(cache_file, max_age)
    return cands[0], source


class FreeModelProvider(LLMProvider):
    """Brain for 'free' mode: newest free model first, automatic failover when a model is
    rate-limited or its upstream provider misbehaves."""

    name = "free"
    model_source = ""

    def __init__(self, base_url: str, api_key: str, candidates: list, temperature: float = 0.2,
                 source: str = ""):
        self._providers = [OpenAICompatProvider(base_url, api_key, m, temperature) for m in candidates]
        self._idx = 0
        self.model = candidates[0]
        self.model_source = f"auto: latest free model ({source})" if source else "auto: latest free model"

    def chat(self, messages, tools):
        for i in range(len(self._providers)):
            idx = (self._idx + i) % len(self._providers)
            p = self._providers[idx]
            try:
                result = p.chat(messages, tools)
                self._idx = idx
                self.model = p.model
                return result
            except (RateLimitedError, ProviderTransientError):
                continue
        raise RuntimeError(
            "All free models are currently unavailable (rate-limited — the OpenRouter free "
            "tier allows ~50 requests/day without credits and resets daily — or their upstream "
            "providers are having issues). Wait a few minutes and try again, or pin a specific "
            "free model with BIGBRO_MODEL in .env."
        )
