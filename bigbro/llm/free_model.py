"""'free' model mode — always use the newest free model that supports tool calling.

Source: OpenRouter's public model list (no auth needed to read it). Free models
carry zero pricing; we additionally require 'tools' in supported_parameters
because BigBro drives everything through tool calls.

Resolution order at startup:
1. Fresh cache (last 24h)            → use it
2. Live fetch of the model list      → newest free + tool-capable model, write cache
3. Fallback constant (kept current)  → used when offline
"""

import json
import time

import requests

from ..config import PROJECT_ROOT

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
CACHE_FILE = PROJECT_ROOT / ".free_model_cache.json"
CACHE_TTL = 86400  # re-check "what's the latest free model" once a day
# Newest free + tool-capable model as of 2026-09-13 (offline fallback; keep updated)
FALLBACK_FREE_MODEL = "inclusionai/ling-3.0-flash-vl:free"


def _is_free(model: dict) -> bool:
    pricing = model.get("pricing", {})
    try:
        return float(pricing.get("prompt", 1) or 1) == 0 and float(pricing.get("completion", 1) or 1) == 0
    except (TypeError, ValueError):
        return False


def pick_latest_free_model(timeout: int = 20) -> str | None:
    """Fetch the live model list and return the newest free model with tools support."""
    r = requests.get(OPENROUTER_MODELS_URL, timeout=timeout)
    r.raise_for_status()
    candidates = []
    for m in r.json().get("data", []):
        if not _is_free(m):
            continue
        if "tools" not in (m.get("supported_parameters") or []):
            continue
        candidates.append((m.get("created", 0), m["id"]))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def resolve_free_model(cache_file= CACHE_FILE, max_age: int = CACHE_TTL):
    """Return (model_id, source) where source is 'cache' | 'live' | 'fallback'."""
    if cache_file is not None and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            if data.get("model") and time.time() - data.get("ts", 0) < max_age:
                return data["model"], "cache"
        except (json.JSONDecodeError, OSError):
            pass
    try:
        model = pick_latest_free_model()
        if model:
            if cache_file is not None:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps({"ts": time.time(), "model": model}))
                except OSError:
                    pass
            return model, "live"
    except Exception:
        pass
    return FALLBACK_FREE_MODEL, "fallback"
