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
