from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
import asyncio
import logging
import uuid
import time
import json
import csv
import yaml
import os
import re
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

from app.globals import (
    db, qa_engine, summary_service, HRM_ENABLED, HRM_CFG, HRM_STATS,
    ARTIFACTS_DIR, env_flag, UPLOAD_DIR
)
from app.hrm import HRMConfig, refine_sort_digits
from app.auth import get_current_user, optional_auth
# from app.ingestion.poml_builder import build_poml

router = APIRouter()

# ---------------- Models ----------------

class ExtractTagsRequest(BaseModel):
    text: str | None = None
    document_id: str | None = None
    dry_run: bool = False
    use_hrm: bool = False
    provider: str | None = None
    model: str | None = None

class AutoTagRequest(BaseModel):
    document_id: str
    provider: str | None = None
    model: str | None = None

class LangExtractRequest(BaseModel):
    text: str
    schema_name: str  # e.g. "person", "invoice"
    provider: str | None = None
    model: str | None = None

class SummaryGenerateRequest(BaseModel):
    document_id: str | None = None
    artifact_ids: List[str] | None = None
    context: str = "general"
    length: str = "medium"
    format: str = "paragraph"
    style: str | None = None
    scope: str | None = None
    force_refresh: bool = False

class ConvertRequest(BaseModel):
    document_id: str | None = None
    artifact_id: str | None = None
    target_format: str = "markdown"  # markdown|text
    format: str | None = None

class CHRRequest(BaseModel):
    document_id: str | None = None
    artifact_id: str | None = None
    K: int | None = None
    units_mode: str | None = None

class DataVZRDRequest(BaseModel):
    document_id: str | None = None
    artifact_id: str | None = None
    title: str | None = None

class DataVZRDLogsRequest(BaseModel):
    document_id: str | None = None
    title: str | None = None

class ExportPOMLRequest(BaseModel):
    document_id: str
    title: str | None = None
    variant: str | None = None

class SortDigitsRequest(BaseModel):
    seq: str
    Mmax: int | None = None
    Mmin: int | None = None

class EchoRequest(BaseModel):
    text: str

# ---------------- Endpoints ----------------

@router.get("/facts")
async def get_facts(
    report_week: str = None,
    # TODO: Use user_id for user-scoped results in future implementation
    _user_id: str = Depends(optional_auth)
):
    """Get all facts, optionally filtered by report week.

    Authentication: Optional. Currently returns global results.
    Future: Authenticated users will get user-scoped facts.
    """
    facts = db.get_facts(report_week)
    return {"facts": facts}

@router.get("/analysis/financials")
async def get_financial_statements(
    artifact_id: str | None = None,
    # TODO: Use user_id for user-scoped results in future implementation
    _user_id: str = Depends(optional_auth)
):
    """Return detected financial statements from processed tables.

    Authentication: Optional. Currently returns global results.
    Future: Authenticated users will get user-scoped statements.
    """
    statements: List[Dict[str, Any]] = []
    for ev in db.get_all_evidence():
        if artifact_id and ev.get("artifact_id") != artifact_id:
            continue
        if ev.get("content_type") not in {"financial_table", "table"}:
            continue
        full_data = ev.get("full_data") or {}
        if not isinstance(full_data, dict):
            continue
        statement = full_data.get("statement") or {}
        if not isinstance(statement, dict):
            continue
        stmt_type = statement.get("type")
        if stmt_type in (None, "", "unknown"):
            continue
        statements.append(
            {
                "evidence_id": ev.get("id"),
                "artifact_id": ev.get("artifact_id"),
                "locator": ev.get("locator"),
                "statement_type": stmt_type,
                "confidence": statement.get("confidence"),
                "summary": statement.get("summary") or {},
                "columns": full_data.get("columns", []),
                "rows": full_data.get("rows", []),
                "header_info": full_data.get("header_info"),
            }
        )

    statements.sort(
        key=lambda item: (
            item.get("artifact_id") or "",
            item.get("statement_type") or "",
            item.get("locator") or "",
        )
    )
    return {"statements": statements}

@router.get("/evidence/{evidence_id}")
async def get_evidence(
    evidence_id: str,
    # TODO: Use user_id for user-scoped access control in future implementation
    _user_id: str = Depends(optional_auth)
):
    """Get evidence by ID.

    Authentication: Optional. Currently allows global access.
    Future: Authenticated users will only access their own evidence.
    """
    evidence = db.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    return evidence

@router.post("/ask")
async def ask_question(
    question: str,
    use_hrm: bool = Query(False, description="Enable HRM sidecar (if supported)"),
    # TODO: Use user_id for user-scoped context in future implementation
    _user_id: str = Depends(optional_auth),
):
    """Ask a question and get answer with citations.

    Authentication: Optional. Currently searches all documents.
    Future: Authenticated users will get answers from their own documents.
    """
    t0 = time.time()
    result = await qa_engine.ask(question)
    if HRM_ENABLED and use_hrm:
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

@router.delete("/reset")
async def reset_database(_user_id: str = Depends(get_current_user)):
    """Clear all data (authentication required)."""
    db.reset()
    return {"status": "Database reset"}

# ---------------- Tags & Extraction ----------------

@router.get("/tags")
async def list_tags(document_id: str | None = None):
    return {"tags": db.list_tags(document_id=document_id)}

@router.post("/extract/tags")
async def extract_tags_text(req: ExtractTagsRequest):
    text = req.text or ""
    if not text and req.document_id:
        # Fetch document text from DB (placeholder as we don't have a direct text store for docs yet, maybe from evidence)
        # For now, just use what's passed or empty
        pass

    if not text:
        return {"tags": []}

    # Try LLM extraction
    import requests
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "llama3.1")
    
    prompt = f"Extract 3-5 relevant tags for the following text. Return ONLY a comma-separated list of tags, no other text.\n\nText: {text[:1000]}"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
    }
    
    tags = []
    try:
        resp = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=10)
        if resp.ok:
            content = resp.json().get("response", "").strip()
            # Clean up response
            content = content.replace("Tags:", "").replace("tags:", "").strip()
            tags = [t.strip() for t in content.split(",") if t.strip()]
        else:
            logger.warning(f"LLM tagging returned non-OK status: {resp.status_code}")
    except requests.RequestException as e:
        logger.warning(f"LLM tagging request failed: {e}")
    except Exception as e:
        logger.error(f"LLM tagging unexpected error: {e}", exc_info=True)
    
    # Fallback to simple keywords if LLM fails or returns nothing
    if not tags:
        common_keywords = {"invoice", "receipt", "contract", "statement", "report", "financial", "log", "error", "warning"}
        text_lower = text.lower()
        tags = [kw for kw in common_keywords if kw in text_lower]
        
    return {"tags": tags}

@router.post("/autotag/{document_id}")
async def auto_tag_document(document_id: str, req: AutoTagRequest):
    # In a real app, we'd fetch the doc content. 
    # For this demo, we'll try to find evidence associated with this artifact/doc
    # and use that text.
    
    # Find artifact first (assuming document_id is artifact_id for now)
    evidence_list = db.get_all_evidence()
    doc_evidence = [e for e in evidence_list if e.get("artifact_id") == document_id]
    
    text_content = ""
    for ev in doc_evidence:
        if ev.get("preview"):
            text_content += ev.get("preview") + "\n"
            
    if not text_content:
        return {"status": "failed", "message": "No content found for document"}
        
    # Call extraction
    extract_req = ExtractTagsRequest(text=text_content)
    res = await extract_tags_text(extract_req)
    
    # Store tags (mock storage for now, or use db.add_tag if we want to persist)
    # We'll just return them
    return {"status": "success", "document_id": document_id, "tags": res["tags"]}

@router.get("/tags/presets")
async def get_tag_presets():
    return {"presets": ["Confidential", "Invoice", "Contract", "Resume"]}

# ---------------- Summaries ----------------

@router.get("/summaries")
async def list_summaries(document_id: str | None = None):
    # If document_id is provided, imply 'artifact' scope filter
    scope = "artifact" if document_id else None
    # We can fetch all and filter in memory if service doesn't support complex filtering
    summaries = summary_service.list_summaries(scope=scope)
    if document_id:
        # Filter strictly for this artifact
        summaries = [s for s in summaries if document_id in s["scope"]["artifact_ids"]]
    return {"summaries": summaries}

@router.post("/summaries/generate")
async def generate_summary(req: SummaryGenerateRequest):
    # Map request to service call
    # Default scope to 'workspace' if not artifact_ids
    scope = "artifact" if (req.scope == "artifact" or req.artifact_ids) else "workspace"
    
    # Ensure style is valid or default
    style = req.style if req.style in ("bullet", "executive", "action_items") else "bullet"
    
    result = summary_service.generate_summary(
        style=style,
        scope=scope,
        artifact_ids=req.artifact_ids,
        force_refresh=req.force_refresh,
    )
    return result

# ---------------- Conversion & Structure ----------------
# NOTE: Real implementations for /convert, /structure/chr, /viz/datavzrd,
# /viz/datavzrd/logs, and /export/poml are in main.py with @app decorators.
# Do NOT add placeholder endpoints here - they will shadow the real implementations.

# ---------------- Experiments ----------------

@router.post("/experiments/hrm/sort_digits")
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

@router.post("/experiments/hrm/echo")
def hrm_echo(req: EchoRequest, Mmax: int = 3, Mmin: int = 1):
    """Echo with a simulated refinement loop; returns steps and variants."""
    cfg = HRMConfig(Mmax=Mmax, Mmin=Mmin, threshold=HRM_CFG.threshold)
    variants: List[str] = [req.text]
    t0 = time.time()
    s = req.text
    steps = 0
    for m in range(1, cfg.Mmax + 1):
        steps = m
        s2 = " ".join(s.strip().split())
        variants.append(s2)
        if m >= cfg.Mmin and s2 == s:
            break
        s = s2
    dt = (time.time() - t0) * 1000.0
    HRM_STATS.record(steps=steps, latency_ms=dt, payload={"mode": "echo"})
    return {"out": s, "steps": steps, "variants": variants, "latency_ms": round(dt, 3)}


# ---------------- API Documentation Generator ----------------

def _is_ollama_available() -> bool:
    """Check if Ollama service is reachable."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        resp = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2.0)
        return resp.status_code == 200
    except requests.RequestException as e:
        logger.debug(f"Ollama not available: {e}")
        return False


def _extract_with_ollama(code: str, language: str, model: Optional[str]) -> Optional[List[Dict[str, Any]]]:
    """Use Ollama for endpoint extraction."""
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = model or os.getenv("OLLAMA_MODEL", "llama3.1")

    prompt = f"""Analyze the following {language} code and extract API endpoint definitions.

For each endpoint found, provide:
1. HTTP method (GET, POST, PUT, DELETE, PATCH)
2. Path/route (e.g., /api/users, /api/users/{{id}})
3. A brief summary of what the endpoint does
4. Request parameters (path params, query params)

Code to analyze:
```{language}
{code[:8000]}
```

Return the endpoints as a JSON array with this structure:
[
  {{
    "method": "GET",
    "path": "/api/users",
    "summary": "List all users",
    "parameters": [],
    "responses": {{"200": {{"description": "Success"}}}}
  }}
]

Return ONLY the JSON array, no other text."""

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
    }

    try:
        resp = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json=payload,
            timeout=60
        )
        if resp.ok:
            response_text = resp.json().get("response", "")
            # Try to parse JSON from response
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except requests.RequestException as e:
        logger.warning(f"Ollama API request failed: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse Ollama response as JSON: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during Ollama extraction: {e}", exc_info=True)

    return None


def _heuristic_endpoint_extraction(code: str, file_ext: str) -> List[Dict[str, Any]]:
    """Extract endpoints using regex patterns when LLM is unavailable."""
    endpoints = []

    if file_ext == ".py":
        # FastAPI patterns: @app.get("/path"), @router.post("/path")
        fastapi_pattern = r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(fastapi_pattern, code, re.IGNORECASE):
            method, path = match.groups()
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "summary": f"{method.upper()} {path}",
                "parameters": [],
                "responses": {"200": {"description": "Success"}}
            })

        # Flask patterns: @app.route("/path", methods=["GET"])
        flask_pattern = r'@(?:app|bp)\s*\.route\s*\(\s*["\']([^"\']+)["\'](?:.*?methods\s*=\s*\[([^\]]+)\])?'
        for match in re.finditer(flask_pattern, code, re.DOTALL):
            path = match.group(1)
            methods_str = match.group(2) or '"GET"'
            methods = re.findall(r'["\'](\w+)["\']', methods_str)
            for method in methods:
                endpoints.append({
                    "method": method.upper(),
                    "path": path,
                    "summary": f"{method.upper()} {path}",
                    "parameters": [],
                    "responses": {"200": {"description": "Success"}}
                })

    elif file_ext in (".js", ".ts"):
        # Express patterns: app.get('/path', ...), router.post('/path', ...)
        express_pattern = r'(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
        for match in re.finditer(express_pattern, code, re.IGNORECASE):
            method, path = match.groups()
            endpoints.append({
                "method": method.upper(),
                "path": path,
                "summary": f"{method.upper()} {path}",
                "parameters": [],
                "responses": {"200": {"description": "Success"}}
            })

        # Next.js API route pattern (export functions)
        nextjs_pattern = r'export\s+(?:async\s+)?function\s+(GET|POST|PUT|DELETE|PATCH)'
        for match in re.finditer(nextjs_pattern, code):
            method = match.group(1)
            endpoints.append({
                "method": method.upper(),
                "path": "/api/[route]",
                "summary": f"{method.upper()} handler",
                "parameters": [],
                "responses": {"200": {"description": "Success"}}
            })

    return endpoints


def _heuristic_schema_extraction(code: str, file_ext: str) -> List[Dict[str, Any]]:
    """Extract schema definitions using regex patterns."""
    schemas = []

    if file_ext == ".py":
        # Pydantic/dataclass patterns
        class_pattern = r'class\s+(\w+)\s*\((?:BaseModel|BaseSettings|TypedDict)'
        for match in re.finditer(class_pattern, code):
            schema_name = match.group(1)
            schemas.append({
                "name": schema_name,
                "type": "object",
                "properties": {},
                "required": []
            })

    elif file_ext == ".ts":
        # TypeScript interface pattern
        interface_pattern = r'(?:interface|type)\s+(\w+)'
        for match in re.finditer(interface_pattern, code):
            schema_name = match.group(1)
            schemas.append({
                "name": schema_name,
                "type": "object",
                "properties": {},
                "required": []
            })

    return schemas


def _build_openapi_spec(
    endpoints: List[Dict[str, Any]],
    schemas: List[Dict[str, Any]],
    title: str,
    version: str,
    description: str,
) -> Dict[str, Any]:
    """Build a complete OpenAPI 3.0 specification from extracted components."""
    # Build paths object
    paths: Dict[str, Dict[str, Any]] = {}
    for ep in endpoints:
        path = ep.get("path", "/")
        method = ep.get("method", "GET").lower()

        if path not in paths:
            paths[path] = {}

        operation: Dict[str, Any] = {
            "summary": ep.get("summary", ""),
            "description": ep.get("description", ""),
            "responses": ep.get("responses", {"200": {"description": "Success"}}),
        }

        if ep.get("parameters"):
            operation["parameters"] = ep["parameters"]

        if ep.get("request_body"):
            operation["requestBody"] = ep["request_body"]

        if ep.get("tags"):
            operation["tags"] = ep["tags"]

        paths[path][method] = operation

    # Build components/schemas
    components: Dict[str, Any] = {}
    if schemas:
        components["schemas"] = {
            s["name"]: {
                "type": s.get("type", "object"),
                "properties": s.get("properties", {}),
                "required": s.get("required", [])
            }
            for s in schemas
        }

    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": title,
            "version": version,
            "description": description,
        },
        "servers": [{"url": "http://localhost:8000", "description": "Default server"}],
        "paths": paths,
        "components": components,
    }

    return spec


def _parse_existing_spec(content: str, file_ext: str) -> Optional[Dict[str, Any]]:
    """Parse existing OpenAPI/Swagger spec from JSON/YAML."""
    try:
        if file_ext == ".json":
            data = json.loads(content)
        else:
            data = yaml.safe_load(content)

        # Validate it's an OpenAPI/Swagger spec
        if isinstance(data, dict) and ("openapi" in data or "swagger" in data):
            return data
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON spec: {e}")
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML spec: {e}")
    except Exception as e:
        logger.error(f"Unexpected error parsing spec: {e}", exc_info=True)

    return None


@router.post("/analysis/api-doc")
async def generate_api_documentation(
    file: UploadFile = File(...),
    format: str = Form("openapi"),
    title: Optional[str] = Form(None),
    version: str = Form("1.0.0"),
    description: Optional[str] = Form(None),
    provider: Optional[str] = Form(None),
    model: Optional[str] = Form(None),
):
    """
    Generate API documentation from uploaded code files.

    Supports:
    - Python (.py) - FastAPI, Flask route detection
    - JavaScript/TypeScript (.js, .ts) - Express, Next.js API routes
    - JSON/YAML (.json, .yaml, .yml) - Existing OpenAPI enhancement

    Returns an OpenAPI 3.0 specification.
    """
    # Validate format parameter (currently only OpenAPI 3.0 supported)
    supported_formats = {"openapi", "openapi3", "openapi3.0"}
    if format.lower() not in supported_formats:
        logger.warning(f"Unsupported format '{format}' requested, defaulting to OpenAPI 3.0")

    # Validate file extension
    allowed_extensions = {".py", ".js", ".ts", ".json", ".yaml", ".yml"}
    file_ext = Path(file.filename or "").suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Read file content
    content = await file.read()
    try:
        code_text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    # Process based on file type
    if file_ext in {".json", ".yaml", ".yml"}:
        # Try to parse as existing OpenAPI spec
        existing_spec = _parse_existing_spec(code_text, file_ext)
        if existing_spec:
            # Return enhanced/validated spec
            return {
                **existing_spec,
                "x-generated-by": "PMOVES-DoX",
                "x-source-type": "existing_spec",
            }

    # Determine language for extraction
    language_map = {
        ".py": "Python",
        ".js": "JavaScript",
        ".ts": "TypeScript",
    }
    language = language_map.get(file_ext, "code")

    # Try LLM extraction first
    endpoints = None
    provider_used = "heuristic"

    provider_name = (provider or os.getenv("LANGEXTRACT_PROVIDER", "")).lower()

    if provider_name in ("ollama", "") and await asyncio.to_thread(_is_ollama_available):
        endpoints = await asyncio.to_thread(_extract_with_ollama, code_text, language, model)
        if endpoints:
            provider_used = "ollama"

    # Fallback to heuristic extraction
    if not endpoints:
        endpoints = _heuristic_endpoint_extraction(code_text, file_ext)

    # Extract schemas
    schemas = _heuristic_schema_extraction(code_text, file_ext)

    # Build OpenAPI specification
    spec = _build_openapi_spec(
        endpoints=endpoints,
        schemas=schemas,
        title=title or Path(file.filename or "API").stem,
        version=version,
        description=description or f"API documentation generated from {file.filename}",
    )

    # Add metadata
    spec["x-generated-by"] = "PMOVES-DoX"
    spec["x-provider"] = provider_used
    spec["x-source-file"] = file.filename
    spec["x-endpoints-count"] = len(endpoints)
    spec["x-schemas-count"] = len(schemas)

    return spec
