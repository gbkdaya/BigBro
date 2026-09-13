"""OpenAI-compatible chat completions provider.

Works with OpenAI, Ollama (/v1 endpoint), OpenRouter, Groq, LM Studio, vLLM,
and anything else that speaks the OpenAI chat-completions protocol.

Free-tier providers are flaky: they intermittently return 429 (quota) and
400 'Provider returned error' (upstream hiccup). This provider retries
transient failures with backoff and raises typed errors so callers
(e.g. FreeModelProvider) can fail over to a different model.
"""

import json
import time

import requests

from .base import ChatResult, LLMProvider, ToolCall


class RateLimitedError(RuntimeError):
    """The model's provider rate-limited us (e.g. free-tier quota)."""

    def __init__(self, model):
        super().__init__(f"model {model} is rate-limited")
        self.model = model


class ProviderTransientError(RuntimeError):
    """The upstream (free) provider rejected the request transiently."""

    def __init__(self, model, detail: str = ""):
        super().__init__(f"upstream provider error for {model}: {detail[:200]}")
        self.model = model


def _is_provider_passthrough(body: str) -> bool:
    """True when OpenRouter itself forwards an upstream provider error (flaky, worth retrying)."""
    return (
        "Provider returned error" in body
        or "invalid request error" in body
        or "provider_name" in body
        or "trace_id" in body
    )


class OpenAICompatProvider(LLMProvider):
    name = "openai-compat"
    model_source = ""  # e.g. "auto: latest free model (live)" for free mode

    def __init__(self, base_url: str, api_key: str, model: str, temperature: float = 0.2,
                 timeout: int = 600, key_required: bool = True):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.key_required = key_required

    def chat(self, messages, tools):
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {"Content-Type": "application/json"}
        if self.api_key and self.key_required:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_detail = ""
        for attempt in range(3):
            try:
                resp = requests.post(f"{self.base_url}/chat/completions", json=payload,
                                     headers=headers, timeout=self.timeout)
            except requests.RequestException as e:
                raise RuntimeError(f"LLM API network error from {self.base_url}: {e}")

            if resp.status_code == 429:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise RateLimitedError(self.model)

            if resp.status_code == 400 and _is_provider_passthrough(resp.text):
                last_detail = resp.text
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise ProviderTransientError(self.model, resp.text)

            if resp.status_code >= 400:
                raise RuntimeError(f"LLM API error {resp.status_code} from {self.base_url}: {resp.text[:500]}")

            return self._parse(resp.json())

        raise ProviderTransientError(self.model, last_detail)

    def _parse(self, data) -> ChatResult:
        msg = data["choices"][0]["message"]
        tool_calls = []
        for i, tc in enumerate(msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(
                id=tc.get("id") or f"call_{i}",
                name=fn.get("name", ""),
                arguments=args,
            ))
        return ChatResult(content=msg.get("content") or "", tool_calls=tool_calls)
