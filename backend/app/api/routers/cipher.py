"""
Cipher Router

Defines the endpoints for:
- Memory management (adding/searching memories).
- Skills registry (listing/toggling skills).
- A2UI demo generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.cipher_service import CipherService
from app.services.a2ui_service import A2UIService
from app.database_factory import get_db_interface

router = APIRouter(prefix="/cipher", tags=["cipher", "memory", "skills", "a2ui"])

class MemoryRequest(BaseModel):
    category: str
    content: Any

class SkillRequest(BaseModel):
    enabled: bool

@router.post("/memory", response_model=Dict[str, str])
def add_memory(req: MemoryRequest):
    service = CipherService()
    # Direct DB access via service wrapper logic
    # In service: return self.db.add_memory("fact", content, context)
    # The service method signature is: add_memory(category, content, context) in DB
    # Service has: add_fact(content, source) -> calls db.add_memory('fact'...)
    # We want generic access here.
    
    # Let's use the DB directly or exposed service method if generic.
    # Service 'search' exists, but 'add_memory' generic isn't explicitly on Service class yet 
    # (it has add_fact, add_preference).
    # Let's use the DB interface directly for generic 'add_memory' to match the flexible API.
    db = get_db_interface()
    mid = db.add_memory(req.category, req.content)
    if not mid:
        raise HTTPException(status_code=500, detail="Failed to store memory")
    return {"id": mid, "status": "stored"}

@router.get("/memory")
def search_memory(q: Optional[str] = None, category: Optional[str] = None):
    service = CipherService()
    return service.search(q or "", category)

@router.get("/skills")
def get_skills():
    service = CipherService()
    return service.list_available_skills()

@router.put("/skills/{skill_id}")
async def toggle_skill(skill_id: str, enabled: bool, db=Depends(get_db_interface)):
    """Enable or disable a skill."""
    # TODO: Implement database update
    # For now, we just return the new state
    return {"id": skill_id, "enabled": enabled}

@router.get("/a2ui/demo")
async def get_a2ui_demo():
    """Returns a sample A2UI payload."""
    return A2UIService.generate_welcome_card()
