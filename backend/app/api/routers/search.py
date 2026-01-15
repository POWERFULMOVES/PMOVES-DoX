from fastapi import APIRouter
from pydantic import BaseModel
import time
from app.globals import search_index

router = APIRouter()

class SearchRequest(BaseModel):
    q: str
    k: int = 5
    types: list[str] | None = None

@router.post("/search")
async def search_documents(req: SearchRequest):
    results = search_index.search(req.q, k=req.k)
    return {"results": results}

@router.post("/search/rebuild")
async def rebuild_search_index():
    t0 = time.time()
    count = search_index.rebuild()
    dt = time.time() - t0
    return {"status": "ok", "indexed_count": count, "duration_seconds": round(dt, 3)}
