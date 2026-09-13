"""Example custom capability — the exact pattern to copy when extending BigBro.

Drop a new .py file in this directory (<project root>/capabilities/).
BigBro auto-loads any module that defines a CAPABILITIES list of Capability classes.
Files starting with "_" are ignored (use that for scratch files).
"""

import datetime

from bigbro.capabilities.base import Capability


class SaveNote(Capability):
    """Tiny demo: ask BigBro to 'save a note' and it appends to workspace/notes.md."""

    name = "save_note"
    description = "Save a sticky note to workspace/notes.md (appends with a timestamp). Example of a user-added capability."
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Note content"}},
        "required": ["text"],
    }

    def execute(self, text: str) -> str:
        p = self.workspace / "notes.md"
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(p, "a") as f:
            f.write(f"\n## {stamp}\n{text.strip()}\n")
        return f"Note saved to {self.rel(p)}"


CAPABILITIES = [SaveNote]
