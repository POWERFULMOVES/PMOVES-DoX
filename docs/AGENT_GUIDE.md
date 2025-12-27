# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

PMOVES-DoX is a document intelligence platform for extracting, analyzing, and structuring data from PDFs, spreadsheets, XML logs, and API collections. It combines AI-powered processing (Docling, spaCy, LangExtract) with visualization tools (datavzrd) in a local-first architecture.

**Main Branch**: `PMOVES.AI-Edition-Hardened` (for PRs)
**Current Branch**: `feat/integrate-internal-agents`

## Common Development Commands

### Backend

```bash
# Local development
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# CLI tool (zero-install)
uvx --from . pmoves-cli --help
uvx --from . pmoves-cli --local-app ingest pdf samples/sample.pdf

# CLI tool (installed)
pip install -e .
pmoves-cli --base-url http://localhost:8000 ingest pdf ./samples/sample.pdf
pmoves-cli --base-url http://localhost:8000 search "revenue" --json

# Run single test
pytest backend/tests/test_specific.py::test_function_name -v

# Database migrations
cd backend
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend

```bash
cd frontend
npm install
npm run dev          # Port 3001 by default
npm run build
npm run lint
npm run test         # Vitest
npm run test:e2e     # Playwright
```

### Docker Compose

```bash
# CPU-only (default for testing)
docker compose -f docker-compose.cpu.yml up --build

# GPU with NVIDIA (main development)
docker compose --compatibility up --build

# GPU with Ollama and tools
docker compose --compatibility --profile ollama --profile tools up --build -d

# Jetson Nano (ARM64, L4T r32.7.1)
docker compose -f docker-compose.jetson.yml up --build

# Jetson Orin (ARM64, L4T r36.3.0)
docker compose -f docker-compose.jetson-orin.yml up --build
```

### Testing & CI

```bash
# Smoke tests (auto start/stop backend via Docker)
npm run smoke        # CPU compose
npm run smoke:gpu    # GPU compose

# UI smoke tests with Playwright
npm run smoke:ui     # CPU compose
npm run smoke:ui:gpu # GPU compose

# Python smoke tests directly (backend must be running)
cd PMOVES-DoX
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r smoke/requirements.txt
$env:API_BASE = 'http://localhost:8000'
python smoke/smoke_backend.py
```

## High-Level Architecture

### Backend Structure

**Core Services** (singleton pattern, initialized in `app/main.py`):
- `Database` (`app/database.py` or `app/database_supabase.py`): SQLModel-based storage (SQLite default, optional Supabase)
- `SearchIndex` (`app/search.py`): FAISS or NumPy fallback for vector search
- `QAEngine` (`app/qa_engine.py`): Question answering with citation retrieval
- `SummarizationService` (`app/analysis/summarization.py`): Multi-provider summarization (Gemini/Ollama/mock)

**Key Processing Pipelines**:
1. **Ingestion** (`app/ingestion/`):
   - PDFs → `pdf_processor.py` (Docling with optional VLM, multi-page tables, formulas, charts)
   - CSV/XLSX → `csv_processor.py`, `xlsx_processor.py`
   - XML logs → `xml_ingestion.py` (configurable XPath mappings)
   - OpenAPI/Postman → `openapi_ingestion.py`, `postman_ingestion.py`
   - Media → `media_transcriber.py` (audio/video transcription)
   - Web URLs → `web_ingestion.py`

2. **Analysis** (`app/analysis/`):
   - Financial statement detection: `financial_statement_detector.py`
   - Named entity recognition: `ner_processor.py` (spaCy)
   - Structure extraction: `structure_processor.py` (heading hierarchy)
   - Metric extraction: `metric_extractor.py` (regex-based)

3. **Export & Visualization**:
   - CHR (Constellation Harvest Regularization): `app/chr_pipeline.py`
   - POML export: `app/export_poml.py`
   - Tag extraction: `app/extraction/langextract_adapter.py`

**API Routers** (`app/api/routers/`):
- `documents.py`: Document upload, listing, ingestion endpoints
- `analysis.py`: Tag extraction, CHR, summarization, datavzrd generation
- `search.py`: Vector search and index rebuild
- `system.py`: Health, config, metrics, tasks
- `cipher.py`: Byterover Cipher memory/skill integration

**Data Models** (`app/database.py`):
- `Artifact`: Uploaded files (PDFs, CSVs, etc.)
- `Evidence`: Extracted content chunks with coordinates
- `Fact`: Structured data extracted from evidence
- `SummaryRow`: Generated summaries with scope/style

**Background Tasks**:
- Watch folder monitoring: Auto-ingest files dropped into `watch/` directory
- Async task tracking: `/tasks` endpoint for long-running operations

### Frontend Structure

**Pages** (`frontend/app/`):
- `page.tsx`: Main application with tabbed interface
- `apis/`, `artifacts/`, `cookbooks/`, `geometry/`, `logs/`, `tags/`: Panel-specific pages

**Components** (`frontend/components/`):
- `FileUpload.tsx`: Drag-and-drop file upload
- `QAInterface.tsx`: Question answering with citations
- `FactsViewer.tsx`: Display extracted facts
- `GlobalSearch.tsx`: Unified search with type filters
- `APIsPanel.tsx`, `LogsPanel.tsx`, `TagsPanel.tsx`: Domain-specific views
- `CHRPanel.tsx`: CHR configuration and visualization
- `SettingsModal.tsx`: Global settings and configuration
- `geometry/`: Geometric Intelligence components (Hyperbolic Navigator, Manifold Visualizer)

**Deep Linking**: UI supports custom events for panel navigation:
```javascript
window.dispatchEvent(new CustomEvent('global-deeplink', {
  detail: { panel: 'apis', api_id: '<ID>' }
}));
```

### Processing Flow

```mermaid
Upload → Ingestion → Evidence Extraction → Fact Creation → Indexing
   ↓         ↓              ↓                    ↓            ↓
Artifacts  Pages/       Chunks with         Structured   FAISS/NumPy
           Tables       Coordinates         Metrics      Vector Index
```

1. **Upload**: Files go to `backend/uploads/` (or S3-compatible storage)
2. **Ingestion**: Processors extract text, tables, structure → Markdown + JSON in `backend/artifacts/`
3. **Evidence**: Text chunks with bounding boxes/page numbers stored in DB
4. **Facts**: Metrics and entities linked to evidence
5. **Indexing**: Embeddings generated for vector search
6. **Query**: Search retrieves relevant evidence, QA engine formats citations

### Key Architectural Patterns

**Database Abstraction**:
- Factory pattern (`database_factory.py`) switches between SQLite and Supabase
- Enable Supabase: `DB_BACKEND=supabase` + Supabase credentials
- Dual-write mode: `SUPABASE_DUAL_WRITE=true` for migration

**HRM (Halting Reasoning Module)**:
- Experimental iterative refinement with early stopping
- Enable: `HRM_ENABLED=true` in backend `.env`
- Used in tag extraction (`use_hrm: true`) and Q&A (`?use_hrm=true`)
- Metrics: `GET /metrics/hrm`

**GPU Acceleration**:
- `SEARCH_DEVICE`: Controls SentenceTransformers device (auto-detects CUDA)
- `DOCLING_DEVICE`, `DOCLING_NUM_THREADS`: Docling accelerator settings
- VLM picture descriptions: `DOCLING_VLM_REPO=ibm-granite/granite-docling-258m-demo`

**Local LLMs (Ollama)**:
- Internal service: `http://ollama:11434` (no host port binding)
- Tag extraction: `LANGEXTRACT_PROVIDER=ollama`, `LANGEXTRACT_MODEL=ollama:gemma3`
- Pull models: `docker exec -it ollama bash -lc "ollama pull gemma3"`

## Important Environment Variables

**Backend** (`backend/.env`):
- `DB_BACKEND`: `sqlite` (default) or `supabase`
- `DB_PATH`: SQLite database path (default: `db.sqlite3`)
- `WATCH_ENABLED`, `WATCH_DIR`: Auto-ingest watch folder
- `FAST_PDF_MODE`: Skip advanced PDF features for speed
- `PDF_FINANCIAL_ANALYSIS`: Enable financial statement detection
- `PDF_OCR_ENABLED`: Enable OCR for scanned PDFs
- `PDF_PICTURE_DESCRIPTION`: VLM captions for figures/charts
- `OPEN_PDF_ENABLED`: Enable PDF viewer links in UI
- `HRM_ENABLED`, `HRM_MMAX`, `HRM_MMIN`: Halting Reasoning Module
- `LANGEXTRACT_PROVIDER`: `ollama` or `gemini`
- `HUGGINGFACE_HUB_TOKEN`: For model downloads
- `AUTO_MIGRATE`: Run Alembic migrations on startup

**Frontend** (`frontend/.env.local`):
- `NEXT_PUBLIC_API_BASE`: Backend URL (default: `http://localhost:8000`)

## Submodules

Initialize with: `git submodule update --init --recursive`

- `PsyFeR_reference`: Byterover Cipher memory framework
- `external/Pmoves-hyperdimensions`: Mathematical visualization (Poincaré disk, manifolds)
- `external/conductor`: Google Conductor context-driven development tools
- `external/PMOVES-Agent-Zero`: Internal agent framework (branch: `PMOVES.AI-Edition-Hardened-DoX`)

## Testing Strategy

**Smoke Tests** (`smoke/`):
- `smoke_backend.py`: Backend API smoke tests (upload, facts, CHR, conversion, search)
- `smoke_security.py`: Security validation (injection attacks, file traversal)
- `run_smoke_docker.py`: Wrapper that starts/stops Docker Compose

**UI Tests** (`frontend/`):
- Playwright e2e: `npm run test:e2e`
- Vitest unit: `npm run test`

**CI Pipeline** (`.github/workflows/ci.yml`):
- `smoke`: CPU backend smoke tests on Ubuntu
- `smoke-gpu`: GPU smoke tests on self-hosted runner
- `ui-smoke`: Playwright UI smoke tests

## Common Gotchas

1. **First Run**: Model downloads (Docling, embeddings) take time on first startup
2. **Port Conflicts**: Backend defaults to 8000, frontend to 3001 (check `docker-compose.yml` overrides)
3. **PDF Processing**: Large PDFs with VLM can be slow; use `FAST_PDF_MODE=true` for quick testing
4. **Submodules**: Run `git submodule update --init --recursive` after clone
5. **Database Migrations**: Set `AUTO_MIGRATE=true` in production; manually run `alembic upgrade head` in dev
6. **Watch Folder**: Files must stabilize (default 1s debounce) before auto-ingestion triggers
7. **GPU Memory**: Ollama models can exceed Jetson Nano 4GB; use quantized models

## Integration Points

**MCP (Model Context Protocol)**: Manifest at `backend/mcp/manifest.json` exposes:
- `search`: POST `/search`
- `extract_tags`: POST `/extract/tags`
- `export_poml`: POST `/export/poml`

**PMOVES-BoTZ Ecosystem**:
- This repo is the "Document Intelligence" module
- Branch `hardened-DoX` is production-ready for BoTZ integration
- Enhanced by n8n workflows (`external/n8n` - not yet committed)

**Datavzrd Dashboards**:
- Generated at `backend/artifacts/datavzrd/<stem>/viz.yaml`
- Served at `http://localhost:5173` by datavzrd service
- Spells: Enable with `DATAVZRD_SPELLS=true`

**Schemavzrd**:
- DB schema docs at `http://localhost:5174`
- Set `DB_URL` env var before starting service

## Code Style Notes

- **Python**: FastAPI conventions, Pydantic models for request/response, avoid globals
- **TypeScript**: Functional React components, minimal state, `NEXT_PUBLIC_` prefix for env vars
- **Naming**: Explicit function names, small focused files
- **Comments**: Document complex pipelines (CHR, HRM) and non-obvious integrations
- **Commits**: Prefix with `feat:`, `fix:`, `chore:`, `docs:`, `ci:`
