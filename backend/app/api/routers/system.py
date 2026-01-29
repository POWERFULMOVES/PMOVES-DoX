"""System information and configuration API router.

Provides endpoints for health checks, configuration discovery,
task status monitoring, and system metrics.
"""

from fastapi import APIRouter, HTTPException, Response
import csv
import io
import os
import time
from app.globals import TASKS, START_TIME, DB_BACKEND_META, env_flag, search_index, db, HRM_STATS


async def check_ollama_available(base_url: str) -> bool:
    """Check if Ollama is available using async HTTP client.

    Args:
        base_url: The base URL of the Ollama service.

    Returns:
        True if Ollama is responding, False otherwise.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def is_docked_mode() -> bool:
    """Detect if DoX is running in docked mode within PMOVES.AI.

    Docked mode is indicated by:
    1. DOCKED_MODE=true environment variable (explicit)
    2. NATS_URL pointing to parent NATS (nats://nats:4222 instead of :4223)

    Returns:
        True if running in docked mode, False for standalone.
    """
    # Explicit check first
    if os.getenv("DOCKED_MODE", "").lower() in {"1", "true", "yes"}:
        return True

    # Check NATS URL - parent uses port 4222, standalone uses 4223
    nats_url = os.getenv("NATS_URL", "")
    if nats_url == "nats://nats:4222":
        return True
    if nats_url == "nats://nats:4223":
        return False

    # Default to standalone if not explicitly docked
    return False


router = APIRouter()

try:
    from watchgod import watch
except Exception:
    watch = None  # type: ignore

@router.get("/")
async def root():
    """Root endpoint providing API status message.

    Returns:
        A dictionary with a message indicating the API name and status.
    """
    return {"message": "PMOVES-DoX API", "status": "running"}


@router.get("/config")
async def config():
    """Get system configuration and deployment information.

    Detects GPU availability, Ollama connectivity, and deployment mode
    (standalone vs docked with parent PMOVES.AI).

    Returns:
        A dictionary containing:
        - vlm_repo: VLM model repository for PDF processing
        - database: Database backend metadata
        - hf_auth: Whether HuggingFace authentication is configured
        - frontend_origin: Allowed CORS origins
        - gpu: GPU availability and device count
        - ollama: Ollama service availability
        - offline: Whether offline mode is enabled
        - open_pdf_enabled: Whether PDF viewer links are enabled
        - deployment: Deployment mode (standalone/docked) and service URLs
    """
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
    ollama["available"] = await check_ollama_available(ollama["base_url"])
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
        "deployment": {
            "mode": "docked" if is_docked_mode() else "standalone",
            "nats_url": os.getenv("NATS_URL", "nats://nats:4222"),
            "tensorzero_url": os.getenv("TENSORZERO_BASE_URL", "http://tensorzero-gateway:3030"),
        },
    }

@router.get("/tasks")
async def list_tasks():
    """List all background tasks with status summary.

    Returns:
        A dictionary containing:
        - total: Total number of tasks
        - queued: Number of queued tasks
        - completed: Number of completed tasks
        - errored: Number of failed tasks
        - queued_items: List of queued task details
    """
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
    """Get the status of a specific background task.

    Args:
        task_id: The unique identifier of the task.

    Returns:
        Task details including status and result.

    Raises:
        HTTPException: 404 if the task is not found.
    """
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task

@router.get("/health")
async def health():
    """Health check endpoint for monitoring.

    Returns:
        A dictionary containing:
        - status: Always "ok" if the service is running
        - uptime_seconds: Service uptime in seconds
    """
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - START_TIME),
    }

@router.get("/watch")
async def watch_status():
    """Get watch folder configuration and status.

    Returns:
        A dictionary containing:
        - enabled: Whether watch folder monitoring is enabled
        - dir: Directory being watched
        - debounce_ms: File stability debounce time in milliseconds
        - min_bytes: Minimum file size to trigger processing
        - available: Whether watchgod library is available
    """
    return {
        "enabled": env_flag("WATCH_ENABLED", True),
        "dir": os.getenv("WATCH_DIR", "/app/watch"),
        "debounce_ms": int(os.getenv("WATCH_DEBOUNCE_MS", "1000")),
        "min_bytes": int(os.getenv("WATCH_MIN_BYTES", "1")),
        "available": bool(watch),
    }

@router.get("/metrics/hrm")
def hrm_metrics():
    """Get HRM (Halting Reasoning Module) metrics snapshot.

    Returns:
        A dictionary with HRM statistics including total runs,
        average steps, and average latency.
    """
    return HRM_STATS.snapshot()

@router.get("/metrics")
def metrics_prometheus():
    """Get Prometheus-formatted metrics for monitoring systems.

    Returns:
        A tuple of (metrics_text, status_code, headers) with
        Prometheus text format metrics.
    """
    snap = HRM_STATS.snapshot()
    lines = [
        f"pmoves_hrm_total_runs {snap['total_runs']}",
        f"pmoves_hrm_avg_steps {snap['avg_steps']}",
        f"pmoves_hrm_avg_latency_ms {snap['avg_latency_ms']}",
    ]
    return ("\n".join(lines) + "\n", 200, {"Content-Type": "text/plain; version=0.0.4"})

@router.get("/logs")
async def get_logs(level: str | None = None, code: str | None = None, q: str | None = None, document_id: str | None = None):
    """Query system logs with optional filters.

    Args:
        level: Filter by log level (ERROR, WARN, INFO, etc.)
        code: Filter by error code
        q: Full-text search query
        document_id: Filter by associated document ID

    Returns:
        A dictionary with a "logs" key containing the filtered log entries.
    """
    logs = db.list_logs(level=level, code=code, q=q, document_id=document_id)
    return {"logs": logs}

@router.get("/logs/export")
async def export_logs(level: str | None = None):
    """Export logs as CSV file.

    Args:
        level: Optional filter by log level.

    Returns:
        A CSV formatted Response with columns: ts, level, code, component, message.
    """
    logs = db.list_logs(level=level)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ts", "level", "code", "component", "message"])
    for log in logs:
        writer.writerow([log.get("ts"), log.get("level"), log.get("code"), log.get("component"), log.get("message")])
    return Response(content=output.getvalue(), media_type="text/csv")

@router.get("/apis")
async def get_apis(method: str | None = None, tag: str | None = None):
    """List discovered API endpoints from imported collections.

    Args:
        method: Filter by HTTP method (GET, POST, etc.)
        tag: Filter by tag/category

    Returns:
        A dictionary with an "apis" key containing the filtered API list.
    """
    apis = db.list_apis(method=method, tag=tag)
    return {"apis": apis}

@router.get("/apis/{api_id}")
async def get_api_detail(api_id: str):
    """Get detailed information about a specific API endpoint.

    Args:
        api_id: The unique identifier of the API.

    Returns:
        Detailed API information including path, method, and parameters.

    Raises:
        HTTPException: 404 if the API is not found.
    """
    all_apis = db.list_apis()
    api = next((a for a in all_apis if a["id"] == api_id), None)
    if not api:
        raise HTTPException(404, "API not found")
    return api

@router.get("/tags")
async def get_tags(document_id: str | None = None):
    """List extracted tags with optional document filtering.

    Args:
        document_id: Optional filter to tags from a specific document.

    Returns:
        A dictionary with a "tags" key containing the filtered tag list.
    """
    tags = db.list_tags(document_id=document_id)
    return {"tags": tags}
