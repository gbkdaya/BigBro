"""Scaffolding capability — copy BigBro starter templates into the workspace."""

import json
import re
import shutil
from pathlib import Path

from bigbro.capabilities.base import Capability

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
NAME_RX = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")


def _template_metas() -> dict:
    out = {}
    if not TEMPLATES_DIR.exists():
        return out
    for d in sorted(TEMPLATES_DIR.iterdir()):
        if not d.is_dir():
            continue
        meta = {}
        mf = d / ".meta.json"
        if mf.exists():
            try:
                meta = json.loads(mf.read_text())
            except json.JSONDecodeError:
                pass
        out[d.name] = meta
    return out


class ScaffoldProject(Capability):
    name = "scaffold_project"
    description = (
        "Create a new project by copying a BigBro starter template into workspace/projects/<name>. "
        "Kinds: website-react, website-next, mobile-flutter, mobile-expo, backend-fastapi, backend-express."
    )
    parameters = {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "description": "Template kind, e.g. website-react"},
            "name": {"type": "string", "description": "Project folder name: lowercase letters, digits, dashes"},
        },
        "required": ["kind", "name"],
    }

    def execute(self, kind: str, name: str) -> str:
        if not NAME_RX.fullmatch(name or ""):
            return "ERROR: name must be lowercase letters/digits/dashes (max 64 chars)."
        src = TEMPLATES_DIR / kind
        if not src.is_dir():
            return f"ERROR: unknown template '{kind}'. Available: {', '.join(sorted(_template_metas()))}"
        dest = self.workspace / "projects" / name
        if dest.exists():
            return f"ERROR: project already exists at {self.rel(dest)} — edit it in place or pick a new name."
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git"))

        files = [str(f.relative_to(dest)) for f in sorted(dest.rglob("*")) if f.is_file()]
        meta = _template_metas().get(kind, {})
        next_steps = meta.get("next_steps", "Inspect the project and implement the feature set.")
        return (
            f"Scaffolded '{name}' from '{kind}' at {self.rel(dest)}\n"
            f"Files:\n" + "\n".join(files[:60])
            + (f"\n... ({len(files)} files total)" if len(files) > 60 else "")
            + f"\n\nSuggested next steps: {next_steps}"
        )


class ListTemplates(Capability):
    name = "list_templates"
    description = "List available BigBro project starter templates with their stack and next-step hints."
    parameters = {"type": "object", "properties": {}}

    def execute(self) -> str:
        metas = _template_metas()
        lines = [
            f"- {kind}: {meta.get('title', '')} [{meta.get('stack', '')}] — next: {meta.get('next_steps', '')}"
            for kind, meta in sorted(metas.items())
        ]
        return "\n".join(lines) if lines else "No templates found."


CAPABILITIES = [ScaffoldProject, ListTemplates]
