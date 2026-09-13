# 🕶️ BigBro — your personal full-stack developer agent

BigBro is a **private, extensible AI developer agent** that does what you instruct it to — end to end:

- **Application UI / frontend** — websites (React + Vite, Next.js) and mobile apps (Flutter, React Native/Expo)
- **Integration layer** — API clients, webhooks, third-party service connections, front↔back↔external data flow
- **Backend** — FastAPI / Express REST APIs, data models, config, tests

It is yours alone: it runs on your machine, binds to localhost by default, and the web dashboard requires
a personal access token. New projects it builds land in `workspace/projects/`, and **everything it can
touch is confined to that folder**.

---

## Quick start

```bash
cd bigbro
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit .env: pick a provider + paste your API key
```

Pick your brain (all are wired up, switch anytime):

| Provider      | `.env` settings                                                        |
|---------------|------------------------------------------------------------------------|
| **Free (default)** | `BIGBRO_PROVIDER=free` + `OPENROUTER_API_KEY=...` — free account, no credit card. BigBro **auto-picks the newest free tool-capable model** (re-checked daily) |
| OpenRouter    | `BIGBRO_PROVIDER=openrouter` + `BIGBRO_MODEL=<any model>` (free or paid) |
| OpenAI        | `BIGBRO_PROVIDER=openai` + `OPENAI_API_KEY=...`                          |
| Anthropic     | `BIGBRO_PROVIDER=anthropic` + `ANTHROPIC_API_KEY=...`                     |
| Google Gemini | `BIGBRO_PROVIDER=gemini` + `GEMINI_API_KEY=...`                           |
| Local Ollama  | `BIGBRO_PROVIDER=ollama` (+ `OLLAMA_MODEL`, fully offline, zero accounts) |

### Model policy — always the latest free model

The default `free` mode implements the standing policy: *always use the latest free model*.
At startup BigBro reads OpenRouter's public model list, keeps the models with **zero pricing**
that support **tool calling**, and uses the most recently released one. The pick is cached for
24 h (`.free_model_cache.json`) and falls back to a known-good free model when offline.
Which model is answering is shown in the CLI banner and the dashboard header.
Set `BIGBRO_MODEL` to pin a specific model if you prefer a stable one.

### Talk to BigBro — terminal

```bash
python -m bigbro.cli                 # interactive chat
python -m bigbro.cli --once "Scaffold a React website for a to-do app and wire it to a FastAPI backend"
```

Commands inside the CLI: `/new` (clear session) · `/caps` (list capabilities) · `/exit`

### Talk to BigBro — web dashboard

```bash
python -m bigbro.web
```

Open `http://127.0.0.1:8321` and enter your access token (printed at startup; also saved in `.env`).
The dashboard shows the live session, every action BigBro took (tool calls), and a capability browser.

No API key yet? Try it offline with the deterministic mock brain:

```bash
python -m bigbro.cli --provider mock --once "hello"
```

## Run with Docker

```bash
cp .env.example .env          # configure provider + key first
docker compose up --build     # web dashboard at http://127.0.0.1:8321
```

- The dashboard binds to `0.0.0.0` **inside** the container; compose maps it to `127.0.0.1` on your host, so it stays local-only.
- `./workspace` is a volume — projects, transcripts and notes survive rebuilds.
- CLI inside the container: `docker compose run --rm bigbro python -m bigbro.cli`
- Exposing beyond localhost (change the port mapping) is possible but keep `BIGBRO_TOKEN` strong.

---

## What BigBro can do (built-in capabilities)

| Capability        | What it does                                                        |
|-------------------|---------------------------------------------------------------------|
| `scaffold_project`| Create a new project from a starter template                        |
| `list_templates`  | Show available starters: website-react, website-next, mobile-flutter, mobile-expo, backend-fastapi, backend-express |
| `read_file` / `write_file` / `edit_file` / `delete_file` | File operations (workspace-confined)   |
| `list_dir` / `search_files` | Explore codebases                              |
| `run_command`     | Run builds, tests, installers (`npm`, `flutter`, `pip`, `uvicorn`, …) |
| `git`             | Safe git ops: init, status, add, commit, diff, log, branch, pull, push |
| `fetch_url`       | Read web pages/API docs (HTML stripped)                             |
| `http_request`    | Send HTTP requests to test your own APIs and integrations           |
| `deploy_project`  | Deploy a built website to **Netlify or Vercel** — returns the live URL |
| `commit_all`      | Stage + commit a project with a timestamped message (`bigbro <timestamp>: ...`) |
| `save_note`       | *(example of a user capability)* sticky notes in `workspace/notes.md` |

### Deploying a website (free)

1. BigBro builds the site (`npm run build`).
2. You add a **free** token to `.env` once:
   - Netlify: `NETLIFY_AUTH_TOKEN` — https://app.netlify.com/user/applications#applications
   - Vercel: `VERCEL_TOKEN` — https://vercel.com/account/tokens
3. Tell BigBro *"deploy my site to Netlify/Vercel"* — it uploads the build output and gives you the live URL.

Optionally set `NETLIFY_SITE_ID` / `VERCEL_PROJECT_ID` in `.env` to redeploy to the same site instead of creating a new one. Tokens are read at deploy time and never shown in chat.

Workflow BigBro follows: **inspect → brief plan → scaffold/modify → verify (runs builds/tests) → report**
(changed files, how to run, open decisions). Session transcripts are saved to `workspace/sessions/`.

---

## Extending BigBro (by you, for your requirements)

### 1. Add a new capability

Drop a file in **`capabilities/`** (project root) — it's auto-loaded on next start:

```python
# capabilities/deploy_capability.py
from bigbro.capabilities.base import Capability

class DeployStaging(Capability):
    name = "deploy_staging"
    description = "Deploy a project to the staging server."
    parameters = {
        "type": "object",
        "properties": {"project": {"type": "string"}},
        "required": ["project"],
    }

    def execute(self, project: str) -> str:
        # your logic here — return a string the LLM will read
        return f"deployed {project}"

CAPABILITIES = [DeployStaging]
```

That's the whole extension API. `self.workspace` is your working area; use `self.safe_path()` to
stay confined; raise on errors (BigBro turns them into `ERROR:` text the model can recover from).
See `capabilities/example_custom.py` and `capabilities/README.md`.

### 2. Tune the persona / standing instructions

- Quick: set `BIGBRO_EXTRA_PERSONA=...` in `.env` (e.g. *"Always use TypeScript strict mode"*,
  *"Reply in Hinglish"*, *"My backend is always FastAPI + Postgres"*).
- Deep: edit the full system prompt in `bigbro/persona.py`.

### 3. Add a project starter template

Copy any folder in `templates/`, adjust it, add a `.meta.json`
(`{"title": ..., "stack": ..., "next_steps": ...}`). It becomes available via `scaffold_project` immediately.

### 4. Swap or add LLM brains

Providers live in `bigbro/llm/`. The normalized message format + `chat()` contract is in
`bigbro/llm/base.py`. OpenAI-compatible endpoints (OpenRouter, Groq, LM Studio, vLLM) need **no new
provider code** — just point `OPENAI_BASE_URL` at them under `BIGBRO_PROVIDER=openai`.

---

## Security model (you-only access)

- **Local-first**: the web dashboard binds to `127.0.0.1` by default — it's not reachable off your machine.
- **Token auth**: the dashboard and every `/api/*` call require your personal `BIGBRO_TOKEN` (auto-generated if unset).
- **Workspace confinement**: file, search, git, and shell capabilities are restricted to `BIGBRO_WORKSPACE` — BigBro cannot read or write outside it.
- **Secrets policy**: BigBro's persona forbids hardcoding, printing, or committing credentials; it references env vars by name.
- **Transcripts**: conversations are logged to `workspace/sessions/*.jsonl` (local only).

> If you ever expose it over the network (`BIGBRO_HOST=0.0.0.0`), keep the token strong and consider a VPN/Tailscale.

---

## Project layout

```
bigbro/
├── bigbro/                  # the agent package
│   ├── core.py              # agent loop (LLM ⇄ tools)
│   ├── config.py            # .env config, token handling
│   ├── persona.py           # BigBro's system prompt
│   ├── cli.py               # terminal chat
│   ├── llm/                 # pluggable brains: openai-compat, anthropic, gemini, mock
│   ├── capabilities/        # built-in tools (files, shell, scaffold, git, http)
│   └── web/                 # FastAPI dashboard + token auth
├── capabilities/            # ← YOUR extensions live here (auto-loaded)
├── templates/               # project starters (website / mobile / backend)
├── workspace/               # BigBro's working area (projects/, sessions/, notes.md)
├── tests/                   # offline test suite (mock brain, no API keys)
├── .env.example             # copy to .env and configure
└── requirements.txt
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

The suite runs BigBro end-to-end with the deterministic mock provider — no network, no API keys.

## Troubleshooting

- `OPENAI_API_KEY is not set` → edit `.env`.
- Ollama time-outs → `ollama pull <model>` first; pick a model that supports tools (llama3.1, qwen2.5…).
- Long builds hang → `run_command` caps at 300 s; start the dev server in your own terminal for interactive work.
- Dashboard 401 → you need the token BigBro printed at startup (in `.env` as `BIGBRO_TOKEN`).
