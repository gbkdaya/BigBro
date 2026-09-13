"""Git capability — a small allowlisted set of safe git operations."""

import subprocess

from bigbro.capabilities.base import Capability

ALLOWED = {
    "init": ["init"],
    "status": ["status"],
    "add": ["add", "."],
    "commit": ["commit", "-m", "{message}"],
    "diff": ["diff"],
    "log": ["log", "--oneline", "-20"],
    "branch": ["branch", "-a"],
    "pull": ["pull"],
    "push": ["push"],
}


class Git(Capability):
    name = "git"
    description = (
        "Run a safe Git operation inside the workspace. Actions: init, status, add, commit (needs message), "
        "diff, log, branch, pull, push."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": sorted(ALLOWED)},
            "message": {"type": "string", "description": "Commit message (required for action=commit)"},
            "cwd": {"type": "string", "description": "Workspace-relative repo directory, default workspace root"},
        },
        "required": ["action"],
    }

    def execute(self, action: str, message: str = "", cwd: str = "") -> str:
        if action not in ALLOWED:
            return f"ERROR: unsupported git action '{action}'. Allowed: {', '.join(sorted(ALLOWED))}"
        if "{message}" in ALLOWED[action] and not (message or "").strip():
            return "ERROR: commit requires a message"
        workdir = self.safe_path(cwd or ".")
        if not workdir.is_dir():
            return f"ERROR: directory not found: {cwd}"
        parts = [message if p == "{message}" else p for p in ALLOWED[action]]
        try:
            proc = subprocess.run(["git"] + parts, cwd=workdir, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            return "ERROR: git command timed out"
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()[:4000]
        return f"exit={proc.returncode}\n{output}" if output else f"exit={proc.returncode}"


CAPABILITIES = [Git]
