# Project — FastAPI backend starter

Scaffolded by BigBro from the `backend-fastapi` template.

## Setup

```bash
pip install -r requirements.txt
uvicorn main:app --reload    # API on http://localhost:8000, docs at /docs
```

## Endpoints

- `GET /health`
- `GET /api/items`, `POST /api/items`, `GET /api/items/{id}`, `DELETE /api/items/{id}`

The data store is in-memory — replace `_store` in `main.py` with a real DB.
