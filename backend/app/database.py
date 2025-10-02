import os
import json
from typing import List, Dict, Optional
from pathlib import Path

from sqlmodel import SQLModel, Field, create_engine, Session, select


class Artifact(SQLModel, table=True):
    id: str = Field(primary_key=True)
    filename: str
    filepath: str
    filetype: str
    report_week: Optional[str] = None
    status: Optional[str] = None


class Evidence(SQLModel, table=True):
    id: str = Field(primary_key=True)
    artifact_id: str
    locator: Optional[str] = None
    preview: Optional[str] = None
    content_type: Optional[str] = None
    coordinates_json: Optional[str] = None
    full_data_json: Optional[str] = None


class Fact(SQLModel, table=True):
    id: str = Field(primary_key=True)
    artifact_id: str
    report_week: Optional[str] = None
    entity: Optional[str] = None
    metrics_json: str


class Database:
    """SQLite-backed database with a similar interface as the prior in-memory DB."""

    def __init__(self, db_path: Optional[str] = None):
        db_path = db_path or os.getenv("DB_PATH", "db.sqlite3")
        self.db_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.db_url, echo=False)
        SQLModel.metadata.create_all(self.engine)

    def add_artifact(self, artifact: Dict) -> str:
        with Session(self.engine) as s:
            row = Artifact(**artifact)
            s.add(row)
            s.commit()
        return artifact["id"]

    def add_fact(self, fact: Dict):
        metrics_json = json.dumps(fact.get("metrics", {}), ensure_ascii=False)
        row = Fact(
            id=fact["id"],
            artifact_id=fact.get("artifact_id", ""),
            report_week=fact.get("report_week"),
            entity=fact.get("entity"),
            metrics_json=metrics_json,
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
        return [row.model_dump() for row in rows]

    def reset(self):
        with Session(self.engine) as s:
            s.exec("DELETE FROM evidence")
            s.exec("DELETE FROM fact")
            s.exec("DELETE FROM artifact")
            s.commit()


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
    json: str  # rows/cells JSON


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
            s.add(DocTable(**table))
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

    def list_logs(self, level: str | None = None, code: str | None = None, q: str | None = None,
                  ts_from: str | None = None, ts_to: str | None = None) -> List[Dict]:
        with Session(self.engine) as s:
            stmt = select(LogEntry)
            if level:
                stmt = stmt.where(LogEntry.level == level)
            if code:
                stmt = stmt.where(LogEntry.code == code)
            rows = s.exec(stmt).all()
        out = []
        for e in rows:
            if q and (q.lower() not in (e.message or '').lower()):
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
            out.append({"id": t.id, "document_id": t.document_id, "tag": t.tag, "score": t.score, "source_ptr": t.source_ptr})
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
