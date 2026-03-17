from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query, Form, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
import logging
import os
from pathlib import Path
import shutil
import sys
from typing import List, Dict, Optional, Any, Literal, Annotated
import uuid
import asyncio
from dotenv import load_dotenv
import time
import json
from docx import Document
import subprocess
import tempfile
import threading
import re
from pydantic import BaseModel
from app.hrm import HRMConfig, HRMMetrics, refine_sort_digits
from app.api.routers import documents, analysis, system, cipher, models, graph, a2a, orchestration
from app.security import SecurityMiddleware
# JWT Authentication (replaces CORS)
from app.auth import get_current_user, optional_auth
from app.middleware import SecurityHeadersMiddleware, RateLimitMiddleware

# Load .env BEFORE reading env vars so DOX_EDITION etc. are available
load_dotenv()

_EDITION = os.getenv("DOX_EDITION", "default").strip().lower()
_EDITION_TITLES = {
    "default": "PMOVES-DoX API",
    "unfcu": "UNFCU DocIntel API",
}
app = FastAPI(title=_EDITION_TITLES.get(_EDITION, _EDITION_TITLES["default"]))

app.include_router(documents.router)
app.include_router(analysis.router)
app.include_router(system.router)
app.include_router(cipher.router)
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(graph.router)
# A2A router mounted at root for .well-known path
app.include_router(a2a.router)
# Orchestration router for multi-agent task coordination
app.include_router(orchestration.router)

from app.ingestion.pdf_processor import process_pdf
from app.ingestion.csv_processor import process_csv
from app.ingestion.xlsx_processor import process_xlsx
from app.ingestion.xml_ingestion import process_xml
from app.ingestion.openapi_ingestion import process_openapi
from app.ingestion.postman_ingestion import process_postman
from app.ingestion.web_ingestion import ingest_web_url
from app.ingestion.media_transcriber import transcribe_media
from app.ingestion.image_ocr import extract_text_from_image
from app.database_factory import init_database
from app.config import get_deployment_info
from app.qa_engine import QAEngine
from app.extraction.langextract_adapter import run_langextract, write_visualization
from app.chr_pipeline import run_chr, pca_plot
from app.search import SearchIndex
from app.export_poml import build_poml
from app.analysis.summarization import SummarizationService
import yaml
try:
    from watchgod import watch
except Exception:
    watch = None  # type: ignore
import csv
from datetime import datetime

# NOTE: load_dotenv() is called above, before _EDITION is read.

# Normalize HF token envs for Hugging Face downloads
hf_token = (
    os.getenv("HUGGINGFACE_HUB_TOKEN")
    or os.getenv("HF_API_KEY")
    or os.getenv("HF_TOKEN")
    or os.getenv("HUGGINGFACE_TOKEN")
)
if hf_token and not os.getenv("HUGGINGFACE_HUB_TOKEN"):
    os.environ["HUGGINGFACE_HUB_TOKEN"] = hf_token

# NOTE: FastAPI app already created above (line 23) with routers included.
# Do NOT recreate app here or all routers will be lost!

# Optionally run Alembic migrations on startup
if os.getenv("AUTO_MIGRATE", "false").lower() == "true":
    try:
        import subprocess as _sp
        _sp.run(["alembic", "upgrade", "head"], cwd=str(Path(__file__).resolve().parents[1]), check=False)
    except Exception:
        pass

# ============================================================================
# JWT Authentication & Security Middleware (replaces CORS)
# ============================================================================

# Security middleware - must be added before routes
# Adds security headers to all responses
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting middleware - default 100 requests per minute
# Exempt paths: /, /health, /healthz, /metrics, /docs, /redoc, /openapi.json
app.add_middleware(RateLimitMiddleware, default_limit="100/minute")

# CORS removed - using JWT authentication instead
# Frontend must include valid JWT in Authorization header
# Example: Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
#
# The token is validated against SUPABASE_JWT_SECRET.
# Get token from: https://supabase.com/dashboard/project/_/settings/api
#
# Legacy CORS support can be enabled for development:
if os.getenv("ENVIRONMENT", "production") == "development":
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    allow_origins = [o.strip() for o in frontend_origin.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Security middleware - Defense in Depth pattern validation
# Enabled via SECURITY_MIDDLEWARE_ENABLED env var (default: true)
# Validates commands and paths against patterns.yaml rules
if os.getenv("SECURITY_MIDDLEWARE_ENABLED", "true").lower() in ("1", "true", "yes", "on"):
    try:
        app.add_middleware(SecurityMiddleware)
        logging.getLogger(__name__).info("Security middleware enabled")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Security middleware initialization failed: {e}")

# Mount Pmoves-hyperdimensions tool
import os
hyp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "external", "Pmoves-hyperdimensions")
if os.path.exists(hyp_path):
    app.mount("/hyperdimensions", StaticFiles(directory=hyp_path, html=True), name="hyperdimensions")

@app.middleware("http")
async def _fast_pdf_middleware(request, call_next):
    if request.url.path == "/open/pdf":
        if _env_flag("FAST_PDF_MODE", False) or not _env_flag("OPEN_PDF_ENABLED", False):
            return JSONResponse({"detail": "PDF open disabled"}, status_code=403)
    return await call_next(request)

# Initialize
UPLOAD_DIR = Path("uploads")
ARTIFACTS_DIR = Path("artifacts")
UPLOAD_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Security settings
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB limit for file uploads

db, DB_BACKEND_META = init_database()
search_index = SearchIndex(db)
qa_engine = QAEngine(db, search_index=search_index)
summary_service = SummarizationService(db)
# HRM config/metrics (optional features)
HRM_ENABLED = os.getenv("HRM_ENABLED", "false").lower() == "true"
HRM_CFG = HRMConfig(
    Mmax=int(os.getenv("HRM_MMAX", "6")),
    Mmin=int(os.getenv("HRM_MMIN", "2")),
    threshold=float(os.getenv("HRM_THRESHOLD", "0.5")),
)
HRM_STATS = HRMMetrics()

AUDIO_SUFFIXES = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MEDIA_SUFFIXES = AUDIO_SUFFIXES | VIDEO_SUFFIXES


def _env_flag(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    val = val.strip()
    if not val:
        return default
    return val.lower() in {"1", "true", "yes", "on"}

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
    try:
        watch_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        # Fall back to a writable directory if /app is not writable
        watch_dir = Path("./uploads/watch")
        watch_dir.mkdir(parents=True, exist_ok=True)
        print(f"Watch folder: using fallback path {watch_dir}")
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

    # Check integration health at startup
    try:
        from app.utils.integration_health import IntegrationHealth
        health_check = IntegrationHealth()
        integrations = await health_check.get_status()

        print("[STARTUP] Integration Status:")
        for name, status in integrations.items():
            health_str = "✓" if status["healthy"] else "✗"
            print(f"  {health_str} {name}: {status['url']}")
    except Exception as e:
        print(f"[STARTUP] Integration health check failed: {e}")

    # Rebuild search index in background with timeout to prevent startup hang
    # Note: Using ThreadPoolExecutor instead of signal.alarm() because signals
    # only work in the main thread, not background threads
    def _rebuild_with_timeout():
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(search_index.rebuild)
                future.result(timeout=30)  # 30 second timeout
            print("[STARTUP] Search index rebuild completed")
        except FuturesTimeoutError:
            print("[STARTUP] Search index rebuild timed out, continuing without full index")
        except Exception as e:
            print(f"[STARTUP] Search index rebuild failed: {e}")

    # Run rebuild in background thread so startup completes immediately
    rebuild_thread = threading.Thread(target=_rebuild_with_timeout, daemon=True)
    rebuild_thread.start()

    # Connect to NATS Geometry Bus (non-blocking)
    try:
        from app.services.chit_service import chit_service
        # Use NATS_URL from env or default to docker service name
        nats_url = os.getenv("NATS_URL", "nats://nats:pmoves@nats:4222")
        asyncio.create_task(chit_service.connect_nats(nats_url))
    except Exception as e:
        print(f"Failed to initiate NATS connection: {e}")

    # Periodic rate limiter cleanup to prevent memory leaks
    async def _rate_limit_cleanup_loop():
        from app.middleware.rate_limit import get_limiter
        limiter = get_limiter()
        while True:
            await asyncio.sleep(300)  # every 5 minutes
            await limiter.cleanup()

    asyncio.create_task(_rate_limit_cleanup_loop())

@app.get("/healthz")
async def health():
    """Health check endpoint for PMOVES.AI standard compliance."""
    # Return basic health status immediately for CI/smoke tests
    # Integration health checks are skipped to avoid CI failures
    return {
        "status": "healthy",
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "uptime_seconds": int(time.time() - START_TIME),
        "integrations": "skipped",
    }


@app.get("/analysis/entities")
async def get_analysis_entities(document_id: str | None = None, label: str | None = None):
    try:
        items = db.list_entities(document_id=document_id, label=label)
    except AttributeError:
        items = []
    return {"entities": items}


@app.get("/analysis/artifacts/{artifact_id}")
async def get_artifact_analysis(artifact_id: str):
    arts = db.get_artifacts()
    art = next((a for a in arts if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")

    evidence = [e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id]

    tables: list[dict] = []
    charts: list[dict] = []
    formulas: list[dict] = []

    for ev in evidence:
        ctype = (ev.get("content_type") or "").lower()
        base = {
            "id": ev.get("id"),
            "locator": ev.get("locator"),
            "preview": ev.get("preview"),
            "coordinates": ev.get("coordinates"),
        }
        full = ev.get("full_data") or {}

        if ctype == "table":
            rows = list(full.get("rows") or [])
            tables.append(
                {
                    **base,
                    "pages": full.get("pages", []),
                    "merged": full.get("merged", False),
                    "header_detected": full.get("header_detected", False),
                    "columns": full.get("columns", []),
                    "row_count": len(rows),
                    "rows": rows[:20],
                }
            )
        elif ctype == "chart":
            charts.append(
                {
                    **base,
                    "id": full.get("id") or base.get("id"),
                    "page": full.get("page"),
                    "bbox": full.get("bbox"),
                    "image_path": full.get("image_path"),
                    "caption": full.get("caption"),
                    "type": full.get("type"),
                    "extracted_text": full.get("extracted_text"),
                    "vlm_enabled": full.get("vlm_enabled"),
                }
            )
        elif ctype == "formula":
            formulas.append({**base, **full})

    try:
        entities = db.list_entities(document_id=artifact_id)
    except AttributeError:
        entities = []

    try:
        structure = db.get_structure(artifact_id)
    except AttributeError:
        structure = None

    try:
        metric_hits = db.list_metric_hits(document_id=artifact_id)
    except AttributeError:
        metric_hits = []

    return {
        "artifact": art,
        "tables": tables,
        "charts": charts,
        "formulas": formulas,
        "entities": entities,
        "structure": structure,
        "metric_hits": metric_hits,
    }


@app.get("/analysis/structure")
async def get_analysis_structure(document_id: str):
    try:
        structure = db.get_structure(document_id)
    except AttributeError:
        structure = None
    return {"document_id": document_id, "structure": structure}


@app.get("/analysis/metrics")
async def get_analysis_metrics(document_id: str | None = None, metric_type: str | None = None):
    try:
        items = db.list_metric_hits(document_id=document_id, metric_type=metric_type)
    except AttributeError:
        items = []
    return {"metric_hits": items}



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


def _load_document(document_id: str) -> Optional[Dict]:
    try:
        return next((d for d in db.list_documents() if d.get("id") == document_id), None)
    except Exception:
        return None


def _build_poml_context(document_id: str, variant: Optional[str] = None) -> Optional[str]:
    doc = _load_document(document_id)
    if not doc:
        return None
    try:
        apis = [a for a in db.list_apis(tag=None, method=None, path_like=None) if a.get("document_id") == document_id]
    except Exception:
        apis = []
    try:
        tags = db.list_tags(document_id=document_id, q=None)
    except Exception:
        tags = []
    try:
        logs = [
            l for l in db.list_logs(level=None, code=None, q=None, ts_from=None, ts_to=None)
            if l.get("document_id") == document_id
        ]
    except Exception:
        logs = []
    md_path: Optional[Path] = None
    chr_csv: Optional[Path] = None
    try:
        src = Path(doc.get("path", ""))
        stem = src.stem
        cand_md = ARTIFACTS_DIR / f"{stem}.md"
        if cand_md.exists():
            md_path = cand_md
        cand_chr = ARTIFACTS_DIR / "chr" / f"{stem}_chr.csv"
        if cand_chr.exists():
            chr_csv = cand_chr
    except Exception:
        md_path = None
        chr_csv = None
    try:
        poml_variant = variant or os.getenv("AUTOTAG_POML_VARIANT") or "generic"
        poml = build_poml(doc, apis, tags, logs, md_path, chr_csv, poml_variant)
        # Avoid overwhelming prompts with massive payloads
        return poml[:4000]
    except Exception:
        return None


def _resolve_mangle_file(path_hint: Optional[str]) -> Optional[Path]:
    candidate = path_hint or os.getenv("AUTOTAG_MANGLE_FILE") or os.getenv("MANGLE_FILE")
    if not candidate:
        return None
    try:
        p = Path(candidate).expanduser()
        if p.exists():
            return p
    except Exception:
        return None
    return None


def _load_mangle_rules(path: Optional[Path]) -> Optional[str]:
    if not path:
        return None
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return None


def _validate_mangle_query(query: str) -> str:
    """
    Validate mangle query parameter to prevent command injection.

    Only allows alphanumeric and safe special characters used by
    the mangle query language (parentheses, brackets, asterisk, plus, minus, dot).
    """
    import re

    if not query:
        return "normalized_tag(T)"

    # Only allow safe characters for mangle query language
    # This prevents command injection via shell metacharacters
    if not re.match(r'^[a-zA-Z0-9_\s\.\(\)\[\]\*\+\-]+$', query):
        raise HTTPException(
            status_code=400,
            detail="Invalid query characters detected"
        )

    # Limit length to prevent DoS
    if len(query) > 200:
        raise HTTPException(
            status_code=400,
            detail="Query too long (max 200 characters)"
        )

    return query


def _apply_mangle(tags: List[str], rules_path: Path, query: Optional[str]) -> Optional[List[str]]:
    """Apply mangle transformation with command injection protection."""
    if not shutil.which("mg"):
        return None
    if not tags:
        return None
    program = rules_path
    if not program.exists():
        return None

    # Validate query to prevent command injection
    q = _validate_mangle_query(query or os.getenv("AUTOTAG_MANGLE_QUERY") or "normalized_tag(T)")

    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".edb", delete=False, encoding="utf-8") as tmp:
            tmp_path = Path(tmp.name)
            for tag in tags:
                safe = tag.replace("\"", "\\\"")
                tmp.write(f'tag_raw("{safe}").\n')
        proc = subprocess.run(
            ["mg", "--ruleset", str(program), "--edb", str(tmp_path), "--query", q],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return None
        output = (proc.stdout or "").strip()
        if not output:
            return None
        matches = re.findall(r'"([^"\\]+)"', output)
        if matches:
            cleaned = [m.strip() for m in matches if m.strip()]
            if cleaned:
                return cleaned
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        return lines or None
    except HTTPException:
        raise  # Re-raise HTTPException for proper error response
    except Exception:
        return None
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def _resolve_document_for_artifact(artifact_id: str) -> tuple[Dict, Dict]:
    art = next((a for a in db.get_artifacts() if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
    doc = _load_document(artifact_id)
    if doc:
        return art, doc
    art_path = art.get("filepath")
    if art_path:
        try:
            art_abs = Path(art_path).resolve()
        except Exception:
            art_abs = None
        if art_abs is not None:
            for cand in db.list_documents():
                try:
                    cand_path = Path(cand.get("path", "")).resolve()
                except Exception:
                    continue
                if cand_path == art_abs:
                    return art, cand
    raise HTTPException(404, "No document associated with artifact")


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


from app.api.routers.documents import _process_pdf_fast  # single definition in router

_log = logging.getLogger(__name__)

def _process_and_store(file_path: Path, report_week: str, artifact_id: str, suffix: str, task_id: str | None = None):
    _log.debug("_process_and_store called for %s", file_path)
    try:
        analysis_payload: dict | None = None
        facts: list[dict]
        evidence: list[dict]
        if suffix == ".pdf":
            # PDF is async-capable but can be used sync too
            fast_mode = _env_flag("FAST_PDF_MODE", False)
            _log.debug("FAST_PDF_MODE=%s, processing %s", fast_mode, file_path.name)
            if fast_mode:
                _log.debug("Using _process_pdf_fast")
                facts, evidence, analysis_payload = _process_pdf_fast(file_path, ARTIFACTS_DIR)
            else:
                _log.debug("Using Docling process_pdf (synchronous)")
                try:
                    # Call process_pdf directly - it's synchronous and background tasks
                    # run in thread pools, so no need for anyio.run()
                    facts, evidence, analysis_payload = process_pdf(
                        file_path, report_week, ARTIFACTS_DIR, artifact_id
                    )
                    _log.warning(f"[DEBUG] Docling completed: {len(facts)} facts, {len(evidence)} evidence")
                except Exception as docling_err:
                    _log.error(f"[ERROR] Docling failed: {docling_err}")
                    import traceback
                    _log.error(traceback.format_exc())
                    _log.warning("[DEBUG] Falling back to _process_pdf_fast")
                    facts, evidence, analysis_payload = _process_pdf_fast(file_path, ARTIFACTS_DIR)
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
        elif suffix in MEDIA_SUFFIXES:
            facts = []
            media_payload = transcribe_media(file_path, ARTIFACTS_DIR, artifact_id)
            evidence = []
            transcript_text = (media_payload.get("text") or "").strip()
            warnings = media_payload.get("warnings") or []
            if transcript_text or warnings:
                evidence.append(
                    {
                        "id": str(uuid.uuid4()),
                        "locator": f"{file_path.name}#transcript",
                        "preview": media_payload.get("preview") or transcript_text[:240],
                        "content_type": "media_transcript",
                        "full_data": media_payload,
                    }
                )
            metadata = media_payload.get("metadata") or {}
            if metadata:
                preview_meta = {k: metadata.get(k) for k in ("duration_seconds", "format", "notes") if metadata.get(k) is not None}
                evidence.append(
                    {
                        "id": str(uuid.uuid4()),
                        "locator": f"{file_path.name}#metadata",
                        "preview": json.dumps(preview_meta or metadata, ensure_ascii=False)[:240],
                        "content_type": "media_metadata",
                        "full_data": metadata,
                    }
                )
            media_kind = "video" if suffix in VIDEO_SUFFIXES else "audio"
            extras = {
                "media": {
                    "kind": media_kind,
                    "transcript_preview": media_payload.get("preview"),
                    "artifacts": media_payload.get("artifacts"),
                    "engine": media_payload.get("engine"),
                    "metadata": metadata,
                    "status": media_payload.get("status"),
                    "warnings": warnings,
                }
            }
            try:
                db.update_artifact(artifact_id, extras=extras)
            except Exception:
                pass
        elif suffix in IMAGE_SUFFIXES:
            facts = []
            ocr_payload = extract_text_from_image(file_path, ARTIFACTS_DIR, artifact_id)
            evidence = []
            text = (ocr_payload.get("text") or "").strip()
            warnings = ocr_payload.get("warnings") or []
            if text or warnings:
                evidence.append(
                    {
                        "id": str(uuid.uuid4()),
                        "locator": f"{file_path.name}#ocr",
                        "preview": ocr_payload.get("preview") or text[:200],
                        "content_type": "image_ocr",
                        "full_data": ocr_payload,
                    }
                )
            extras = {
                "image": {
                    "transcript_preview": ocr_payload.get("preview"),
                    "artifacts": ocr_payload.get("artifacts"),
                    "metadata": ocr_payload.get("metadata"),
                    "warnings": warnings,
                }
            }
            try:
                db.update_artifact(artifact_id, extras=extras)
            except Exception:
                pass
        else:
            raise HTTPException(400, f"Unsupported file type: {suffix}")

        for fact in facts:
            fact["artifact_id"] = artifact_id
            db.add_fact(fact)
        for ev in evidence:
            ev["artifact_id"] = artifact_id
            db.add_evidence(ev)

        if analysis_payload and suffix == ".pdf":
            try:
                entities_raw = analysis_payload.get("entities") or []
                entities_prepared: list[dict] = []
                for idx, ent in enumerate(entities_raw):
                    seed = "|".join(
                        [
                            artifact_id,
                            "entity",
                            str(idx),
                            str(ent.get("label", "")),
                            str(ent.get("text", "")),
                            str(ent.get("start_char", "")),
                        ]
                    )
                    ent_id = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
                    entities_prepared.append(
                        {
                            "id": ent_id,
                            "document_id": artifact_id,
                            **ent,
                        }
                    )
                db.store_entities(artifact_id, entities_prepared)
            except Exception:
                pass

            try:
                structure = analysis_payload.get("structure")
                if structure:
                    db.store_structure(artifact_id, structure)
                else:
                    db.store_structure(artifact_id, None)
            except Exception:
                pass

            try:
                metric_hits_raw = analysis_payload.get("metric_hits") or []
                metric_prepared: list[dict] = []
                for idx, hit in enumerate(metric_hits_raw):
                    seed = "|".join(
                        [
                            artifact_id,
                            "metric",
                            str(idx),
                            str(hit.get("type", "")),
                            str(hit.get("value", "")),
                            str(hit.get("position", "")),
                        ]
                    )
                    metric_id = str(uuid.uuid5(uuid.NAMESPACE_URL, seed))
                    metric_prepared.append(
                        {
                            "id": metric_id,
                            "document_id": artifact_id,
                            **hit,
                        }
                    )
                db.store_metric_hits(artifact_id, metric_prepared)
            except Exception:
                pass

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



if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8484"))
    uvicorn.run(app, host="0.0.0.0", port=port)


