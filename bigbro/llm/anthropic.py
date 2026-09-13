"""Anthropic (Claude) provider using the native Messages API."""

import requests

from .base import ChatResult, LLMProvider, ToolCall

API_URL = "https://api.anthropic.com/v1/messages"


def _convert(messages):
    """Normalize messages into Anthropic format (system separated, tool_use/tool_result blocks)."""
    system_parts = []
    out = []
    for m in messages:
        role = m["role"]
        if role == "system":
            system_parts.append(m.get("content", ""))
        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id", ""),
                "content": m.get("content", ""),
            }
            last = out[-1] if out else None
            if (
                last
                and last.get("role") == "user"
                and isinstance(last.get("content"), list)
                and all(b.get("type") == "tool_result" for b in last["content"])
            ):
                last["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
        elif role == "assistant":
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m.get("tool_calls") or []:
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["arguments"]})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "…"}]})
        else:
            out.append({"role": "user", "content": m.get("content", "")})
    return "\n".join(p for p in system_parts if p), out


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str, temperature: float = 0.2,
                 max_tokens: int = 8192, timeout: int = 600):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def chat(self, messages, tools):
        system, msgs = _convert(messages)
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "messages": msgs,
        }
        if system:
            payload["system"] = system
        if tools:
            payload["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "input_schema": t["function"].get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]

        resp = requests.post(
            API_URL,
            json=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        tool_calls = [
            ToolCall(id=b["id"], name=b["name"], arguments=b.get("input") or {})
            for b in data.get("content", [])
            if b.get("type") == "tool_use"
        ]
        return ChatResult(content=text, tool_calls=tool_calls)
