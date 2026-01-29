"""
Cipher Router

Defines the endpoints for:
- Memory management (adding/searching memories).
- Skills registry (listing/toggling skills).
- A2UI demo generation.

Memory operations support user_id for RLS (Row Level Security) scoping.
When using Supabase backend with RLS enabled, user_id should be provided
via the X-User-ID header or in the request body to ensure proper data isolation.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body, Header
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from app.services.cipher_service import CipherService
from app.services.a2ui_service import A2UIService
from app.services.chit_service import chit_service
from app.services.geometry_engine import geometry_engine
import os
import json
import logging
import numpy as np
from app.globals import search_index

logger = logging.getLogger(__name__)
from app.database_factory import get_db_interface

router = APIRouter(prefix="/cipher", tags=["cipher", "memory", "skills", "a2ui"])


class MemoryRequest(BaseModel):
    category: str
    content: Any
    user_id: Optional[str] = None  # Optional in body, can also come from header


class SkillRequest(BaseModel):
    enabled: bool


@router.post("/memory", response_model=Dict[str, str])
def add_memory(
    req: MemoryRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Add a memory entry.

    User identification for RLS scoping can be provided via:
    - X-User-ID header (recommended for authenticated requests)
    - user_id field in request body

    Header takes precedence over body if both are provided.

    TODO: In production, validate X-User-ID against authenticated JWT identity
    to prevent spoofing. Currently trusts client-provided values.
    """
    # Determine user_id: header takes precedence over body
    # TODO: Validate against authenticated context (JWT/session) to prevent spoofing
    user_id = x_user_id or req.user_id

    db = get_db_interface()
    mid = db.add_memory(req.category, req.content, user_id=user_id)
    if not mid:
        raise HTTPException(status_code=500, detail="Failed to store memory")
    return {"id": mid, "status": "stored"}


@router.get("/memory")
def search_memory(
    q: Optional[str] = None,
    category: Optional[str] = None,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID")
):
    """Search memory entries.

    User identification for RLS scoping can be provided via X-User-ID header.
    When provided, only memories belonging to that user will be returned.
    """
    service = CipherService()
    return service.search_memory(category=category, q=q, user_id=x_user_id)

@router.get("/skills")
def get_skills():
    service = CipherService()
    return service.list_skills()

@router.put("/skills/{skill_id}")
async def toggle_skill(skill_id: str, enabled: bool, db=Depends(get_db_interface)):
    """Enable or disable a skill."""
    try:
        updated_skill = db.update_skill(skill_id, enabled)
        if updated_skill is None:
            raise HTTPException(status_code=404, detail=f"Skill with id '{skill_id}' not found")
        return updated_skill
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update skill %s", skill_id)
        raise HTTPException(status_code=500, detail="Failed to update skill") from e

@router.get("/a2ui/demo")
async def get_a2ui_demo():
    """Returns a sample A2UI payload."""
    return A2UIService.generate_welcome_card()

@router.post("/geometry/simulate")
async def simulate_geometry_event(cgp: Dict[str, Any] = Body(...)):
    """
    Simulate receiving a CHIT Geometry Packet (CGP).
    Decodes it and returns the A2UI SurfaceUpdate to visualize it.

    Zeta frequencies are dynamically computed from:
    1. Constellation point spectra (if available)
    2. Point coordinate distributions
    3. Falls back to default zeta zeros if insufficient data
    """
    # Validate CGP structure (decode for validation, result not needed)
    _ = chit_service.decode_cgp(cgp)

    # Extract embeddings from CGP for zeta spectrum computation
    # Use constellation spectra and point coordinates as proxy embeddings
    raw_embeddings = []
    super_nodes = cgp.get("super_nodes", [])

    for node in super_nodes:
        constellations = node.get("constellations", [])
        for const in constellations:
            # Use spectrum as embedding if available
            spectrum = const.get("spectrum", [])
            if spectrum and len(spectrum) >= 2:
                raw_embeddings.append(spectrum)

            # Also use point coordinates as 2D embeddings
            points = const.get("points", [])
            for pt in points:
                x = pt.get("x", 0)
                y = pt.get("y", 0)
                proj = pt.get("proj", 0.5)
                conf = pt.get("conf", 0.5)
                raw_embeddings.append([x, y, proj, conf])

    # Normalize embeddings to consistent dimension (pad/truncate to avoid ragged arrays)
    target_dim = 4  # Use 4D as minimum for point embeddings
    if raw_embeddings:
        max_dim = max(len(e) for e in raw_embeddings)
        target_dim = max(target_dim, max_dim)
        embeddings = []
        for e in raw_embeddings:
            if len(e) < target_dim:
                # Pad with zeros
                embeddings.append(e + [0.0] * (target_dim - len(e)))
            elif len(e) > target_dim:
                # Truncate
                embeddings.append(e[:target_dim])
            else:
                embeddings.append(e)
    else:
        embeddings = []

    # Compute dynamic zeta spectrum from embeddings
    frequencies, amplitudes = geometry_engine.compute_zeta_spectrum(embeddings)

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
                                "super_nodes": super_nodes
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
                            "frequencies": frequencies,
                            "amplitudes": amplitudes
                        }
                    }
                }
            ]
        },
        "beginRendering": {
            "surfaceId": "main-surface",
            "root": "geo-nav-1"
        },
        "meta": {
            "computed_zeta": True,
            "embedding_count": len(embeddings),
            "frequency_count": len(frequencies)
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
        # High variance in distances to centroid = hyperbolic geometry
        # Mix of tight center points and far outliers
        np.random.seed(42)
        dim = 64  # Lower dim for clearer variance

        # Tight center cluster (very close to origin)
        center = np.zeros(dim)
        for _ in range(8):
            embeddings.append((center + np.random.normal(0, 0.01, dim)).tolist())

        # Far outliers at varying distances (tree branches)
        # Outlier 1: Very far
        outlier1 = np.ones(dim) * 15.0
        embeddings.append(outlier1.tolist())

        # Outlier 2: Far in opposite direction
        outlier2 = np.ones(dim) * -12.0
        embeddings.append(outlier2.tolist())

        # Outlier 3: Different direction
        outlier3 = np.zeros(dim)
        outlier3[:32] = 10.0
        outlier3[32:] = -10.0
        embeddings.append(outlier3.tolist())

        # Medium distance points (intermediate hierarchy levels)
        for _ in range(4):
            mid = np.random.randn(dim) * 3.0
            embeddings.append(mid.tolist())
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
        
    # 5. Compute zeta spectrum from embeddings
    frequencies, amplitudes = geometry_engine.compute_zeta_spectrum(embeddings)

    # 6. Publish manifold update to NATS for real-time visualization
    try:
        import asyncio
        asyncio.create_task(chit_service.publish_manifold_update(analysis))
    except Exception as e:
        # Non-blocking - log but don't fail the request
        logger.warning(f"Failed to publish manifold update to NATS: {e}")

    # 7. Return Link and metrics
    return {
        "status": "ok",
        "shape": config.get("meta", {}).get("inferred_shape"),
        "metrics": analysis,
        "zeta_spectrum": {
            "frequencies": frequencies,
            "amplitudes": amplitudes
        },
        "url": "http://localhost:8000/hyperdimensions?load=chit_manifold.json"
    }
