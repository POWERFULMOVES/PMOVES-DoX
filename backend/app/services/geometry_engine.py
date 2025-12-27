"""
Geometry Engine service for PMOVES-DoX.
Calculates geometric properties (curvature, epsilon) of data manifolds 
and generates CHIT configurations for the visualization engine.
"""
import numpy as np
from typing import List, Dict, Any, Optional
import json

class GeometryEngine:
    """
    Analyzes the 'shape' of data embeddings to determine if they form a
    Hyperbolic (Tree), Spherical (Cycle), or Euclidean (Flat) manifold.
    """

    def analyze_curvature(self, embeddings: List[List[float]]) -> Dict[str, float]:
        """
        Estimates the delta-hyperbolicity of a set of embeddings using a 4-point condition check
        or a simplified centroid-distance distribution metrics.
        
        Returns:
            dict: {
                "delta": float (lower is more hyperbolic),
                "curvature_k": float (mapped parameter for vis),
                "epsilon": float (noise/temperature)
            }
        """
        if not embeddings or len(embeddings) < 4:
            # Not enough data for shape analysis, return flat default
            return {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

        # Simplified heuristic: 
        # 1. Compute centroid
        # 2. Compute distances to centroid
        # 3. Analyze distribution of distances (Poincaré data crowds at edge)
        
        data = np.array(embeddings)
        try:
            centroid = np.mean(data, axis=0)
            dists = np.linalg.norm(data - centroid, axis=1)
            
            # Simple heuristic for "Tree-likeness" (Hyperbolicity):
            # In high-dim Euclidean embedding of trees, norms tend to variance.
            # Real delta-hyp is expensive O(N^4), so we use a proxy score.
            # High variance + outliers = likely hierarchical/hyperbolic.
            dist_std = np.std(dists)
            dist_mean = np.mean(dists)
            
            # "Shape Score": 
            # High std/mean ratio -> Hyperbolic (Tree)
            # Low std/mean ratio -> Spherical/Compact
            shape_ratio = dist_std / (dist_mean + 1e-9)

            # Map to K (Visual Curvature):
            # shape_ratio > 0.5 -> Negative Curvature (Hyperbolic) -> K < -1
            # shape_ratio < 0.2 -> Positive Curvature (Spherical) -> K > 1
            
            k = 0.0
            if shape_ratio > 0.5:
                # Map 0.5..1.0 to -1.0..-5.0
                k = -1.0 - (shape_ratio - 0.5) * 8.0
            elif shape_ratio < 0.2:
                # Map 0.0..0.2 to 5.0..1.0
                k = 5.0 - (shape_ratio * 20.0)
            
            # Epsilon (Noise): Based on local clustering density or just entropy
            # High epsilon = chaotic.
            epsilon = min(1.0, shape_ratio)

            return {
                "delta": shape_ratio, # Using ratio as proxy for delta
                "curvature_k": k,
                "epsilon": epsilon
            }
        except Exception:
            return {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

    def generate_chit_config(self, analysis: Dict[str, float]) -> Dict[str, Any]:
        """
        Generates a 'chit_manifold.json' compatible dictionary for the
        Pmoves-hyperdimensions visualization tool.
        """
        k = analysis.get("curvature_k", 0.0)
        eps = analysis.get("epsilon", 0.1)
        
        # Determine surface function based on K
        # Default to Pseudosphere logic (from our earlier custom save),
        # but adapt based on sign of K.
        
        surface_type = "Flat"
        if k < -0.5:
            surface_type = "Hyperbolic (Pseudosphere)"
        elif k > 0.5:
            surface_type = "Spherical"

        # Construct the JSON model
        return {
            "surfaceFn": self._get_surface_fn_code(k),
            "params": {
                "uMin": 0, "uMax": 1,
                "vMin": 0, "vMax": 1,
                "uSegs": 150, "vSegs": 150
            },
            "surfaceInput": {
                "u": 0, "v": 0,
                "curvature": k,
                "epsilon": eps
            },
            "animatedParams": [
                {
                    "name": "epsilon",
                    "playing": True,
                    "min": max(0.0, eps - 0.2),
                    "max": min(1.0, eps + 0.2),
                    "step": 0.01,
                    "time": 5,
                    "phase": 0
                }
            ],
            "camera": {
                "position": {"x": 5, "y": 5, "z": 2},
                "target": {"x": 0, "y": 0, "z": 0}
            },
            "shininess": 150,
            "globalSaturation": 1.5,
            "meta": {
                "inferred_shape": surface_type,
                "delta_proxy": analysis.get("delta")
            }
        }

    def _get_surface_fn_code(self, k: float) -> str:
        """Returns the JS function string injected into the tool."""
        # Using a unified formula that morphs based on K if possible,
        # or switching logic. For now, strictly Pseudosphere-ish for K < 0.
        
        if k < -0.1:
            # Hyperbolic/Tractrix-like
            # Abs(k) controls size/opening
            return """function surface(input) {
    const u = input.u * 4 * Math.PI;
    const v = input.v * 2.9 + 0.1; 
    const k = Math.abs(input.curvature || 1.0);
    const eps = input.epsilon || 0.0;
    
    // Tractrix/Pseudosphere
    const x = k * (Math.cos(u) * Math.sin(v));
    const y = k * (Math.sin(u) * Math.sin(v));
    const z = -k * (Math.cos(v) + Math.log(Math.tan(v/2)));
    
    // Noise
    const noise = Math.sin(u * 10) * eps * 0.1;
    
    return {
        x: x, 
        y: y, 
        z: z + noise, 
        r: 0.5 + 0.5 * Math.sin(v), 
        g: 0.2, 
        b: 1.0 - eps, 
        a: 0.9
    };
}"""
        elif k > 0.1:
            # Spherical
            return """function surface(input) {
    const u = input.u * 2 * Math.PI;
    const v = input.v * Math.PI;
    const k = Math.abs(input.curvature || 1.0);
    const eps = input.epsilon || 0.0;
    
    const x = k * Math.sin(v) * Math.cos(u);
    const y = k * Math.sin(v) * Math.sin(u);
    const z = k * Math.cos(v);
    
    const noise = Math.cos(v * 20) * eps * 0.1;
    
    return {
        x: x + noise, 
        y: y + noise, 
        z: z, 
        r: 1.0 - eps, 
        g: 0.5 + 0.5*Math.cos(u), 
        b: 0.2, 
        a: 0.9
    };
}"""
        else:
            # Flat Plane
            return """function surface(input) {
    const u = (input.u - 0.5) * 10;
    const v = (input.v - 0.5) * 10;
    const eps = input.epsilon || 0.0;
    
    const z = Math.sin(u)*Math.cos(v) * eps;
    
    return {
        x: u, 
        y: v, 
        z: z, 
        r: 0.5, 
        g: 0.5, 
        b: 0.5, 
        a: 0.8
    };
}"""

geometry_engine = GeometryEngine()
