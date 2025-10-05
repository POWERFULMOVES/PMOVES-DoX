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

### Recent Updates (2025-10-03)
- Global Search now shows a page indicator for PDF hits (e.g., “PDF p. 7”).
- CI workflows set `OPEN_PDF_ENABLED=true` across CPU/GPU/UI jobs so smoke tests can validate PDF open links.
- Minor UI polish: added the small page badge next to the result type label.

### Recent Updates (2025-10-04)
- Unified the FastAPI `/search` route so timing/count telemetry is retained alongside type-filtering and deeplink enrichment.
- Added backend unit coverage for `/search` filter edge cases, PDF text-units fallbacks, and `/open/pdf` error handling; see `backend/tests/test_search_routes.py`.
- Introduced GPU-aware toggles (`SEARCH_DEVICE`, `DOCLING_DEVICE`, `DOCLING_NUM_THREADS`) so SentenceTransformers and Docling can target the RTX 4090 or fall back gracefully.
- CUDA detection now prioritizes RTX/Jetson GPUs (with CPU fallback) and matches the Windows > WSL > Linux docker stack guidance.
- Draft Supabase migration playbook captured in [`docs/SUPABASE_MIGRATION.md`](SUPABASE_MIGRATION.md).
- Supabase backfill CLI added at 	ools/backfill_supabase.py; run supabase start then python tools/backfill_supabase.py --from-sqlite backend/db.sqlite3 --reset (script reads .supabase/.env automatically).

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
  - PDF deep-links: ensure per-sentence page mapping in CHR when `units_mode='sentences'` (fallback to nearest preceding unit page)
- P1.5
  - LangExtract auto‑examples: when none are provided, backend supplies curated LMS few‑shot examples and a default prompt. Toggle via env if needed.
  - Prompt augmentation: optionally embed POML snippets and run prompt through a local `mangle` file before calling LangExtract.
  - Multi‑process ingest: on PDF ingest, spawn CHR and Auto‑Tag jobs (Docling→CHR→LangExtract) to compute structure and initial tags with page‑mapped citations.
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
  - Auto‑examples pipeline (fallback few‑shot from presets; derive examples from existing Tags when available)
  - POML‑aware prompts and `mangle` pre‑processing (backend flags)
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
  - In Global Search, verify PDF results display a page label; if `OPEN_PDF_ENABLED=true`, “Open PDF at page” should download or open the file.

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

## PMOVES Agent Persona & Orchestration
- Persona: “PMOVES Analyst” — expert LMS documentation/logs/API analyst that chains project tools.
- Tooling flow (baseline):
  - Search vector index → open hits (PDF page, API row, log record)
  - Tag extraction via LangExtract (uses curated few‑shot automatically if none given)
  - Prompt builder can inject POML context and pass through a `mangle` transform
  - CHR structuring → optional datavzrd dashboards
  - Export POML for downstream copilots
  - Auto‑ingest pipeline (PDF): Docling parses → CHR clusters with Range/Partition entropy tracking → auto‑tags from content → map tags back to Docling page spans.
- Acceptance:
  - If user asks general questions (e.g., “What is PMOVES?”), the agent provides domain‑aware guidance and suggests relevant tools/views.
  - Tag extraction succeeds out‑of‑the‑box with fallback few‑shot; users can later supply custom examples.

## Configuration Flags (new)
- `TAGS_PROMPT`: default prompt for LangExtract fallback.
- `LANGEXTRACT_PROVIDER`: `ollama` or default remote provider. If `ollama`, `OLLAMA_BASE_URL` is honored.
- `POML_IN_PROMPT` (optional UI wiring): include POML snippet into prompts for tag extraction.
  - API accepts per‑request flags: `include_poml`, `poml_variant`.
- `MANGLE_FILE` (optional): path to a local `.mangle` file used to transform prompts. API accepts per‑request `mangle_file`.
- Ingest pipeline (PDF):
  - `MULTI_PROCESS_INGEST` (default true)
  - `CHR_ON_INGEST` (default true), `CHR_K`, `CHR_ITERS`, `CHR_BINS`, `CHR_BETA`, `CHR_UNITS_MODE`, `CHR_INCLUDE_TABLES`
  - `AUTOTAG_ON_INGEST` (default true), `AUTOTAG_INCLUDE_POML` (default true), `AUTOTAG_POML_VARIANT`
  - `AUTOTAG_USE_HRM` (default false) — apply HRM refinement to extracted tags during auto‑tag; steps recorded in HRM metrics
  - `AUTOTAG_MANGLE_FILE`, `AUTOTAG_MANGLE_EXEC` (false), `AUTOTAG_MANGLE_QUERY`

## Mangle (Google) Integration
- Reference: https://github.com/google/mangle and https://mangle.readthedocs.io/
- Mode A — Inline (shipped): backend will inline a `.mg` program into the prompt as guidance under a fenced block labeled “MANGLE RULES”. This steers the LLM to obey normalization/constraints.
- Mode B — Execute (shipped): when the `mg` interpreter is available, backend can run a `.mg` ruleset against an auto‑generated EDB of extracted tags and replace tags with `normalized_tag/1` results.
  - API flags: `mangle_exec=true`, `mangle_file=path`, optional `mangle_query` (default `normalized_tag(T)`).
  - EDB facts provided: `tag_raw("<tag>").`
  - Sample rules: docs/samples/mangle/normalized_tags.mg
  - Fallbacks: if mg is missing or query returns no results, original tags are used.
- Install mg:
  - `go install github.com/google/mangle/cmd/mg@latest`
  - Verify: `mg --help`
  - Examples: https://github.com/google/mangle?tab=readme-ov-file#examples

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
  - Ensure `OPEN_PDF_ENABLED` present (DONE)

- Tests
  - /search filters + deeplink construction edge cases (invalid/empty type lists) - owner: __, due: 2025-10-06 (DONE 2025-10-04)
  - PDF page mapping fallbacks (missing or mismatched `text_units.json`) - owner: __, due: 2025-10-06 (DONE 2025-10-04)
  - `/open/pdf` toggle + error paths (disabled, missing artifact, non-PDF) - owner: __, due: 2025-10-07

- HRM sidecar experiment wired to backend `/experiments/hrm/*` - owner: __, due: 2025-10-09
- Add HRM toggle + params to Settings modal - owner: __, due: 2025-10-10
- HRM evaluator script + metrics endpoint - owner: __, due: 2025-10-10

## Backlog
- Search result deep links (open PDF chunk, API row, or log record)
- Tag merge visualization (diff previous vs new)
- Export/import governance presets per LMS vendor
