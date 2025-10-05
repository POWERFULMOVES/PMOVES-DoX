import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlmodel import Session, select

SUPABASE_CLI_ENV = BACKEND_DIR.parent / ".supabase" / ".env"

from app.database import (
    ExtendedDatabase,
    Artifact,
    Evidence,
    Fact,
    Document,
    Section,
    DocTable,
    APIEndpoint,
    LogEntry,
    TagRow,
    TagPrompt,
)
from app.database_supabase import SupabaseDatabase, SupabaseUnavailable

LOGGER = logging.getLogger("backfill_supabase")


def _maybe_json(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str) and value.strip() == "":
        return None
    return value


def _deserialize_fact(row: Fact) -> Dict[str, Any]:
    data = row.model_dump()
    metrics = _maybe_json(data.pop("metrics_json", "{}"))
    if isinstance(metrics, str):
        try:
            import json

            metrics = json.loads(metrics)
        except Exception:
            metrics = {}
    data["metrics"] = metrics or {}
    return data


def _deserialize_evidence(row: Evidence) -> Dict[str, Any]:
    data = row.model_dump()
    import json

    coords = data.pop("coordinates_json", None)
    if coords:
        try:
            data["coordinates"] = json.loads(coords)
        except Exception:
            data["coordinates"] = None
    full_data = data.pop("full_data_json", None)
    if full_data:
        try:
            data["full_data"] = json.loads(full_data)
        except Exception:
            data["full_data"] = None
    return data


def _deserialize_tag(row: TagRow) -> Dict[str, Any]:
    return row.model_dump()


def _deserialize_prompt(row: TagPrompt) -> Dict[str, Any]:
    import json

    payload = row.model_dump()
    examples = payload.pop("examples_json", None)
    if examples:
        try:
            payload["examples"] = json.loads(examples)
        except Exception:
            payload["examples"] = None
    return payload


def gather_sqlite_rows(db: ExtendedDatabase) -> Dict[str, Iterable[Dict[str, Any]]]:
    with Session(db.engine) as session:
        artifacts = [row.model_dump() for row in session.exec(select(Artifact)).all()]
        documents = [row.model_dump() for row in session.exec(select(Document)).all()]
        sections = [row.model_dump() for row in session.exec(select(Section)).all()]
        tables = [row.model_dump() for row in session.exec(select(DocTable)).all()]
        apis = [row.model_dump() for row in session.exec(select(APIEndpoint)).all()]
        logs = [row.model_dump() for row in session.exec(select(LogEntry)).all()]
        tags = [_deserialize_tag(row) for row in session.exec(select(TagRow)).all()]
        facts = [_deserialize_fact(row) for row in session.exec(select(Fact)).all()]
        evidence = [_deserialize_evidence(row) for row in session.exec(select(Evidence)).all()]
        prompts = [_deserialize_prompt(row) for row in session.exec(select(TagPrompt)).all()]

    return {
        "artifacts": artifacts,
        "documents": documents,
        "sections": sections,
        "tables": tables,
        "apis": apis,
        "logs": logs,
        "tags": tags,
        "facts": facts,
        "evidence": evidence,
        "prompts": prompts,
    }


def _load_supabase_cli_env() -> None:
    if SUPABASE_CLI_ENV.exists():
        for line in SUPABASE_CLI_ENV.read_text().splitlines():
            if not line or line.strip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key == "API_URL" and not os.getenv("SUPABASE_URL"):
                os.environ["SUPABASE_URL"] = value
            elif key == "SERVICE_ROLE_KEY" and not os.getenv("SUPABASE_SERVICE_KEY"):
                os.environ["SUPABASE_SERVICE_KEY"] = value
            elif key == "ANON_KEY" and not os.getenv("SUPABASE_ANON_KEY"):
                os.environ["SUPABASE_ANON_KEY"] = value


def backfill(sqlite_path: Path, reset: bool = False) -> None:
    db = ExtendedDatabase(db_path=str(sqlite_path))
    _load_supabase_cli_env()
    try:
        supabase = SupabaseDatabase()
    except SupabaseUnavailable as exc:
        raise SystemExit(f"Supabase unavailable: {exc}") from exc

    if reset:
        LOGGER.info("Resetting Supabase tables before backfill")
        supabase.reset()
        try:
            supabase.reset_search_chunks()
        except Exception as exc:
            LOGGER.warning("Unable to reset remote search chunks: %s", exc)

    payload = gather_sqlite_rows(db)

    for artifact in payload["artifacts"]:
        supabase.add_artifact(artifact)
    for doc in payload["documents"]:
        supabase.add_document(doc)
    for section in payload["sections"]:
        supabase.add_section(section)
    for table in payload["tables"]:
        supabase.add_table(table)
    for api in payload["apis"]:
        supabase.add_api(api)
    for log in payload["logs"]:
        supabase.add_log(log)
    for tag in payload["tags"]:
        supabase.add_tag(tag)
    for fact in payload["facts"]:
        supabase.add_fact(fact)
    for ev in payload["evidence"]:
        supabase.add_evidence(ev)
    for prompt in payload["prompts"]:
        supabase.save_tag_prompt(
            document_id=prompt["document_id"],
            prompt_text=prompt["prompt_text"],
            examples=prompt.get("examples"),
            author=prompt.get("author"),
        )

    LOGGER.info("Backfill complete: %d artifacts, %d documents, %d tags", len(payload["artifacts"]), len(payload["documents"]), len(payload["tags"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill Supabase from SQLite store")
    parser.add_argument("--from-sqlite", required=True, help="Path to SQLite database (db.sqlite3)")
    parser.add_argument("--reset", action="store_true", help="Reset Supabase tables before import")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    sqlite_path = Path(args.from_sqlite).expanduser().resolve()
    if not sqlite_path.exists():
        raise SystemExit(f"SQLite database not found at {sqlite_path}")
    backfill(sqlite_path, reset=args.reset)


if __name__ == "__main__":
    main()
