"""OpenAI-compatible chat completions provider.

Works with OpenAI, Ollama (/v1 endpoint), OpenRouter, Groq, LM Studio, vLLM,
and anything else that speaks the OpenAI chat-completions protocol.
"""

import json

import requests

from .base import ChatResult, LLMProvider, ToolCall


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

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"LLM API error {resp.status_code} from {self.base_url}: {resp.text[:500]}")

        data = resp.json()
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
