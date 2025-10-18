# PMOVES DoX × PMOVES.AI × Open Notebook Integration Plan

This roadmap unifies the earlier discovery plan for PMOVES-DoX ↔︎ Open Notebook integration with the staged rollout that keeps PMOVES.AI in the loop. It is designed so the three platforms complement each other:

- **PMOVES-DoX** stays focused on high-fidelity ingestion, enrichment, and search over LMS documents, logs, and API collections.
- **Open Notebook** provides privacy-first notebook authoring, multi-model orchestration, and export surfaces that transform DoX outputs into narrative assets.
- **PMOVES.AI** coordinates the end-to-end analyst experience, automations, and visibility across both systems.

The phases below highlight the shared touchpoints (infrastructure, APIs, UX) and the responsibilities for each stack to deliver a cohesive experience.

## Phase 0 – Alignment & Topology

1. **Shared outcomes & personas** – Co-create journey maps that show how artifacts flow from PMOVES.AI orchestration → DoX ingestion → Notebook authoring. Decide the handoff events (artifact ready, notebook enriched, podcast published) and document the chosen transport (REST hook, queue, shared DB channel).
2. **Service placement** – Choose whether Open Notebook co-resides in the DoX Docker compose profile (ideal for demos) or is hosted by PMOVES.AI with a stable base URL/token. Capture pros/cons and rollout implications for each environment.
3. **Auth alignment** – Standardize on credential storage (env vars, Supabase secrets, or PMOVES.AI vault) so DoX, Notebook, and PMOVES.AI can authenticate to each other without duplicating secret management.

## Phase 1 – Infrastructure & Configuration

1. **Compose & deployment updates**
   - Extend DoX Docker profiles with an optional `open-notebook` service (port 5055 API, 8502 UI) and shared volumes (`/data/notebooks`, `/data/surreal`).
   - Mirror `.env` handling so operators can toggle Notebook participation without breaking CPU/GPU profiles.
   - Surface Notebook availability in DoX `/config` responses; PMOVES.AI reads the same config to know which features are active per workspace.
2. **Health & observability** – Add health checks for Notebook services and integrate logs/metrics with PMOVES.AI dashboards. Use structured JSON including artifact IDs to enable cross-system tracing.
3. **Secret propagation** – Ensure password middleware and embedding model credentials are distributed through the same pipelines PMOVES.AI uses (e.g., Terraform vars, GitHub Actions secrets), avoiding repo storage.

## Phase 2 – Data Flow & Synchronization

1. **Artifact push connector (DoX → Notebook)**
   - After DoX completes `_process_and_store`, invoke a Notebook sync service that POSTs normalized artifacts (Markdown, transcripts, chart metadata) to `/api/sources`.
   - Store returned Notebook source IDs in `artifact.extra_json` so updates remain idempotent.
   - Implement retry/backoff and expose status via DoX `TASKS`; PMOVES.AI can mirror the same status in its hub UI.
2. **Status feedback (Notebook → DoX/PMOVES.AI)** – Poll or subscribe to Notebook processing status. Show progress beside DoX artifact cards and stream the same events to PMOVES.AI through webhooks/queues.
3. **Search index harmonization** – Decide whether Notebook consumes DoX embeddings (exported from `SearchIndex.payloads`) or maintains its own vector store. Preserve document IDs and page anchors so Notebook chat can deep-link back to DoX artifacts displayed in PMOVES.AI.

## Phase 3 – Retrieval, QA, and Model Orchestration

1. **Backend composition** – Wrap Notebook `/api/search` and `/api/search/ask` inside DoX search/QA pipelines. Treat Notebook as an external vector provider that can be toggled per request based on config flags.
2. **Answer synthesis** – Expand DoX QA models to merge Notebook streaming responses with local FAISS results, producing unified answers that cite both stores. PMOVES.AI surfaces these combined responses in its chat/analysis tools.
3. **Model catalog exposure** – Publish Notebook’s provider inventory (LLMs, transformations, podcast generation) through PMOVES.AI’s orchestration layer so analysts can select Notebook-backed workflows while DoX continues powering document tagging and metrics extraction.

## Phase 4 – Frontend & UX Cohesion

1. **DoX UI additions** – Add a “Notebook Sync” settings card with health indicators, auth status, and deep links to the Notebook UI. Extend the global search bar to label Notebook results with provider badges.
2. **PMOVES.AI surface** – Within PMOVES.AI, introduce panels that display DoX ingestion states, Notebook enrichment progress, and quick actions (open DoX artifact, open Notebook, re-sync). Maintain consistent terminology so users know which surface they are on.
3. **Cross-service deeplinks** – Store Notebook URLs inside `artifact.extras` and expose them across DoX and PMOVES.AI interfaces. Provide guardrails (feature flags, “data leaves DoX” notices) to respect privacy expectations.

## Phase 5 – Automation & Developer Experience

1. **CLI parity** – Extend `pmoves-cli` with Notebook subcommands (`notebook sync`, `notebook status`) so PMOVES.AI CI pipelines or automation scripts can drive both systems headlessly.
2. **Event contracts** – Define webhook schemas for “artifact ingested”, “notebook synced”, “notebook output ready”. PMOVES.AI subscribes and updates its dashboards without polling.
3. **Content round-trip** – Allow Notebook-generated outputs (summaries, podcasts) to be re-ingested into DoX as new evidence rows, ensuring search/export in DoX stays authoritative while PMOVES.AI aggregates the latest insights.

## Phase 6 – Testing, Documentation, and Rollout

1. **Integration smoke tests** – Add automated scenarios that spin up Notebook (or a stub) to verify artifact sync, status surfacing, and UI toggles. Gate them with a feature flag so default CI stays lightweight.
2. **Documentation** – Update DoX README quick-start with optional Notebook steps, create operator runbooks for failure recovery, and document shared schema contracts for PMOVES.AI engineers.
3. **Phased enablement** – Start with an internal “Notebook sync beta” flag driven by PMOVES.AI feature toggles, gather telemetry, and expand to general availability once stability targets are met.

---

This plan ensures PMOVES-DoX continues to deliver high-quality ingestion and search, Open Notebook transforms structured artifacts into collaborative notebooks, and PMOVES.AI orchestrates the blended experience for analysts and automation pipelines.
