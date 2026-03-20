from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import time
from app.globals import search_index
from app.auth import get_current_user, optional_auth
from app.api.routers.analysis import _get_user_artifact_ids

router = APIRouter()

class SearchRequest(BaseModel):
    q: str
    k: int = 5
    types: list[str] | None = None

@router.post("/search")
async def search_documents(
    req: SearchRequest,
    user_id: Optional[str] = Depends(optional_auth),
):
    """Search documents, scoped to authenticated user's artifacts."""
    results = search_index.search(req.q, k=req.k)
    allowed = _get_user_artifact_ids(user_id)
    if allowed is not None:
        results = [r for r in results if r.get("artifact_id") in allowed]
    return {"results": results}

@router.post("/search/rebuild")
async def rebuild_search_index(_user_id: str = Depends(get_current_user)):
    """Rebuild the search index (authentication required)."""
    t0 = time.time()
    count = search_index.rebuild()
    dt = time.time() - t0
    return {"status": "ok", "indexed_count": count, "duration_seconds": round(dt, 3)}
