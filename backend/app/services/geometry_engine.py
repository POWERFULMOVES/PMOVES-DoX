"""
Geometry Engine service for PMOVES-DoX.
Calculates geometric properties (curvature, epsilon) of data manifolds
and generates CHIT configurations for the visualization engine.

Hyperbolicity Computation:
- Uses the 4-point Gromov product condition to measure delta-hyperbolicity
- Set EXACT_DELTA=true to enable exact computation (O(N^4), slow for large datasets)
- Default mode uses faster proxy heuristics based on centroid-distance variance
"""
import numpy as np
import os
import itertools
from typing import List, Dict, Any, Optional, Tuple
import json
import logging

logger = logging.getLogger(__name__)

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

            # Check if exact delta computation is requested
            use_exact = os.getenv("EXACT_DELTA", "").lower() in {"1", "true", "yes"}

            if use_exact and len(embeddings) >= 4:
                exact_delta = self.compute_exact_delta(embeddings)
                logger.info(f"Exact delta-hyperbolicity: {exact_delta:.4f}")
                # Use exact delta if computed successfully
                if exact_delta > 0:
                    # Adjust curvature based on exact delta
                    # Lower delta = more hyperbolic
                    if exact_delta < 0.1:
                        k = -3.0 - (0.1 - exact_delta) * 20
                    elif exact_delta < 0.3:
                        k = -1.0 - (0.3 - exact_delta) * 6.67
                    else:
                        k = shape_ratio * 2 if shape_ratio < 0.3 else k

                    return {
                        "delta": exact_delta,
                        "delta_proxy": shape_ratio,
                        "curvature_k": k,
                        "epsilon": epsilon
                    }

            return {
                "delta": shape_ratio,  # Using ratio as proxy for delta
                "curvature_k": k,
                "epsilon": epsilon
            }
        except Exception as e:
            logger.error(f"analyze_curvature error: {e}")
            return {"delta": 0.0, "curvature_k": 0.0, "epsilon": 0.0}

    def compute_exact_delta(
        self,
        embeddings: List[List[float]],
        sample_size: int = 100
    ) -> float:
        """
        Compute exact delta-hyperbolicity via the 4-point Gromov product condition.

        The 4-point condition states that for any four points x, y, z, w in a
        delta-hyperbolic space:
            (x|z)_w >= min((x|y)_w, (y|z)_w) - delta

        where (x|y)_w = 0.5 * (d(w,x) + d(w,y) - d(x,y)) is the Gromov product.

        This is an O(N^4) algorithm, so we sample for large datasets.

        Args:
            embeddings: List of embedding vectors.
            sample_size: Maximum number of points to sample (default: 100).

        Returns:
            Delta value (lower = more hyperbolic, 0 = tree metric).
        """
        if len(embeddings) < 4:
            return 0.0

        data = np.array(embeddings)
        n = len(data)

        # Sample if dataset is too large
        if n > sample_size:
            indices = np.random.choice(n, sample_size, replace=False)
            data = data[indices]
            n = sample_size
            logger.info(f"Exact delta: sampling {sample_size} points from {len(embeddings)}")

        # Precompute all pairwise distances
        # dist_matrix[i,j] = ||data[i] - data[j]||
        diff = data[:, np.newaxis, :] - data[np.newaxis, :, :]
        dist_matrix = np.sqrt(np.sum(diff ** 2, axis=2))

        # Compute delta via 4-point condition
        max_delta = 0.0

        # For efficiency, we iterate over all 4-tuples
        # Using combination iteration to avoid duplicates
        for w in range(n):
            for x, y, z in itertools.combinations(range(n), 3):
                if w in (x, y, z):
                    continue

                # Gromov products at basepoint w
                # (x|y)_w = 0.5 * (d(w,x) + d(w,y) - d(x,y))
                gp_xy_w = 0.5 * (dist_matrix[w, x] + dist_matrix[w, y] - dist_matrix[x, y])
                gp_xz_w = 0.5 * (dist_matrix[w, x] + dist_matrix[w, z] - dist_matrix[x, z])
                gp_yz_w = 0.5 * (dist_matrix[w, y] + dist_matrix[w, z] - dist_matrix[y, z])

                # 4-point condition: (x|z)_w >= min((x|y)_w, (y|z)_w) - delta
                # Rearranging: delta >= min((x|y)_w, (y|z)_w) - (x|z)_w
                # We want the maximum delta that makes this hold

                # Check all three orderings
                deltas = [
                    min(gp_xy_w, gp_yz_w) - gp_xz_w,
                    min(gp_xy_w, gp_xz_w) - gp_yz_w,
                    min(gp_xz_w, gp_yz_w) - gp_xy_w,
                ]
                local_delta = max(deltas)
                max_delta = max(max_delta, local_delta)

        return max_delta

    def compute_zeta_spectrum(self, embeddings: List[List[float]]) -> Tuple[List[float], List[float]]:
        """
        Derive Riemann Zeta-like frequencies from embedding covariance eigenvalues.

        The eigenvalues of the covariance matrix capture the principal variance
        directions of the embedding space. We map these to frequencies near the
        first non-trivial zeta zeros (14.13, 21.02, 25.01, ...) for visualization.

        Args:
            embeddings: List of embedding vectors

        Returns:
            Tuple of (frequencies, amplitudes) for ZetaVisualizer
        """
        # Default zeta zeros (first non-trivial zeros of Riemann zeta function)
        default_frequencies = [14.134725, 21.022040, 25.010858, 30.424876, 32.935062]
        default_amplitudes = [0.8, 0.6, 0.5, 0.4, 0.3]

        if not embeddings or len(embeddings) < 2:
            return default_frequencies[:3], default_amplitudes[:3]

        try:
            matrix = np.array(embeddings)

            # Handle 1D case (single feature)
            if matrix.ndim == 1 or matrix.shape[1] == 1:
                return default_frequencies[:3], default_amplitudes[:3]

            # Compute covariance matrix
            cov = np.cov(matrix.T)

            # Handle scalar covariance (2 samples)
            if np.isscalar(cov) or cov.ndim == 0:
                return default_frequencies[:3], default_amplitudes[:3]

            # Get eigenvalues (sorted ascending)
            eigenvalues = np.linalg.eigvalsh(cov)

            # Take top eigenvalues (largest variance directions)
            top_eigenvalues = eigenvalues[-8:][::-1]  # Reverse to get descending order

            # Normalize eigenvalues to [0, 1] range
            ev_max = np.max(np.abs(top_eigenvalues)) + 1e-9
            normalized_ev = np.abs(top_eigenvalues) / ev_max

            # Map to zeta-like frequencies: base_freq + eigenvalue_contribution
            # First zeta zero is ~14.13, spacing is roughly 5-7 between zeros
            base_freq = 14.13
            frequencies = base_freq + normalized_ev * 20  # Scale to spread across 14-34 range

            # Amplitudes decay with index (higher eigenvalues = stronger signal)
            n = len(frequencies)
            amplitudes = 1.0 / (1.0 + np.arange(n) * 0.3)

            # Modulate amplitudes by normalized eigenvalue magnitude
            amplitudes = amplitudes * (0.5 + 0.5 * normalized_ev)

            return frequencies.tolist(), amplitudes.tolist()

        except Exception:
            return default_frequencies[:3], default_amplitudes[:3]

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
