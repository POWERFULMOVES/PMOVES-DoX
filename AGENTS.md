# AGENTS.md — Agent Working Agreement (Meeting Analyst App)

This file defines how agents should work within this repository. Its scope covers the entire `meeting-analyst-app/` directory tree.

## Mission
Build and operate a documentation + troubleshooting workbench focused on LMS docs (PDF), XML logs, and API collections (OpenAPI/Postman). Core features:
- Ingest + structure docs (Docling), logs (XML), API collections (OpenAPI/Postman)
- Extract metrics/tables/text with citations, and “application tags” via LangExtract
- Search and visualize with datavzrd dashboards; schema docs with schemavzrd

## Environment Expectations (Codex CLI)
- Filesystem: full write access within this repo; ok to create/modify files under `meeting-analyst-app/`
- Network: enabled (to build images, pull models, fetch dependencies)
- Approvals: prefer `on-failure` or `never` for smooth iteration
- GPU: available on machines running the GPU compose profile (NVIDIA Container Toolkit required)

### Required local tools
- Docker Desktop (WSL2 on Windows recommended)
- Python 3.11+
- Node 20+

### Core services & ports
- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- datavzrd: http://localhost:5173 (static dashboard)
- schemavzrd: http://localhost:5174 (DB schema docs)

## Runbook
- CPU (default smoke):
  - `docker compose -f docker-compose.cpu.yml up --build`
- GPU (NVIDIA):
  - `docker compose --compatibility up --build`
- Smoke tests (auto start/stop backend):
  - `python -m venv venv && ./venv/Scripts/Activate.ps1`
  - `pip install -r smoke/requirements.txt requests`
  - CPU: `python smoke/run_smoke_docker.py`
  - GPU: `SMOKE_COMPOSE=docker-compose.yml python smoke/run_smoke_docker.py`

## Configuration (.env)
- Backend env example: `backend/.env.example` (copy to `.env`)
  - WATCH_DIR: folder for LMS files (PDF/XML/OpenAPI/Postman)
  - DATAVZRD_SPELLS=true to enable table spells (wrapping)
  - HUGGINGFACE_HUB_TOKEN (for Docling model downloads), DOCLING_VLM_REPO
  - LANGEXTRACT_PROVIDER=ollama | (Gemini by API key)
- Frontend env example: `frontend/.env.local.example`

## Coding Conventions
- Python: FastAPI, SQLModel; avoid globals beyond service singletons; prefer Pydantic models for requests/responses
- TS/React: functional components, minimal state; env via `NEXT_PUBLIC_*`; fetch with simple `fetch` or axios
- Names: prefer explicit function names; keep files small and focused
- Tests: smoke under `smoke/`; lightweight unit tests under `backend/tests/` (future)

## Safe Areas for Agents
- It is safe to:
  - edit/add files under `backend/app/**`, `frontend/**`, `tools/**`, `smoke/**`, `samples/**`, `docs/**`
  - add new API endpoints, UI components, docs, migrations
- Avoid:
  - storing secrets in repo
  - rewriting third‑party generated content without need

## Implementation TODOs (Next Steps)
- Search & RAG
  - Add FAISS vector index; endpoints: `/search`
  - UI: global search bar with type filters
- XML/OpenAPI enrichments
  - Add XPath mapping for LMS logs; normalize OpenAPI components/security
- Tag Extraction
  - Curated LMS prompts + few‑shot examples; dry‑run/apply modes; governance (merge/rename)
- APIs Explorer
  - Endpoint detail modal (params/responses/examples); copy cURL
- Logs UX
  - Time range filters; export CSV from UI; component drill‑downs
- CHR
  - UI controls (iters/beta/sentences); progress indicator; PCA palette options
- DB & Migrations
  - Add indexes; auto‑run Alembic on startup (guarded)
- CI
  - Extend smoke to cover `/search` + tags apply; nightly GPU job on self‑hosted runner

## PR & Commit Guidance
- Small, atomic commits; include “feat/ fix/ chore/ docs/ ci” prefixes
- Update README and smoke tests when adding endpoints or flows

## Support Scripts
- `smoke/run_smoke_docker.py` — starts/stops backend via Compose and runs smoke
- `setup.ps1` — local setup helper

---

This AGENTS.md is meant to keep agent behavior consistent and safe. When in doubt, open a short PR with proposed changes and a one‑paragraph explanation.
