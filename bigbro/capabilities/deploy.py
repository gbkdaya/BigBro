"""Deploy capability — ship websites to Netlify (zip API) or Vercel (files API).

Tokens are read from the environment (.env): NETLIFY_AUTH_TOKEN / VERCEL_TOKEN.
Tokens are never echoed into logs or LLM context.
"""

import base64
import io
import os
import re
import zipfile

import requests

from bigbro.capabilities.base import Capability

SKIP_DIR_NAMES = {"node_modules", ".git", ".next", ".expo", "build", "coverage", "__pycache__"}
MAX_FILES = 2000
MAX_TOTAL_BYTES = 80 * 1024 * 1024
TIMEOUT = 180


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    return s or "bigbro-site"


def _iter_files(root):
    files, total = [], 0
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part in SKIP_DIR_NAMES for part in p.relative_to(root).parts):
            continue
        files.append(p)
        total += p.stat().st_size
        if len(files) > MAX_FILES:
            raise RuntimeError(f"too many files (> {MAX_FILES}) — deploy a smaller build output folder")
        if total > MAX_TOTAL_BYTES:
            raise RuntimeError(f"total size > {MAX_TOTAL_BYTES // (1024 * 1024)}MB — deploy a smaller build output folder")
    return files


def _netlify(token: str, project_name: str, src_dir) -> str:
    files = _iter_files(src_dir)
    if not files:
        raise RuntimeError(f"no files found in {src_dir} — build the project first (e.g. run_command 'npm run build')")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in files:
            zf.write(p, p.relative_to(src_dir).as_posix())

    site_id = os.environ.get("NETLIFY_SITE_ID", "").strip()
    if not site_id:
        r = requests.post(
            "https://api.netlify.com/api/v1/sites",
            json={"name": _slug(project_name)},
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"Netlify site creation failed ({r.status_code}): {r.text[:300]} "
                "— if the name is taken, set NETLIFY_SITE_ID in .env to redeploy to an existing site."
            )
        site_id = r.json()["id"]

    r = requests.post(
        f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
        data=buf.getvalue(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/zip"},
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Netlify deploy failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    url = d.get("ssl_url") or d.get("url") or d.get("deploy_url") or ""
    return f"Deployed to Netlify: {url} (site {site_id}, state: {d.get('state', 'unknown')})"


def _vercel(token: str, project_name: str, src_dir) -> str:
    files = _iter_files(src_dir)
    if not files:
        raise RuntimeError(f"no files found in {src_dir} — build the project first (e.g. run_command 'npm run build')")
    payload_files = [
        {"file": p.relative_to(src_dir).as_posix(), "data": base64.b64encode(p.read_bytes()).decode()}
        for p in files
    ]
    headers = {"Authorization": f"Bearer {token}"}
    slug = _slug(project_name)

    proj_id = os.environ.get("VERCEL_PROJECT_ID", "").strip()
    if not proj_id:
        r = requests.post("https://api.vercel.com/v13/projects", json={"name": slug}, headers=headers, timeout=60)
        if r.status_code < 400:
            proj_id = r.json().get("id") or r.json().get("projectId")
        else:
            r2 = requests.get("https://api.vercel.com/v13/projects", headers=headers, timeout=60)
            if r2.status_code < 400:
                for p in r2.json().get("projects", []):
                    if p.get("name") == slug:
                        proj_id = p.get("id") or p.get("projectId")
                        break
        if not proj_id:
            raise RuntimeError(f"could not create/find Vercel project '{slug}': {r.text[:300]}")

    r = requests.post(
        f"https://api.vercel.com/v13/projects/{proj_id}/deployments",
        json={"files": payload_files, "target": "production"},
        headers=headers,
        timeout=TIMEOUT,
    )
    if r.status_code >= 400:
        raise RuntimeError(f"Vercel deploy failed ({r.status_code}): {r.text[:300]}")
    d = r.json()
    url = d.get("url") or d.get("alias") or ""
    if url and not url.startswith("http"):
        url = "https://" + url
    return f"Deployed to Vercel: {url} (state: {d.get('state', 'unknown')})"


class DeployProject(Capability):
    name = "deploy_project"
    description = (
        "Deploy a website to Netlify or Vercel. project = folder name under projects/. "
        "subdir = subfolder to upload — usually the built output ('dist' for Vite/React, 'out' for Next.js export). "
        "Use '' to upload the whole project (Vercel can then build it from source). "
        "Needs NETLIFY_AUTH_TOKEN or VERCEL_TOKEN in .env (both free)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "platform": {"type": "string", "enum": ["netlify", "vercel"]},
            "project": {"type": "string", "description": "Project folder name under projects/"},
            "subdir": {"type": "string", "description": "Subfolder to deploy, default the project root"},
        },
        "required": ["platform", "project"],
    }

    def execute(self, platform: str, project: str, subdir: str = "") -> str:
        if platform == "netlify":
            token = os.environ.get("NETLIFY_AUTH_TOKEN", "").strip()
            if not token:
                return (
                    "ERROR: NETLIFY_AUTH_TOKEN is not set. Get a free token at "
                    "https://app.netlify.com/user/applications#applications and add NETLIFY_AUTH_TOKEN to .env."
                )
        elif platform == "vercel":
            token = os.environ.get("VERCEL_TOKEN", "").strip()
            if not token:
                return (
                    "ERROR: VERCEL_TOKEN is not set. Get a free token at "
                    "https://vercel.com/account/tokens and add VERCEL_TOKEN to .env."
                )
        else:
            return "ERROR: platform must be 'netlify' or 'vercel'."

        base = self.safe_path(f"projects/{project}")
        src = self.safe_path(f"projects/{project}/{subdir}") if subdir else base
        if not src.is_dir():
            return (
                f"ERROR: {self.rel(src)} is not a directory. Build first "
                f"(e.g. run_command 'npm run build' in {self.rel(base)}), then deploy the output folder."
            )
        try:
            if platform == "netlify":
                return _netlify(token, project, src)
            return _vercel(token, project, src)
        except requests.RequestException as e:
            return f"ERROR: network error during deploy: {e}"


CAPABILITIES = [DeployProject]
