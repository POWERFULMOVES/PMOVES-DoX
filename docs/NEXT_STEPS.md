# Next Steps Plan (PMOVES_DoX)

## Goals
- Ingest + structure LMS Admin Guides (PDF), XML logs, and API collections
- Extract tables/text and derive application tags with citations
- Provide troubleshooting views and API catalogs; dashboards via datavzrd

## Status (as of 2025-10-03)
- Core ingestion (PDF/XML/OpenAPI/Postman) in place
- Vector search + global UI search shipped
- Logs filters + CSV export shipped
- API detail modal (params/responses + copy‑cURL) shipped
- Tag presets, dry‑run/apply, governance (save/history/restore) shipped
- Header with health + rebuild; Settings modal (API base, author, VLM) shipped
- Backend and UI smoke tests wired; backend smoke passing

## Priorities (Weeks 3–4)
- P0
  - DONE: FAISS vector search + `/search` + Global search bar (header)
  - DONE: Logs time‑range filters + CSV export
  - DONE: API detail modal (params/responses/examples) + copy‑cURL
  - DONE: Tag prompt presets (LMS), dry‑run/apply, governance (save/history/restore)
- P1
  - XML XPath mapping for LMS logs; enrich OpenAPI components/security
  - CHR parameter UI in UI; DB indexes for logs/apis/tags; Alembic auto‑run (guarded)
  - CI: GitHub Actions for smoke (backend + UI) on PRs/merge to main
- P2
  - datavzrd theme/pinned dashboards; nightly GPU smoke; Copilot actions

## Acceptance Criteria
- `/search` returns lexical+vector hits with citations ≤ 300 ms (small corpora)
- Logs view filters by time/level/code and exports current view
- Tag extraction writes TagRow with source pointers; re‑runs merge predictably
- API detail modal shows params/responses and copy‑cURL
- Tag prompt governance supports: load preset, edit, save (author), list history, restore into editor, restore & save

### Performance Targets
- PDF -> Markdown (Docling, 10-page guide) ≤ 20s on CPU, ≤ 8s on mid‑range GPU
- Index rebuild on 1k chunks ≤ 2s; query P50 ≤ 250 ms, P95 ≤ 500 ms
- Logs export for 50k rows completes ≤ 2s server time

## Risks & Mitigations
- Large PDFs/logs → queue + progress; chunking + streaming
- Model downloads → HF cache volume + prefetch scripts
- Schema churn → Alembic migrations; versioned API schema

## Work Breakdown
- Ingestion
  - XML (lxml + XPath map); OpenAPI components/security parsing
- Search
  - FAISS index build/update; `/search` endpoint; UI bar and results list
- Tags
  - LMS prompt presets; examples; dry‑run/apply; review UI
- APIs/Logs UI
  - Endpoint modal; logs filters/export; drill‑downs
- Viz
  - CHR controls; PCA palette; datavzrd themes/spells
- DB
  - Indexes; migrations; auto‑run option
- CI
  - Extend smoke to call `/search` and `/extract/tags`; nightly GPU job

## Validation Plan
- Backend smoke (Docker CPU):
  - `npm run smoke` (wrapper) or `python smoke/run_smoke_docker.py`
- UI smoke (Playwright):
  - `npm run smoke:ui` (brings up backend+frontend, runs headless UI checks)
- Manual spot checks:
  - Upload PDF/XML/OpenAPI under `samples/`, verify tags, search hits, API modal
  - Rebuild index from header and assert search latency in browser DevTools

## Compact
- Stabilize deploy + health/migrate; better .envs
- Ingest v2: XML XPath, OpenAPI components/security
- FAISS + `/search` + UI search (DONE)
- Tag presets, dry‑run/apply, governance (DONE)
- API detail modal; Logs time filters + CSV export (DONE)
- CHR controls + richer PCA; datavzrd themes/spells
- DB indexes; Alembic auto‑run; nightly GPU smoke
- Docs walkthroughs + screencasts (update with PMOVES_DoX branding)

## HRM/Reasoning Enhancements
- Sidecar HRM for iterative refinement
  - Backend: add optional HRM sidecar module to wrap existing encoders/heads used in `qa_engine` and tag extraction. Support `Mmax`, `Mmin`, and `halt_threshold` with ACT-style halting at inference.
  - Endpoints: `/experiments/hrm/sort_digits` (toy) and `/experiments/hrm/echo` for sanity; flags to enable HRM in `/ask` and `/extract/tags`.
- Metrics + evaluation
  - Track exact-match accuracy, avg refinement steps, and latency deltas (with/without halting). Expose at `/metrics/hrm` and log to artifacts.
  - Add dataset harness in `samples/experiments/hrm/` and a quick evaluator script.
- UI controls
  - Settings: toggle “Use HRM Sidecar”, sliders for `Mmax`/`Mmin`, and a threshold input. Show per-request steps badge in header.
  - Visualization: small panel in CHR view to compare outputs across steps for a sample.
- Docs & Colab
  - Link and ship `docs/Understanding the HRM Model_ A Simple Guide.md` and `docs/hrm_transformer_sidecar_colab.py` under an Experiments section in README.
  - Brief how-to for enabling HRM in backend and UI, with screenshots.

### Acceptance (HRM)
- With HRM+halting enabled on toy tasks, accuracy improves vs. no-halting baseline and average steps < `Mmax`.
- Toggling HRM in Settings updates behavior of `/ask` and tag extraction without restart.
- Metrics endpoint reports rolling averages and last-run details (accuracy, steps, latency).

## Short-Term Tasks (assign/track)
- XML XPath mapping starter (map common LMS log shapes) - owner: __, due: 2025-10-10
- OpenAPI enrichment (components/security) - owner: __, due: 2025-10-10
- DB indices (apis.path, apis.method, logs.level/code/ts, tags.tag) - owner: __, due: 2025-10-09
- CHR panel controls (K, units mode, include tables) - owner: __, due: 2025-10-09
- CI: add GH Actions workflow (smoke + ui-smoke) - owner: __, due: 2025-10-08

- HRM sidecar experiment wired to backend `/experiments/hrm/*` - owner: __, due: 2025-10-09
- Add HRM toggle + params to Settings modal - owner: __, due: 2025-10-10
- HRM evaluator script + metrics endpoint - owner: __, due: 2025-10-10

## Backlog
- Search result deep links (open PDF chunk, API row, or log record)
- Tag merge visualization (diff previous vs new)
- Export/import governance presets per LMS vendor
