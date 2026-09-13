"""Shared LLM types. Messages use a normalized OpenAI-style format:

    {"role": "system"|"user"|"assistant"|"tool", "content": str,
     "tool_calls": [{"id","name","arguments"}],          # assistant only
     "tool_call_id": str, "name": str}                    # tool role only

Each provider converts this format to its native wire format.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ChatResult:
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)


class LLMProvider:
    name = "base"
    model = "base"

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ChatResult:
        raise NotImplementedError
