# Next Steps Plan (LMS‑Centered)

## Goals
- Ingest + structure LMS Admin Guides (PDF), XML logs, and API collections
- Extract tables/text and derive application tags with citations
- Provide troubleshooting views and API catalogs; dashboards via datavzrd

## Priorities (Week 1–2)
- P0
  - Add FAISS vector search + `/search` endpoint + UI global search
  - Logs time‑range filters + CSV export
  - API detail modal (params/responses/examples)
  - Tag prompt presets (LMS), dry‑run/apply + governance
- P1
  - XML XPath mapping for LMS logs; enrich OpenAPI components/security
  - CHR parameter UI; DB indexes; Alembic auto‑run (guarded)
- P2
  - datavzrd theme/pinned dashboards; nightly GPU smoke; Copilot actions

## Acceptance Criteria
- `/search` returns lexical+vector hits with citations ≤ 300 ms (small corpora)
- Logs view filters by time/level/code and exports current view
- Tag extraction writes TagRow with source pointers; re‑runs merge predictably
- API detail modal shows params/responses and copy‑cURL

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

## Compact
- Stabilize deploy + health/migrate; better .envs
- Ingest v2: XML XPath, OpenAPI components/security
- Add FAISS + `/search` + UI search
- Tag presets, dry‑run/apply, governance
- API detail modal; Logs time filters + CSV export
- CHR controls + richer PCA; datavzrd themes/spells
- DB indexes; Alembic auto‑run; nightly GPU smoke
- Docs walkthroughs + screencasts
