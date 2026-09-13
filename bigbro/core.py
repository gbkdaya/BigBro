"""The agent loop: user message → LLM → tool calls → results → final answer."""

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .capabilities import load_capabilities
from .config import Config
from .llm import make_provider
from .persona import build_persona

HISTORY_LIMIT = 80          # keep last N normalized messages in context
TOOL_RESULT_LIMIT = 20000   # max chars of a tool result fed back to the LLM


@dataclass
class AgentEvent:
    kind: str  # "tool"
    name: str = ""
    detail: str = ""


class BigBro:
    """LLM brain + capability tools, confined to the owner's workspace."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.provider = make_provider(cfg)
        self.caps = load_capabilities(cfg.workspace)
        self._by_name = {c.name: c for c in self.caps}
        self.tool_schemas = [c.tool_schema() for c in self.caps]
        self.persona = build_persona(cfg.workspace, cfg.extra_persona)

    def run(
        self,
        user_message: str,
        history: Optional[List[Dict[str, Any]]] = None,
        session_id: str = "",
    ) -> Tuple[List[Dict[str, Any]], str, List[AgentEvent]]:
        history = list(history or [])
        start = len(history)
        history.append({"role": "user", "content": user_message})
        events: List[AgentEvent] = []
        final = ""

        for _ in range(self.cfg.max_turns):
            try:
                res = self.provider.chat(
                    [{"role": "system", "content": self.persona}] + history,
                    self.tool_schemas,
                )
            except Exception as e:  # network / API errors should not kill the session
                final = f"⚠ BigBro's brain (LLM provider) failed: {e}\n\nCheck `.env` (provider, API key, model) and try again."
                break

            if res.tool_calls:
                history.append({
                    "role": "assistant",
                    "content": res.content or "",
                    "tool_calls": [
                        {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                        for tc in res.tool_calls
                    ],
                })
                for tc in res.tool_calls:
                    result, _ok = self._execute(tc)
                    events.append(AgentEvent(kind="tool", name=tc.name, detail=result[:400]))
                    history.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.name,
                        "content": result[:TOOL_RESULT_LIMIT],
                    })
            else:
                final = res.content
                history.append({"role": "assistant", "content": final})
                break
        else:
            final = "I hit my turn budget before finishing. Here's where I got to — say 'continue' and I'll pick up."
            history.append({"role": "assistant", "content": final})

        if len(history) > HISTORY_LIMIT:
            history = history[-HISTORY_LIMIT:]
        if session_id:
            self._append_transcript(session_id, history[start:])
        return history, final, events

    def _execute(self, tc):
        cap = self._by_name.get(tc.name)
        if cap is None:
            return f"ERROR: unknown capability '{tc.name}'.", False
        try:
            return cap.execute(**tc.arguments), True
        except TypeError as e:
            return f"ERROR: bad arguments for '{tc.name}': {e}", False
        except Exception as e:
            return f"ERROR: {type(e).__name__}: {e}", False

    def new_session_id(self) -> str:
        return time.strftime("%Y%m%d-") + uuid.uuid4().hex[:6]

    def _append_transcript(self, session_id: str, messages: List[Dict[str, Any]]) -> None:
        try:
            sessions = self.cfg.workspace / "sessions"
            sessions.mkdir(parents=True, exist_ok=True)
            with open(sessions / f"{session_id}.jsonl", "a") as f:
                for m in messages:
                    rec = {"role": m["role"], "content": str(m.get("content", ""))[:5000]}
                    if m.get("tool_calls"):
                        rec["tool_calls"] = m["tool_calls"]
                    f.write(json.dumps(rec, default=str) + "\n")
        except OSError:
            pass
