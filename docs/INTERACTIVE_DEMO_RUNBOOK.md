# PMOVES-DoX Interactive Demo Runbook

> **For Agent Zero and Claude Code Execution**
> Estimated Duration: 20 minutes
> Last Updated: 2026-01-22

This document provides step-by-step executable commands for demonstrating all PMOVES-DoX features. Each step includes commands, expected outputs, and success criteria that AI agents can verify.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Part 1: System Verification](#part-1-system-verification-2-min) (2 min)
3. [Part 2: Document Intelligence](#part-2-document-intelligence-demo-5-min) (5 min)
4. [Part 3: Geometric Intelligence](#part-3-geometric-intelligence-demo-5-min) (5 min)
5. [Part 4: Agent Zero Integration](#part-4-agent-zero-integration-3-min) (3 min)
6. [Part 5: Advanced Features](#part-5-advanced-features-5-min) (5 min)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting the demo, ensure the following:

### Required Services

| Service | Port | Health Check |
|---------|------|--------------|
| Backend API | 8484 | `http://localhost:8484/` |
| Frontend UI | 3001 | `http://localhost:3001/` |
| Agent Zero | 50051 | `http://localhost:50051/` |
| NATS WebSocket | 9223 | WebSocket connection |
| TensorZero | 3000 | `http://localhost:3000/` |

### Sample Files
Ensure sample files exist in `samples/` directory:
- `sample.pdf` - Test PDF document
- `marketing_data.csv` - Sample structured data (optional)

### Environment
- Docker services running in GPU mode
- Agent Zero profile: `pmoves_custom`

---

## Part 1: System Verification (2 min)

### Step 1.1: Backend Health Check

**Command:**
```bash
curl -s http://localhost:8484/ | jq .
```

**Expected Output:**
```json
{
  "message": "PMOVES-DoX API",
  "status": "running"
}
```

**Success Criteria:** `status` equals `"running"`

---

### Step 1.2: List Running Docker Services

**Command:**
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -20
```

**Expected Output:**
Should show 14+ containers including:
- `pmoves-dox-backend`
- `pmoves-dox-frontend`
- `pmoves-agent-zero`
- `pmoves-dox-nats`
- `pmoves-dox-tensorzero`

**Success Criteria:** All containers show `Up` status

---

### Step 1.3: Verify NATS WebSocket

**Command:**
```bash
curl -s --http1.1 -H "Connection: Upgrade" -H "Upgrade: websocket" -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" http://localhost:9223/ -o /dev/null -w "%{http_code}"
```

**Expected Output:**
```
101
```

**Success Criteria:** HTTP status code `101` (Switching Protocols)

---

### Step 1.4: Verify TensorZero LLM Orchestrator

**Command:**
```bash
curl -s http://localhost:3000/health 2>/dev/null || echo "TensorZero health endpoint not available - checking via backend"
```

**Alternative (via backend inference test):**
```bash
curl -s -X POST http://localhost:8484/extract/tags \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test document about machine learning and neural networks.", "max_tags": 3}' | jq .
```

**Success Criteria:** Returns tags array or inference result

---

## Part 2: Document Intelligence Demo (5 min)

### Step 2.0: Rebuild Search Index (if needed)

If this is a fresh start or search returns empty results, rebuild the index:

**Command:**
```bash
curl -s -X POST http://localhost:8484/search/rebuild | jq .
```

**Expected Output:**
```json
{
  "status": "success",
  "indexed": <number>
}
```

**Success Criteria:** Returns indexed count > 0 (or 0 if no documents yet)

---

### Step 2.1: Upload Sample PDF

**Command:**
```bash
curl -s -X POST http://localhost:8484/upload \
  -F "file=@samples/sample.pdf" | jq .
```

**Expected Output:**
```json
{
  "artifact_id": "<UUID>",
  "filename": "sample.pdf",
  "status": "uploaded"
}
```

**Success Criteria:** Returns `artifact_id` UUID

**Save the artifact_id for subsequent steps:**
```bash
export ARTIFACT_ID=$(curl -s -X POST http://localhost:8484/upload -F "file=@samples/sample.pdf" | jq -r '.artifact_id')
echo "Artifact ID: $ARTIFACT_ID"
```

---

### Step 2.2: List Uploaded Documents

**Command:**
```bash
curl -s http://localhost:8484/artifacts | jq '.artifacts[:3]'
```

**Expected Output:**
```json
[
  {
    "id": "<UUID>",
    "filename": "sample.pdf",
    "file_type": "pdf",
    "status": "processed"
  }
]
```

**Success Criteria:** At least one artifact with `status: "processed"`

---

### Step 2.3: Extract Facts from Document

**Command:**
```bash
curl -s "http://localhost:8484/facts?artifact_id=$ARTIFACT_ID" | jq '.facts[:5]'
```

**Expected Output:**
```json
[
  {
    "id": "<UUID>",
    "content": "<extracted fact>",
    "evidence_id": "<UUID>",
    "fact_type": "statement"
  }
]
```

**Success Criteria:** Returns array of extracted facts

---

### Step 2.4: Semantic Search

**Prerequisite:** Rebuild search index if needed:
```bash
curl -s -X POST http://localhost:8484/search/rebuild | jq .
```

**Command:**
```bash
curl -s -X POST http://localhost:8484/search \
  -H "Content-Type: application/json" \
  -d '{"query": "main topic", "k": 5}' | jq '.results[:3]'
```

**Expected Output:**
```json
[
  {
    "text": "<relevant text chunk>",
    "score": 0.85,
    "artifact_id": "<UUID>"
  }
]
```

**Success Criteria:** Returns results with relevance scores > 0.5

---

### Step 2.5: Question & Answer with Citations

**Command:**
```bash
curl -s -X POST http://localhost:8484/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main subject of this document?"}' | jq .
```

**Expected Output:**
```json
{
  "answer": "<generated answer>",
  "citations": [
    {
      "text": "<source text>",
      "page": 1,
      "artifact_id": "<UUID>"
    }
  ]
}
```

**Success Criteria:** Returns answer with at least one citation

---

## Part 3: Geometric Intelligence Demo (5 min)

### Step 3.1: Get CHIT Demo Packet (CGP)

**Command:**
```bash
curl -s http://localhost:8484/cipher/geometry/demo-packet | jq .
```

**Expected Output:**
```json
{
  "spec": "chit.cgp.v0.1",
  "meta": { "source": "demo" },
  "super_nodes": [
    {
      "id": "super_0",
      "x": 0,
      "y": 0,
      "r": 200,
      "label": "Resonant Mode 0",
      "constellations": [
        {
          "id": "const_0_0",
          "anchor": [1, 0, 0],
          "summary": "Logistics Cluster",
          "spectrum": [0.9, 0.2, 0.1, 0.0, 0.0],
          "points": [...]
        }
      ]
    }
  ]
}
```

**Success Criteria:** Returns `super_nodes` array with constellations and points

---

### Step 3.2: Analyze Manifold Curvature

**Command (requires a document with embeddings):**
```bash
# First, get an artifact ID
ARTIFACT_ID=$(curl -s http://localhost:8484/artifacts | jq -r '.artifacts[0].id')

# Then analyze its manifold
curl -s -X POST http://localhost:8484/cipher/geometry/visualize_manifold \
  -H "Content-Type: application/json" \
  -d "{\"document_id\": \"$ARTIFACT_ID\"}" | jq .
```

**Expected Output:**
```json
{
  "curvature_k": <number>,
  "delta_hyperbolicity": <number>,
  "epsilon": <number>,
  "shape": "Hyperbolic|Spherical|Euclidean",
  "points_analyzed": <number>
}
```

**Success Criteria:** Returns curvature metrics with shape classification:
- **K < -0.1**: Hyperbolic (tree-like hierarchies)
- **K > 0.1**: Spherical (compact clusters)
- **-0.1 ≤ K ≤ 0.1**: Euclidean (flat)

**Note:** This endpoint requires a document with embeddings. If you see "No embeddings found", rebuild the search index first:
```bash
curl -s -X POST http://localhost:8484/search/rebuild | jq .
```

---

### Step 3.3: Simulate CHIT Geometry Packet

**Command:**
```bash
curl -s -X POST http://localhost:8484/cipher/geometry/simulate \
  -H "Content-Type: application/json" \
  -d '{"text": "Artificial intelligence and machine learning are transforming how we process documents and extract knowledge from unstructured data."}' | jq .
```

**Expected Output:**
```json
{
  "super_nodes": [...],
  "manifold": {
    "curvature_k": <number>,
    "shape": "<shape>"
  },
  "zeta_spectrum": [...]
}
```

**Success Criteria:** Returns CGP packet with manifold analysis

---

### Step 3.4: Frontend Geometry Visualization

**Browser Action:**
Navigate to: `http://localhost:3001/geometry`

**Verification Steps:**
1. Page loads without errors
2. HyperbolicNavigator (2D) view shows super nodes
3. Toggle to "Manifold (3D)" button
4. 3D surface renders with auto-rotation
5. ZetaVisualizer shows animated ripples

**Success Criteria:** All three visualizers render correctly

---

### Step 3.5: Explain Curvature Metrics

**Curvature Metrics Reference:**

| Metric | Description | Range |
|--------|-------------|-------|
| **curvature_k (K)** | Gaussian curvature | K < 0: Hyperbolic, K > 0: Spherical, K ≈ 0: Flat |
| **delta_hyperbolicity** | 4-point condition measure | Lower = more hyperbolic |
| **epsilon** | Perturbation/noise factor | 0-1, affects surface wobble |
| **shape** | Classification result | "Hyperbolic", "Spherical", "Euclidean" |

**CHIT Protocol Components:**
- **Super Nodes**: Clustered semantic regions
- **Constellations**: Sub-groupings within super nodes
- **Zeta Spectrum**: Riemann zeta zero frequencies for spectral analysis

---

## Part 4: Agent Zero Integration (3 min)

### Step 4.1: Verify Agent Zero Web UI

**Browser Action:**
Navigate to: `http://localhost:50051`

**Verification Steps:**
1. Agent Zero chat interface loads
2. Profile shows `pmoves_custom`
3. Model selector shows TensorZero-backed models

**Success Criteria:** UI loads with correct profile

---

### Step 4.2: Check Agent Zero MCP Endpoint

> **Note:** Replace `${MCP_TOKEN}` with your configured token (default: `pmoves-dox-mcp-token`)

**Command:**
```bash
# Set token (default value shown)
export MCP_TOKEN="${MCP_TOKEN:-pmoves-dox-mcp-token}"
curl -s "http://localhost:50051/mcp/t-${MCP_TOKEN}/sse" -o /dev/null -w "%{http_code}"
```

**Expected Output:**
```text
200
```

**Success Criteria:** MCP SSE endpoint returns 200

---

### Step 4.3: Test Agent Zero Tool Execution

**Via Agent Zero UI:**
Send message: `What tools do you have available?`

**Expected Response:**
Agent should list available tools including:
- Document search
- File operations
- Shell commands
- Browser automation

**Success Criteria:** Agent responds with tool capabilities

---

### Step 4.4: A2UI (Agent-to-UI) Page

**Browser Action:**
Navigate to: `http://localhost:3001/a2ui`

**Verification Steps:**
1. Page loads
2. Shows NATS connection status
3. Real-time payload rendering area visible

**Success Criteria:** A2UI page renders with NATS connection

---

## Part 5: Advanced Features (5 min)

### Step 5.1: CHR Clustering (Constellation Harvest Regularization)

**Command:**
```bash
curl -s -X POST http://localhost:8484/structure/chr \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": "'$ARTIFACT_ID'", "n_clusters": 3}' | jq .
```

**Expected Output:**
```json
{
  "clusters": [
    {
      "id": 0,
      "center": [<embedding>],
      "members": ["<evidence_id>", ...],
      "summary": "<cluster summary>"
    }
  ],
  "pca_2d": [...],
  "silhouette_score": 0.65
}
```

**Success Criteria:** Returns clusters with silhouette score > 0

**Note:** CHR requires sufficient data points. Small documents may fail with "Too many bins for data range" error.

---

### Step 5.2: Tag Extraction with LangExtract

**Command:**
```bash
curl -s -X POST http://localhost:8484/extract/tags \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This quarterly financial report shows revenue growth of 15% driven by cloud services and AI product adoption. Operating margins improved by 200 basis points.",
    "max_tags": 10
  }' | jq .
```

**Expected Output:**
```json
{
  "tags": [
    "financial report",
    "revenue growth",
    "cloud services",
    "AI products",
    "operating margins"
  ],
  "model": "ollama:gemma3",
  "provider": "ollama"
}
```

**Success Criteria:** Returns relevant semantic tags

---

### Step 5.3: Tag Governance (Save & History)

**Save Tags:**
```bash
curl -s -X POST http://localhost:8484/tags \
  -H "Content-Type: application/json" \
  -d '{
    "artifact_id": "'$ARTIFACT_ID'",
    "tags": ["demo", "test-document", "sample"]
  }' | jq .
```

**List Tags:**
```bash
curl -s http://localhost:8484/tags | jq '.tags[:5]'
```

**Success Criteria:** Tags persist and can be retrieved

---

### Step 5.4: POML Export (Copilot Integration)

**Command:**
```bash
curl -s -X POST http://localhost:8484/export/poml \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": "'$ARTIFACT_ID'"}' | jq .
```

**Expected Output:**
```json
{
  "poml": {
    "metadata": {
      "source": "<filename>",
      "exported_at": "<timestamp>"
    },
    "content": [...],
    "facts": [...],
    "tags": [...]
  }
}
```

**Success Criteria:** Returns POML-formatted document

---

### Step 5.5: Generate Datavzrd Dashboard

**Command:**
```bash
curl -s -X POST http://localhost:8484/analysis/datavzrd \
  -H "Content-Type: application/json" \
  -d '{"artifact_id": "'$ARTIFACT_ID'"}' | jq .
```

**Expected Output:**
```json
{
  "dashboard_url": "http://localhost:5173/artifacts/datavzrd/<stem>/",
  "status": "generated"
}
```

**Success Criteria:** Returns dashboard URL

**Browser Action:**
Navigate to the returned `dashboard_url` to view interactive visualizations.

---

### Step 5.6: API Catalog Demo

**List Ingested APIs:**
```bash
curl -s http://localhost:8484/apis | jq '.apis[:5]'
```

**Search APIs:**
```bash
curl -s "http://localhost:8484/apis?path_like=/upload" | jq .
```

**Success Criteria:** Returns API endpoint catalog

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `CONNECTION_CLOSED` on geometry page | NATS WebSocket disconnected | Refresh page; check NATS container |
| CHR returns 500 error | Insufficient data points | Use larger document with more evidence |
| Tag extraction timeout | TensorZero/Ollama slow | Wait for model warm-up; check GPU usage |
| Search returns empty | Index not built | Call `POST /search/rebuild` |
| PDF processing fails | Docling model not loaded | Wait for first-run model downloads |
| "No embeddings found" | Document not indexed | Call `POST /search/rebuild` then retry |
| Manifold analysis fails | No embeddings for document | Ensure document is processed and search index is built |

### Health Check Script

Run all health checks at once:

```bash
#!/bin/bash
echo "=== PMOVES-DoX Health Check ==="

# Backend
echo -n "Backend: "
curl -s http://localhost:8484/ | jq -r '.status // "FAIL"'

# Frontend
echo -n "Frontend: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:3001/ && echo " OK" || echo " FAIL"

# NATS
echo -n "NATS: "
curl -s --http1.1 -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
  http://localhost:9223/ -o /dev/null -w "%{http_code}\n"

# Agent Zero
echo -n "Agent Zero: "
curl -s -o /dev/null -w "%{http_code}" http://localhost:50051/ && echo " OK" || echo " FAIL"

# Docker containers
echo "=== Running Containers ==="
docker ps --format "{{.Names}}: {{.Status}}" | grep pmoves
```

---

## Quick Reference Card

### Key Endpoints

| Action | Method | Endpoint |
|--------|--------|----------|
| Health check | GET | `/` |
| Upload file | POST | `/upload` |
| List documents | GET | `/artifacts` |
| List facts | GET | `/facts` |
| Semantic search | POST | `/search` |
| Q&A query | POST | `/ask` |
| CGP demo packet | GET | `/cipher/geometry/demo-packet` |
| Manifold analysis | POST | `/cipher/geometry/visualize_manifold` |
| CHR clustering | POST | `/structure/chr` |
| Tag extraction | POST | `/extract/tags` |
| POML export | POST | `/export/poml` |

### Frontend Pages

| Page | URL | Purpose |
|------|-----|---------|
| Main Dashboard | `/` | Document upload and management |
| Geometry | `/geometry` | 2D/3D geometric visualizations |
| A2UI | `/a2ui` | Agent-to-UI NATS payload viewer |
| APIs | `/apis` | API catalog browser |
| Tags | `/tags` | Tag governance |

### Agent Zero Commands

| Command | Description |
|---------|-------------|
| `search <query>` | Semantic search across documents |
| `ask <question>` | Q&A with citations |
| `analyze <artifact_id>` | Run full document analysis |
| `export <artifact_id>` | Export to POML format |

---

## Demo Complete

**Total Duration:** ~20 minutes

**Features Demonstrated:**
- Document upload and processing (PDF)
- Fact extraction and evidence linking
- Semantic search with vector embeddings
- Q&A with citations
- Geometric intelligence (CHIT Protocol, CGP)
- Manifold curvature detection
- 2D hyperbolic and 3D manifold visualization
- Agent Zero MCP integration
- CHR clustering
- Tag extraction and governance
- POML export
- Datavzrd dashboards

**Next Steps:**
- Try uploading your own documents
- Experiment with different curvature parameters
- Build custom Agent Zero workflows
- Explore the API reference at `/docs`
