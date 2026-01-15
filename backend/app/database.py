"""SQLite database models and operations for PMOVES-DoX.

This module provides SQLModel-based database schemas for documents,
artifacts, evidence, facts, and other application data. It includes
both core tables (Artifact, Evidence, Fact) and extended tables
(Document, APIEndpoint, LogEntry, etc.) for advanced features.

Classes:
    Artifact: Uploaded file metadata
    Evidence: Extracted content chunks with coordinates
    Fact: Structured data extracted from evidence
    SummaryRow: Generated summaries with scope/style
    Document: Extended document metadata
    APIEndpoint: Discovered API endpoint definitions
    LogEntry: System and application logs
    TagRow: Extracted tags from documents
    Database: Core database operations (SQLite)
    ExtendedDatabase: Extended database with additional methods
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from sqlmodel import SQLModel, Field, create_engine, Session, select, delete, text


class Artifact(SQLModel, table=True):
    """Uploaded file metadata.

    Attributes:
        id: Unique artifact identifier
        filename: Original filename
        filepath: Path to stored file
        filetype: File extension or MIME type
        report_week: Optional reporting week identifier
        status: Processing status (queued, processing, completed, error)
        source_url: URL if file was downloaded
        extra_json: Additional metadata as JSON string
    """
    id: str = Field(primary_key=True)
    filename: str
    filepath: str
    filetype: str
    report_week: Optional[str] = None
    status: Optional[str] = None
    source_url: Optional[str] = None
    extra_json: Optional[str] = None


class Evidence(SQLModel, table=True):
    """Extracted content chunk from a document.

    Attributes:
        id: Unique evidence identifier
        artifact_id: Parent artifact reference
        locator: Page/section reference (e.g., "page 5")
        preview: Text preview of the content
        content_type: MIME type of original content
        coordinates_json: Bounding box coordinates as JSON
        full_data_json: Complete extracted data as JSON
    """
    id: str = Field(primary_key=True)
    artifact_id: str
    locator: Optional[str] = None
    preview: Optional[str] = None
    content_type: Optional[str] = None
    coordinates_json: Optional[str] = None
    full_data_json: Optional[str] = None


class Fact(SQLModel, table=True):
    """Structured metric extracted from document evidence.

    Attributes:
        id: Unique fact identifier
        artifact_id: Parent artifact reference
        report_week: Optional reporting week identifier
        entity: Named entity associated with the metric
        metrics_json: Metric data as JSON string
        evidence_id: Source evidence reference
    """
    id: str = Field(primary_key=True)
    artifact_id: str
    report_week: Optional[str] = None
    entity: Optional[str] = None
    metrics_json: str
    evidence_id: Optional[str] = None


class SummaryRow(SQLModel, table=True):
    """Generated document summary with configurable scope and style.

    Attributes:
        id: Unique summary identifier
        scope: Summary scope (workspace, document, custom)
        scope_key: Scope-specific key for grouping
        style: Summary style (bullet, detailed, executive)
        provider: LLM provider used for generation
        prompt: Optional custom prompt used
        summary_text: Generated summary content
        artifact_ids_json: Referenced artifact IDs as JSON
        evidence_ids_json: Referenced evidence IDs as JSON
        created_at: ISO timestamp of generation
    """
    __tablename__ = "summaries"

    id: str = Field(primary_key=True)
    scope: str
    scope_key: str
    style: str
    provider: Optional[str] = None
    prompt: Optional[str] = None
    summary_text: str
    artifact_ids_json: Optional[str] = None
    evidence_ids_json: Optional[str] = None
    created_at: str


class Database:
    """SQLite-backed database with SQLModel ORM.

    Provides CRUD operations for artifacts, evidence, facts, and summaries.
    Handles schema migrations for backward compatibility.

    Attributes:
        db_url: SQLAlchemy database URL
        engine: SQLAlchemy engine instance
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the SQLite database.

        Args:
            db_path: Path to SQLite file. Defaults to DB_PATH env var or "db.sqlite3".
        """
        db_path = db_path or os.getenv("DB_PATH", "db.sqlite3")
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)
        self._ensure_fact_evidence_column()
        self._ensure_artifact_columns()

    def _ensure_fact_evidence_column(self) -> None:
        """Ensure the fact table has the evidence_id column for backward compatibility."""
        with self.engine.connect() as conn:
            columns = conn.exec_driver_sql("PRAGMA table_info(fact)").fetchall()
            column_names = {row[1] for row in columns}
            if "evidence_id" not in column_names:
                conn.exec_driver_sql("ALTER TABLE fact ADD COLUMN evidence_id TEXT")

    def _ensure_artifact_columns(self) -> None:
        """Add optional artifact columns when migrating from older versions."""
        with self.engine.connect() as conn:
            columns = conn.exec_driver_sql("PRAGMA table_info(artifact)").fetchall()
            column_names = {row[1] for row in columns}
            if "source_url" not in column_names:
                conn.exec_driver_sql("ALTER TABLE artifact ADD COLUMN source_url TEXT")
            if "extra_json" not in column_names:
                conn.exec_driver_sql("ALTER TABLE artifact ADD COLUMN extra_json TEXT")

    def add_artifact(self, artifact: Dict) -> str:
        """Add a new artifact to the database.

        Args:
            artifact: Dictionary containing artifact metadata.

        Returns:
            The artifact ID.
        """
        payload = dict(artifact)
        extras = payload.pop("extras", None) or payload.pop("metadata", None)
        if extras is not None:
            payload["extra_json"] = json.dumps(extras, ensure_ascii=False)
        with Session(self.engine) as s:
            row = Artifact(**payload)
            s.add(row)
            s.commit()
        return payload["id"]

    def update_artifact(self, artifact_id: str, **fields: Any) -> None:
        extras = fields.pop("extras", None)
        with Session(self.engine) as s:
            row = s.get(Artifact, artifact_id)
            if not row:
                return
            for key, value in fields.items():
                if hasattr(row, key):
                    setattr(row, key, value)
            if extras is not None:
                base: Dict[str, Any]
                if row.extra_json:
                    try:
                        base = json.loads(row.extra_json)
                    except json.JSONDecodeError:
                        base = {}
                else:
                    base = {}
                base.update(extras)
                row.extra_json = json.dumps(base, ensure_ascii=False)
            s.add(row)
            s.commit()

    def add_fact(self, fact: Dict):
        metrics_json = json.dumps(fact.get("metrics", {}), ensure_ascii=False)
        row = Fact(
            id=fact["id"],
            artifact_id=fact.get("artifact_id", ""),
            report_week=fact.get("report_week"),
            entity=fact.get("entity"),
            metrics_json=metrics_json,
            evidence_id=fact.get("evidence_id"),
        )
        with Session(self.engine) as s:
            s.add(row)
            s.commit()

    def add_evidence(self, evidence: Dict):
        row = Evidence(
            id=evidence["id"],
            artifact_id=evidence.get("artifact_id", ""),
            locator=evidence.get("locator"),
            preview=evidence.get("preview"),
            content_type=evidence.get("content_type"),
            coordinates_json=json.dumps(evidence.get("coordinates")) if evidence.get("coordinates") is not None else None,
            full_data_json=json.dumps(evidence.get("full_data")) if evidence.get("full_data") is not None else None,
        )
        with Session(self.engine) as s:
            s.add(row)
            s.commit()

    def store_summary(self, summary: Dict) -> str:
        payload = SummaryRow(
            id=summary.get("id", str(uuid.uuid4())),
            scope=summary.get("scope", "workspace"),
            scope_key=summary.get("scope_key", summary.get("scope", "workspace")),
            style=summary.get("style", "bullet"),
            provider=summary.get("provider"),
            prompt=summary.get("prompt"),
            summary_text=summary.get("summary_text", ""),
            artifact_ids_json=json.dumps(summary.get("artifact_ids", []), ensure_ascii=False),
            evidence_ids_json=json.dumps(summary.get("evidence_ids", []), ensure_ascii=False),
            created_at=summary.get("created_at")
            or datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
        with Session(self.engine) as s:
            existing = s.get(SummaryRow, payload.id)
            if existing:
                existing.scope = payload.scope
                existing.scope_key = payload.scope_key
                existing.style = payload.style
                existing.provider = payload.provider
                existing.prompt = payload.prompt
                existing.summary_text = payload.summary_text
                existing.artifact_ids_json = payload.artifact_ids_json
                existing.evidence_ids_json = payload.evidence_ids_json
                existing.created_at = payload.created_at
            else:
                s.add(payload)
            s.commit()
        return payload.id

    def get_summary(self, scope_key: str, style: str) -> Optional[Dict]:
        with Session(self.engine) as s:
            stmt = (
                select(SummaryRow)
                .where(SummaryRow.scope_key == scope_key)
                .where(SummaryRow.style == style)
                .order_by(SummaryRow.created_at.desc())
            )
            row = s.exec(stmt).first()
        if not row:
            return None
        return self._summary_to_dict(row)

    def list_summaries(
        self,
        *,
        scope: Optional[str] = None,
        style: Optional[str] = None,
    ) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(SummaryRow)
            if scope:
                stmt = stmt.where(SummaryRow.scope == scope)
            if style:
                stmt = stmt.where(SummaryRow.style == style)
            stmt = stmt.order_by(SummaryRow.created_at.desc())
            rows = s.exec(stmt).all()
        return [self._summary_to_dict(r) for r in rows]

    def _summary_to_dict(self, row: SummaryRow) -> Dict:
        return {
            "id": row.id,
            "scope": row.scope,
            "scope_key": row.scope_key,
            "style": row.style,
            "provider": row.provider,
            "prompt": row.prompt,
            "summary_text": row.summary_text,
            "artifact_ids": json.loads(row.artifact_ids_json or "[]"),
            "evidence_ids": json.loads(row.evidence_ids_json or "[]"),
            "created_at": row.created_at,
        }

    def get_facts(self, report_week: Optional[str] = None) -> List[Dict]:
        with Session(self.engine) as s:
            if report_week:
                rows = s.exec(select(Fact).where(Fact.report_week == report_week)).all()
            else:
                rows = s.exec(select(Fact)).all()
        out: List[Dict] = []
        for f in rows:
            out.append(
                {
                    "id": f.id,
                    "artifact_id": f.artifact_id,
                    "report_week": f.report_week,
                    "entity": f.entity,
                    "metrics": json.loads(f.metrics_json or "{}"),
                    "evidence_id": f.evidence_id,
                }
            )
        return out

    def get_evidence(self, evidence_id: str) -> Optional[Dict]:
        with Session(self.engine) as s:
            e = s.get(Evidence, evidence_id)
        if not e:
            return None
        return {
            "id": e.id,
            "artifact_id": e.artifact_id,
            "locator": e.locator,
            "preview": e.preview,
            "content_type": e.content_type,
            "coordinates": json.loads(e.coordinates_json) if e.coordinates_json else None,
            "full_data": json.loads(e.full_data_json) if e.full_data_json else None,
        }

    def get_all_evidence(self) -> List[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(Evidence)).all()
        out: List[Dict] = []
        for e in rows:
            out.append(
                {
                    "id": e.id,
                    "artifact_id": e.artifact_id,
                    "locator": e.locator,
                    "preview": e.preview,
                    "content_type": e.content_type,
                    "coordinates": json.loads(e.coordinates_json) if e.coordinates_json else None,
                    "full_data": json.loads(e.full_data_json) if e.full_data_json else None,
                }
            )
        return out

    def get_artifacts(self) -> List[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(Artifact)).all()
        items: List[Dict] = []
        for row in rows:
            data = row.model_dump()
            extra_payload = data.pop("extra_json", None)
            if extra_payload:
                try:
                    data["extras"] = json.loads(extra_payload)
                except json.JSONDecodeError:
                    data["extras"] = extra_payload
            else:
                data["extras"] = None
            items.append(data)
        return items

    def reset(self):
        with Session(self.engine) as s:
            s.exec(delete(SummaryRow))
            s.exec(text("DELETE FROM evidence"))
            s.exec(text("DELETE FROM fact"))
            s.exec(text("DELETE FROM artifact"))
            s.exec(delete(DocumentEntity))
            s.exec(delete(DocumentMetricHit))
            s.exec(delete(DocumentStructureRow))
            s.commit()


    def reset_search_chunks(self) -> None:
        """No-op for SQLite backend; Supabase variant overrides."""
        return None

    def store_search_chunks(self, chunks: List[Dict]) -> None:
        return None

# -------- Extended schema for LMS_DOCS --------

class Document(SQLModel, table=True):
    id: str = Field(primary_key=True)
    path: str
    type: str  # pdf|xml|openapi|postman
    title: str | None = None
    source: str | None = None
    created_at: str | None = None


class Section(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    order: int
    text: str
    page: int | None = None
    bbox_json: str | None = None


class DocTable(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    order: int
    table_content_json: str  # rows/cells JSON


class APIEndpoint(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    name: str | None = None
    method: str
    path: str
    summary: str | None = None
    tags_json: str | None = None
    params_json: str | None = None
    responses_json: str | None = None


class DocumentEntity(SQLModel, table=True):
    __tablename__ = "document_entities"

    id: str = Field(primary_key=True)
    document_id: str
    label: str
    text: str
    start_char: int | None = None
    end_char: int | None = None
    page: int | None = None
    entity_context: str | None = None
    source_index: int | None = None


class DocumentStructureRow(SQLModel, table=True):
    __tablename__ = "document_structure"

    document_id: str = Field(primary_key=True)
    hierarchy_json: str | None = None


class DocumentMetricHit(SQLModel, table=True):
    __tablename__ = "document_metric_hits"

    id: str = Field(primary_key=True)
    document_id: str
    type: str
    value: str | None = None
    metric_context: str | None = None
    position: int | None = None
    page: int | None = None
    source_index: int | None = None


class LogEntry(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    ts: str | None = None
    level: str | None = None
    code: str | None = None
    component: str | None = None
    message: str | None = None
    attrs_json: str | None = None


class TagRow(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    tag: str
    score: float | None = None
    source_ptr: str | None = None
    hrm_steps: int | None = None


class TagPrompt(SQLModel, table=True):
    id: str = Field(primary_key=True)
    document_id: str
    prompt_text: str
    examples_json: str | None = None
    created_at: str | None = None
    author: str | None = None



# -------- Cipher / Memory Models --------

class CipherMemory(SQLModel, table=True):
    __tablename__ = "cipher_memory"

    id: str = Field(primary_key=True)
    category: str
    content_json: str  # JSONB
    context_json: str | None = None  # JSONB
    created_at: str | None = None


class UserPref(SQLModel, table=True):
    __tablename__ = "user_prefs"

    user_id: str = Field(primary_key=True)
    preferences_json: str  # JSONB
    updated_at: str | None = None


class SkillRegistry(SQLModel, table=True):
    __tablename__ = "skills_registry"

    id: str = Field(primary_key=True)
    name: str = Field(unique=True)
    description: str
    parameters_json: str  # JSONB
    workflow_def_json: str  # JSONB
    enabled: bool = True
    created_at: str | None = None


def _ensure_extended(engine):
    SQLModel.metadata.create_all(engine)


class ExtendedDatabase(Database):
    def __init__(self, db_path: Optional[str] = None):
        super().__init__(db_path)
        _ensure_extended(self.engine)

    # ---- document helpers ----
    def add_document(self, doc: Dict) -> str:
        with Session(self.engine) as s:
            row = Document(**doc)
            s.add(row)
            s.commit()
        return doc["id"]

    def add_section(self, section: Dict):
        with Session(self.engine) as s:
            s.add(Section(**section))
            s.commit()

    def add_table(self, table: Dict):
        with Session(self.engine) as s:
            t_data = dict(table)
            if "json" in t_data:
                t_data["table_content_json"] = t_data.pop("json")
            s.add(DocTable(**t_data))
            s.commit()

    def add_api(self, api: Dict):
        with Session(self.engine) as s:
            s.add(APIEndpoint(**api))
            s.commit()

    def add_log(self, log: Dict):
        with Session(self.engine) as s:
            s.add(LogEntry(**log))
            s.commit()

    def add_tag(self, tag: Dict):
        with Session(self.engine) as s:
            s.add(TagRow(**tag))
            s.commit()

    def store_entities(self, document_id: str, entities: List[Dict]) -> None:
        with Session(self.engine) as s:
            s.exec(delete(DocumentEntity).where(DocumentEntity.document_id == document_id))
            for entity in entities:
                row = DocumentEntity(
                    id=str(entity.get("id") or uuid.uuid4()),
                    document_id=document_id,
                    label=str(entity.get("label") or ""),
                    text=str(entity.get("text") or ""),
                    start_char=entity.get("start_char"),
                    end_char=entity.get("end_char"),
                    page=entity.get("page"),
                    entity_context=entity.get("context"),
                    source_index=entity.get("source_index"),
                )
                s.add(row)
            s.commit()

    def store_structure(self, document_id: str, structure: Dict | None) -> None:
        with Session(self.engine) as s:
            s.exec(delete(DocumentStructureRow).where(DocumentStructureRow.document_id == document_id))
            if structure is not None:
                payload = DocumentStructureRow(
                    document_id=document_id,
                    hierarchy_json=json.dumps(structure, ensure_ascii=False),
                )
                s.add(payload)
            s.commit()

    def store_metric_hits(self, document_id: str, metrics: List[Dict]) -> None:
        with Session(self.engine) as s:
            s.exec(delete(DocumentMetricHit).where(DocumentMetricHit.document_id == document_id))
            for metric in metrics:
                row = DocumentMetricHit(
                    id=str(metric.get("id") or uuid.uuid4()),
                    document_id=document_id,
                    type=str(metric.get("type") or ""),
                    value=metric.get("value"),
                    metric_context=metric.get("context"),
                    position=metric.get("position"),
                    page=metric.get("page"),
                    source_index=metric.get("source_index"),
                )
                s.add(row)
            s.commit()

    def list_entities(self, document_id: str | None = None, label: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(DocumentEntity)
            if document_id:
                stmt = stmt.where(DocumentEntity.document_id == document_id)
            if label:
                stmt = stmt.where(DocumentEntity.label == label)
            rows = s.exec(stmt).all()
        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "label": r.label,
                "text": r.text,
                "start_char": r.start_char,
                "end_char": r.end_char,
                "page": r.page,
                "context": r.entity_context,
                "source_index": r.source_index,
            }
            for r in rows
        ]

    def get_structure(self, document_id: str) -> Optional[Dict]:
        with Session(self.engine) as s:
            row = s.get(DocumentStructureRow, document_id)
        if not row or not row.hierarchy_json:
            return None
        return json.loads(row.hierarchy_json)

    def list_metric_hits(self, document_id: str | None = None, metric_type: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(DocumentMetricHit)
            if document_id:
                stmt = stmt.where(DocumentMetricHit.document_id == document_id)
            if metric_type:
                stmt = stmt.where(DocumentMetricHit.type == metric_type)
            rows = s.exec(stmt).all()
        return [
            {
                "id": r.id,
                "document_id": r.document_id,
                "type": r.type,
                "value": r.value,
                "context": r.metric_context,
                "position": r.position,
                "page": r.page,
                "source_index": r.source_index,
            }
            for r in rows
        ]

    def list_logs(self, level: str | None = None, code: str | None = None, q: str | None = None,
                  ts_from: str | None = None, ts_to: str | None = None,
                  document_id: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(LogEntry)
            if level:
                stmt = stmt.where(LogEntry.level == level)
            if code:
                stmt = stmt.where(LogEntry.code == code)
            if document_id:
                stmt = stmt.where(LogEntry.document_id == document_id)
            rows = s.exec(stmt).all()
        out = []
        # parse time bounds once
        from datetime import datetime
        t_from = None
        t_to = None
        def parse_ts(sval: str | None):
            if not sval:
                return None
            # try common formats
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    return datetime.strptime(sval[:len(fmt)], fmt)
                except Exception:
                    continue
            return None
        if ts_from:
            t_from = parse_ts(ts_from)
        if ts_to:
            t_to = parse_ts(ts_to)
        for e in rows:
            # apply q filter
            if q and (q.lower() not in (e.message or '').lower()):
                continue
            # apply time window if possible
            if t_from or t_to:
                et = parse_ts(e.ts)
                if et is None:
                    # skip when we can't compare
                    pass
                else:
                    if t_from and et < t_from:
                        continue
                    if t_to and et > t_to:
                        continue
            out.append({
                "id": e.id,
                "document_id": e.document_id,
                "ts": e.ts,
                "level": e.level,
                "code": e.code,
                "component": e.component,
                "message": e.message,
                "attrs": json.loads(e.attrs_json) if e.attrs_json else None,
            })
        return out

    def list_apis(self, tag: str | None = None, method: str | None = None, path_like: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(APIEndpoint)).all()
        out = []
        for a in rows:
            if method and a.method.lower() != method.lower():
                continue
            if path_like and path_like not in a.path:
                continue
            if tag:
                tags = json.loads(a.tags_json) if a.tags_json else []
                if tag not in tags:
                    continue
            out.append({
                "id": a.id,
                "document_id": a.document_id,
                "name": a.name,
                "method": a.method,
                "path": a.path,
                "summary": a.summary,
                "tags": json.loads(a.tags_json) if a.tags_json else [],
            })
        return out

    def list_tags(self, document_id: str | None = None, q: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(TagRow)).all()
        out = []
        for t in rows:
            if document_id and t.document_id != document_id:
                continue
            if q and q.lower() not in t.tag.lower():
                continue
            # prefer stored column, fall back to legacy encoding in source_ptr
            hrm_steps = t.hrm_steps
            if hrm_steps is None and t.source_ptr and isinstance(t.source_ptr, str) and t.source_ptr.startswith("hrm-refined:steps"):
                try:
                    hrm_steps = int(t.source_ptr.replace("hrm-refined:steps", ""))
                except Exception:
                    hrm_steps = None
            item = {"id": t.id, "document_id": t.document_id, "tag": t.tag, "score": t.score, "source_ptr": t.source_ptr}
            if hrm_steps is not None:
                item["hrm_steps"] = hrm_steps
            out.append(item)
        return out

    def has_tag(self, document_id: str, tag: str) -> bool:
        with Session(self.engine) as s:
            rows = s.exec(select(TagRow).where(TagRow.document_id == document_id)).all()
        for r in rows:
            if r.tag.strip().lower() == tag.strip().lower():
                return True
        return False

    # ---- tag prompt governance ----
    def save_tag_prompt(self, document_id: str, prompt_text: str, examples: Optional[list] = None, author: Optional[str] = None) -> str:
        import json as _json
        from datetime import datetime
        row = TagPrompt(
            id=str(uuid.uuid4()),  # type: ignore
            document_id=document_id,
            prompt_text=prompt_text,
            examples_json=_json.dumps(examples) if examples is not None else None,
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
            author=author,
        )
        with Session(self.engine) as s:
            s.add(row)
            s.commit()
        return row.id

    def get_latest_tag_prompt(self, document_id: str) -> Optional[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(TagPrompt).where(TagPrompt.document_id == document_id)).all()
        if not rows:
            return None
        rows.sort(key=lambda r: r.created_at or "", reverse=True)
        r = rows[0]
        import json as _json
        return {
            "id": r.id,
            "document_id": r.document_id,
            "prompt_text": r.prompt_text,
            "examples": _json.loads(r.examples_json) if r.examples_json else None,
            "created_at": r.created_at,
            "author": r.author,
        }

    def list_tag_prompt_history(self, document_id: str, limit: int = 20) -> List[Dict]:
        with Session(self.engine) as s:
            rows = s.exec(select(TagPrompt).where(TagPrompt.document_id == document_id)).all()
        rows.sort(key=lambda r: r.created_at or "", reverse=True)
        out: List[Dict] = []
        import json as _json
        for r in rows[:limit]:
            out.append({
                "id": r.id,
                "document_id": r.document_id,
                "prompt_text": r.prompt_text,
                "examples": _json.loads(r.examples_json) if r.examples_json else None,
                "created_at": r.created_at,
                "author": r.author,
            })
        return out

    def list_documents(self, type: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(Document)
            if type:
                stmt = stmt.where(Document.type == type)
            rows = s.exec(stmt).all()
        return [r.model_dump() for r in rows]

    def list_log_messages(self, document_id: str) -> List[str]:
        with Session(self.engine) as s:
            rows = s.exec(select(LogEntry).where(LogEntry.document_id == document_id)).all()
        return [r.message for r in rows if r.message]


    # ---- Cipher / Memory Methods ----
    def add_memory(self, category: str, content: Dict, context: Optional[Dict] = None) -> str:
        mid = str(uuid.uuid4())
        row = CipherMemory(
            id=mid,
            category=category,
            content_json=json.dumps(content, ensure_ascii=False),
            context_json=json.dumps(context, ensure_ascii=False) if context else None,
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z"
        )
        with Session(self.engine) as s:
            s.add(row)
            s.commit()
        return mid

    def search_memory(
        self, 
        category: Optional[str] = None, 
        limit: int = 10, 
        q: Optional[str] = None
    ) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(CipherMemory)
            if category:
                stmt = stmt.where(CipherMemory.category == category)
            # Naive sorting by recency as we don't have vector search in SQLite here
            stmt = stmt.order_by(CipherMemory.created_at.desc()).limit(limit)
            rows = s.exec(stmt).all()
        
        results = []
        for r in rows:
            content = {}
            if r.content_json:
                try:
                    content = json.loads(r.content_json)
                except Exception:
                    pass
            # Simple in-memory filter for 'q' if provided (inefficient but works for small local DB)
            if q:
                if q.lower() not in json.dumps(content).lower():
                    continue

            results.append({
                "id": r.id,
                "category": r.category,
                "content": content,
                "context": json.loads(r.context_json) if r.context_json else {},
                "created_at": r.created_at
            })
        return results

    def get_user_prefs(self, user_id: str) -> Dict:
        with Session(self.engine) as s:
            row = s.get(UserPref, user_id)
        if row and row.preferences_json:
            return json.loads(row.preferences_json)
        return {}

    def set_user_pref(self, user_id: str, key: str, value: Any) -> None:
        with Session(self.engine) as s:
            row = s.get(UserPref, user_id)
            existing = {}
            if row and row.preferences_json:
                existing = json.loads(row.preferences_json)
            
            existing[key] = value
            
            if not row:
                row = UserPref(
                    user_id=user_id,
                    preferences_json=json.dumps(existing, ensure_ascii=False),
                    updated_at=datetime.utcnow().isoformat(timespec="seconds") + "Z"
                )
                s.add(row)
            else:
                row.preferences_json = json.dumps(existing, ensure_ascii=False)
                row.updated_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
                s.add(row)
            s.commit()

    def register_skill(
        self, 
        name: str, 
        description: str, 
        parameters: Dict, 
        workflow_def: Dict,
        enabled: bool = True
    ) -> str:
        # Pre-generate ID if needed, but for upsert logic we need to be careful
        # We'll just return the ID we find or create
        target_id = ""
        with Session(self.engine) as s:
            # Check exist first to handle 'upsert' logic
            existing = s.exec(select(SkillRegistry).where(SkillRegistry.name == name)).first()
            if existing:
                existing.description = description
                existing.parameters_json = json.dumps(parameters, ensure_ascii=False)
                existing.workflow_def_json = json.dumps(workflow_def, ensure_ascii=False)
                existing.enabled = enabled
                row = existing
                target_id = existing.id
            else:
                target_id = str(uuid.uuid4())
                row = SkillRegistry(
                    id=target_id,
                    name=name,
                    description=description,
                    parameters_json=json.dumps(parameters, ensure_ascii=False),
                    workflow_def_json=json.dumps(workflow_def, ensure_ascii=False),
                    enabled=enabled,
                    created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z"
                )
                s.add(row)
            s.commit()
        return target_id

    def list_skills(self, enabled_only: bool = True) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(SkillRegistry)
            if enabled_only:
                stmt = stmt.where(SkillRegistry.enabled == True)
            rows = s.exec(stmt).all()
        
        out = []
        for r in rows:
            out.append({
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "parameters": json.loads(r.parameters_json) if r.parameters_json else {},
                "workflow_def": json.loads(r.workflow_def_json) if r.workflow_def_json else {},
                "enabled": r.enabled,
                "created_at": r.created_at
            })
        return out
