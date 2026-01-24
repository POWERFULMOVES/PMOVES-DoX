# Agent Skill: CHIT Geometry Bus

**Version:** 1.0.0
**Model:** Any (Tool-based execution)
**Thread Type:** Base Thread (B) - Infrastructure service

## Description

This skill enables agents to interact with the CHIT (Cymatic-Holographic Information Transfer) Geometry Bus. It provides tools for publishing and subscribing to CHIT Geometry Packets (CGP), generating embeddings, and managing NATS-based real-time geometry event streams.

**When to use:**
- Publishing document geometry to the visualization layer
- Subscribing to real-time geometry updates from other services
- Creating CGP structures from document analysis results
- Generating text embeddings for semantic operations
- Broadcasting manifold parameter updates for 3D visualization

**Why it exists:**
The CHIT service acts as the nervous system for geometric intelligence, bridging document analysis with hyperbolic/spherical/Euclidean manifold visualizations. It enables the "Mathematical UI" paradigm where data shapes are computed and rendered in real-time.

## Core Principles

1. **Graceful Degradation:** In docked mode (PMOVES.AI integration), NATS failures do not crash the service. Always check `is_nats_available` before publishing.
2. **Lazy Loading:** Embedding models are loaded on first use, not at startup. This minimizes cold-start latency.
3. **Mode Awareness:** The service auto-detects standalone vs. docked mode via `DOCKED_MODE` or `NATS_URL` environment variables.
4. **Geometry-First:** All document content flows through the CGP structure before visualization.

## Capabilities

- **NATS Connection:** Connect to NATS JetStream for reliable message delivery
- **CGP Publishing:** Publish CHIT Geometry Packets to the geometry bus
- **CGP Decoding:** Unpack CGP structures into usable text fragments
- **Manifold Updates:** Broadcast curvature/epsilon parameters for 3D rendering
- **Embedding Generation:** Generate vector embeddings using SentenceTransformers
- **CGP Construction:** Build CGP from document sections and curvature analysis

## Tools

The following methods are available on the `chit_service` singleton:

| Method | Description | Usage |
|--------|-------------|-------|
| `connect_nats(nats_url)` | Connect to NATS JetStream | `await chit_service.connect_nats("nats://nats:4222")` |
| `publish_cgp(cgp, subject)` | Publish a CGP to the geometry bus | `await chit_service.publish_cgp(cgp_dict, "tokenism.cgp.ready.v1")` |
| `decode_cgp(cgp)` | Unpack CGP into text fragments | `result = chit_service.decode_cgp(cgp_dict)` |
| `subscribe_geometry_events(handler)` | Subscribe to geometry events | `await chit_service.subscribe_geometry_events(my_async_handler)` |
| `publish_manifold_update(params)` | Broadcast manifold parameters | `await chit_service.publish_manifold_update({"curvature_k": -2.5})` |
| `generate_embeddings(texts)` | Generate embeddings for text list | `embeddings = chit_service.generate_embeddings(["text1", "text2"])` |
| `create_cgp_from_document(doc_id, sections, curvature)` | Build CGP from document | `cgp = chit_service.create_cgp_from_document("uuid", sections, curvature_result)` |

## Context Priming

Before using the CHIT service:
1. Check `chit_service.is_nats_available` to verify NATS connection status
2. Check `chit_service.has_local_embeddings` if you need embedding generation
3. Review the CGP spec version in generated packets: `"spec": "chit.cgp.v0.1"`
4. Understand the NATS subjects:
   - `tokenism.cgp.ready.v1` - Published CGP packets
   - `geometry.event.manifold_update` - Manifold parameter broadcasts

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NATS_URL` | NATS server URL | `nats://nats:4222` |
| `DOCKED_MODE` | Explicit docked mode flag | `false` |
| `CHIT_USE_LOCAL_EMBEDDINGS` | Enable local SentenceTransformer | `false` |
| `CHIT_EMBEDDING_MODEL` | Model for local embeddings | `all-MiniLM-L6-v2` |

## CGP Structure Reference

```json
{
  "spec": "chit.cgp.v0.1",
  "meta": {
    "source": "pmoves-dox.document.<uuid>",
    "curvature_k": -2.5,
    "delta": 0.3,
    "epsilon": 0.1
  },
  "super_nodes": [{
    "id": "doc_<short_uuid>",
    "label": "Document <short_uuid>",
    "x": 0, "y": 0, "r": 200,
    "constellations": [{
      "id": "const_0",
      "anchor": [1, 0, 0],
      "summary": "Section Title",
      "spectrum": [0.5, 0.5, 0.5, 0.5, 0.5],
      "radial_minmax": [0, 1],
      "points": [{
        "id": "p_0_0",
        "x": -60, "y": -60,
        "proj": 0.5,
        "conf": 0.8,
        "text": "Chunk text..."
      }]
    }]
  }]
}
```

## Integration Example

```python
from app.services.chit_service import chit_service
from app.services.geometry_engine import geometry_engine

# Analyze document embeddings
curvature = geometry_engine.analyze_curvature(embeddings)

# Create CGP from document structure
cgp = chit_service.create_cgp_from_document(
    document_id="abc123",
    sections=sections_list,
    curvature_result=curvature
)

# Publish to geometry bus
if chit_service.is_nats_available:
    await chit_service.publish_cgp(cgp)
    await chit_service.publish_manifold_update(curvature)
```

## Cookbook (Progressive Disclosure)

Refer to the following for advanced patterns:
- **NATS Stream Setup:** The service auto-creates the `GEOMETRY` stream on first connection
- **Durable Consumers:** Subscribe uses `dox-geometry-consumer` for reliable delivery
- **NumPy Serialization:** The service handles numpy type conversion automatically for JSON
