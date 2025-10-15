from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - supabase client optional during tests
    from supabase import Client, ClientOptions, create_client  # type: ignore
except Exception:  # pragma: no cover - package may be absent in local/offline envs
    Client = Any  # type: ignore
    ClientOptions = Any  # type: ignore
    create_client = None  # type: ignore


LOGGER = logging.getLogger(__name__)


class SupabaseUnavailable(RuntimeError):
    """Raised when Supabase credentials or SDK are missing."""


class SupabaseDatabase:
    """Supabase-backed implementation mirroring ExtendedDatabase."""

    def __init__(
        self,
        url: Optional[str] = None,
        key: Optional[str] = None,
        schema: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        if create_client is None:
            raise SupabaseUnavailable(
                "supabase client library not available; install `supabase` and retry"
            )

        self.url = url or os.getenv("SUPABASE_URL")
        self.key = (
            key
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )
        if not self.url or not self.key:
            raise SupabaseUnavailable("Supabase credentials (URL/key) are not configured")

        supabase_schema = schema or os.getenv("SUPABASE_SCHEMA", "public")
        client_options = ClientOptions(schema=supabase_schema) if ClientOptions else None
        try:
            self.client: Client = create_client(self.url, self.key, options=client_options)  # type: ignore[arg-type]
        except Exception as exc:  # pragma: no cover - network/credential failures
            raise SupabaseUnavailable(f"Unable to initialize Supabase client: {exc}") from exc

        self.timeout = (
            int(timeout)
            if timeout is not None
            else int(os.getenv("SUPABASE_TIMEOUT", "10"))
        )

    # ------------------------------------------------------------------ helpers
    def _table(self, name: str):
        return self.client.table(name)

    def _run(self, query, *, operation: str) -> List[Dict[str, Any]]:
        try:
            response = query.execute()
        except Exception as exc:
            raise RuntimeError(f"Supabase {operation} failed: {exc}") from exc
        error = getattr(response, "error", None)
        if error:
            raise RuntimeError(f"Supabase {operation} error: {error}")
        data = getattr(response, "data", None)
        if data is None:
            return []
        if isinstance(data, list):
            return data
        return [data]

    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # ----------------------------------------------------------------- mutations
    def add_artifact(self, artifact: Dict) -> str:
        self._run(
            self._table("artifacts").upsert(artifact, on_conflict="id"),
            operation="add_artifact",
        )
        return artifact["id"]

    def add_fact(self, fact: Dict) -> None:
        payload = {**fact, "metrics": fact.get("metrics", {})}
        self._run(self._table("facts").upsert(payload, on_conflict="id"), operation="add_fact")

    def add_evidence(self, evidence: Dict) -> None:
        payload = evidence.copy()
        if isinstance(payload.get("coordinates"), (dict, list)):
            payload.setdefault("coordinates", payload["coordinates"])
        if "full_data" in payload and payload["full_data"] is None:
            payload.pop("full_data", None)
        self._run(
            self._table("evidence").upsert(payload, on_conflict="id"),
            operation="add_evidence",
        )

    def add_document(self, doc: Dict) -> str:
        self._run(self._table("documents").upsert(doc, on_conflict="id"), operation="add_document")
        return doc["id"]

    def add_section(self, section: Dict) -> None:
        self._run(self._table("document_sections").upsert(section, on_conflict="id"), operation="add_section")

    def add_table(self, table: Dict) -> None:
        self._run(self._table("document_tables").upsert(table, on_conflict="id"), operation="add_table")

    def add_api(self, api: Dict) -> None:
        payload = api.copy()
        if isinstance(payload.get("tags"), list):
            payload["tags"] = payload["tags"]
        self._run(self._table("api_endpoints").upsert(payload, on_conflict="id"), operation="add_api")

    def add_log(self, log: Dict) -> None:
        payload = log.copy()
        if isinstance(payload.get("attrs"), (dict, list)):
            payload["attrs"] = payload["attrs"]
        self._run(self._table("log_entries").upsert(payload, on_conflict="id"), operation="add_log")

    def add_tag(self, tag: Dict) -> None:
        self._run(self._table("tags").upsert(tag, on_conflict="id"), operation="add_tag")

    def save_tag_prompt(
        self,
        document_id: str,
        prompt_text: str,
        examples: Optional[list] = None,
        author: Optional[str] = None,
    ) -> str:
        prompt_id = str(uuid.uuid4())
        payload = {
            "id": prompt_id,
            "document_id": document_id,
            "prompt_text": prompt_text,
            "examples": examples,
            "created_at": self._now_iso(),
            "author": author,
        }
        self._run(self._table("tag_prompts").insert(payload), operation="save_tag_prompt")
        return prompt_id

    # ------------------------------------------------------------------- queries
    def get_facts(self, report_week: Optional[str] = None) -> List[Dict]:
        query = self._table("facts").select("*")
        if report_week:
            query = query.eq("report_week", report_week)
        rows = self._run(query, operation="get_facts")
        for row in rows:
            metrics = row.get("metrics")
            if isinstance(metrics, str):
                try:
                    row["metrics"] = json.loads(metrics)
                except Exception:
                    row["metrics"] = {}
        return rows

    def get_evidence(self, evidence_id: str) -> Optional[Dict]:
        rows = self._run(
            self._table("evidence").select("*").eq("id", evidence_id),
            operation="get_evidence",
        )
        return rows[0] if rows else None

    def get_all_evidence(self) -> List[Dict]:
        return self._run(self._table("evidence").select("*"), operation="get_all_evidence")

    def get_artifacts(self) -> List[Dict]:
        return self._run(self._table("artifacts").select("*"), operation="get_artifacts")

    def reset_search_chunks(self) -> None:
        try:
            self._run(
                self._table("search_chunks").delete().neq("id", None),
                operation="reset_search_chunks",
            )
        except Exception as exc:
            raise RuntimeError(f"Supabase reset_search_chunks failed: {exc}") from exc

    def store_search_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        if not chunks:
            return
        rows: List[Dict[str, Any]] = []
        for chunk in chunks:
            embedding = chunk.get("embedding")
            if embedding is None:
                continue
            if not isinstance(embedding, list):
                embedding = list(embedding)
            meta = chunk.get("meta") or {}
            rows.append(
                {
                    "id": chunk.get("id"),
                    "document_id": chunk.get("document_id")
                    or meta.get("artifact_id")
                    or meta.get("document_id"),
                    "source_type": chunk.get("source_type") or meta.get("type"),
                    "chunk_index": chunk.get("chunk_index"),
                    "text": chunk.get("text"),
                    "meta": meta,
                    "embedding": embedding,
                }
            )
        if not rows:
            return
        self._run(
            self._table("search_chunks").upsert(rows, on_conflict="id"),
            operation="store_search_chunks",
        )

    def list_documents(self, type: Optional[str] = None) -> List[Dict]:
        query = self._table("documents").select("*")
        if type:
            query = query.eq("type", type)
        return self._run(query, operation="list_documents")

    def list_logs(
        self,
        level: Optional[str] = None,
        code: Optional[str] = None,
        q: Optional[str] = None,
        ts_from: Optional[str] = None,
        ts_to: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> List[Dict]:
        query = self._table("log_entries").select("*")
        if level:
            query = query.eq("level", level)
        if code:
            query = query.eq("code", code)
        if document_id:
            query = query.eq("document_id", document_id)
        rows = self._run(query, operation="list_logs")

        def _matches(row: Dict) -> bool:
            msg = (row.get("message") or "").lower()
            if q and q.lower() not in msg:
                return False
            if not (ts_from or ts_to):
                return True
            ts_value = row.get("ts")
            if not ts_value:
                return False
            try:
                parsed = datetime.fromisoformat(ts_value.replace("Z", "+00:00"))
            except Exception:
                return False
            if ts_from:
                try:
                    if parsed < datetime.fromisoformat(ts_from.replace("Z", "+00:00")):
                        return False
                except Exception:
                    pass
            if ts_to:
                try:
                    if parsed > datetime.fromisoformat(ts_to.replace("Z", "+00:00")):
                        return False
                except Exception:
                    pass
            return True

        return [row for row in rows if _matches(row)]

    def list_apis(
        self,
        tag: Optional[str] = None,
        method: Optional[str] = None,
        path_like: Optional[str] = None,
    ) -> List[Dict]:
        query = self._table("api_endpoints").select("*")
        if method:
            query = query.eq("method", method.upper())
        rows = self._run(query, operation="list_apis")
        out: List[Dict] = []
        for row in rows:
            tags = row.get("tags")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = []
            if tag and tag not in (tags or []):
                continue
            if path_like and path_like not in (row.get("path") or ""):
                continue
            row["tags"] = tags or []
            out.append(row)
        return out

    def list_tags(self, document_id: Optional[str] = None, q: Optional[str] = None) -> List[Dict]:
        query = self._table("tags").select("*")
        if document_id:
            query = query.eq("document_id", document_id)
        rows = self._run(query, operation="list_tags")
        out: List[Dict] = []
        for row in rows:
            tag_value = row.get("tag") or ""
            if q and q.lower() not in tag_value.lower():
                continue
            out.append(row)
        return out

    def list_tag_prompt_history(self, document_id: str, limit: int = 20) -> List[Dict]:
        rows = self._run(
            self._table("tag_prompts")
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(limit),
            operation="list_tag_prompt_history",
        )
        return rows

    def get_latest_tag_prompt(self, document_id: str) -> Optional[Dict]:
        rows = self._run(
            self._table("tag_prompts")
            .select("*")
            .eq("document_id", document_id)
            .order("created_at", desc=True)
            .limit(1),
            operation="get_latest_tag_prompt",
        )
        return rows[0] if rows else None

    def list_log_messages(self, document_id: str) -> List[str]:
        rows = self._run(
            self._table("log_entries").select("message").eq("document_id", document_id),
            operation="list_log_messages",
        )
        return [row["message"] for row in rows if row.get("message")]

    def reset(self) -> None:
        for table in (
            "evidence",
            "facts",
            "tags",
            "log_entries",
            "api_endpoints",
            "document_tables",
            "document_sections",
            "documents",
            "artifacts",
            "tag_prompts",
        ):
            try:
                self._run(self._table(table).delete().neq("id", None), operation=f"reset_{table}")
            except Exception as exc:  # pragma: no cover - avoid hard failure during cleanup
                LOGGER.warning("Supabase reset skipped for %s: %s", table, exc)
