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
        except (ValueError, TypeError, np.linalg.LinAlgError) as e:
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

        except (ValueError, TypeError, np.linalg.LinAlgError) as e:
            logger.debug(f"compute_zeta_spectrum fallback to defaults: {e}")
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

    def analyze_semantic_clusters(
        self,
        embeddings: List[np.ndarray],
        labels: Optional[List[str]] = None,
        n_clusters: Optional[int] = None
    ) -> Dict[str, Any]:
        """Analyze semantic clusters in embedding space.

        Uses K-Means clustering with automatic cluster count detection via
        the elbow method when n_clusters is not specified.

        Args:
            embeddings: List of embedding vectors.
            labels: Optional labels for each embedding.
            n_clusters: Number of clusters (auto-detect if None).

        Returns:
            ClusterAnalysis dict with:
            - clusters: List of cluster info (centroid, members, density)
            - silhouette_score: Clustering quality metric (-1 to 1, higher is better)
            - manifold_type: Detected manifold type for clusters
        """
        if not embeddings or len(embeddings) < 2:
            return {
                "clusters": [],
                "silhouette_score": 0.0,
                "manifold_type": "insufficient_data"
            }

        try:
            from sklearn.cluster import KMeans
            from sklearn.metrics import silhouette_score
        except ImportError:
            logger.warning("sklearn not available, using simplified clustering")
            return self._fallback_clustering(embeddings, labels)

        data = np.array([np.array(e) for e in embeddings])
        n_samples = len(data)

        # Auto-detect optimal number of clusters using elbow method
        if n_clusters is None:
            n_clusters = self._detect_optimal_clusters(data)

        # Ensure valid n_clusters
        n_clusters = max(2, min(n_clusters, n_samples - 1))

        try:
            # Perform K-Means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(data)

            # Calculate silhouette score
            if n_clusters >= 2 and n_clusters < n_samples:
                sil_score = silhouette_score(data, cluster_labels)
            else:
                sil_score = 0.0

            # Build cluster info
            clusters = []
            for i in range(n_clusters):
                mask = cluster_labels == i
                cluster_points = data[mask]
                member_indices = np.where(mask)[0].tolist()

                # Calculate cluster density (inverse of average distance to centroid)
                centroid = kmeans.cluster_centers_[i]
                distances = np.linalg.norm(cluster_points - centroid, axis=1)
                avg_dist = np.mean(distances) if len(distances) > 0 else 0.0
                density = 1.0 / (avg_dist + 1e-9)

                # Get member labels if provided
                member_labels = None
                if labels:
                    member_labels = [labels[j] for j in member_indices if j < len(labels)]

                clusters.append({
                    "cluster_id": i,
                    "centroid": centroid.tolist(),
                    "member_indices": member_indices,
                    "member_labels": member_labels,
                    "size": int(np.sum(mask)),
                    "density": float(density),
                    "avg_distance_to_centroid": float(avg_dist)
                })

            # Detect manifold type based on cluster distribution
            manifold_type = self._detect_cluster_manifold_type(clusters, data)

            return {
                "clusters": clusters,
                "silhouette_score": float(sil_score),
                "manifold_type": manifold_type,
                "n_clusters": n_clusters
            }

        except Exception as e:
            logger.error(f"analyze_semantic_clusters error: {e}")
            return {
                "clusters": [],
                "silhouette_score": 0.0,
                "manifold_type": "error"
            }

    def _detect_optimal_clusters(self, data: np.ndarray, max_clusters: int = 10) -> int:
        """Detect optimal number of clusters using elbow method.

        Args:
            data: Embedding data matrix.
            max_clusters: Maximum clusters to consider.

        Returns:
            Optimal number of clusters.
        """
        try:
            from sklearn.cluster import KMeans
        except ImportError:
            return min(3, len(data) - 1)

        n_samples = len(data)
        max_k = min(max_clusters, n_samples - 1)

        if max_k < 2:
            return 2

        inertias = []
        k_range = range(2, max_k + 1)

        for k in k_range:
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            kmeans.fit(data)
            inertias.append(kmeans.inertia_)

        # Find elbow using second derivative
        if len(inertias) < 3:
            return 2

        inertias = np.array(inertias)
        # Compute second derivative
        d1 = np.diff(inertias)
        d2 = np.diff(d1)

        # Elbow is where second derivative is maximum (most negative to less negative)
        elbow_idx = np.argmax(d2) + 2  # +2 because we started at k=2 and lost 2 from diff
        optimal_k = list(k_range)[min(elbow_idx, len(k_range) - 1)]

        return optimal_k

    def _detect_cluster_manifold_type(
        self,
        clusters: List[Dict[str, Any]],
        data: np.ndarray
    ) -> str:
        """Detect manifold type based on cluster distribution.

        Args:
            clusters: Cluster analysis results.
            data: Original embedding data.

        Returns:
            Manifold type string.
        """
        if len(clusters) < 2:
            return "flat"

        # Analyze inter-cluster distances
        centroids = np.array([c["centroid"] for c in clusters])

        # Compute pairwise distances between centroids
        n = len(centroids)
        inter_dists = []
        for i in range(n):
            for j in range(i + 1, n):
                inter_dists.append(np.linalg.norm(centroids[i] - centroids[j]))

        if not inter_dists:
            return "flat"

        inter_dists = np.array(inter_dists)

        # Analyze variance of inter-cluster distances
        dist_cv = np.std(inter_dists) / (np.mean(inter_dists) + 1e-9)

        # Analyze cluster densities
        densities = [c["density"] for c in clusters]
        density_cv = np.std(densities) / (np.mean(densities) + 1e-9)

        # High variance in distances = hierarchical = hyperbolic
        # Low variance, compact = spherical
        if dist_cv > 0.5 or density_cv > 0.5:
            return "hyperbolic"
        elif dist_cv < 0.2 and density_cv < 0.3:
            return "spherical"
        else:
            return "euclidean"

    def _fallback_clustering(
        self,
        embeddings: List[np.ndarray],
        labels: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Fallback clustering when sklearn is not available.

        Uses simple centroid-based single cluster approach.
        """
        data = np.array([np.array(e) for e in embeddings])
        centroid = np.mean(data, axis=0)
        distances = np.linalg.norm(data - centroid, axis=1)

        return {
            "clusters": [{
                "cluster_id": 0,
                "centroid": centroid.tolist(),
                "member_indices": list(range(len(data))),
                "member_labels": labels,
                "size": len(data),
                "density": float(1.0 / (np.mean(distances) + 1e-9)),
                "avg_distance_to_centroid": float(np.mean(distances))
            }],
            "silhouette_score": 0.0,
            "manifold_type": "euclidean"
        }

    def compute_geodesic_distance(
        self,
        point_a: np.ndarray,
        point_b: np.ndarray,
        geometry: str = "auto"
    ) -> float:
        """Compute geodesic distance between two points.

        Computes the distance on the specified manifold type:
        - Hyperbolic: Poincaré ball distance
        - Spherical: Great circle (arc) distance
        - Euclidean: Standard L2 norm

        Args:
            point_a: First embedding vector.
            point_b: Second embedding vector.
            geometry: Manifold type ("hyperbolic", "spherical", "euclidean", "auto")

        Returns:
            Geodesic distance on the manifold.
        """
        a = np.array(point_a)
        b = np.array(point_b)

        # Auto-detect geometry from point norms
        if geometry == "auto":
            geometry = self._detect_geometry_from_points(a, b)

        if geometry == "hyperbolic":
            return self._poincare_distance(a, b)
        elif geometry == "spherical":
            return self._spherical_distance(a, b)
        else:  # euclidean
            return float(np.linalg.norm(a - b))

    def _detect_geometry_from_points(
        self,
        point_a: np.ndarray,
        point_b: np.ndarray
    ) -> str:
        """Detect geometry type from point characteristics.

        Uses norms and relative positions to infer manifold type.
        """
        norm_a = np.linalg.norm(point_a)
        norm_b = np.linalg.norm(point_b)

        # Points very close to unit sphere boundary suggest Poincaré model
        if norm_a > 0.8 or norm_b > 0.8:
            if norm_a < 1.0 and norm_b < 1.0:
                return "hyperbolic"

        # Points on or near unit sphere suggest spherical geometry
        if 0.95 < norm_a < 1.05 and 0.95 < norm_b < 1.05:
            return "spherical"

        return "euclidean"

    def _poincare_distance(self, point_a: np.ndarray, point_b: np.ndarray) -> float:
        """Compute Poincaré ball distance.

        d(a, b) = arccosh(1 + 2 * ||a - b||^2 / ((1 - ||a||^2)(1 - ||b||^2)))

        Args:
            point_a: First point in Poincaré ball.
            point_b: Second point in Poincaré ball.

        Returns:
            Hyperbolic distance.
        """
        norm_a_sq = np.sum(point_a ** 2)
        norm_b_sq = np.sum(point_b ** 2)
        diff_sq = np.sum((point_a - point_b) ** 2)

        # Clamp norms to stay inside the ball
        norm_a_sq = min(norm_a_sq, 0.999)
        norm_b_sq = min(norm_b_sq, 0.999)

        denominator = (1 - norm_a_sq) * (1 - norm_b_sq)

        if denominator <= 0:
            return float('inf')

        # Poincaré distance formula
        x = 1 + 2 * diff_sq / denominator

        # arccosh(x) = ln(x + sqrt(x^2 - 1))
        if x < 1:
            x = 1.0

        return float(np.arccosh(x))

    def _spherical_distance(self, point_a: np.ndarray, point_b: np.ndarray) -> float:
        """Compute great circle distance on a sphere.

        d(a, b) = arccos(a · b / (||a|| ||b||))

        Args:
            point_a: First point (normalized to unit sphere).
            point_b: Second point (normalized to unit sphere).

        Returns:
            Spherical (arc) distance.
        """
        norm_a = np.linalg.norm(point_a)
        norm_b = np.linalg.norm(point_b)

        if norm_a < 1e-9 or norm_b < 1e-9:
            return 0.0

        # Normalize to unit sphere
        a_unit = point_a / norm_a
        b_unit = point_b / norm_b

        # Dot product gives cosine of angle
        cos_angle = np.dot(a_unit, b_unit)

        # Clamp to valid range for arccos
        cos_angle = np.clip(cos_angle, -1.0, 1.0)

        return float(np.arccos(cos_angle))

    def determine_attention_allocation(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
        temperature: float = 1.0
    ) -> List[float]:
        """Determine attention weights for candidates based on query.

        Uses geodesic distances and softmax to compute attention weights.
        Closer candidates receive higher attention weights.

        Args:
            query_embedding: The query vector.
            candidate_embeddings: List of candidate vectors.
            temperature: Softmax temperature (lower = sharper focus).

        Returns:
            List of attention weights summing to 1.0.
        """
        if not candidate_embeddings:
            return []

        if len(candidate_embeddings) == 1:
            return [1.0]

        query = np.array(query_embedding)

        # Compute geodesic distances from query to each candidate
        distances = []
        for candidate in candidate_embeddings:
            dist = self.compute_geodesic_distance(query, np.array(candidate), geometry="auto")
            distances.append(dist)

        distances = np.array(distances)

        # Handle infinite distances
        max_finite = np.max(distances[np.isfinite(distances)]) if np.any(np.isfinite(distances)) else 1.0
        distances = np.where(np.isfinite(distances), distances, max_finite * 2)

        # Convert distances to similarities (negative distances)
        # and apply softmax with temperature
        # Lower distance = higher similarity = higher attention
        similarities = -distances / (temperature + 1e-9)

        # Softmax for numerical stability
        similarities = similarities - np.max(similarities)
        exp_sims = np.exp(similarities)
        attention_weights = exp_sims / (np.sum(exp_sims) + 1e-9)

        return attention_weights.tolist()

    def detect_knowledge_gaps(
        self,
        embeddings: List[np.ndarray],
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Detect low-density regions indicating knowledge gaps.

        Uses kernel density estimation to find sparse regions in the
        embedding space that may represent gaps in coverage.

        Args:
            embeddings: Embedding vectors representing knowledge.
            threshold: Density threshold for gap detection (0-1, lower = more gaps).

        Returns:
            List of gap regions with centroids and suggested topics.
        """
        if not embeddings or len(embeddings) < 3:
            return []

        data = np.array([np.array(e) for e in embeddings])
        n_samples, n_dims = data.shape

        try:
            # Compute local density for each point using k-NN distances
            k = min(5, n_samples - 1)

            # Pairwise distance matrix
            diff = data[:, np.newaxis, :] - data[np.newaxis, :, :]
            dist_matrix = np.sqrt(np.sum(diff ** 2, axis=2))

            # For each point, get average distance to k nearest neighbors
            local_densities = []
            for i in range(n_samples):
                dists = np.sort(dist_matrix[i])[1:k+1]  # Exclude self (distance 0)
                avg_knn_dist = np.mean(dists)
                # Density is inverse of average distance
                density = 1.0 / (avg_knn_dist + 1e-9)
                local_densities.append(density)

            local_densities = np.array(local_densities)

            # Normalize densities to [0, 1]
            min_density = np.min(local_densities)
            max_density = np.max(local_densities)
            if max_density > min_density:
                normalized_densities = (local_densities - min_density) / (max_density - min_density)
            else:
                normalized_densities = np.ones(n_samples) * 0.5

            # Find low-density points (below threshold)
            gap_mask = normalized_densities < threshold
            gap_indices = np.where(gap_mask)[0]

            if len(gap_indices) == 0:
                return []

            # Cluster gap points to find distinct gap regions
            gap_points = data[gap_indices]
            gap_regions = self._cluster_gap_points(gap_points, gap_indices, normalized_densities)

            return gap_regions

        except Exception as e:
            logger.error(f"detect_knowledge_gaps error: {e}")
            return []

    def _cluster_gap_points(
        self,
        gap_points: np.ndarray,
        gap_indices: np.ndarray,
        densities: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Cluster gap points into distinct regions.

        Args:
            gap_points: Embedding vectors identified as gaps.
            gap_indices: Original indices of gap points.
            densities: Normalized density values for all points.

        Returns:
            List of gap region descriptions.
        """
        if len(gap_points) == 0:
            return []

        if len(gap_points) == 1:
            return [{
                "region_id": 0,
                "centroid": gap_points[0].tolist(),
                "member_indices": gap_indices.tolist(),
                "avg_density": float(densities[gap_indices[0]]),
                "size": 1,
                "severity": float(1.0 - densities[gap_indices[0]]),
                "suggested_topic": "Underexplored area near boundary"
            }]

        try:
            from sklearn.cluster import DBSCAN

            # Use DBSCAN to find natural clusters of gap points
            eps = np.percentile(
                np.linalg.norm(gap_points[:, np.newaxis] - gap_points, axis=2),
                30
            )
            clustering = DBSCAN(eps=max(eps, 0.1), min_samples=1).fit(gap_points)
            cluster_labels = clustering.labels_

        except ImportError:
            # Fallback: treat all gaps as one region
            cluster_labels = np.zeros(len(gap_points), dtype=int)

        # Build gap region info
        gap_regions = []
        unique_labels = np.unique(cluster_labels)

        for i, label in enumerate(unique_labels):
            if label == -1:  # DBSCAN noise points
                continue

            mask = cluster_labels == label
            region_points = gap_points[mask]
            region_indices = gap_indices[mask]

            centroid = np.mean(region_points, axis=0)
            avg_density = np.mean(densities[region_indices])

            # Severity based on how sparse the region is
            severity = 1.0 - avg_density

            # Generate suggested topic based on centroid position
            suggested_topic = self._generate_gap_topic_suggestion(centroid, severity)

            gap_regions.append({
                "region_id": int(i),
                "centroid": centroid.tolist(),
                "member_indices": region_indices.tolist(),
                "avg_density": float(avg_density),
                "size": int(np.sum(mask)),
                "severity": float(severity),
                "suggested_topic": suggested_topic
            })

        # Sort by severity (most severe gaps first)
        gap_regions.sort(key=lambda x: x["severity"], reverse=True)

        return gap_regions

    def _generate_gap_topic_suggestion(
        self,
        centroid: np.ndarray,
        severity: float
    ) -> str:
        """Generate a suggested topic description for a knowledge gap.

        Args:
            centroid: Center of the gap region.
            severity: How severe the gap is (0-1).

        Returns:
            Suggested topic string.
        """
        # Analyze centroid characteristics
        norm = np.linalg.norm(centroid)
        dim = len(centroid)

        # Determine position description
        if norm < 0.3:
            position = "central"
        elif norm < 0.7:
            position = "intermediate"
        else:
            position = "peripheral"

        # Severity description
        if severity > 0.8:
            severity_desc = "Critical"
        elif severity > 0.5:
            severity_desc = "Significant"
        else:
            severity_desc = "Minor"

        return f"{severity_desc} gap in {position} region (norm={norm:.2f}, dim={dim})"


geometry_engine = GeometryEngine()
