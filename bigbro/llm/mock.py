"""Deterministic mock provider — used by the test suite and for offline demos.

A 'script' is a list of steps: ("tool", name, args) or ("final", text).
"""

from .base import ChatResult, LLMProvider, ToolCall


class MockProvider(LLMProvider):
    name = "mock"
    model = "mock"

    def __init__(self, script=None):
        if script is None:
            script = [
                ("tool", "list_templates", {}),
                (
                    "final",
                    "This is **BigBro** running in mock mode (deterministic, no LLM).\n\n"
                    "To give me a real brain, edit `.env`:\n"
                    "- set your key (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY`)\n"
                    "- set `BIGBRO_PROVIDER=openai|anthropic|gemini` (or `ollama` for local)\n\n"
                    "Then run me again.",
                ),
            ]
        self.script = list(script)
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        if not self.script:
            return ChatResult(content="(mock script exhausted — nothing more to say)")
        step = self.script.pop(0)
        if step[0] == "tool":
            _, name, args = step
            return ChatResult(content="", tool_calls=[ToolCall(id=f"mock_{self.calls}", name=name, arguments=args)])
        return ChatResult(content=step[1])
