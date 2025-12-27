from fastapi import APIRouter, HTTPException, Response
import csv
import io
import os
import time
from app.globals import TASKS, START_TIME, DB_BACKEND_META, env_flag, search_index, db, HRM_STATS

router = APIRouter()

try:
    from watchgod import watch
except Exception:
    watch = None  # type: ignore

@router.get("/")
async def root():
    return {"message": "PMOVES-DoX API", "status": "running"}

@router.get("/config")
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
    frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    
    return {
        "vlm_repo": os.getenv("DOCLING_VLM_REPO"),
        "database": DB_BACKEND_META,
        "hf_auth": bool(os.getenv("HUGGINGFACE_HUB_TOKEN")),
        "frontend_origin": frontend_origin,
        "gpu": gpu,
        "ollama": ollama,
        "offline": offline,
        "open_pdf_enabled": env_flag("OPEN_PDF_ENABLED", False),
    }

@router.get("/tasks")
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

@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@router.get("/health")
async def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
    }

@router.get("/watch")
async def watch_status():
    return {
        "enabled": env_flag("WATCH_ENABLED", True),
        "dir": os.getenv("WATCH_DIR", "/app/watch"),
        "debounce_ms": int(os.getenv("WATCH_DEBOUNCE_MS", "1000")),
        "min_bytes": int(os.getenv("WATCH_MIN_BYTES", "1")),
        "available": bool(watch),
    }

@router.get("/metrics/hrm")
def hrm_metrics():
    return HRM_STATS.snapshot()

@router.get("/metrics")
def metrics_prometheus():
    snap = HRM_STATS.snapshot()
    lines = [
        f"pmoves_hrm_total_runs {snap['total_runs']}",
        f"pmoves_hrm_avg_steps {snap['avg_steps']}",
        f"pmoves_hrm_avg_latency_ms {snap['avg_latency_ms']}",
    ]
    return ("\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"})

@router.get("/logs")
async def get_logs(level: str | None = None, code: str | None = None, q: str | None = None, document_id: str | None = None):
    logs = db.list_logs(level=level, code=code, q=q, document_id=document_id)
    return {"logs": logs}

@router.get("/logs/export")
async def export_logs(level: str | None = None):
    logs = db.list_logs(level=level)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ts", "level", "code", "component", "message"])
    for log in logs:
        writer.writerow([log.get("ts"), log.get("level"), log.get("code"), log.get("component"), log.get("message")])
    return Response(content=output.getvalue(), media_type="text/csv")

@router.get("/apis")
async def get_apis(method: str | None = None, tag: str | None = None):
    apis = db.list_apis(method=method, tag=tag)
    return {"apis": apis}

@router.get("/apis/{api_id}")
async def get_api_detail(api_id: str):
    all_apis = db.list_apis()
    api = next((a for a in all_apis if a["id"] == api_id), None)
    if not api:
        raise HTTPException(404, "API not found")
    return api

@router.get("/tags")
async def get_tags(document_id: str | None = None):
    tags = db.list_tags(document_id=document_id)
    return {"tags": tags}
