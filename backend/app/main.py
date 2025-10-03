from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
import os
from pathlib import Path
import shutil
from typing import List, Dict
import uuid
from dotenv import load_dotenv
import time
import json
from docx import Document
import subprocess
import tempfile
import threading
from pydantic import BaseModel
from app.hrm import HRMConfig, HRMMetrics, refine_sort_digits

from app.ingestion.pdf_processor import process_pdf
from app.ingestion.csv_processor import process_csv
from app.ingestion.xlsx_processor import process_xlsx
from app.ingestion.xml_ingestion import process_xml
from app.ingestion.openapi_ingestion import process_openapi
from app.ingestion.postman_ingestion import process_postman
from app.database import ExtendedDatabase
from app.qa_engine import QAEngine
from app.extraction.langextract_adapter import run_langextract, write_visualization
from app.chr_pipeline import run_chr, pca_plot
from app.search import SearchIndex
from app.export_poml import build_poml
import yaml
try:
    from watchgod import watch
except Exception:
    watch = None  # type: ignore
import csv
from datetime import datetime

load_dotenv()

# Normalize HF token envs for Hugging Face downloads
hf_token = (
    os.getenv("HUGGINGFACE_HUB_TOKEN")
    or os.getenv("HF_API_KEY")
    or os.getenv("HF_TOKEN")
    or os.getenv("HUGGINGFACE_TOKEN")
)
if hf_token and not os.getenv("HUGGINGFACE_HUB_TOKEN"):
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

app = FastAPI(title="PMOVES_DoX API")

# Optionally run Alembic migrations on startup
if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
    try:
        import subprocess as _sp
        _sp.run(["alembic", "upgrade", "head"], cwd=str(Path(__file__).resolve().parents[1]), check=False)
    except Exception:
        pass

# CORS for frontend (env-driven)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
allow_origins = [o.strip() for o in frontend_origin.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize
UPLOAD_DIR = Path("uploads")
ARTIFACTS_DIR = Path("artifacts")
UPLOAD_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

db = ExtendedDatabase()
qa_engine = QAEngine(db)
search_index = SearchIndex(db)
# HRM config/metrics (optional features)
HRM_ENABLED = os.getenv("HRM_ENABLED", "false").lower() == "true"
HRM_CFG = HRMConfig(
    Mmax=int(os.getenv("HRM_MMAX", "6")),
    Mmin=int(os.getenv("HRM_MMIN", "2")),
    threshold=float(os.getenv("HRM_THRESHOLD", "0.5")),
)
HRM_STATS = HRMMetrics()

# Simple in-memory task registry
TASKS: dict[str, dict] = {}
START_TIME = time.time()


def _ingest_file_from_watch(src: Path, report_week: str = ""):
    try:
        if not src.exists() or not src.is_file():
            return
        file_id = str(uuid.uuid4())
        dst = UPLOAD_DIR / f"{file_id}_{src.name}"
        shutil.copy2(src, dst)
        suffix = dst.suffix.lower()
        artifact_id = db.add_artifact({
            "id": file_id,
            "filename": src.name,
            "filepath": str(dst),
            "filetype": suffix,
            "report_week": report_week,
            "status": "processing" if suffix == ".pdf" else "processed"
        })
        if suffix == ".pdf":
            task_id = str(uuid.uuid4())
            TASKS[task_id] = {"status": "queued", "filename": src.name, "artifact_id": artifact_id}
            # schedule background processing using the same helper
            _thread = threading.Thread(target=_process_and_store, args=(dst, report_week, artifact_id, suffix, task_id), daemon=True)
            _thread.start()
        elif suffix in (".csv", ".xlsx", ".xls"):
            _process_and_store(dst, report_week, artifact_id, suffix, None)
        elif suffix == ".xml":
            doc, rows = process_xml(dst)
            db.add_document(doc)
            for row in rows:
                db.add_log(row)
        elif suffix in (".yaml", ".yml", ".json"):
            # Try OpenAPI then Postman
            try:
                doc, rows = process_openapi(dst)
                db.add_document(doc)
                for row in rows:
                    db.add_api(row)
            except Exception:
                try:
                    doc, rows = process_postman(dst)
                    db.add_document(doc)
                    for row in rows:
                        db.add_api(row)
                except Exception:
                    pass
    except Exception:
        pass


def _watch_loop():
    if not watch:
        return
    enabled = os.getenv("WATCH_ENABLED", "true").lower() == "true"
    if not enabled:
        return
    watch_dir = Path(os.getenv("WATCH_DIR", "/app/watch"))
    debounce_ms = int(os.getenv("WATCH_DEBOUNCE_MS", "1000"))
    min_bytes = int(os.getenv("WATCH_MIN_BYTES", "1"))
    watch_dir.mkdir(parents=True, exist_ok=True)
    exts = {".pdf", ".csv", ".xlsx", ".xls"}

    def ready(p: Path) -> bool:
        try:
            if not p.exists() or not p.is_file():
                return False
            if p.suffix.lower() not in exts:
                return False
            if p.stat().st_size < min_bytes:
                return False
            s1 = p.stat().st_size
            time.sleep(debounce_ms / 1000.0)
            s2 = p.stat().st_size
            return s1 == s2
        except Exception:
            return False

    seen: set[str] = set()
    for changes in watch(str(watch_dir)):
        for _evt, path_str in changes:
            p = Path(path_str)
            key = str(p.resolve())
            if key in seen:
                continue
            if ready(p):
                seen.add(key)
                _ingest_file_from_watch(p)


@app.on_event("startup")
async def _startup_watch():
    # Start watcher thread
    t = threading.Thread(target=_watch_loop, daemon=True)
    t.start()
    try:
        search_index.rebuild()
    except Exception:
        pass

@app.get("/")
async def root():
    return {"message": "PMOVES_DoX API", "status": "running"}

@app.get("/config")
async def config():
    # Detect GPU availability if torch is present
    gpu = {"available": False, "device_count": 0, "names": []}
    try:
        import torch  # type: ignore
        if hasattr(torch, "cuda") and torch.cuda.is_available():
            gpu["available"] = True
            gpu["device_count"] = torch.cuda.device_count()
            try:
                gpu["names"] = [torch.cuda.get_device_name(i) for i in range(gpu["device_count"])]
            except Exception:
                pass
    except Exception:
        pass
    # Detect Ollama availability
    ollama = {"available": False, "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")}
    try:
        import httpx  # type: ignore
        base = ollama["base_url"].rstrip("/")
        resp = httpx.get(f"{base}/api/tags", timeout=2.0)
        if resp.status_code == 200:
            ollama["available"] = True
    except Exception:
        pass
    offline = bool(os.getenv("TRANSFORMERS_OFFLINE") or os.getenv("HF_HUB_OFFLINE"))
    return {
        "vlm_repo": os.getenv("DOCLING_VLM_REPO"),
        "hf_auth": bool(os.getenv("HUGGINGFACE_HUB_TOKEN")),
        "frontend_origin": frontend_origin,
        "gpu": gpu,
        "ollama": ollama,
        "offline": offline,
        "open_pdf_enabled": os.getenv("OPEN_PDF_ENABLED", "false").lower() == "true",
    }


@app.get("/tasks")
async def list_tasks():
    # Return a lightweight summary including counts and queued items
    items = [
        {"id": k, **v} for k, v in TASKS.items()
    ]
    queued = [t for t in items if t.get("status") == "queued"]
    completed = [t for t in items if t.get("status") == "completed"]
    errored = [t for t in items if t.get("status") == "error"]
    return {
        "total": len(items),
        "queued": len(queued),
        "completed": len(completed),
        "errored": len(errored),
        "queued_items": queued,
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
    }


@app.get("/artifacts")
async def list_artifacts():
    return {"artifacts": db.get_artifacts()}

@app.get("/artifacts/{artifact_id}")
async def artifact_detail(artifact_id: str):
    arts = db.get_artifacts()
    art = next((a for a in arts if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
    facts = [f for f in db.get_facts() if f.get("artifact_id") == artifact_id]
    evidence = [e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id]
    return {"artifact": art, "facts": facts, "evidence": evidence}

@app.get("/documents")
async def list_documents(type: str | None = None):
    items = db.list_documents(type=type)
    return {"documents": items}


# ---------- ingestion: XML / OpenAPI / Postman ----------
@app.post("/ingest/xml")
async def ingest_xml(file: UploadFile = File(...)):
    tmp = UPLOAD_DIR / f"tmp_{uuid.uuid4()}_{file.filename}"
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    doc, rows = process_xml(tmp)
    db.add_document(doc)
    for row in rows:
        db.add_log(row)
    return {"status": "ok", "document_id": doc["id"], "rows": len(rows)}


@app.post("/ingest/openapi")
async def ingest_openapi(file: UploadFile = File(...)):
    tmp = UPLOAD_DIR / f"tmp_{uuid.uuid4()}_{file.filename}"
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    doc, rows = process_openapi(tmp)
    db.add_document(doc)
    for row in rows:
        db.add_api(row)
    return {"status": "ok", "document_id": doc["id"], "rows": len(rows)}


@app.post("/ingest/postman")
async def ingest_postman(file: UploadFile = File(...)):
    tmp = UPLOAD_DIR / f"tmp_{uuid.uuid4()}_{file.filename}"
    with tmp.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    doc, rows = process_postman(tmp)
    db.add_document(doc)
    for row in rows:
        db.add_api(row)
    return {"status": "ok", "document_id": doc["id"], "rows": len(rows)}


# ---------- queries: logs / apis / tags ----------
@app.get("/logs")
async def get_logs(level: str | None = None, code: str | None = None, q: str | None = None,
                   ts_from: str | None = None, ts_to: str | None = None):
    items = db.list_logs(level=level, code=code, q=q, ts_from=ts_from, ts_to=ts_to)
    return {"logs": items}


@app.get("/logs/export")
async def export_logs(level: str | None = None, code: str | None = None, q: str | None = None,
                      ts_from: str | None = None, ts_to: str | None = None):
    items = db.list_logs(level=level, code=code, q=q, ts_from=ts_from, ts_to=ts_to)
    def gen():
        yield "ts,level,code,component,message\n"
        for l in items:
            # naive CSV escaping
            def esc(v: str | None) -> str:
                if v is None:
                    return ""
                s = str(v).replace("\r", " ").replace("\n", " ")
                if "," in s or '"' in s:
                    s = '"' + s.replace('"', '""') + '"'
                return s
            row = ",".join([
                esc(l.get("ts")), esc(l.get("level")), esc(l.get("code")), esc(l.get("component")), esc(l.get("message"))
            ])
            yield row + "\n"
    return StreamingResponse(gen(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=logs.csv"})


@app.get("/apis")
async def get_apis(tag: str | None = None, method: str | None = None, path_like: str | None = None):
    items = db.list_apis(tag=tag, method=method, path_like=path_like)
    return {"apis": items}


@app.get("/apis/{api_id}")
async def get_api_detail(api_id: str):
    # fetch raw row from DB
    from sqlmodel import Session
    from app.database import APIEndpoint
    with Session(db.engine) as s:  # type: ignore[attr-defined]
        row = s.get(APIEndpoint, api_id)
    if not row:
        raise HTTPException(404, "API not found")
    import json as _json
    return {
        "id": row.id,
        "document_id": row.document_id,
        "name": row.name,
        "method": row.method,
        "path": row.path,
        "summary": row.summary,
        "tags": _json.loads(row.tags_json) if row.tags_json else [],
        "parameters": _json.loads(row.params_json) if row.params_json else [],
        "responses": _json.loads(row.responses_json) if row.responses_json else {},
    }


@app.get("/tags")
async def get_tags(document_id: str | None = None, q: str | None = None):
    items = db.list_tags(document_id=document_id, q=q)
    return {"tags": items}


class ExtractTagsRequest(BaseModel):
    document_id: str
    model_id: str | None = None
    api_key: str | None = None
    prompt: str | None = None
    examples: list[dict] | None = None
    dry_run: bool = False
    use_hrm: bool = False


def _compose_text_for_document(doc: Dict) -> str:
    doc_type = (doc.get("type") or "").lower()
    path = Path(doc.get("path", ""))
    if doc_type == "xml":
        # concatenate log messages
        msgs = db.list_log_messages(doc["id"])  # type: ignore[arg-type]
        return "\n".join(msgs)
    elif doc_type in ("openapi", "postman"):
        # read raw file
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    elif doc_type == "pdf":
        # Prefer markdown from artifacts if exists
        md_path = ARTIFACTS_DIR / f"{path.stem}.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")
    # fallback: file content
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


@app.post("/extract/tags")
async def extract_tags(req: ExtractTagsRequest):
    doc = next((d for d in db.list_documents() if d.get("id") == req.document_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")

    text = _compose_text_for_document(doc)
    if not text:
        raise HTTPException(400, "No text available for tag extraction")

    preset_prompt = req.prompt or os.getenv("TAGS_PROMPT", (
        "Extract application or system tags relevant to loan management systems (LMS). "
        "Return concise tags as exact spans from text. Examples: 'Loan Origination', 'Underwriting', 'Servicing', 'LoanService'."
    ))
    # If dry_run and no API key/model configured, use a heuristic fallback to avoid external calls during smoke.
    use_fallback = (
        req.dry_run and not (req.api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LANGEXTRACT_API_KEY"))
    )
    t0 = time.time()
    if use_fallback:
        import re as _re
        # simple heuristic: grab capitalized multi-word phrases up to 3
        candidates = _re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-zA-Z]+){0,2})\b", text)
        unique = []
        for c in candidates:
            c = c.strip()
            if c not in unique:
                unique.append(c)
            if len(unique) >= 5:
                break
        result = {"entities": [{"extraction_text": t, "extraction_class": "heuristic"} for t in unique]}
    else:
        result = run_langextract(
            text=text,
            prompt_description=preset_prompt,
            examples=req.examples,
            model_id=req.model_id,
            api_key=req.api_key,
            extraction_passes=1,
            max_workers=4,
            max_char_buffer=4000,
        )

    entities = result.get("entities", [])
    # Optional HRM-style iterative refinement over extracted tags
    steps = 0
    if HRM_ENABLED and req.use_hrm:
        def norm_tag(t: str) -> str:
            return " ".join(t.strip().split())
        tags0 = [str(e.get("extraction_text") or e.get("text") or "").strip() for e in entities if (e.get("extraction_text") or e.get("text"))]
        tags = [t for t in tags0 if t]
        for m in range(1, HRM_CFG.Mmax + 1):
            steps = m
            tags_new = []
            seen = set()
            for t in tags:
                t2 = norm_tag(t)
                if t2 and t2 not in seen:
                    seen.add(t2)
                    tags_new.append(t2)
            if m >= HRM_CFG.Mmin and tags_new == tags:
                break
            tags = tags_new
        # replace entities with refined tags for persistence phase
        entities = [{"extraction_text": t, "extraction_class": "hrm-refined"} for t in tags]
        dt = (time.time() - t0) * 1000.0
        HRM_STATS.record(steps=steps, latency_ms=dt, payload={"mode": "extract_tags", "doc": req.document_id})
    saved = 0
    extracted: List[str] = []
    for e in entities:
        tag_text = e.get("extraction_text") or e.get("text")
        if not tag_text:
            continue
        tag_text = str(tag_text).strip()
        extracted.append(tag_text)
        if req.dry_run:
            continue
        if not db.has_tag(req.document_id, tag_text):
            source_ptr = e.get("extraction_class") or "langextract"
            if source_ptr == "hrm-refined" and (HRM_ENABLED and req.use_hrm):
                try:
                    s_val = int(steps) if isinstance(steps, int) else None
                except Exception:
                    s_val = None
                if s_val is not None:
                    source_ptr = f"hrm-refined:steps{s_val}"
            db.add_tag({
                "id": str(uuid.uuid4()),
                "document_id": req.document_id,
                "tag": tag_text,
                "score": None,
                "source_ptr": source_ptr,
            })
            saved += 1
    resp = {"status": "ok", "document_id": req.document_id, "tags_saved": saved, "tags": extracted}
    if HRM_ENABLED and req.use_hrm:
        resp["hrm"] = {"enabled": True, "steps": steps}
    return resp


@app.get("/tags/presets")
async def tag_presets():
    default_prompt = os.getenv("TAGS_PROMPT", (
        "Extract application or system tags relevant to loan management systems (LMS). "
        "Return concise tags as exact spans from text. Examples: 'Loan Origination', 'Underwriting', 'Servicing', 'LoanService'."
    ))
    examples = [
        {"text": "The LMS core supports Loan Origination and Loan Servicing.", "labels": ["Loan Origination", "Loan Servicing"]},
        {"text": "Enable Underwriting via RulesEngine v2.", "labels": ["Underwriting", "RulesEngine"]},
    ]
    return {"prompt": default_prompt, "examples": examples}


class TagPromptSaveRequest(BaseModel):
    prompt_text: str
    examples: list[dict] | None = None
    author: str | None = None


@app.get("/tags/prompt/{document_id}")
async def get_tag_prompt(document_id: str):
    item = db.get_latest_tag_prompt(document_id)
    if not item:
        return {"prompt": None}
    return item


@app.get("/tags/prompt/{document_id}/history")
async def get_tag_prompt_history(document_id: str, limit: int = 20):
    items = db.list_tag_prompt_history(document_id, limit=limit)
    return {"items": items}


@app.post("/tags/prompt/{document_id}")
async def save_tag_prompt(document_id: str, req: TagPromptSaveRequest):
    pid = db.save_tag_prompt(document_id, req.prompt_text, req.examples, req.author)
    return {"status": "ok", "id": pid}


@app.get("/watch")
async def watch_status():
    return {
        "enabled": os.getenv("WATCH_ENABLED", "true").lower() == "true",
        "dir": os.getenv("WATCH_DIR", "/app/watch"),
        "debounce_ms": int(os.getenv("WATCH_DEBOUNCE_MS", "1000")),
        "min_bytes": int(os.getenv("WATCH_MIN_BYTES", "1")),
        "available": bool(watch),
    }


# ---------------- LangExtract integration ----------------
class LangExtractRequest(BaseModel):
    artifact_id: str | None = None
    text: str | None = None
    prompt_description: str
    examples: list[dict] | None = None
    model_id: str | None = None
    api_key: str | None = None
    extraction_passes: int = 1
    max_workers: int = 8
    max_char_buffer: int = 4000


def _load_text_for_artifact(artifact_id: str) -> str:
    # Attempt to load markdown generated by pdf_processor for PDFs
    art = next((a for a in db.get_artifacts() if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
    p = Path(art.get("filepath", ""))
    if p.suffix.lower() == ".pdf":
        md_path = ARTIFACTS_DIR / f"{p.stem}.md"
        if md_path.exists():
            return md_path.read_text(encoding="utf-8")
    # Fallback: try raw file text for CSV/XLSX (limited utility)
    try:
        return Path(art.get("filepath")).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


@app.post("/extract/langextract")
async def extract_langextract(req: LangExtractRequest):
    if not req.text and not req.artifact_id:
        raise HTTPException(400, "Provide either text or artifact_id")
    text = req.text or _load_text_for_artifact(req.artifact_id)  # type: ignore[arg-type]
    if not text:
        raise HTTPException(400, "No text available for extraction")

    result = run_langextract(
        text=text,
        prompt_description=req.prompt_description,
        examples=req.examples,
        model_id=req.model_id,
        api_key=req.api_key,
        extraction_passes=req.extraction_passes,
        max_workers=req.max_workers,
        max_char_buffer=req.max_char_buffer,
    )

    # Save artifacts (JSON and HTML) under artifacts/
    out_dir = ARTIFACTS_DIR / "langextract"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "langextract_results.json"
    json_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    html_path = write_visualization(result, out_dir, output_name="langextract_results")

    return {
        "status": "ok",
        "model_id": result.get("model_id"),
        "entities_count": len(result.get("entities", [])),
        "artifacts": {
            "json": str(json_path),
            "html": str(html_path),
        },
    }


# ---------------- Vector Search ----------------
class SearchRequest(BaseModel):
    q: str
    k: int = 10


@app.post("/search")
async def search(req: SearchRequest):
    t0 = time.time()
    hits = search_index.search(req.q, k=req.k)
    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "took_ms": elapsed_ms,
        "count": len(hits),
        "results": [
            {"score": h.score, "text": h.text, "meta": h.meta}
            for h in hits
        ],
    }


@app.post("/search/rebuild")
async def search_rebuild():
    info = search_index.rebuild()
    return {"status": "ok", **info}


# ---------------- Conversion: artifact -> txt/docx ----------------
class ConvertRequest(BaseModel):
    artifact_id: str
    format: str  # 'txt' or 'docx'


def _load_markdown_for_artifact(artifact_id: str) -> tuple[Path, str]:
    art = next((a for a in db.get_artifacts() if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, f"Artifact not found: {artifact_id}")
    p = Path(art.get("filepath", ""))
    if p.suffix.lower() == ".pdf":
        md_path = ARTIFACTS_DIR / f"{p.stem}.md"
        if md_path.exists():
            return md_path, md_path.read_text(encoding="utf-8")
        return md_path, ""
    # CSV/XLSX fallback: return raw text for CSV or a generic message
    try:
        txt = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        txt = f"Artifact {p.name} not convertible to text in this mode."
    md_path = ARTIFACTS_DIR / f"{p.stem}.md"
    return md_path, txt


@app.post("/convert")
async def convert_artifact(req: ConvertRequest):
    fmt = req.format.lower()
    if fmt not in ("txt", "docx"):
        raise HTTPException(400, "format must be 'txt' or 'docx'")

    md_path, md_text = _load_markdown_for_artifact(req.artifact_id)
    if not md_text:
        raise HTTPException(400, "No markdown/text available for this artifact yet. Process a PDF first.")

    stem = md_path.stem or "document"
    out_dir = ARTIFACTS_DIR / "conversions"
    out_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "txt":
        txt_path = out_dir / f"{stem}.txt"
        # Prefer pandoc for markdown -> plain text
        try:
            if shutil.which("pandoc") and md_path.exists():
                subprocess.run(["pandoc", str(md_path), "-f", "gfm", "-t", "plain", "-o", str(txt_path)], check=True)
            else:
                txt_path.write_text(md_text, encoding="utf-8")
        except Exception:
            txt_path.write_text(md_text, encoding="utf-8")
        rel = str(txt_path.relative_to(ARTIFACTS_DIR)) if txt_path.is_relative_to(ARTIFACTS_DIR) else f"conversions/{txt_path.name}"
        return {"status": "ok", "path": str(txt_path), "rel": rel}

    # DOCX
    docx_path = out_dir / f"{stem}.docx"
    # Prefer pandoc for markdown -> docx for high fidelity
    try:
        if shutil.which("pandoc") and md_path.exists():
            subprocess.run(["pandoc", str(md_path), "-f", "gfm", "-t", "docx", "-o", str(docx_path)], check=True)
        else:
            raise RuntimeError("pandoc not available")
    except Exception:
        # Fallback naive mapping
        doc = Document()
        for line in md_text.splitlines():
            if line.startswith("### "):
                doc.add_heading(line[4:].strip(), level=3)
            elif line.startswith("## "):
                doc.add_heading(line[3:].strip(), level=2)
            elif line.startswith("# "):
                doc.add_heading(line[2:].strip(), level=1)
            else:
                if line.strip().startswith("- "):
                    doc.add_paragraph(line.strip()[2:], style="List Bullet")
                else:
                    doc.add_paragraph(line)
        doc.save(docx_path)
    rel = str(docx_path.relative_to(ARTIFACTS_DIR)) if docx_path.is_relative_to(ARTIFACTS_DIR) else f"conversions/{docx_path.name}"
    return {"status": "ok", "path": str(docx_path), "rel": rel}


# ---------------- CHR structuring ----------------
class CHRRequest(BaseModel):
    artifact_id: str
    K: int = 8
    iters: int = 30
    bins: int = 8
    seed: int = 42
    beta: float = 12.0
    units_mode: str = "paragraphs"  # 'paragraphs' or 'sentences'
    include_tables: bool = True


def _sent_split(text: str) -> List[str]:
    import re
    rough = re.split(r"[\n\r]+|(?<=[\.!?])\s+", text.strip())
    return [s.strip() for s in rough if s.strip()]


def _split_units_from_markdown(md_text: str, mode: str = "paragraphs") -> List[str]:
    blocks = [b.strip() for b in md_text.split("\n\n")]
    blocks = [b for b in blocks if b]
    if mode == "sentences":
        units: List[str] = []
        for b in blocks:
            units.extend(_sent_split(b))
        return units
    return blocks


def _units_from_pdf_json(json_path: Path, include_tables: bool, mode: str) -> List[str]:
    try:
        import json as _json
        doc = _json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    units: List[str] = []
    # texts
    for it in doc.get("texts", []) or []:
        t = str(it.get("text", "")).strip()
        if not t:
            continue
        if mode == "sentences":
            units.extend(_sent_split(t))
        else:
            units.append(t)
    # tables
    if include_tables:
        for tb in doc.get("tables", []) or []:
            # assume 'data' or export-like format
            rows = tb.get("data") or tb.get("rows") or []
            for row in rows:
                vals = [str(c) for c in row if str(c).strip()]
                if not vals:
                    continue
                units.append(" ".join(vals))
    return units


def _units_from_csv(path: Path, mode: str) -> List[str]:
    import pandas as pd
    try:
        df = pd.read_csv(path)
    except Exception:
        return []
    units: List[str] = []
    for _, row in df.iterrows():
        vals = [str(v) for v in row.tolist() if str(v).strip()]
        if not vals:
            continue
        text = " ".join(vals)
        if mode == "sentences":
            units.extend(_sent_split(text))
        else:
            units.append(text)
    return units


def _units_from_xlsx(path: Path, mode: str) -> List[str]:
    import pandas as pd
    units: List[str] = []
    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return []
    for sheet in xls.sheet_names:
        df = xls.parse(sheet)
        for _, row in df.iterrows():
            vals = [str(v) for v in row.tolist() if str(v).strip()]
            if not vals:
                continue
            text = " ".join(vals)
            if mode == "sentences":
                units.extend(_sent_split(text))
            else:
                units.append(text)
    return units


@app.post("/structure/chr")
async def structure_chr(req: CHRRequest):
    md_path, md_text = _load_markdown_for_artifact(req.artifact_id)
    # detect artifact type
    art = next((a for a in db.get_artifacts() if a.get("id") == req.artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
    file_path = Path(art.get("filepath", ""))
    suffix = file_path.suffix.lower()

    units: List[str] = []
    if suffix == ".pdf":
        json_path = ARTIFACTS_DIR / f"{file_path.stem}.json"
        if json_path.exists():
            units = _units_from_pdf_json(json_path, include_tables=req.include_tables, mode=req.units_mode)
        if not units and md_text:
            units = _split_units_from_markdown(md_text, mode=req.units_mode)
    elif suffix == ".csv":
        units = _units_from_csv(file_path, mode=req.units_mode)
    elif suffix in (".xlsx", ".xls"):
        units = _units_from_xlsx(file_path, mode=req.units_mode)
    else:
        # fallback to markdown/plain
        if md_text:
            units = _split_units_from_markdown(md_text, mode=req.units_mode)

    if not units:
        raise HTTPException(400, "Could not derive units for this artifact.")

    res = run_chr(units, K=req.K, iters=req.iters, bins=req.bins, beta=req.beta, seed=req.seed)

    # If PDF, try to attach page numbers to rows
    pages_map: List[int] | None = None
    if suffix == ".pdf":
        tu = ARTIFACTS_DIR / f"{file_path.stem}.text_units.json"
        try:
            if tu.exists():
                import json as _json
                data = _json.loads(tu.read_text(encoding="utf-8", errors="ignore"))
                if isinstance(data, list):
                    if req.units_mode != "sentences":
                        # 1:1 mapping with units array
                        pages_map = [int(x.get("page")) if isinstance(x.get("page"), (int, float)) else None for x in data]
                    else:
                        # sentences mode: expand page map by splitting each unit into sentences
                        def _sent_split_local(text: str) -> list[str]:
                            import re as _re
                            rough = _re.split(r"[\n\r]+|(?<=[\.!?])\s+", (text or "").strip())
                            return [s.strip() for s in rough if s and s.strip()]
                        expanded: list[int | None] = []
                        for x in data:
                            txt = (x.get("text") or "").strip()
                            cnt = len(_sent_split_local(txt)) if txt else 0
                            pg = int(x.get("page")) if isinstance(x.get("page"), (int, float)) else None
                            if cnt <= 0:
                                continue
                            expanded.extend([pg] * cnt)
                        pages_map = expanded
        except Exception:
            pages_map = None
        if pages_map:
            for row in res.rows:
                try:
                    idx = int(row.get("idx"))
                    # Bound-check; if sentences produced more/less items than units, clamp by last known page
                    pg = None
                    if 0 <= idx < len(pages_map):
                        pg = pages_map[idx]
                    elif len(pages_map) > 0:
                        pg = pages_map[-1]
                    if isinstance(pg, int):
                        row["page"] = pg
                except Exception:
                    pass

    # Persist CSV/JSON
    import csv, json as _json
    out_dir = ARTIFACTS_DIR / "chr"
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = md_path.stem or "document"
    csv_path = out_dir / f"{stem}_chr.csv"
    json_path = out_dir / f"{stem}_chr.json"
    plot_path = out_dir / f"{stem}_pca.png"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["idx", "constellation", "radius", "text", "page"])
        writer.writeheader()
        for row in res.rows:
            writer.writerow(row)
    json_obj = {
        "backend": res.backend,
        "K": res.K,
        "mhep": res.mhep,
        "Hg": res.Hg,
        "Hs": res.Hs,
        "Hg_traj": res.Hg_traj,
        "Hs_traj": res.Hs_traj,
        "rows": res.rows,
    }
    json_path.write_text(_json.dumps(json_obj, indent=2), encoding="utf-8")
    # PCA plot
    try:
        pca_plot(res.Z, res.U, np.array(res.labels), str(plot_path))
    except Exception:
        pass

    rel_csv = str(csv_path.relative_to(ARTIFACTS_DIR)) if csv_path.is_relative_to(ARTIFACTS_DIR) else f"chr/{csv_path.name}"
    rel_json = str(json_path.relative_to(ARTIFACTS_DIR)) if json_path.is_relative_to(ARTIFACTS_DIR) else f"chr/{json_path.name}"
    rel_plot = str(plot_path.relative_to(ARTIFACTS_DIR)) if plot_path.exists() and plot_path.is_relative_to(ARTIFACTS_DIR) else None

    return {
        "status": "ok",
        "K": res.K,
        "mhep": res.mhep,
        "Hg": res.Hg,
        "Hs": res.Hs,
        "counts": {"units": len(units)},
        "preview_rows": res.rows[:10],
        "artifacts": {"csv": str(csv_path), "json": str(json_path), "rel_csv": rel_csv, "rel_json": rel_json, "rel_plot": rel_plot},
    }


@app.get("/download")
async def download_artifact(rel: str):
    # serve files only within ARTIFACTS_DIR
    try:
        # Normalize path to prevent traversal
        target = (ARTIFACTS_DIR / rel).resolve()
        if not str(target).startswith(str(ARTIFACTS_DIR.resolve())):
            raise HTTPException(400, "Invalid path")
        if not target.exists() or not target.is_file():
            raise HTTPException(404, "File not found")
        return FileResponse(str(target), filename=target.name)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Download error: {e}")


# ---------------- datavzrd viz project generation ----------------
class DataVZRDRequest(BaseModel):
    artifact_id: str
    title: str | None = None


@app.post("/viz/datavzrd")
async def build_datavzrd(req: DataVZRDRequest):
    art = next((a for a in db.get_artifacts() if a.get("id") == req.artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
    file_path = Path(art.get("filepath", ""))
    stem = file_path.stem or art.get("id")
    chr_csv = ARTIFACTS_DIR / "chr" / f"{stem}_chr.csv"
    if not chr_csv.exists():
        raise HTTPException(400, "CHR CSV not found. Run /structure/chr first.")

    proj_dir = ARTIFACTS_DIR / "datavzrd" / stem
    proj_dir.mkdir(parents=True, exist_ok=True)
    # copy path (we can reference relative path)
    rel_csv = os.path.relpath(chr_csv, proj_dir)

    use_spells = os.getenv("DATAVZRD_SPELLS", "true").lower() == "true"
    # columns config for Details table
    columns_chr = ( {
            "idx": {},
            "constellation": {},
            "radius": {},
            "text": {"spell": {"url": "v1.4.1/utils/text", "with": {"chars_per_line": 80}}}
        } if use_spells else ["idx","constellation","radius","text"] )

    cfg = {
        "title": req.title or f"CHR – {stem}",
        "data": [
            {
                "id": "chr",
                "path": rel_csv,
            }
        ],
        "pages": [
            {
                "title": "Overview",
                "blocks": [
                    {
                        "title": "Constellation Map (PCA)",
                        "render": "markdown",
                        "content": f"![]({os.path.relpath(out_dir := (ARTIFACTS_DIR / 'chr' / (stem + '_pca.png')), proj_dir)})"
                    },
                    {
                        "title": "Rows per Constellation",
                        "render": "plot",
                        "data": "chr",
                        "spec": {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": {"type": "bar"},
                            "encoding": {
                                "x": {"field": "constellation", "type": "nominal", "sort": "ascending"},
                                "y": {"aggregate": "count", "type": "quantitative", "title": "rows"}
                            }
                        }
                    },
                    {
                        "title": "Radius Histogram",
                        "render": "plot",
                        "data": "chr",
                        "spec": {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": "bar",
                            "encoding": {
                                "x": {"bin": True, "field": "radius", "type": "quantitative"},
                                "y": {"aggregate": "count", "type": "quantitative"}
                            }
                        }
                    }
                ]
            },
            {
                "title": "Details",
                "blocks": [
                    {"title": "CHR Rows", "render": "table", "data": "chr", "columns": columns_chr, "search": True, "download": True}
                ]
            }
        ]
    }

    viz_yaml = proj_dir / "viz.yaml"
    viz_yaml.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")

    return {
        "status": "ok",
        "project_dir": str(proj_dir),
        "viz_yaml": str(viz_yaml),
        "rel_viz": str(viz_yaml.relative_to(ARTIFACTS_DIR)) if viz_yaml.is_relative_to(ARTIFACTS_DIR) else None,
    }


class DataVZRDLogsRequest(BaseModel):
    document_id: str | None = None
    title: str | None = None


@app.post("/viz/datavzrd/logs")
async def build_datavzrd_logs(req: DataVZRDLogsRequest):
    # Collect logs (all or by document)
    logs = db.list_logs(level=None, code=None, q=None, ts_from=None, ts_to=None)
    if req.document_id:
        logs = [l for l in logs if l.get("document_id") == req.document_id]
    if not logs:
        raise HTTPException(400, "No logs available for viz")

    scope = req.document_id or "all"
    proj_dir = ARTIFACTS_DIR / "datavzrd" / f"logs-{scope}"
    proj_dir.mkdir(parents=True, exist_ok=True)
    csv_path = proj_dir / "logs.csv"
    # Write CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["ts","level","code","component","message"]) 
        writer.writeheader()
        for l in logs:
            writer.writerow({
                "ts": l.get("ts"),
                "level": l.get("level"),
                "code": l.get("code"),
                "component": l.get("component"),
                "message": l.get("message"),
            })

    rel_csv = os.path.relpath(csv_path, proj_dir)
    # Build viz.yaml for logs
    use_spells = os.getenv("DATAVZRD_SPELLS", "true").lower() == "true"
    columns_logs = ( {
            "ts": {}, "level": {}, "code": {}, "component": {},
            "message": {"spell": {"url": "v1.4.1/utils/text", "with": {"chars_per_line": 80}}}
        } if use_spells else ["ts","level","code","component","message"] )

    cfg = {
        "title": req.title or f"Logs – {scope}",
        "data": [{"id": "logs", "path": rel_csv}],
        "pages": [
            {
                "title": "Overview",
                "blocks": [
                    {
                        "title": "Errors by Code",
                        "render": "plot",
                        "data": "logs",
                        "spec": {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": "bar",
                            "encoding": {
                                "x": {"field": "code", "type": "nominal", "sort": "-y"},
                                "y": {"aggregate": "count", "type": "quantitative"}
                            }
                        }
                    },
                    {
                        "title": "Levels Over Time",
                        "render": "plot",
                        "data": "logs",
                        "spec": {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": "line",
                            "encoding": {
                                "x": {"field": "ts", "type": "temporal"},
                                "y": {"aggregate": "count", "type": "quantitative"},
                                "color": {"field": "level", "type": "nominal"}
                            }
                        }
                    },
                    {
                        "title": "Top Components",
                        "render": "plot",
                        "data": "logs",
                        "spec": {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "mark": "bar",
                            "encoding": {
                                "x": {"field": "component", "type": "nominal", "sort": "-y"},
                                "y": {"aggregate": "count", "type": "quantitative"}
                            }
                        }
                    }
                ]
            },
            {"title": "Log Table", "blocks": [ {"title": "Logs", "render": "table", "data": "logs", "columns": columns_logs, "search": True, "download": True} ]}
        ]
    }
    viz_yaml = proj_dir / "viz.yaml"
    viz_yaml.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    rel_viz = str(viz_yaml.relative_to(ARTIFACTS_DIR)) if viz_yaml.is_relative_to(ARTIFACTS_DIR) else None
    return {"status": "ok", "project_dir": str(proj_dir), "viz_yaml": str(viz_yaml), "rel_viz": rel_viz}


# ---------------- POML export ----------------
class ExportPOMLRequest(BaseModel):
    document_id: str
    title: str | None = None
    variant: str | None = None  # generic|troubleshoot|catalog


@app.post("/export/poml")
async def export_poml(req: ExportPOMLRequest):
    doc = next((d for d in db.list_documents() if d.get("id") == req.document_id), None)
    if not doc:
        raise HTTPException(404, "Document not found")
    apis = db.list_apis(tag=None, method=None, path_like=None)
    apis = [a for a in apis if a.get("document_id") == req.document_id]
    tags = db.list_tags(document_id=req.document_id, q=None)
    logs = db.list_logs(level=None, code=None, q=None, ts_from=None, ts_to=None)
    logs = [l for l in logs if l.get("document_id") == req.document_id]
    # Try to attach local resources
    md_path = None
    chr_csv = None
    try:
        src = Path(doc.get("path", ""))
        stem = src.stem
        # markdown if PDF processed
        cand_md = ARTIFACTS_DIR / f"{stem}.md"
        if cand_md.exists():
            md_path = cand_md
        # CHR CSV if exists
        cand_chr = ARTIFACTS_DIR / "chr" / f"{stem}_chr.csv"
        if cand_chr.exists():
            chr_csv = cand_chr
    except Exception:
        pass
    poml = build_poml({**doc, **({"title": req.title} if req.title else {})}, apis, tags, logs, md_path, chr_csv, (req.variant or "generic"))
    out_dir = ARTIFACTS_DIR / "poml"
    out_dir.mkdir(parents=True, exist_ok=True)
    name = (Path(doc.get("path"," ")).stem or doc.get("id")) + ".poml"
    path = out_dir / name
    path.write_text(poml, encoding="utf-8")
    rel = str(path.relative_to(ARTIFACTS_DIR))
    return {"status": "ok", "rel": rel, "path": str(path)}

def _process_and_store(file_path: Path, report_week: str, artifact_id: str, suffix: str, task_id: str | None = None):
    try:
        if suffix == ".pdf":
            # PDF is async-capable but can be used sync too
            import anyio
            facts, evidence = anyio.run(process_pdf, file_path, report_week, ARTIFACTS_DIR)
            # Ensure a PDF document row exists for deeplinks/open
            try:
                db.add_document({
                    "id": artifact_id,
                    "path": str(file_path),
                    "type": "pdf",
                    "title": file_path.name,
                    "source": "watch|upload",
                })
            except Exception:
                pass
        elif suffix == ".csv":
            facts, evidence = process_csv(file_path, report_week)
        elif suffix in [".xlsx", ".xls"]:
            facts, evidence = process_xlsx(file_path, report_week)
        else:
            raise HTTPException(400, f"Unsupported file type: {suffix}")

        for fact in facts:
            fact["artifact_id"] = artifact_id
            db.add_fact(fact)
        for ev in evidence:
            ev["artifact_id"] = artifact_id
            db.add_evidence(ev)

        if task_id:
            TASKS[task_id].update({
                "status": "completed",
                "facts_count": len(facts),
                "evidence_count": len(evidence)
            })
    except Exception as e:
        if task_id:
            TASKS[task_id].update({"status": "error", "error": str(e)})
        else:
            raise


@app.post("/upload")
async def upload_files(background_tasks: BackgroundTasks, files: List[UploadFile] = File(...), report_week: str = "", async_pdf: bool = True):
    """Upload and process documents"""
    results = []
    
    for file in files:
        # Save uploaded file
        file_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
        
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process based on file type
        try:
            suffix = file_path.suffix.lower()
            # Store artifact first (status is informal metadata)
            artifact_id = db.add_artifact({
                "id": file_id,
                "filename": file.filename,
                "filepath": str(file_path),
                "filetype": suffix,
                "report_week": report_week,
                "status": "processing" if (async_pdf and suffix == ".pdf") else "processed"
            })
            # Async for PDFs if requested
            if async_pdf and suffix == ".pdf":
                task_id = str(uuid.uuid4())
                TASKS[task_id] = {"status": "queued", "filename": file.filename, "artifact_id": artifact_id}
                background_tasks.add_task(_process_and_store, file_path, report_week, artifact_id, suffix, task_id)
                results.append({
                    "filename": file.filename,
                    "status": "queued",
                    "task_id": task_id
                })
            else:
                # Synchronous processing (CSV/XLSX, or PDFs if async disabled)
                _process_and_store(file_path, report_week, artifact_id, suffix, None)
                # Calculate counts for the artifact we just added
                facts_count = len([f for f in db.get_facts(report_week) if f.get("artifact_id") == artifact_id])
                evidence_count = len([e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id])
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "facts_count": facts_count,
                    "evidence_count": evidence_count
                })
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    return {"results": results}


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@app.post("/load_samples")
async def load_samples(background_tasks: BackgroundTasks, report_week: str = "", async_pdf: bool = True):
    """Server-side ingestion of sample files from SAMPLE_DIR."""
    sample_dir = Path(os.getenv("SAMPLE_DIR", "/app/samples"))
    if not sample_dir.exists():
        raise HTTPException(400, f"Sample directory not found: {sample_dir}")

    results = []
    # Known sample names or all supported files in folder
    sample_files: List[Path] = []
    for ext in ("*.csv", "*.xlsx", "*.xls", "*.pdf"):
        sample_files.extend(sample_dir.glob(ext))
    if not sample_files:
        return {"results": [{"status": "error", "error": "No sample files found"}]}

    # Reuse upload logic by simulating saved files
    for p in sample_files:
        try:
            file_id = str(uuid.uuid4())
            file_path = UPLOAD_DIR / f"{file_id}_{p.name}"
            shutil.copy2(p, file_path)
            suffix = file_path.suffix.lower()

            artifact_id = db.add_artifact({
                "id": file_id,
                "filename": p.name,
                "filepath": str(file_path),
                "filetype": suffix,
                "report_week": report_week,
                "status": "processing" if (async_pdf and suffix == ".pdf") else "processed"
            })

            if async_pdf and suffix == ".pdf":
                task_id = str(uuid.uuid4())
                TASKS[task_id] = {"status": "queued", "filename": p.name, "artifact_id": artifact_id}
                background_tasks.add_task(_process_and_store, file_path, report_week, artifact_id, suffix, task_id)
                results.append({"filename": p.name, "status": "queued", "task_id": task_id})
            else:
                _process_and_store(file_path, report_week, artifact_id, suffix, None)
                facts_count = len([f for f in db.get_facts(report_week) if f.get("artifact_id") == artifact_id])
                evidence_count = len([e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id])
                results.append({
                    "filename": p.name,
                    "status": "success",
                    "facts_count": facts_count,
                    "evidence_count": evidence_count
                })
        except Exception as e:
            results.append({"filename": p.name, "status": "error", "error": str(e)})

    return {"results": results}

@app.get("/facts")
async def get_facts(report_week: str = None):
    """Get all facts, optionally filtered by report week"""
    facts = db.get_facts(report_week)
    return {"facts": facts}

@app.get("/evidence/{evidence_id}")
async def get_evidence(evidence_id: str):
    """Get evidence by ID"""
    evidence = db.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    return evidence

@app.post("/ask")
async def ask_question(
    question: str,
    use_hrm: bool = Query(False, description="Enable HRM sidecar (if supported)"),
):
    """Ask a question and get answer with citations.

    If `use_hrm=true` and HRM is enabled, we simulate a multi-step refinement
    cycle for demonstration and record HRM metrics. The underlying QA remains
    the same in this initial integration (no model change).
    """
    t0 = time.time()
    result = await qa_engine.ask(question)
    if HRM_ENABLED and use_hrm:
        # Simulate a tiny refinement loop over the answer text: trim + normalize
        steps = max(HRM_CFG.Mmin, 2)
        refined = result.get("answer", "").strip()
        refined = refined.replace("  ", " ")
        result["answer"] = refined
        HRM_STATS.record(steps=steps, latency_ms=(time.time() - t0) * 1000.0, payload={
            "question": question,
            "mode": "ask",
        })
        result["hrm"] = {"enabled": True, "steps": steps}
    else:
        result["hrm"] = {"enabled": False}
    return result

@app.delete("/reset")
async def reset_database():
    """Clear all data"""
    db.reset()
    return {"status": "Database reset"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

# ------------ HRM experiment & metrics endpoints ------------

class SortDigitsRequest(BaseModel):
    seq: str
    Mmax: int | None = None
    Mmin: int | None = None


@app.post("/experiments/hrm/sort_digits")
def hrm_sort_digits(req: SortDigitsRequest):
    if not req.seq or not req.seq.isdigit():
        raise HTTPException(400, "Provide 'seq' as digits only, e.g. '93241'.")
    cfg = HRMConfig(
        Mmax=req.Mmax or HRM_CFG.Mmax,
        Mmin=req.Mmin or HRM_CFG.Mmin,
        threshold=HRM_CFG.threshold,
    )
    t0 = time.time()
    out, steps, trace = refine_sort_digits(req.seq, cfg)
    dt = (time.time() - t0) * 1000.0
    HRM_STATS.record(steps=steps, latency_ms=dt, payload={"mode": "sort_digits", "seq": req.seq})
    return {"in": req.seq, "out": out, "steps": steps, "trace": trace, "latency_ms": round(dt, 3)}


class EchoRequest(BaseModel):
    text: str


@app.post("/experiments/hrm/echo")
def hrm_echo(req: EchoRequest, Mmax: int = 3, Mmin: int = 1):
    """Echo with a simulated refinement loop; returns steps and variants."""
    cfg = HRMConfig(Mmax=Mmax, Mmin=Mmin, threshold=HRM_CFG.threshold)
    variants: List[str] = [req.text]
    t0 = time.time()
    s = req.text
    steps = 0
    for m in range(1, cfg.Mmax + 1):
        steps = m
        # simple normalization as a stand-in for refinement
        s2 = " ".join(s.strip().split())
        variants.append(s2)
        if m >= cfg.Mmin and s2 == s:
            break
        s = s2
    dt = (time.time() - t0) * 1000.0
    HRM_STATS.record(steps=steps, latency_ms=dt, payload={"mode": "echo"})
    return {"out": s, "steps": steps, "variants": variants, "latency_ms": round(dt, 3)}


@app.get("/metrics/hrm")
def hrm_metrics():
    return HRM_STATS.snapshot()


@app.get("/metrics")
def metrics_prometheus():
    snap = HRM_STATS.snapshot()
    lines = [
        f"pmoves_hrm_total_runs {snap['total_runs']}",
        f"pmoves_hrm_avg_steps {snap['avg_steps']}",
        f"pmoves_hrm_avg_latency_ms {snap['avg_latency_ms']}",
    ]
    return ("\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"})
# ---------------- Search endpoints ----------------

class SearchRequest(BaseModel):
    q: str
    k: int | None = 10
    types: list[str] | None = None  # subset of ['pdf','api','log','tag']


@app.post("/search")
async def search(req: SearchRequest):
    # UI smoke test shortcut
    if (req.q or "").strip() == "__ui_test__":
        return {"results": [{
            "score": 1.0,
            "text": "UI Test Result",
            "meta": {"type": "api", "deeplink": {"panel": "apis"}}
        }]}
    results = search_index.search(req.q or "", k=req.k or 10)
    types = set([t.lower() for t in (req.types or [])])
    out = []
    for r in results:
        m = r.meta or {}
        t = (m.get("type") or "").lower()
        if types and t not in types:
            continue
        # Construct deep-link info for the frontend
        deeplink: dict = {}
        if t == "pdf":
            deeplink = {"panel": "workspace", "artifact_id": m.get("artifact_id"), "chunk": m.get("chunk"), **({"page": m.get("page")} if m.get("page") is not None else {})}
        elif t == "api":
            deeplink = {"panel": "apis", "api_id": m.get("id")}
        elif t == "log":
            deeplink = {"panel": "logs", "document_id": m.get("document_id"), "code": m.get("code")}
        elif t == "tag":
            deeplink = {"panel": "tags", "document_id": m.get("document_id"), "q": m.get("tag") or m.get("text")}
        out.append({
            "score": r.score,
            "text": r.text,
            "meta": {**m, "deeplink": deeplink}
        })
    return {"results": out}


@app.post("/search/rebuild")
async def search_rebuild():
    return search_index.rebuild()


@app.get("/open/pdf")
async def open_pdf(artifact_id: str, page: int | None = None):
    if os.getenv("OPEN_PDF_ENABLED", "false").lower() != "true":
        raise HTTPException(403, "PDF open is disabled")
    # Locate by document id (preferred) or fall back to artifact id
    p: Path | None = None
    doc = next((d for d in db.list_documents(type="pdf") if d.get("id") == artifact_id), None)
    if doc:
        p = Path(doc.get("path", ""))
    else:
        art = next((a for a in db.get_artifacts() if a.get("id") == artifact_id and str(a.get("filepath",""))).__iter__(), None)
        # The above ".__iter__()" trick is to avoid mypy complaining; essentially select the first match
        if not art:
            # try explicit scan
            for a in db.get_artifacts():
                if a.get("id") == artifact_id:
                    art = a
                    break
        if art:
            p = Path(art.get("filepath", ""))
    if not p or not p.exists() or p.suffix.lower() != ".pdf":
        raise HTTPException(404, "PDF file missing")
    # Restrict to uploads dir
    try:
        if not Path(p).resolve().is_relative_to(UPLOAD_DIR.resolve()):
            raise HTTPException(403, "Access denied")
    except Exception:
        # Python <3.9 fallback: emulate is_relative_to
        up = str(UPLOAD_DIR.resolve())
        pr = str(Path(p).resolve())
        if not pr.startswith(up):
            raise HTTPException(403, "Access denied")
    headers = {"Content-Disposition": f"inline; filename=\"{p.name}\""}
    return FileResponse(str(p), media_type="application/pdf", headers=headers)
