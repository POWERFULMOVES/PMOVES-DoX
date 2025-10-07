# Supabase Migration Plan

## Overview
Migrate PMOVES-DoX backend persistence from the local SQLite layer (`ExtendedDatabase`) to Supabase (managed Postgres + `pgvector`) while keeping feature parity for ingestion, tagging, search, and HRM metrics. The migration must preserve existing APIs and enable advanced LangExtract/Docling workflows across heterogeneous hardware (RTX 50-series, Jetson Orin, mobile edge devices) by delegating storage and vector math to Supabase where possible.

## Environment & Tooling
- **Credentials**: define `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` as env vars (service key stored outside git; use local `.env` only).
- **SDK**: adopt `supabase-py` (async) or `postgrest` + `gotrue` clients for Python 3.11; wrap in a thin adapter class to avoid leaking SDK types through the app.
- **Vector Support**: enable the Supabase `pgvector` extension, with embedding columns sized for Docling + LangExtract vectors (e.g., 384-d for MiniLM, 1024-d for larger models).
- **Local stack**: `docker-compose.supabase.yml` spins up `supabase-db` (`supabase/postgres:15.14.1.013` + pgvector) and `supabase-rest` (PostgREST). Boot with `docker compose -f docker-compose.supabase.yml up -d` and point the backend at `SUPABASE_URL=http://localhost:65421` with disposable keys (`SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoic2VydmljZV9yb2xlIiwiaXNzIjoic3VwYWJhc2UiLCJpYXQiOjAsImV4cCI6MjUzNDAyMzAwNzk5fQ.HPvdDMnzeFHOYHVnKEwec71btVPz2lZ5xgiSSAQgGOU`, `SUPABASE_ANON_KEY=anon`).

## Schema Mapping
| SQLite Table | Supabase Target | Notes |
|--------------|-----------------|-------|
| `artifact`, `document`, `section`, `doc_table` | `artifacts`, `documents`, `document_sections`, `document_tables` | Consolidate joins with foreign keys + cascade deletes. |
| `apiendpoint`, `logentry`, `tagrow` | `api_endpoints`, `log_entries`, `tags` | Normalize JSON blobs into JSONB; add indexes on (`method`, `path`), (`level`, `code`, `ts`), (`tag`). |
| `fact`, `evidence` | `facts`, `evidence` | Store metrics as JSONB; use Supabase storage bucket for large artifacts if needed. |
| Search chunks | `search_chunks` | Include `embedding vector(384)` column; store metadata JSON for deeplinks. |
| HRM metrics | `hrm_runs`, `hrm_metrics` | Track halting stats, accuracy, latency per run. |

Define the schema with SQL migration scripts checked into `backend/migrations/supabase/`. Example snippet:
```sql
create extension if not exists "vector";
create table if not exists search_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id text,
  chunk_index int,
  embedding vector(384),
  meta jsonb,
  created_at timestamptz default now()
);
create index if not exists idx_search_chunks_embedding on search_chunks using ivfflat (embedding vector_cosine_ops);
```

## Data Access Layer
1. Create `backend/app/database_supabase.py` with `SupabaseDatabase` mirroring the `ExtendedDatabase` API.
2. Inject via env switch `DB_BACKEND=supabase`. Default remains SQLite for local/offline.
3. Implement helper methods:
   - `upsert_artifact_with_document(...)` using RPC or multi-statement transactions.
   - `list_logs`, `list_tags` via filtered PostgREST queries; respect pagination for large datasets.
   - `store_search_chunk_embeddings(chunks)` batching embeddings into Supabase inserts.
4. Provide graceful fallback when Supabase is unreachable (raise 503; surface in health endpoint).

## Ingestion & Search Workflow Adjustments
- During ingest, continue writing interim artifacts locally for Docling/CHR, but send structured metadata + embeddings to Supabase.
- Update `/search/rebuild` to:
  1. Recompute embeddings with SentenceTransformers (GPU-accelerated when available).
  2. Push vectors to Supabase `search_chunks`.
  3. Optionally cache FAISS locally for offline mode.
- For LangExtract governance, persist prompts, history, and HRM runs in Supabase tables to support multi-device collaboration.

## Migration Steps
1. **Bootstrap**: run Supabase migrations via `supabase db push` or `psql`. Verify extensions.
2. **Backfill**: add a CLI script `python -m tools.backfill_supabase --from-sqlite path/to/db.sqlite3` to copy existing rows (artifacts, documents, logs, tags, search chunks) using Supabase bulk inserts.
3. **Dual-Write Phase**: behind feature flag, write to both SQLite and Supabase while validating parity.
4. **Cutover**: toggle `DB_BACKEND=supabase` in `.env`/compose once confidence is high; disable SQLite writes except for tests.
5. **Testing**: update smoke + CI workflows to spin up Supabase (local docker) and exercise migration paths.

## Operational Considerations
- **Secrets**: use `.env.supabase` locally; rely on deployment secret manager in production.
- **Rate Limits**: batch vector inserts (e.g., 100 rows per call) to respect Supabase quotas.
- **Offline Mode**: keep SQLite as a fallback when Supabase unavailable, but warn via `/config` endpoint.
- **Monitoring**: add Supabase health check to `/config` response; track latency for search queries vs. local FAISS.

## Timeline (Draft)
- Week 1: finalize schema, generate migrations, implement Supabase client adapter.
- Week 2: dual-write ingest/search, add backfill tool, extend smoke tests.
- Week 3: execute data migration, cut over staging, monitor performance, document operational playbook.

## Validation Checklist
- `docker compose -f docker-compose.supabase.yml up -d` (Supabase services)
- `python tools/backfill_supabase.py --from-sqlite backend/db.sqlite3 --reset`
- Set `DB_BACKEND=supabase` (or `SUPABASE_DUAL_WRITE=true`) and run `python -m pytest backend/tests`.
- Exercise `/search/rebuild` to confirm embeddings sync to Supabase (`search_chunks` table populated).
