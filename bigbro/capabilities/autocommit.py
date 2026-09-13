"""Auto-commit capability — BigBro version-controls its own work with timestamped commits."""

import datetime
import subprocess

from bigbro.capabilities.base import Capability


class CommitAll(Capability):
    name = "commit_all"
    description = (
        "Stage ALL changes in a project folder and commit them with a timestamped message "
        "(format: 'bigbro YYYY-MM-DD HH:MM: <your message>'). Use after finishing a build step. "
        "If the folder is not a git repo yet, run the git capability with action=init first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "project": {"type": "string", "description": "Project folder under the workspace, e.g. projects/my-app"},
            "message": {"type": "string", "description": "Concise summary of what was built/changed"},
        },
        "required": ["project", "message"],
    }

    def execute(self, project: str, message: str) -> str:
        repo = self.safe_path(project)
        if not repo.is_dir():
            return f"ERROR: not a directory: {project}"
        if not (repo / ".git").exists():
            return f"ERROR: {self.rel(repo)} is not a git repo — run the git capability with action=init there first."
        try:
            subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True, text=True, timeout=120, check=True)
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, timeout=60
            )
            if not status.stdout.strip():
                return "Nothing to commit — working tree clean."
            stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            proc = subprocess.run(
                ["git", "commit", "-m", f"bigbro {stamp}: {message.strip()}"],
                cwd=repo,
                capture_output=True,
                text=True,
                timeout=120,
            )
            out = ((proc.stdout or "") + (proc.stderr or "")).strip()[:500]
            if proc.returncode != 0:
                return f"ERROR: commit failed: {out}"
            log = subprocess.run(["git", "log", "--oneline", "-1"], cwd=repo, capture_output=True, text=True, timeout=60)
            return f"Committed {self.rel(repo)}: {log.stdout.strip()}"
        except subprocess.CalledProcessError as e:
            return f"ERROR: git add failed: {e.stderr or e}"
        except subprocess.TimeoutExpired:
            return "ERROR: git operation timed out"


CAPABILITIES = [CommitAll]
