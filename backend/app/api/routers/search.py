from fastapi import APIRouter, Depends
from pydantic import BaseModel
import time
from app.globals import search_index
from app.auth import get_current_user, optional_auth

router = APIRouter()

class SearchRequest(BaseModel):
    q: str
    k: int = 5
    types: list[str] | None = None

@router.post("/search")
async def search_documents(req: SearchRequest, _user_id: str = Depends(optional_auth)):
    """Search documents (optionally authenticated for user-specific results)."""
    results = search_index.search(req.q, k=req.k)
    return {"results": results}

@router.post("/search/rebuild")
async def rebuild_search_index(_user_id: str = Depends(get_current_user)):
    """Rebuild the search index (authentication required)."""
    t0 = time.time()
    count = search_index.rebuild()
    dt = time.time() - t0
    return {"status": "ok", "indexed_count": count, "duration_seconds": round(dt, 3)}
