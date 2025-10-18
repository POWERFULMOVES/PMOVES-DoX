# PMOVES Triad Integration Blueprint

This blueprint consolidates the earlier PMOVES-DoX ↔︎ Pmoves-open-notebook roadmap with the coordination work underway for PMOVES.AI. It focuses on delivering a unified analyst journey where the three systems amplify each other: DoX handles ingestion, enrichment, and auditability; Open Notebook provides multimodal notebook authoring and model routing; PMOVES.AI orchestrates persona workflows and exposes the combined capabilities to operators.

## 1. Shared North Star

* **Unified knowledge loop** – Ingest once in DoX, contextualize in Open Notebook, operationalize via PMOVES.AI.
* **Consistent trust markers** – Preserve citations, artifact IDs, and provenance fields end-to-end so analysts can trace every insight back to source material.
* **Composable automation** – Allow PMOVES.AI to trigger, monitor, and remix tasks across DoX and Notebook without duplicating business logic.

## 2. Platform Topology

| Capability | PMOVES-DoX | Pmoves-open-notebook | PMOVES.AI |
| --- | --- | --- | --- |
| Primary role | High-fidelity ingestion, extraction, tagging, search | Notebook authoring, multi-model chat, transformations & podcast generation | Persona workflows, orchestration, unified UI/CLI |
| Hosting profile | FastAPI + worker + Next.js (Docker) | SurrealDB-backed API (5055) + Streamlit UI (8502) | Hub coordinating cross-service actions |
| Shared assets | Artifact metadata, embeddings, task registry | Notebook sources, model catalog, context stores | Personas, automations, analytics dashboards |

## 3. Integration Pillars & Tasks

### Pillar A — Infrastructure & Configuration
1. **Compose federation**
   * Extend DoX compose profiles with optional Notebook services (API + UI) gated by `ENABLE_NOTEBOOK=true`.
   * Share volume roots: `/data/artifacts`, `/data/notebooks`, `/data/surreal`.
2. **Central credentials**
   * Route Notebook password middleware and API tokens through the same secret provider PMOVES.AI will consume (e.g., Supabase secrets or environment manager).
3. **Health propagation**
   * Register Notebook readiness checks within DoX’s `/config` endpoint so PMOVES.AI can display tri-service health in a single dashboard.

### Pillar B — Data & Workflow Handshake
1. **Artifact mirror service**
   * After DoX finishes `_process_and_store`, push normalized payloads (Markdown, tables, embeddings) to `/api/sources` in Open Notebook and cache returned IDs in `artifact.extra_json`.
   * Implement retries/backoff and reflect progress in DoX task registry (`TASKS`).
2. **Status echo & telemetry**
   * Poll Notebook source status; emit events/webhooks (e.g., `artifact_synced`, `notebook_ready`) that PMOVES.AI subscribes to.
   * Align logging schemas (JSON with `artifact_id`, `notebook_source_id`, `persona_id`).
3. **Embeddings cooperation**
   * Offer DoX embeddings to Notebook when a local model is unavailable; otherwise, allow Notebook embeddings to seed DoX’s external search provider interface.

### Pillar C — Retrieval, QA & Automation
1. **Hybrid search gateway**
   * Add a DoX backend adapter that proxies Notebook’s `/api/search` and `/api/search/ask` endpoints, exposing them via DoX’s `SearchIndex`.
   * Merge responses with DoX’s FAISS hits, tagging each result with its origin for UI differentiation.
2. **Streaming answer reconciliation**
   * Extend DoX’s QA engine to ingest Notebook streaming answers and unify citation blocks before emitting responses to PMOVES.AI clients.
3. **CLI symmetry**
   * Expand `pmoves-cli` with `notebook sync`, `notebook search`, and `triad status` commands so PMOVES.AI scripts can trigger and monitor flows headlessly.

### Pillar D — Experience Integration
1. **Settings & feature flags**
   * Add a DoX settings card “Notebook Sync” with toggle, health indicator, and deep link to Notebook UI.
   * PMOVES.AI mirrors the toggle in its admin view, persisting preference for downstream automations.
2. **Unified search UX**
   * Update DoX’s and PMOVES.AI’s search bars to surface Notebook hits alongside local results using consistent badges (e.g., `DoX`, `Notebook`).
3. **Contextual deep links**
   * Embed Notebook URLs inside DoX artifact views and PMOVES.AI persona dashboards for quick jumps into curated notes or podcasts.
4. **Persona-aware prompts**
   * Let PMOVES.AI route persona-specific prompts to either DoX pipelines (for extraction/tagging) or Notebook (for summarization/podcast) based on capability tags.

### Pillar E — Governance, QA & Rollout
1. **Cross-service smoke tests**
   * Add a triad smoke suite that spins up the optional Notebook service, ingests a sample artifact, validates sync, and confirms search aggregation.
2. **Documentation & runbooks**
   * Update DoX and PMOVES.AI READMEs with Notebook integration steps; add an operator runbook covering common failure points (auth mismatch, sync stuck, embedding mismatch).
3. **Phased release**
   * Internal beta with feature flags → limited PMOVES.AI persona rollout → general availability with telemetry guardrails.
4. **Feedback loop**
   * Establish a shared backlog triage (GitHub discussions or Notion) so improvements discovered in one system feed the others (e.g., new Notebook transformation powering DoX export).

## 4. Sequence Overview

1. **Alignment sprint** – Confirm topology, env vars, and persona requirements with PMOVES.AI stakeholders.
2. **Infrastructure sprint** – Deliver compose updates, `/config` exposure, and secret wiring.
3. **Data handshake sprint** – Ship artifact mirror service, status sync, and webhook events.
4. **Experience sprint** – Implement hybrid search, UI flags, and CLI updates.
5. **Rollout sprint** – Finalize smoke tests, docs, and phased enablement.

## 5. Success Metrics

* Time-to-context: minutes from DoX ingestion complete to Notebook source ready (target < 3 minutes).
* Adoption: percentage of PMOVES.AI personas using Notebook-enhanced flows per week.
* Reliability: <1% Notebook sync failures per 100 ingests, auto-retriable.
* Traceability: 100% of Notebook responses include DoX citation metadata.

This integrated plan ensures PMOVES-DoX, Pmoves-open-notebook, and PMOVES.AI operate as a cohesive triad, enriching each other while preserving modular ownership.
