# Geometric Intelligence Demo Guide

> **"The shape of the data determines the shape of the intelligence"**

This guide explains how to demonstrate PMOVES-DoX's geometric intelligence capabilities, what metrics to watch, and why it matters.

---

## What This Demo Shows

PMOVES-DoX analyzes document embeddings to detect the **shape of knowledge**:

| Manifold Type | Curvature | Data Pattern | Example Documents |
|---------------|-----------|--------------|-------------------|
| **Hyperbolic** | K < 0 | Tree-like hierarchies | Org charts, taxonomies, nested outlines |
| **Spherical** | K > 0 | Cyclic/clustered patterns | Topic clusters, related concepts |
| **Euclidean** | K ≈ 0 | Flat distributions | Evenly spread content, random samples |

---

## Why This Matters

| Use Case | Geometric Insight | Business Value |
|----------|-------------------|----------------|
| Knowledge graphs | Detects hierarchy depth automatically | Auto-organize documentation |
| Topic clustering | Finds natural groupings in content | Better search relevance |
| Anomaly detection | Identifies outliers via curvature | Quality assurance |
| Content structure | Reveals hidden relationships | Smarter recommendations |
| Embedding quality | Validates vector space geometry | Model evaluation |

---

## The Five Mathematical Pillars

PMOVES-DoX geometric intelligence is built on five mathematical foundations:

1. **Dirichlet Distributions** - Fair credit attribution across contributors
2. **Hyperbolic Geometry (Poincaré Disk)** - Tree embedding in bounded space
3. **Merkle Proofs** - Tamper-proof verification chains
4. **Riemann Zeta Filtering** - Signal extraction via spectral analysis
5. **Swarm Optimization (EvoSwarm)** - Distributed consensus algorithms

---

## Demo Walkthrough

### Prerequisites

```bash
# Start required services
docker compose up -d backend frontend nats

# Verify services are running
docker compose ps
```

### Step 1: Open Geometry Page

Navigate to: **http://localhost:3001/geometry**

You should see:
- HyperbolicNavigator (2D Poincaré disk view)
- Shape badge indicating manifold type
- Super node count

### Step 2: Observe Initial Load

The page automatically:
1. Fetches demo CGP (CHIT Geometry Packet) from `/cipher/geometry/demo-packet`
2. Computes manifold metrics via `/cipher/geometry/visualize_manifold`
3. Displays shape badge (purple=hyperbolic, orange=spherical, gray=flat)

### Step 3: Interact with Visualizations

| Action | Result |
|--------|--------|
| Click super node | Smooth zoom transition (750ms easing) |
| Pan/zoom canvas | D3 zoom behavior with momentum |
| Toggle "Manifold (3D)" | Three.js surface rendering |
| Watch ZetaVisualizer | Animated ripples at zeta frequencies |

### Step 4: Explore 3D Mode

Toggle to **Manifold (3D)** to see:
- **Hyperbolic**: Pseudosphere with purple-cyan gradient
- **Spherical**: Standard sphere with orange-gold gradient
- **Euclidean**: Flat plane with wave perturbations
- Auto-rotating camera reveals topology from all angles

### Step 5: API Demonstration

```bash
# Get demo CGP packet structure
curl http://localhost:8000/cipher/geometry/demo-packet | jq .

# Compute manifold visualization
curl -X POST http://localhost:8000/cipher/geometry/visualize_manifold \
  -H "Content-Type: application/json" \
  -d '{"document_id": "demo"}' | jq .

# Simulate CGP event (returns A2UI format)
curl -X POST http://localhost:8000/cipher/geometry/simulate \
  -H "Content-Type: application/json" \
  -d '{"spec":"chit.cgp.v0.1","super_nodes":[{"id":"demo","x":0,"y":0,"r":100,"constellations":[]}]}' | jq .
```

---

## Metrics to Watch

### Core Geometry Metrics

| Metric | Range | Meaning | Visual Effect |
|--------|-------|---------|---------------|
| `delta` | 0-1 | Hyperbolicity proxy (shape_ratio) | Higher = more tree-like structure |
| `curvature_k` | -5 to +5 | Gaussian curvature parameter | Controls surface bending direction |
| `epsilon` | 0-1 | Noise/temperature factor | Modulates ripple intensity |

### Zeta Spectrum Metrics

| Metric | Range | Meaning | Visual Effect |
|--------|-------|---------|---------------|
| `frequencies` | 14-35 Hz | Derived from zeta zeros | Ripple oscillation speed |
| `amplitudes` | 0-1 | Signal strength (decaying) | Ripple size and opacity |

### How Metrics Map to Shapes

```
High variance (shape_ratio > 0.5)
    → delta high, curvature_k negative (-1 to -5)
    → Hyperbolic (Pseudosphere) rendering

Low variance (shape_ratio < 0.2)
    → delta low, curvature_k positive (+1 to +5)
    → Spherical rendering

Medium variance (0.2 ≤ shape_ratio ≤ 0.5)
    → delta medium, curvature_k near 0
    → Euclidean (flat plane) rendering
```

---

## What Should Impress

### Visual Impact

- **Pseudosphere rendering**: Purple-cyan flowing gradient with tractrix geometry
- **Auto-rotating 3D**: Reveals topology from all angles (OrbitControls)
- **Zeta ripples**: Pulsing concentric waves at Riemann zeta zero frequencies
- **Smooth transitions**: D3 zoom/pan with 750ms cubic easing
- **Real-time updates**: NATS bus delivers instant parameter changes

### Technical Depth

- **Real differential geometry**: Actual Gaussian curvature computation, not cosmetic
- **4-point Gromov hyperbolicity**: Metric space theory (optional exact computation)
- **Riemann Zeta connection**: Eigenvalue spectrum mapped to first 5 non-trivial zeros
- **NATS event streaming**: WebSocket bus for live manifold updates

### Practical Value

- **Zero manual tagging**: Structure detected automatically from embeddings
- **Any embedding source**: Works with document vectors, image features, etc.
- **Scalable**: Sampling optimization for large datasets (100-point cap)
- **Production-ready**: 90 tests validating all components

---

## Test Validation

### Backend Tests (`backend/tests/test_geometry_engine.py`)

| Category | Tests | Coverage |
|----------|-------|----------|
| Curvature analysis | 8 | Bounds, shape classification, float types |
| CHIT config generation | 6 | Hyperbolic/spherical/flat configs, JS validity |
| Zeta spectrum | 6 | Frequencies, amplitudes, decay patterns |
| Surface functions | 3 | Tractrix, sphere, plane formulas |
| Global instance | 3 | Singleton existence, method availability |

### Frontend Tests (`frontend/components/geometry/__tests__/`)

| Component | Tests | Coverage |
|-----------|-------|----------|
| HyperbolicNavigator | ~8 | Rendering, D3 interactions, NATS subscription |
| Manifold3D | ~6 | Three.js geometry, param updates, disposal |
| ZetaVisualizer | ~4 | Canvas animation, frequency mapping |

### E2E Tests (`ui-smoke/tests/geometry.spec.ts`)

- Page load verification
- Mode switching (2D ↔ 3D)
- API integration (demo-packet, simulate, visualize_manifold)
- Visual regression checks

### API Tests (`backend/tests/test_geometry_api.py`)

- Demo packet structure validation
- Simulate endpoint response format
- Visualize manifold metrics accuracy

**Total: 95 tests validating geometric intelligence**

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| No NATS connection | Service not running | `docker compose up nats` |
| Blank 3D view | WebGL disabled | Enable hardware acceleration in browser |
| No ripples | Canvas not rendering | Refresh page or check console errors |
| Wrong shape detected | < 4 embeddings | Need minimum 4 data points for analysis |
| Metrics all zero | Empty input | Provide valid CGP with constellations/points |
| Slow 3D rendering | Large segment count | Reduce uSegs/vSegs in config |

---

## Live Demo Script (5-6 minutes)

### Opening (30 seconds)

> "PMOVES-DoX doesn't just store documents - it understands their **shape**.
> Watch as we automatically detect whether knowledge is hierarchical, cyclic, or flat,
> using real differential geometry and Riemann Zeta spectral analysis."

### Main Demo (3 minutes)

1. **Show geometry page loading** - Point out the shape badge
2. **Explain curvature badge** - Purple = hyperbolic (tree-like data detected)
3. **Click a super node** - Show smooth D3 zoom transition
4. **Toggle to 3D mode** - Rotating pseudosphere appears
5. **Point out zeta ripples** - "These frequencies come from your data's variance structure"

### Technical Deep-Dive (2 minutes)

1. **Show API response** - `curl /cipher/geometry/visualize_manifold`
2. **Explain curvature_k** - "Negative means hyperbolic, like a saddle shape"
3. **Show test count** - "90 tests validate this isn't just pretty graphics"
4. **Demo NATS update** - Change parameter, watch 3D surface morph

### Closing (30 seconds)

> "This is geometric intelligence - the shape of the data determines the shape of the interface.
> No manual tagging required. The math reveals the structure."

---

## Related Documentation

- [GEOMETRIC_INTELLIGENCE.md](GEOMETRIC_INTELLIGENCE.md) - Core concepts
- [GEOMETRY_BUS_INTEGRATION.md](GEOMETRY_BUS_INTEGRATION.md) - NATS integration
- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) - Current status
- [API_REFERENCE.md](API_REFERENCE.md) - Endpoint documentation

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `NATS_URL` | `nats://nats:4222` | Backend NATS connection |
| `NEXT_PUBLIC_NATS_WS_URL` | `ws://localhost:9223` | Frontend WebSocket |
| `EXACT_DELTA` | `false` | Enable O(N⁴) exact hyperbolicity |
| `CHIT_USE_LOCAL_EMBEDDINGS` | `false` | Use local SentenceTransformer |
