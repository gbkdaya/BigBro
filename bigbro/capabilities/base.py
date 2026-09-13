"""Base class for all BigBro capabilities.

To add a capability, subclass Capability, set name/description/parameters,
implement execute(), and put your module in the capabilities/ directory.
"""

from pathlib import Path


class Capability:
    name = ""
    description = ""
    parameters = {"type": "object", "properties": {}}

    def __init__(self, workspace):
        self.workspace = Path(workspace).resolve()

    def tool_schema(self):
        """OpenAI-style function schema (converted per provider)."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    def execute(self, **kwargs) -> str:
        raise NotImplementedError

    # ---------- helpers ----------

    def safe_path(self, p: str) -> Path:
        """Resolve a path and guarantee it stays inside the workspace."""
        target = Path(p)
        target = (target if target.is_absolute() else self.workspace / target).resolve()
        if target != self.workspace and self.workspace not in target.parents:
            raise PermissionError(f"Path is outside the BigBro workspace: {p}")
        return target

    def rel(self, p) -> str:
        try:
            return str(Path(p).resolve().relative_to(self.workspace))
        except ValueError:
            return str(p)
