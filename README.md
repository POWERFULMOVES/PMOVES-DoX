# PMOVES-DoX

The ultimate document structured data extraction and analysis tool. Extract, analyze, transform, and visualize data from PDFs, XML logs, CSV/XLSX, and OpenAPI/Postman collections. Local‑first with Hugging Face + Ollama; ships as standalone, Docker, and MS Teams Copilot/MCP‑friendly.

## Quick Start

Option A - Docker (CPU, default)

```bash
cd PMOVES-DoX
cp .env.example .env  # first time only
docker compose -f docker-compose.cpu.yml up --build -d
```

Option B — GPU + Tools (internal Ollama, no host port conflicts)

```bash
cd PMOVES-DoX
cp .env.example .env  # first time only
# Start full stack with GPU backend + internal Ollama + tools (datavzrd/schemavzrd)
docker compose --compatibility --profile ollama --profile tools up --build -d
```

Notes
- Internal Ollama is reachable on the compose network at `http://ollama:11434` and does not bind a host port.
- Backend already points to `OLLAMA_BASE_URL=http://ollama:11434` by default (.env).
- To use a global host Ollama instead, copy `docker-compose.override.yml.example` to `docker-compose.override.yml` and start without the `ollama` profile.

Option C — Local dev

1) Backend
```bash
cd PMOVES-DoX/backend
python -m venv venv && . venv/bin/activate  # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

2) Frontend
```bash
cd PMOVES-DoX/frontend
npm i
npm run dev
```

Then:
- Visit http://localhost:3000
- Settings → confirm API Base = http://localhost:8000
- Upload sample CSV/PDF or click “Load Samples”
- Try Global Search; explore Logs/APIs/Tags
- Tags → Load LMS Preset → Preview/Extract → Export POML (pick variant)

### Optional: Supabase Backend

1. **Start Supabase locally**
   ```bash
   supabase start
   ```
   - The Supabase CLI (install via `npm i -g supabase` or the Windows installer) spins up Postgres, PostgREST, and storage using Docker.
   - CLI output (or `.supabase/.env`) contains `API_URL`, `SERVICE_ROLE_KEY`, and `ANON_KEY` that the backend/backfill script will read automatically.
   - If you prefer a custom setup, fall back to `docker compose -f docker-compose.supabase.yml up -d`.
2. Seed Supabase from your existing SQLite data:
   ```bash
   python tools/backfill_supabase.py --from-sqlite backend/db.sqlite3 --reset
   ```
3. Point the backend at Supabase (choose one):
   - **Supabase CLI** (recommended)
     ```bash
     export DB_BACKEND=supabase
     set -a && source .supabase/.env && set +a   # bash/zsh
     ```
     PowerShell:
     ```powershell
     foreach ($line in Get-Content .supabase/.env) {
       if (-not $line.Contains('=')) { continue }
       $name,$value = $line -split '=',2
       Set-Item Env:$name $value
     }
     ```
   - **Manual compose fallback**
     ```bash
     export DB_BACKEND=supabase
     export SUPABASE_URL=http://127.0.0.1:55425
     export SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjAsImV4cCI6MjUzNDAyMzAwNzk5fQ.HPvdDMnzeFHOYHVnKEwec71btVPz2lZ5xgiSSAQgGOU
     export SUPABASE_ANON_KEY=anon
     ```
4. Optional: keep SQLite + Supabase in sync during migration with `SUPABASE_DUAL_WRITE=true`.
5. When finished, stop the local stack:
   ```bash
   supabase stop
   ```

> The Supabase schema lives under `backend/migrations/supabase/001_init.sql`. Apply it (or run `supabase db push`) before switching a hosted environment.

### GPU Controls

- `SEARCH_DEVICE` – preferred device for SentenceTransformers (auto-detects CUDA when present).
- `DOCLING_DEVICE` / `DOCLING_NUM_THREADS` – Docling accelerator preference and CPU thread cap.
- Hardware preference order follows Windows → WSL → Linux (Docker). Set the env vars in your `.env`/compose overrides to pin behaviour across hardware (RTX 50-series, Jetson Orin, mobile edge).

Local-first models
- Ollama (optional): docker compose up ollama (GPU compose) and toggle “Use Ollama” in Tags.
- Offline HF: set TRANSFORMERS_OFFLINE/HF_HUB_OFFLINE to prefer cached models.

## Features

- Multi‑format ingestion: PDF (Docling), CSV/XLSX, XML logs, OpenAPI/Postman
- Vector search (FAISS or NumPy fallback) with a global UI search bar
- PDF page awareness: Global Search displays page numbers for PDF hits; optional "Open PDF at page" links when enabled
- Logs view with time/level/code filters and CSV export
- APIs catalog with detail modal (params/responses) and copy-cURL
- Tag extraction via LangExtract with LMS presets, dry‑run, and governance (save/history/restore)
- CHR structuring + datavzrd dashboards (overview + details)
- Q&A with citations over extracted facts

OpenAPI/XML enrichments
- OpenAPI: path-level parameters are merged into each operation; effective security is normalized and surfaced under `responses.x_security.schemes`.
- XML logs: optional XPath mapping lets you map arbitrary XML shapes to {ts, level, code, component, message}. Configure via `XML_XPATH_MAP` or `XML_XPATH_MAP_FILE`.
   - Sample mapping: `docs/samples/xpath_lms.yaml`
   - Example (PowerShell):
     - `$env:XML_XPATH_MAP_FILE = "${PWD}\docs\samples\xpath_lms.yaml"`
     - `docker compose -f docker-compose.cpu.yml up --build`

## Technology Stack

### Backend
- FastAPI
- Docling (IBM Granite model for PDF processing)
- Pandas for data analysis
- FAISS (CPU) or NumPy fallback for vector search
- Python 3.10+

### Frontend
- Next.js 14 + TypeScript + Tailwind
- Sticky header with product name, global search, and index rebuild button
- Settings modal (API base, default author, VLM badge)
- POML export for Microsoft Copilot Studio / POML workflows
- Faceted views (workspace/logs/apis/tags/artifacts) with toasts for UX

## Setup Instructions (Windows/PowerShell)

### Backend Setup

```powershell
# Navigate to backend directory
cd PMOVES-DoX/backend

# Copy env template (optional)
copy .env.example .env

# (Optional) Add Hugging Face token for model downloads
# In .env, set HUGGINGFACE_HUB_TOKEN=your_token (or HF_API_KEY)
# Optionally enable VLM picture descriptions:
# DOCLING_VLM_REPO=ibm-granite/granite-docling-258m-demo

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the backend (PORT via .env if set)
python -m app.main
```

Backend will run on `http://localhost:8000`

### Frontend Setup

```powershell
# Navigate to frontend directory
cd PMOVES-DoX/frontend

# Copy env template (optional)
copy .env.local.example .env.local

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend will run on `http://localhost:3000`

## Docker Compose (GPU default)

Prereqs: Docker Desktop installed and running.

```powershell
cd PMOVES-DoX
# Optional (recommended on Docker Desktop):
docker compose --compatibility up --build
```

- Backend (GPU): http://localhost:8000 (CORS allows http://localhost:3000 by default)
- Frontend: http://localhost:3000 (talks to backend at http://localhost:8000)
- datavzrd dashboard (if a viz has been generated): http://localhost:5173
 - schemavzrd schema docs (if DB_URL is set): http://localhost:5174

Data folders `backend/uploads` and `backend/artifacts` are volume-mounted.
There is also a watch folder: `PMOVES-DoX/watch` mounted to `/app/watch` in the backend.

PDF OCR support in container: the backend image installs `poppler-utils`, `tesseract-ocr`, and `tesseract-ocr-eng` to support Docling’s PDF parsing and OCR.

Hugging Face auth in Compose:
- Set an environment variable on your host named `HF_API_KEY` or `HUGGINGFACE_HUB_TOKEN` before running compose, e.g. in PowerShell:
  - `$env:HF_API_KEY = 'hf_xxx_your_token'`
  - `docker compose up --build`
- To enable Granite Docling picture descriptions, set on host:
  - `$env:DOCLING_VLM_REPO = 'ibm-granite/granite-docling-258M'` (or `'ibm-granite/granite-docling-258m-demo'`)

Notes on model downloads:
- The first run will download model weights into a cached volume (`hf-cache`). This can take a few minutes depending on bandwidth.
- Backend image includes CPU-only PyTorch; no GPU is required for the 258M model.

### CPU-only mode
If you don’t want to use the GPU image, run the CPU override:

```powershell
docker compose -f docker-compose.cpu.yml up --build
```

### GPU acceleration (NVIDIA)
If you have an NVIDIA GPU and the NVIDIA Container Toolkit installed, you can run the default CUDA-enabled backend image for faster PDF + VLM processing.

1) Set environment variables (PowerShell example):

```
$env:HF_API_KEY = 'hf_xxx_your_token'
$env:DOCLING_VLM_REPO = 'ibm-granite/granite-docling-258M'
```

2) Start (GPU is default in docker-compose.yml):

```
cd PMOVES-DoX
docker compose --compatibility --profile ollama --profile tools up --build -d
```

This uses `backend/Dockerfile.gpu` based on `pytorch/pytorch:2.3.1-cuda12.1-cudnn8-runtime` and requests a GPU from Docker Desktop.

Troubleshooting:
- Make sure the NVIDIA drivers and Container Toolkit are installed. Run `nvidia-smi` on the host, and `docker run --gpus all nvidia/cuda:12.1.1-runtime-ubuntu22.04 nvidia-smi` to confirm GPU is available in containers.
- If the container cannot access the GPU, ensure Docker Desktop settings have GPU support enabled and the NVIDIA toolkit is installed.

### Jetson (JetPack / L4T)

Jetson Nano (JetPack 4.x, L4T r32.7.1)

```bash
# On the Jetson device (ARM64)
cd PMOVES-DoX
cp .env.example .env

# Start backend + frontend (CPU/GPU via L4T runtime)
docker compose -f docker-compose.jetson.yml up -d --build

# Optionally include internal Ollama and tools (resource-heavy on Nano)
docker compose -f docker-compose.jetson.yml --profile ollama --profile tools up -d --build
```

Notes
- Backend base: `nvcr.io/nvidia/l4t-ml:r32.7.1-py3` (includes CUDA/cuDNN, JetPack 4.x).
- The backend image does not pin `torch`; it uses the version provided by the base image.
- Ollama on Jetson is ARM64 but large models may exceed Nano’s 4GB; prefer small models.
- Ensure the NVIDIA Container Runtime is active; if `runtime: nvidia` fails, install the NVIDIA Container Toolkit for L4T.

Jetson Orin Nano (latest JetPack 5/6, L4T r35/r36)

Use the Orin-specific compose + Dockerfile that default to an L4T ML base for r36.3.0. You can override the exact base tag via a build arg.

```bash
# On the Orin Nano (ARM64)
cd PMOVES-DoX
cp .env.example .env

# Start backend + frontend with Orin/L4T base (defaults to r36.3.0)
docker compose -f docker-compose.jetson-orin.yml up -d --build

# If your JetPack uses a different L4T ML tag, override BASE_IMAGE:
docker compose -f docker-compose.jetson-orin.yml build \
  --build-arg BASE_IMAGE=nvcr.io/nvidia/l4t-ml:r35.4.1-py3 backend
docker compose -f docker-compose.jetson-orin.yml up -d

# Optional: internal Ollama and tools (ensure you have enough RAM/VRAM)
docker compose -f docker-compose.jetson-orin.yml --profile ollama --profile tools up -d --build
```

Notes
- Backend base defaults to `nvcr.io/nvidia/l4t-ml:r36.3.0-py3` (JetPack 6 / L4T r36). Adjust to your installed JetPack.
- PyTorch/CUDA come from the base image; we do not install torch in the Dockerfile.
- On Orin Nano, use small/quantized models for Ollama to fit memory.

## Usage

1. **Upload Documents**: Drag and drop or select PDF, CSV, or XLSX files
2. **Automatic Processing**: Files are automatically analyzed and facts extracted
3. **Ask Questions**: Type questions like "what is the total ROAS?" or "show me revenue"
4. **View Citations**: See exactly where each fact came from with page numbers and coordinates

### Sample files
- CSV: `PMOVES-DoX/samples/sample.csv`
- PDF: `PMOVES-DoX/samples/sample.pdf` (downloaded by `setup.ps1`; or use any PDF you have)

### Watch Folder

Drop `.pdf`, `.csv`, `.xlsx`, or `.xls` files into `PMOVES-DoX/watch` and the backend will auto-ingest them. Behavior is controlled by env vars (see `backend/.env.example`):

- `WATCH_ENABLED` (default `true`)
- `WATCH_DIR` (default `/app/watch` in the container)
- `WATCH_DEBOUNCE_MS` (default `1000`) — wait for file size to stabilize
- `WATCH_MIN_BYTES` (default `1`) — minimum size to consider a file ready

Watcher status: `GET /watch`

## API Endpoints

- `POST /upload` - Upload and process documents
- `GET /facts` - Retrieve all extracted facts
- `GET /evidence/{id}` - Get specific evidence by ID
- `POST /ask` - Ask a question and get answer with citations (accepts `use_hrm=true`)
- `DELETE /reset` - Clear all data
- `POST /extract/langextract` - Run Google LangExtract over an artifact or raw text (returns structured entities + HTML visualization path)
- `POST /extract/tags` - Extract application tags (accepts JSON body `use_hrm: true` for iterative refine/dedupe; response may include `{ hrm: { enabled, steps } }`)
- `POST /convert` - Convert processed artifact to txt or docx
- `GET /download?rel=...` - Download artifacts (whitelisted under `artifacts/`)
- `POST /structure/chr` - Run Constellation Harvest Regularization over an artifact (PDF/CSV/XLSX)
  - Body: `{ artifact_id, K?, iters?, bins?, beta?, seed?, units_mode? ('paragraphs'|'sentences'), include_tables? }`
  - Returns: `mhep`, `Hg`, `Hs`, `preview_rows`, and artifact paths (CSV/JSON/plot)
- `POST /viz/datavzrd` - Materialize a datavzrd project for the artifact’s CHR CSV
- `POST /viz/datavzrd/logs` - Materialize a datavzrd logs dashboard (all logs or per document)
- `GET /artifacts` - List uploaded artifacts (ids, filenames)
- `GET /documents` - List ingested documents (pdf/xml/openapi/postman)
- `GET /tasks` and `GET /tasks/{id}` - Background task summaries + status
- `GET /config` - Runtime config (VLM repo, HF auth, GPU availability)
- `GET /health` - Uptime status

## Local LLMs (Ollama)

This compose spins up an Ollama service by default (port 11434) to support local models for LangExtract.

Use local Gemma 3 (LLM) and Gemma Embedding:

```powershell
docker exec -it ollama bash -lc "ollama pull gemma3 && ollama pull gemma-embedding"
```

Configure backend to use Ollama:

- In `backend/.env`:
  - `LANGEXTRACT_PROVIDER=ollama`
  - `LANGEXTRACT_MODEL=ollama:gemma3`
  - `OLLAMA_BASE_URL=http://ollama:11434`

Now `POST /extract/langextract` will run extraction against the local Gemma 3 model.

Notes:
- You can also pull Qwen models via Ollama if available (e.g., `ollama pull qwen2.5`).
- For HF-only local runners (vLLM/TGI), we can add another service on request; Ollama covers most local use-cases with minimal setup.

## Project Structure

```
PMOVES-DoX/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI application
│   │   ├── database.py          # In-memory database
│   │   ├── qa_engine.py         # Question answering logic
│   │   └── ingestion/
│   │       ├── pdf_processor.py  # PDF processing with Docling
│   │       ├── csv_processor.py  # CSV processing
│   │       └── xlsx_processor.py # Excel processing
│   ├── uploads/                  # Uploaded files
│   ├── artifacts/                # Processed outputs (MD, JSON)
│   └── requirements.txt
└── frontend/
    ├── app/
    │   └── page.tsx             # Main page
    ├── components/
    │   ├── FileUpload.tsx       # File upload component
    │   ├── QAInterface.tsx      # Q&A interface
    │   └── FactsViewer.tsx      # Facts display
    └── package.json
```

## Next Steps

See `ADVANCED_FEATURES_PLAN.md` for roadmap of advanced PDF processing features.

## Smoke Tests

One-command smoke via npm (uses Python + Docker Compose under the hood):

```bash
cd PMOVES-DoX
npm run smoke         # CPU compose (default)
npm run smoke:gpu     # GPU compose (internal Ollama)
```

UI smoke with Playwright (brings up frontend + backend, runs headless tests):

```bash
cd PMOVES-DoX
npm run smoke:ui       # CPU compose
npm run smoke:ui:gpu   # GPU compose
```

Run the Python smoke directly against a running backend:

```bash
cd PMOVES-DoX
API_BASE=http://localhost:8000 python smoke/smoke_backend.py
```

## MCP Usage (starter)

An MCP manifest is provided for PMOVES-DoX tools (search, extract_tags, export_poml):

- Path: `backend/mcp/manifest.json`
- Tools:
  - `search` → POST `/search` with `{ q, k? }`
  - `extract_tags` → POST `/extract/tags` with `{ document_id, model_id?, prompt?, examples?, dry_run? }`
  - `export_poml` → POST `/export/poml` with `{ document_id, title?, variant? }`

Example client (pseudo):

```ts
import fetch from 'node-fetch';

const API = process.env.API_BASE || 'http://localhost:8000';

async function mcpSearch(q: string) {
  const r = await fetch(`${API}/search`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ q, k: 5 })});
  return await r.json();
}

async function mcpExportPOML(document_id: string, variant = 'generic') {
  const r = await fetch(`${API}/export/poml`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ document_id, variant })});
  const data = await r.json();
  // download
  const d = await fetch(`${API}/download?rel=${encodeURIComponent(data.rel)}`);
  const text = await d.text();
  return text;
}
```

## Experiments (HRM)

- Understanding HRM: see `docs/Understanding the HRM Model_ A Simple Guide.md` for an overview of the L‑Module refinement loop and Q‑Head halting.
- Colab/Script prototype: `docs/hrm_transformer_sidecar_colab.py` implements a sidecar HRM around a tiny transformer on a toy sorting task.
  - Run locally: `python docs/hrm_transformer_sidecar_colab.py` (requires PyTorch; GPU optional).
  - Outputs exact‑match accuracy and average refinement steps; demonstrates early halting.
  - This is a prototype; backend/UI integration is planned in NEXT_STEPS under “HRM/Reasoning Enhancements”.

Backend integration (experimental)
- Enable in backend: set `HRM_ENABLED=true` in `backend/.env` (defaults: `HRM_MMAX=6`, `HRM_MMIN=2`).
- Endpoints:
  - `POST /experiments/hrm/echo` with `{ "text": "  a   b  c  " }` → returns normalized `out`, `steps`, `variants`.
  - `POST /experiments/hrm/sort_digits` with `{ "seq": "93241" }` → returns `trace` of refinement and `steps`.
  - `GET /metrics/hrm` → totals and rolling averages.
- UI toggles:
  - Settings → “Use HRM Sidecar (experimental)”: when on, the Q&A panel calls `/ask?use_hrm=true`, and the Tags panel passes `use_hrm: true` to `/extract/tags` for a simple iterative refine/dedupe pass with early halting.

Examples
- Extract tags with HRM (body flag) and preview response:

```bash
curl -s -X POST http://localhost:8000/extract/tags \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"<DOC_ID>", "use_hrm": true, "dry_run": true}' | jq
```

- Ask with HRM (query flag):

```bash
curl -s -X POST "http://localhost:8000/ask?question=what%20is%20the%20total%20revenue%3F&use_hrm=true" | jq
```

Copilot Studio / POML
- Use Export POML from the UI or the API to generate a `.poml` artifact per document.
- Variants: `generic`, `troubleshoot`, `catalog` depending on your task.

Option A — use Docker from the script (recommended):

```powershell
cd PMOVES-DoX
$env:SMOKE_COMPOSE = 'docker-compose.cpu.yml'    # or 'docker-compose.yml' for GPU
python -m venv venv; ./venv/Scripts/Activate.ps1
pip install -r smoke/requirements.txt requests
python smoke/run_smoke_docker.py
```

Option B — run against an already running backend:

```powershell
cd PMOVES-DoX
python -m venv venv; ./venv/Scripts/Activate.ps1
pip install -r smoke/requirements.txt
$env:API_BASE = 'http://localhost:8000'
python smoke/smoke_backend.py
```

What it does:
- Checks `/health`
- Uploads `samples/sample.csv`
- Confirms facts were extracted
- Runs CHR on the new artifact and downloads the CSV
- Converts the artifact to TXT and downloads it
- Generates a datavzrd project
- Ingests XML/OpenAPI/Postman samples and queries `/logs` and `/apis`

Exit code 0 indicates success; otherwise the script prints an error and returns non‑zero.
### High-fidelity DOCX via Pandoc

The backend images include `pandoc`. Conversion from markdown (Docling output) to DOCX/TXT uses pandoc when available for best fidelity and falls back to a minimal python-docx mapping otherwise.
### datavzrd Dashboard Service

This repo includes a datavzrd service that builds the latest `viz.yaml` under `artifacts/datavzrd/**/viz.yaml` (from the CHR panel’s “Generate datavzrd project”) and serves the generated static dashboard at http://localhost:5173.

- The service image builds from source (`cargo install datavzrd`) — the first build can take a few minutes.
- By default it picks the newest viz.yaml. To force a specific one, set `VIZ_FILE` in the service to the absolute path, e.g. `VIZ_FILE=/app/artifacts/datavzrd/<stem>/viz.yaml` (edit `docker-compose.yml`).
- You can regenerate dashboards by clicking “Generate datavzrd project” again and refreshing the datavzrd page.

#### Spells (datavzrd-spells)

You can enrich dashboards with prebuilt spells from https://github.com/datavzrd/datavzrd-spells. The current service builds and serves dashboards from `viz.yaml`. To use spells:

- Add spell configs to your `viz.yaml` (see the spells repo for examples).
- If a spell requires local assets, mount them under `backend/artifacts/datavzrd/<stem>/` and reference them relative in `viz.yaml`.

### schemavzrd (DB Schema Docs)

The compose file includes a `schemavzrd` service (http://localhost:5174). Set `DB_URL` in your environment before starting compose, for example:

```powershell
$env:DB_URL = 'postgresql://user:pass@host:5432/dbname'
docker compose up --build schemavzrd
```

The service writes outputs to `backend/artifacts/out/schema` and serves them.

### Mangle (data transformation)

To include https://github.com/google/mangle in your workflow, run it alongside the stack (outside of Compose), and output transformed CSVs into `backend/artifacts` or `watch/`. A minimal pattern:

```powershell
# Install Go and mangle on your host, or build a container separately
go install github.com/google/mangle/cmd/mangle@latest

# Transform a CSV and drop into watch folder for auto-ingest
mangle run your.mangle -i path\to\input.csv -o PMOVES-DoX\watch\transformed.csv
```

You can also add a custom container for mangle later if you prefer containerized transforms.

## Database Migrations (Alembic)

SQLite is used by default (`db.sqlite3`). Alembic scaffolding is included:

```powershell
cd PMOVES-DoX/backend
alembic upgrade head           # apply migrations (none initially)
alembic revision --autogenerate -m "init"  # create a new migration from current SQLModel metadata
alembic upgrade head
```
### Search Filters + Deep Links
- Filters: The global search bar supports type filters (PDF, API, LOG, TAG). Toggle them to filter results server-side.
- Deep links: Results include a target panel and identifier. Clicking “Open in…” switches to the right panel:
  - PDF → Workspace panel (future: scroll to chunk)
  - API → APIs panel and opens the endpoint detail modal
  - LOG → Logs panel with code pre-filter
  - TAG → Tags panel with document/q pre-filled
  
API:
- `POST /search` with `{ q, k?, types?: ['pdf','api','log','tag'] }` → `{ results: [{ score, text, meta: { type, deeplink, ... } }] }`
- `POST /search/rebuild` → rebuilds the vector index

### Deeplink API (UI)
- From the browser console or client code, trigger panel navigation with:

```js
// Open APIs panel and show a specific endpoint
window.dispatchEvent(new CustomEvent('global-deeplink', {
  detail: { panel: 'apis', api_id: '<API_ID>' }
}));

// Open Logs panel, pre-filter by code
window.dispatchEvent(new CustomEvent('global-deeplink', {
  detail: { panel: 'logs', code: 'ERROR' }
}));

// Open Tags panel for a document and query
window.dispatchEvent(new CustomEvent('global-deeplink', {
  detail: { panel: 'tags', document_id: '<DOC_ID>', q: 'Loan Origination' }
}));

// Open Workspace and highlight a PDF chunk (by index)
window.dispatchEvent(new CustomEvent('global-deeplink', {
  detail: { panel: 'workspace', artifact_id: '<ARTIFACT_ID>', chunk: 12 }
}));
```
### PDF Text Units + Page Map
- During PDF ingestion, the backend writes `artifacts/<stem>.text_units.json` containing an array of `{ text, page }` extracted from Docling's text items.
- The search index prefers this file to build PDF chunks with page numbers. If missing, it falls back to splitting the Markdown.
- To regenerate: delete the existing `artifacts/<stem>.text_units.json` and re-run ingestion for that PDF.

### Enable "Open PDF at page" links
- Set `OPEN_PDF_ENABLED=true` in the backend environment (compose already passes this in CI). When enabled, the UI shows a button to open the source PDF at the reported page for a search hit.
- Local (PowerShell):
  - `$env:OPEN_PDF_ENABLED = 'true'`
  - `docker compose -f docker-compose.cpu.yml up --build`
- Notes:
  - Endpoint: `GET /open/pdf?artifact_id=<ID>&page=<N>` (served by the backend; simple file responder for now).
  - Security: this serves files from the artifacts directory only; consider a dedicated viewer for finer control later.
