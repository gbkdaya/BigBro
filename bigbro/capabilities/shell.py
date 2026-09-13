"""Shell capability — run builds, tests, installers. Confined to the workspace."""

import subprocess

from bigbro.capabilities.base import Capability


class RunCommand(Capability):
    name = "run_command"
    description = (
        "Run a shell command inside the workspace (e.g. 'npm install', 'npm test', 'flutter pub get', "
        "'pip install -r requirements.txt', 'uvicorn main:app --port 8000'). "
        "Returns exit code, stdout and stderr. Max 300 seconds."
    )
    parameters = {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command line"},
            "cwd": {"type": "string", "description": "Workspace-relative working directory, default workspace root"},
            "timeout": {"type": "integer", "description": "Seconds, default 120, max 300"},
        },
        "required": ["command"],
    }

    def execute(self, command: str, cwd: str = "", timeout: int = 120) -> str:
        timeout = max(5, min(int(timeout or 120), 300))
        workdir = self.safe_path(cwd or ".")
        if not workdir.is_dir():
            return f"ERROR: working directory not found: {cwd}"
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"ERROR: command timed out after {timeout}s: {command}"

        head = f"exit={proc.returncode}  cmd: {command}  (cwd: {self.rel(workdir)})"
        parts = [head]
        if (proc.stdout or "").strip():
            parts.append("stdout:\n" + (proc.stdout or "")[-8000:])
        if (proc.stderr or "").strip():
            parts.append("stderr:\n" + (proc.stderr or "")[-4000:])
        return "\n".join(parts)


CAPABILITIES = [RunCommand]
