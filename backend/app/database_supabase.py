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

    def update_artifact(self, artifact_id: str, **fields: Any) -> None:
        """Update an artifact's fields, merging extras if provided."""
        extras = fields.pop("extras", None)

        # If extras provided, fetch current and merge
        if extras is not None:
            rows = self._run(
                self._table("artifacts").select("extras").eq("id", artifact_id),
                operation="get_artifact_extras",
            )
            if rows:
                current_extras = rows[0].get("extras") or {}
                if isinstance(current_extras, str):
                    try:
                        current_extras = json.loads(current_extras)
                    except json.JSONDecodeError:
                        current_extras = {}
                current_extras.update(extras)
                fields["extras"] = current_extras
            else:
                fields["extras"] = extras

        if not fields:
            return

        self._run(
            self._table("artifacts").update(fields).eq("id", artifact_id),
            operation="update_artifact",
        )

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
        # Handle tags_json -> tags mapping (SQLite uses tags_json, Supabase uses tags)
        if "tags_json" in payload:
            tags_value = payload.pop("tags_json")
            if tags_value is not None:
                # tags_json is stored as JSON string, parse it for JSONB column
                if isinstance(tags_value, str):
                    try:
                        payload["tags"] = json.loads(tags_value)
                    except json.JSONDecodeError:
                        payload["tags"] = []
                else:
                    payload["tags"] = tags_value
        if isinstance(payload.get("tags"), list):
            payload["tags"] = payload["tags"]
        self._run(self._table("api_endpoints").upsert(payload, on_conflict="id"), operation="add_api")

    def add_log(self, log: Dict) -> None:
        payload = log.copy()
        # Handle attrs_json -> attrs mapping (SQLite uses attrs_json, Supabase uses attrs)
        if "attrs_json" in payload:
            attrs_value = payload.pop("attrs_json")
            if attrs_value is not None:
                payload["attrs"] = attrs_value
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

    def store_entities(self, document_id: str, entities: List[Dict]) -> None:
        self._run(
            self._table("document_entities").delete().eq("document_id", document_id),
            operation="clear_entities",
        )
        if not entities:
            return
        rows = []
        for entity in entities:
            rows.append(
                {
                    "id": entity.get("id") or str(uuid.uuid4()),
                    "document_id": document_id,
                    "label": entity.get("label"),
                    "text": entity.get("text"),
                    "start_char": entity.get("start_char"),
                    "end_char": entity.get("end_char"),
                    "page": entity.get("page"),
                    "context": entity.get("context"),
                    "source_index": entity.get("source_index"),
                }
            )
        self._run(
            self._table("document_entities").insert(rows),
            operation="store_entities",
        )

    def store_summary(self, summary: Dict) -> str:
        payload = {
            "id": summary.get("id") or str(uuid.uuid4()),
            "scope": summary.get("scope", "workspace"),
            "scope_key": summary.get("scope_key", summary.get("scope", "workspace")),
            "style": summary.get("style", "bullet"),
            "provider": summary.get("provider"),
            "prompt": summary.get("prompt"),
            "summary_text": summary.get("summary_text", ""),
            "artifact_ids": summary.get("artifact_ids", []),
            "evidence_ids": summary.get("evidence_ids", []),
            "created_at": summary.get("created_at") or self._now_iso(),
        }
        self._run(
            self._table("summaries").upsert(payload, on_conflict="id"),
            operation="store_summary",
        )
        return payload["id"]

    def get_summary(self, scope_key: str, style: str) -> Optional[Dict]:
        rows = self._run(
            self._table("summaries")
            .select("*")
            .eq("scope_key", scope_key)
            .eq("style", style)
            .order("created_at", desc=True)
            .limit(1),
            operation="get_summary",
        )
        if not rows:
            return None
        return self._coerce_summary(rows[0])

    def list_summaries(
        self,
        *,
        scope: Optional[str] = None,
        style: Optional[str] = None,
    ) -> List[Dict]:
        query = self._table("summaries").select("*")
        if scope:
            query = query.eq("scope", scope)
        if style:
            query = query.eq("style", style)
        rows = self._run(
            query.order("created_at", desc=True),
            operation="list_summaries",
        )
        return [self._coerce_summary(row) for row in rows]

    def store_structure(self, document_id: str, structure: Optional[Dict]) -> None:
        if structure is None:
            self._run(
                self._table("document_structure").delete().eq("document_id", document_id),
                operation="clear_structure",
            )
            return
        payload = {
            "document_id": document_id,
            "hierarchy": structure,
        }
        self._run(
            self._table("document_structure").upsert(payload, on_conflict="document_id"),
            operation="store_structure",
        )

    def store_metric_hits(self, document_id: str, metrics: List[Dict]) -> None:
        self._run(
            self._table("document_metric_hits").delete().eq("document_id", document_id),
            operation="clear_metric_hits",
        )
        if not metrics:
            return
        rows = []
        for metric in metrics:
            rows.append(
                {
                    "id": metric.get("id") or str(uuid.uuid4()),
                    "document_id": document_id,
                    "type": metric.get("type"),
                    "value": metric.get("value"),
                    "context": metric.get("context"),
                    "position": metric.get("position"),
                    "page": metric.get("page"),
                    "source_index": metric.get("source_index"),
                }
            )
        self._run(
            self._table("document_metric_hits").insert(rows),
            operation="store_metric_hits",
        )

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

    def list_entities(self, document_id: Optional[str] = None, label: Optional[str] = None) -> List[Dict]:
        query = self._table("document_entities").select("*")
        if document_id:
            query = query.eq("document_id", document_id)
        if label:
            query = query.eq("label", label)
        return self._run(query, operation="list_entities")

    def get_structure(self, document_id: str) -> Optional[Dict]:
        rows = self._run(
            self._table("document_structure").select("*").eq("document_id", document_id),
            operation="get_structure",
        )
        if not rows:
            return None
        row = rows[0]
        hierarchy = row.get("hierarchy") or row.get("hierarchy_json")
        if isinstance(hierarchy, str):
            try:
                return json.loads(hierarchy)
            except Exception:
                return None
        if isinstance(hierarchy, dict):
            return hierarchy
        return None

    def list_metric_hits(self, document_id: Optional[str] = None, metric_type: Optional[str] = None) -> List[Dict]:
        query = self._table("document_metric_hits").select("*")
        if document_id:
            query = query.eq("document_id", document_id)
        if metric_type:
            query = query.eq("type", metric_type)
        return self._run(query, operation="list_metric_hits")

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
            "summaries",
        ):
            try:
                self._run(self._table(table).delete().neq("id", None), operation=f"reset_{table}")
            except Exception as exc:  # pragma: no cover - avoid hard failure during cleanup
                LOGGER.warning("Supabase reset skipped for %s: %s", table, exc)

    def _coerce_summary(self, row: Dict[str, Any]) -> Dict[str, Any]:
        artifact_ids = row.get("artifact_ids")
        if isinstance(artifact_ids, str):
            try:
                artifact_ids = json.loads(artifact_ids)
            except Exception:
                artifact_ids = [artifact_ids]
        evidence_ids = row.get("evidence_ids")
        if isinstance(evidence_ids, str):
            try:
                evidence_ids = json.loads(evidence_ids)
            except Exception:
                evidence_ids = [evidence_ids]
        return {
            "id": row.get("id"),
            "scope": row.get("scope"),
            "scope_key": row.get("scope_key"),
            "style": row.get("style"),
            "provider": row.get("provider"),
            "prompt": row.get("prompt"),
            "summary_text": row.get("summary_text", ""),
            "artifact_ids": artifact_ids or [],
            "evidence_ids": evidence_ids or [],
            "created_at": row.get("created_at", self._now_iso()),
        }

    # ----------------------------------------------------------------- Cipher / Memory
    def add_memory(self, category: str, content: Dict, context: Optional[Dict] = None) -> str:
        payload = {
            "category": category,
            "content": content,
            "context": context or {},
            "created_at": self._now_iso(),
        }
        # If accessing the native supabase client returning the inserted row:
        # data = self._table("cipher_memory").insert(payload).execute()
        # But we use the helper _run which returns a list of rows if configured correctly, 
        # or we might need to fetch the ID depending on the client config.
        # Assuming defaults that return inserted data:
        rows = self._run(self._table("cipher_memory").insert(payload).select(), operation="add_memory")
        if rows and len(rows) > 0:
            return rows[0]["id"]
        return ""

    def search_memory(
        self, 
        category: Optional[str] = None, 
        limit: int = 10, 
        q: Optional[str] = None
    ) -> List[Dict]:
        query = self._table("cipher_memory").select("*")
        if category:
            query = query.eq("category", category)
        
        # Simple text search on the JSONB content if 'q' is provided is hard without pg_trgm validation
        # For now, we return recent items. Real semantic search requires the vector extension.
        query = query.order("created_at", desc=True).limit(limit)
        
        return self._run(query, operation="search_memory")

    def get_user_prefs(self, user_id: str) -> Dict:
        rows = self._run(
            self._table("user_prefs").select("*").eq("user_id", user_id), 
            operation="get_user_prefs"
        )
        if rows:
            return rows[0].get("preferences", {})
        return {}

    def set_user_pref(self, user_id: str, key: str, value: Any) -> None:
        # First get existing
        existing = self.get_user_prefs(user_id)
        existing[key] = value
        
        payload = {
            "user_id": user_id,
            "preferences": existing,
            "updated_at": self._now_iso()
        }
        self._run(self._table("user_prefs").upsert(payload), operation="set_user_pref")

    def register_skill(
        self, 
        name: str, 
        description: str, 
        parameters: Dict, 
        workflow_def: Dict,
        enabled: bool = True
    ) -> str:
        payload = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "workflow_def": workflow_def,
            "enabled": enabled,
            "created_at": self._now_iso()
        }
        # Upsert by name if possible, but standard upsert needs unique constraint/index
        # We assume 'name' has a unique constraint in schema
        rows = self._run(
            self._table("skills_registry").upsert(payload, on_conflict="name").select(), 
            operation="register_skill"
        )
        if rows:
            return rows[0]["id"]
        return ""

    def list_skills(self, enabled_only: bool = True) -> List[Dict]:
        query = self._table("skills_registry").select("*")
        if enabled_only:
            query = query.eq("enabled", True)
        return self._run(query, operation="list_skills")
