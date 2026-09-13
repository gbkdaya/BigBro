"""Configuration loading for BigBro. Everything is driven by environment variables (usually from a local .env file)."""

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv is optional; .env just won't be auto-loaded
    load_dotenv = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

PROVIDER_DEFAULT_MODELS = {
    # keep in sync with bigbro/llm/free_model.py
    "free": "inclusionai/ling-3.0-flash-vl:free",
    "openrouter": "inclusionai/ling-3.0-flash-vl:free",
    "openai": "gpt-5",
    "anthropic": "claude-sonnet-4-5",
    "gemini": "gemini-2.5-flash",
    "ollama": "llama3.1:8b",
    "mock": "mock",
}


@dataclass
class Config:
    provider: str = "free"
    model: str = ""
    workspace: Path = PROJECT_ROOT / "workspace"
    token: str = ""
    host: str = "127.0.0.1"
    port: int = 8321
    max_turns: int = 40
    temperature: float = 0.2
    extra_persona: str = ""

    def model_for_provider(self, provider: str | None = None) -> str:
        provider = provider or self.provider
        if self.model:
            return self.model
        env_model = os.environ.get(f"BIGBRO_{provider.upper()}_MODEL")
        return env_model or PROVIDER_DEFAULT_MODELS.get(provider, "gpt-5")


def load_config() -> Config:
    if load_dotenv is not None:
        load_dotenv(ENV_FILE)
    ws = Path(os.environ.get("BIGBRO_WORKSPACE", str(PROJECT_ROOT / "workspace")))
    if not ws.is_absolute():
        ws = (PROJECT_ROOT / ws).resolve()
    return Config(
        provider=os.environ.get("BIGBRO_PROVIDER", "free").strip().lower(),
        model=os.environ.get("BIGBRO_MODEL", "").strip(),
        workspace=ws,
        token=os.environ.get("BIGBRO_TOKEN", "").strip(),
        host=os.environ.get("BIGBRO_HOST", "127.0.0.1").strip(),
        port=int(os.environ.get("BIGBRO_PORT", "8321")),
        max_turns=int(os.environ.get("BIGBRO_MAX_TURNS", "40")),
        temperature=float(os.environ.get("BIGBRO_TEMPERATURE", "0.2")),
        extra_persona=os.environ.get("BIGBRO_EXTRA_PERSONA", "").strip(),
    )


def ensure_token(cfg: Config) -> str:
    """Guarantee the web UI always has a personal access token.

    If BIGBRO_TOKEN is not set, a random one is generated and persisted to .env
    so that only the person who owns this machine knows it.
    """
    if cfg.token:
        return cfg.token
    cfg.token = uuid.uuid4().hex
    try:
        env_exists = ENV_FILE.exists()
        with open(ENV_FILE, "a" if env_exists else "w") as f:
            if not env_exists:
                f.write("# BigBro local config — keep this file private\n")
            f.write(f"BIGBRO_TOKEN={cfg.token}\n")
    except OSError:
        pass
    return cfg.token
