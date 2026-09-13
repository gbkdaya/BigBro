"""Filesystem capabilities — all paths are confined to the workspace."""

import re
from pathlib import Path

from bigbro.capabilities.base import Capability

MAX_READ = 40000


class ReadFile(Capability):
    name = "read_file"
    description = "Read a text file inside the workspace and return its content (truncated at 40k chars)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Path inside the workspace"}},
        "required": ["path"],
    }

    def execute(self, path: str) -> str:
        p = self.safe_path(path)
        if not p.exists():
            return f"ERROR: file not found: {path}"
        if not p.is_file():
            return f"ERROR: not a file: {path}"
        text = p.read_text(errors="replace")
        if len(text) > MAX_READ:
            return text[:MAX_READ] + f"\n... [truncated — {len(text)} chars total]"
        return text


class WriteFile(Capability):
    name = "write_file"
    description = "Create or overwrite a file inside the workspace. Parent directories are created automatically."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "content": {"type": "string", "description": "Full file content"},
        },
        "required": ["path", "content"],
    }

    def execute(self, path: str, content: str) -> str:
        p = self.safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"Wrote {len(content)} chars to {self.rel(p)}"


class EditFile(Capability):
    name = "edit_file"
    description = "Replace the first exact occurrence of old_text in a file with new_text."
    parameters = {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "old_text": {"type": "string"},
            "new_text": {"type": "string"},
        },
        "required": ["path", "old_text", "new_text"],
    }

    def execute(self, path: str, old_text: str, new_text: str) -> str:
        p = self.safe_path(path)
        if not p.is_file():
            return f"ERROR: file not found: {path}"
        text = p.read_text(errors="replace")
        if old_text not in text:
            return "ERROR: old_text not found in file. Re-read the file and retry with the exact text."
        p.write_text(text.replace(old_text, new_text, 1))
        return f"Edited {self.rel(p)}"


class ListDir(Capability):
    name = "list_dir"
    description = "List files and directories at a workspace path (directories marked with /)."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory path, default workspace root"}},
        "required": [],
    }

    def execute(self, path: str = "") -> str:
        d = self.safe_path(path or ".")
        if not d.is_dir():
            return f"ERROR: not a directory: {path}"
        entries = []
        for e in sorted(d.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            suffix = "/" if e.is_dir() else f" ({e.stat().st_size}b)"
            entries.append(f"{e.name}{suffix}")
        return "\n".join(entries) if entries else "(empty)"


class SearchFiles(Capability):
    name = "search_files"
    description = (
        "Regex-search file contents inside the workspace (skips binary and very large files). "
        "Returns 'path:line: text' matches, max 100."
    )
    parameters = {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regular expression"},
            "path": {"type": "string", "description": "Subdirectory to search, default workspace root"},
            "glob": {"type": "string", "description": "Filename glob filter, e.g. '*.py' (default: all files)"},
        },
        "required": ["pattern"],
    }

    def execute(self, pattern: str, path: str = "", glob: str = "*") -> str:
        d = self.safe_path(path or ".")
        try:
            rx = re.compile(pattern)
        except re.error as e:
            return f"ERROR: invalid regex: {e}"
        matches = []
        for f in (d.rglob(glob) if glob else d.rglob("*")):
            if not f.is_file():
                continue
            try:
                if f.stat().st_size > 500_000:
                    continue
                data = f.read_bytes()
                if b"\0" in data[:8192]:
                    continue
            except OSError:
                continue
            for i, line in enumerate(data.decode(errors="ignore").splitlines(), 1):
                if rx.search(line):
                    matches.append(f"{self.rel(f)}:{i}: {line.strip()[:200]}")
                    if len(matches) >= 100:
                        return "\n".join(matches) + "\n... [stopped at 100 matches]"
        return "\n".join(matches) if matches else "No matches."


class DeleteFile(Capability):
    name = "delete_file"
    description = "Delete a single file inside the workspace."
    parameters = {
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    }

    def execute(self, path: str) -> str:
        p = self.safe_path(path)
        if not p.is_file():
            return f"ERROR: file not found: {path}"
        p.unlink()
        return f"Deleted {self.rel(p)}"


CAPABILITIES = [ReadFile, WriteFile, EditFile, ListDir, SearchFiles, DeleteFile]
