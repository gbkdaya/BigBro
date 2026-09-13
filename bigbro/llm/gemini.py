"""Google Gemini provider using the native REST API (function calling)."""

import requests

from .base import ChatResult, LLMProvider, ToolCall

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _convert(messages):
    system = ""
    contents = []
    for m in messages:
        role = m["role"]
        if role == "system":
            system += m.get("content", "")
        elif role == "tool":
            part = {"functionResponse": {"name": m.get("name", "unknown"), "response": {"result": m.get("content", "")}}}
            last = contents[-1] if contents else None
            if last and last["role"] == "user" and all("functionResponse" in p for p in last["parts"]):
                last["parts"].append(part)
            else:
                contents.append({"role": "user", "parts": [part]})
        elif role == "assistant":
            parts = []
            if m.get("content"):
                parts.append({"text": m["content"]})
            for tc in m.get("tool_calls") or []:
                parts.append({"functionCall": {"name": tc["name"], "args": tc["arguments"]}})
            contents.append({"role": "model", "parts": parts or [{"text": "…"}]})
        else:
            contents.append({"role": "user", "parts": [{"text": m.get("content", "")}]})
    return system, contents


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, temperature: float = 0.2, timeout: int = 600):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def chat(self, messages, tools):
        system, contents = _convert(messages)
        payload = {
            "contents": contents,
            "generationConfig": {"temperature": self.temperature},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if tools:
            payload["tools"] = [{"functionDeclarations": [
                {
                    "name": t["function"]["name"],
                    "description": t["function"].get("description", ""),
                    "parameters": t["function"].get("parameters", {"type": "object", "properties": {}}),
                }
                for t in tools
            ]}]

        url = f"{BASE}/{self.model}:generateContent"
        resp = requests.post(
            url,
            json=payload,
            headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        text = "".join(p.get("text", "") for p in parts if "text" in p)
        tool_calls = [
            ToolCall(id=f"gemini_{i}", name=p["functionCall"]["name"], arguments=p["functionCall"].get("args") or {})
            for i, p in enumerate(parts)
            if "functionCall" in p
        ]
        return ChatResult(content=text, tool_calls=tool_calls)
