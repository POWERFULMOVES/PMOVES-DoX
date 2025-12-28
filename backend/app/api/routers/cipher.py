"""
Cipher Router

Defines the endpoints for:
- Memory management (adding/searching memories).
- Skills registry (listing/toggling skills).
- A2UI demo generation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.cipher_service import CipherService
from app.services.a2ui_service import A2UIService
from app.services.chit_service import chit_service
from app.services.geometry_engine import geometry_engine
import os
import json
import numpy as np
from app.globals import search_index
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
    return service.search_memory(category=category, q=q)

@router.get("/skills")
def get_skills():
    service = CipherService()
    return service.list_skills()

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

@router.post("/geometry/simulate")
async def simulate_geometry_event(cgp: Dict[str, Any] = Body(...)):
    """
    Simulate receiving a CHIT Geometry Packet (CGP).
    Decodes it and returns the A2UI SurfaceUpdate to visualize it.
    """
    decoded = chit_service.decode_cgp(cgp)
    
    return {
        "surfaceUpdate": {
            "surfaceId": "main-surface",
            "components": [
                {
                    "id": "geo-nav-1",
                    "component": {
                        "HyperbolicNavigator": {
                            "className": "w-full h-[600px] border-none shadow-none",
                            "width": 800,
                            "height": 600,
                            "data": {
                                "super_nodes": cgp.get("super_nodes", [])
                            }
                        }
                    }
                },
                {
                    "id": "zeta-vis-1",
                    "component": {
                        "ZetaVisualizer": {
                            "className": "w-full h-[150px] mt-4",
                            "width": 800,
                            "height": 150,
                            "frequencies": [14.13, 21.02, 25.01, 30.42, 32.93, 37.58, 40.91, 43.32],
                            "amplitudes": [0.8, 0.6, 0.5, 0.3, 0.2, 0.1, 0.4, 0.7]
                        }
                    }
                }
            ]
        },
        "beginRendering": {
            "surfaceId": "main-surface",
            "root": "geo-nav-1" # Note: renderer only does root. Ideally this structure handles lists.
        }
    }

@router.get("/geometry/demo-packet")
async def get_demo_cgp():
    """Returns a static CGP for testing."""
    return {
      "spec": "chit.cgp.v0.1",
      "meta": { "source": "demo" },
      "super_nodes": [
        {
          "id": "super_0",
          "x": 0, "y": 0, "r": 200, "label": "Resonant Mode 0",
          "constellations": [
            {
              "id": "const_0_0",
              "anchor": [1, 0, 0],
              "summary": "Logistics Cluster",
              "spectrum": [0.9, 0.2, 0.1, 0.0, 0.0],
              "radial_minmax": [0, 1],
              "points": [
                 { "id": "p1", "x": 50, "y": 50, "proj": 0.9, "conf": 0.95, "text": "St. Maarten Bridge Status: OK" },
                 { "id": "p2", "x": -40, "y": 60, "proj": 0.8, "conf": 0.85, "text": "Supply Chain Node A" }
              ]
            },
             {
              "id": "const_0_1",
              "anchor": [0, 1, 0],
              "summary": "Safety Cluster",
              "spectrum": [0.1, 0.8, 0.3, 0.1, 0.0],
              "radial_minmax": [0, 1],
              "points": [
                 { "id": "p3", "x": -20, "y": -80, "proj": 0.7, "conf": 0.80, "text": "Emergency Response Protocol" }
              ]
            }
          ]
        }
      ]
    }

@router.post("/geometry/visualize_manifold")
async def visualize_manifold(document_id: str = Body(..., embed=True)):
    """
    Analyzes the document's geometry and serves a 'trickout' visualization.
    Pass document_id='demo' to see a simulated hyperbolic tree.
    """
    embeddings = []
    
    if document_id == "demo":
        # Simulate a tree-like structure (Hyperbolic) for demo
        # Centroid + branching noise
        np.random.seed(42)
        # Create 4 clusters expanding outward (tree-like)
        for i in range(5): 
            base = np.random.rand(128) # 128-dim
            for j in range(10):
                # Add increasing noise to simulate divergence/hierarchy
                embeddings.append(base + np.random.normal(0, 0.5 * (i+1), 128))
    else:
        # Fetch real embeddings
        embeddings = search_index.get_embeddings_for_document(document_id)
        if not embeddings:
            raise HTTPException(status_code=404, detail=f"No embeddings found for document '{document_id}'. Ensure it is processed and text-indexed.")

    # 2. Analyze Shape
    analysis = geometry_engine.analyze_curvature(embeddings)
    
    # 3. Generate Config
    config = geometry_engine.generate_chit_config(analysis)
    
    # 4. Save to Pmoves-hyperdimensions submodule
    # Assuming submodule is at external/Pmoves-hyperdimensions
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    target_path = os.path.join(root, "external", "Pmoves-hyperdimensions", "saves", "chit_manifold.json")
    
    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        raise HTTPException(500, f"Failed to save manifold config: {e}")
        
    # 5. Return Link
    return {
        "status": "ok",
        "shape": config.get("meta", {}).get("inferred_shape"),
        "metrics": analysis,
        "url": "http://localhost:8000/hyperdimensions?load=chit_manifold.json"
    }
