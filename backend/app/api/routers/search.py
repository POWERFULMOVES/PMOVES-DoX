from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
import time
from app.globals import db, search_index
from app.auth import get_current_user, optional_auth

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
    # Filter results to user-owned artifacts when authenticated
    if user_id:
        artifacts = db.get_artifacts()
        owned_ids = {
            a.get("id") for a in artifacts
            if a.get("uploaded_by") == user_id or a.get("user_id") == user_id
        }
        # Only apply filter if ownership metadata exists
        if owned_ids:
            results = [r for r in results if r.get("artifact_id") in owned_ids]
    return {"results": results}

@router.post("/search/rebuild")
async def rebuild_search_index(_user_id: str = Depends(get_current_user)):
    """Rebuild the search index (authentication required)."""
    t0 = time.time()
    count = search_index.rebuild()
    dt = time.time() - t0
    return {"status": "ok", "indexed_count": count, "duration_seconds": round(dt, 3)}
