"""BigBro backend starter — FastAPI with an in-memory store.
Swap the in-memory store for a real database (SQLAlchemy, Prisma, etc.) as needed.
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="BigBro API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- in-memory store (replace with a real DB) ---
_store = {}
_next_id = 1
# ------------------------------------------------


class ItemIn(BaseModel):
    name: str
    value: Optional[str] = None


class Item(ItemIn):
    id: int


@app.get("/health")
def health():
    return {"status": "ok", "service": "bigbro-api"}


@app.get("/api/items", response_model=List[Item])
def list_items():
    return sorted(_store.values(), key=lambda i: i["id"])


@app.post("/api/items", response_model=Item, status_code=201)
def create_item(item: ItemIn):
    global _next_id
    created = {"id": _next_id, "name": item.name, "value": item.value}
    _store[_next_id] = created
    _next_id += 1
    return created


@app.get("/api/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in _store:
        raise HTTPException(status_code=404, detail="item not found")
    return _store[item_id]


@app.delete("/api/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in _store:
        raise HTTPException(status_code=404, detail="item not found")
    del _store[item_id]
