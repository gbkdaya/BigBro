"""Token-protected local web dashboard for BigBro."""

import uuid
from typing import Dict, List

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..config import Config, ensure_token
from ..core import BigBro
from . import index_html

SESSIONS: Dict[str, List[dict]] = {}


class LoginIn(BaseModel):
    token: str


class ChatIn(BaseModel):
    message: str
    session_id: str = ""


def create_app(cfg: Config) -> FastAPI:
    bb = BigBro(cfg)
    app = FastAPI(title="BigBro", docs_url=None, redoc_url=None)

    def authorized(authorization: str | None):
        token = (authorization or "").removeprefix("Bearer ").strip()
        if token != cfg.token:
            raise HTTPException(status_code=401, detail="invalid or missing token")

    @app.get("/", response_class=HTMLResponse)
    def home():
        return index_html.PAGE

    @app.post("/api/login")
    def login(body: LoginIn):
        if body.token.strip() != cfg.token:
            raise HTTPException(status_code=401, detail="invalid token")
        return {"ok": True}

    @app.get("/api/health")
    def health(authorization: str | None = Header(None)):
        authorized(authorization)
        return {
            "ok": True,
            "provider": cfg.provider,
            "model": bb.provider.model,
            "model_source": getattr(bb.provider, "model_source", ""),
            "capabilities": [c.name for c in bb.caps],
        }

    @app.get("/api/capabilities")
    def capabilities(authorization: str | None = Header(None)):
        authorized(authorization)
        return [c.tool_schema()["function"] for c in bb.caps]

    @app.post("/api/chat")
    def chat(body: ChatIn, authorization: str | None = Header(None)):
        authorized(authorization)
        if not body.message.strip():
            raise HTTPException(status_code=400, detail="empty message")
        sid = body.session_id or uuid.uuid4().hex[:10]
        history = SESSIONS.get(sid, [])
        history, reply, events = bb.run(body.message, history, session_id=sid)
        SESSIONS[sid] = history
        return {
            "session_id": sid,
            "reply": reply,
            "events": [e.__dict__ for e in events],
        }

    return app


def serve(cfg: Config):
    import uvicorn

    cfg.token = ensure_token(cfg)
    app = create_app(cfg)
    print(f"🕶️  BigBro web UI → http://{cfg.host}:{cfg.port}")
    print(f"   access token     → {cfg.token}")
    print("   (token is stored in .env; the browser must know it to use BigBro)")
    uvicorn.run(app, host=cfg.host, port=cfg.port, log_level="warning")
