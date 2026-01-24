# Agent Skill: Geometry Engine (Curvature Analysis)

**Version:** 1.0.0
**Model:** Any (Tool-based execution)
**Thread Type:** Base Thread (B) - Computational service

## Description

This skill enables agents to analyze the geometric properties of data manifolds. It computes curvature (hyperbolic/spherical/Euclidean), delta-hyperbolicity, and Riemann Zeta-like spectral frequencies from embedding vectors. The output drives the PMOVES-DoX "Mathematical UI" visualization layer.

**When to use:**
- Determining if document embeddings form a tree-like (hyperbolic) or cluster-like (spherical) structure
- Computing delta-hyperbolicity using the 4-point Gromov condition
- Generating spectral frequencies for ZetaVisualizer animations
- Creating CHIT manifold configurations for Pmoves-hyperdimensions
- Understanding the "shape" of knowledge for optimal visualization

**Why it exists:**
Different document structures have different geometric signatures. Hierarchical documents (org charts, taxonomies) are hyperbolic. Clustered topics (related products) are spherical. The Geometry Engine detects this automatically, enabling the visualization layer to render the appropriate manifold surface.

## Core Principles

1. **Curvature Mapping:** Embedding variance ratios map to curvature K: high variance = hyperbolic (K < 0), low variance = spherical (K > 0).
2. **Computational Awareness:** Exact delta computation is O(N^4) - use sampling for large datasets (> 100 points).
3. **Graceful Defaults:** Insufficient data (< 4 embeddings) returns flat/zero curvature defaults.
4. **Visualization-Ready Output:** All outputs are designed to feed directly into Three.js or D3.js visualizers.

## Capabilities

- **Curvature Analysis:** Compute delta-hyperbolicity and curvature K from embeddings
- **Exact Delta:** Compute true Gromov 4-point delta (optional, expensive)
- **Zeta Spectrum:** Derive visualization frequencies from covariance eigenvalues
- **CHIT Config Generation:** Create `chit_manifold.json` for Pmoves-hyperdimensions
- **Surface Function Generation:** Generate JavaScript surface functions for Three.js

## Tools

The following methods are available on the `geometry_engine` singleton:

| Method | Description | Usage |
|--------|-------------|-------|
| `analyze_curvature(embeddings)` | Compute curvature from embeddings | `result = geometry_engine.analyze_curvature(embeddings_list)` |
| `compute_exact_delta(embeddings, sample_size)` | Exact 4-point Gromov delta | `delta = geometry_engine.compute_exact_delta(embeddings, 100)` |
| `compute_zeta_spectrum(embeddings)` | Get frequencies and amplitudes | `freqs, amps = geometry_engine.compute_zeta_spectrum(embeddings)` |
| `generate_chit_config(analysis)` | Create CHIT manifold config | `config = geometry_engine.generate_chit_config(curvature_result)` |

## Context Priming

Before using the Geometry Engine:
1. Ensure embeddings are normalized or at least comparable in scale
2. Check embedding count: minimum 4 for curvature, 2 for zeta spectrum
3. For exact delta, set `EXACT_DELTA=true` in environment (expensive!)
4. Understand the curvature interpretation:
   - K < -0.5: Hyperbolic (tree-like, hierarchical)
   - K > 0.5: Spherical (clustered, compact)
   - -0.5 <= K <= 0.5: Euclidean (flat, random)

## Output Schemas

### analyze_curvature() Response

```python
{
    "delta": 0.35,           # Proxy or exact delta-hyperbolicity
    "curvature_k": -2.5,     # Mapped curvature for visualization
    "epsilon": 0.25,         # Noise/temperature parameter
    # If EXACT_DELTA=true:
    "delta_proxy": 0.35      # The heuristic estimate
}
```

### Curvature K Interpretation

| K Range | Surface Type | Shape | Example Data |
|---------|--------------|-------|--------------|
| K < -1.0 | Hyperbolic (Pseudosphere) | Saddle-like | Org charts, taxonomies |
| -1.0 to -0.5 | Mildly Hyperbolic | Gentle curves | Hierarchical docs |
| -0.5 to 0.5 | Euclidean (Flat) | Plane | Random data |
| 0.5 to 1.0 | Mildly Spherical | Gentle dome | Related topics |
| K > 1.0 | Spherical | Ball-like | Tightly clustered data |

### generate_chit_config() Response

```json
{
  "surfaceFn": "function surface(input) { ... }",
  "params": {
    "uMin": 0, "uMax": 1,
    "vMin": 0, "vMax": 1,
    "uSegs": 150, "vSegs": 150
  },
  "surfaceInput": {
    "u": 0, "v": 0,
    "curvature": -2.5,
    "epsilon": 0.25
  },
  "animatedParams": [{
    "name": "epsilon",
    "playing": true,
    "min": 0.05, "max": 0.45,
    "step": 0.01, "time": 5, "phase": 0
  }],
  "camera": {
    "position": {"x": 5, "y": 5, "z": 2},
    "target": {"x": 0, "y": 0, "z": 0}
  },
  "shininess": 150,
  "globalSaturation": 1.5,
  "meta": {
    "inferred_shape": "Hyperbolic (Pseudosphere)",
    "delta_proxy": 0.35
  }
}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `EXACT_DELTA` | Enable exact 4-point delta computation | `false` |

## Integration Example

```python
from app.services.geometry_engine import geometry_engine
from app.services.chit_service import chit_service

# Get embeddings from search index
embeddings = search_index.get_embeddings_for_document("doc_123")

# Analyze the geometric shape
curvature = geometry_engine.analyze_curvature(embeddings)
print(f"Curvature K: {curvature['curvature_k']}")
print(f"Shape: {'Hyperbolic' if curvature['curvature_k'] < -0.5 else 'Spherical' if curvature['curvature_k'] > 0.5 else 'Euclidean'}")

# Get spectral frequencies for ZetaVisualizer
frequencies, amplitudes = geometry_engine.compute_zeta_spectrum(embeddings)
print(f"Zeta frequencies: {frequencies}")

# Generate CHIT config for Pmoves-hyperdimensions
config = geometry_engine.generate_chit_config(curvature)
with open("chit_manifold.json", "w") as f:
    json.dump(config, f)

# Publish to geometry bus
await chit_service.publish_manifold_update(curvature)
```

## Algorithm Details

### Curvature Estimation (Heuristic)

1. Compute centroid of all embedding vectors
2. Compute distances from each point to centroid
3. Calculate shape ratio: `std(distances) / mean(distances)`
4. Map ratio to curvature K:
   - ratio > 0.5: Hyperbolic (K = -1.0 - (ratio - 0.5) * 8.0)
   - ratio < 0.2: Spherical (K = 5.0 - ratio * 20.0)
   - Otherwise: Euclidean (K = 0)

### Exact Delta-Hyperbolicity (4-Point Condition)

For all 4-tuples (w, x, y, z):
1. Compute Gromov products at basepoint w:
   - (x|y)_w = 0.5 * (d(w,x) + d(w,y) - d(x,y))
2. Check condition: (x|z)_w >= min((x|y)_w, (y|z)_w) - delta
3. Return maximum delta that satisfies all tuples

### Zeta Spectrum Derivation

1. Compute covariance matrix of embeddings
2. Extract eigenvalues (principal variance directions)
3. Normalize eigenvalues to [0, 1]
4. Map to frequencies near Riemann Zeta zeros (14.13, 21.02, 25.01, ...)
5. Compute decaying amplitudes based on eigenvalue magnitude

## Cookbook (Progressive Disclosure)

Refer to the following for advanced patterns:
- **Large Dataset Handling:** For > 100 points, exact delta samples automatically
- **Custom Surface Functions:** Modify `_get_surface_fn_code()` for custom geometries
- **Eigenvalue Analysis:** Zeta frequencies reflect embedding dimensionality structure
- **Real-time Updates:** Combine with `publish_manifold_update()` for live visualization
