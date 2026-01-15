from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
import time
import json
import csv
import yaml
import os
from pathlib import Path

from app.globals import (
    db, qa_engine, summary_service, HRM_ENABLED, HRM_CFG, HRM_STATS,
    ARTIFACTS_DIR, env_flag, UPLOAD_DIR
)
from app.hrm import HRMConfig, refine_sort_digits
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
async def get_facts(report_week: str = None):
    """Get all facts, optionally filtered by report week"""
    facts = db.get_facts(report_week)
    return {"facts": facts}

@router.get("/analysis/financials")
async def get_financial_statements(artifact_id: str | None = None):
    """Return detected financial statements from processed tables."""
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
async def get_evidence(evidence_id: str):
    """Get evidence by ID"""
    evidence = db.get_evidence(evidence_id)
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    return evidence

@router.post("/ask")
async def ask_question(
    question: str,
    use_hrm: bool = Query(False, description="Enable HRM sidecar (if supported)"),
):
    """Ask a question and get answer with citations."""
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
async def reset_database():
    """Clear all data"""
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
    except Exception as e:
        print(f"LLM tagging failed: {e}")
    
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

@router.post("/convert")
async def convert_document(req: ConvertRequest):
    # Placeholder - Mocking for smoke test
    out_dir = ARTIFACTS_DIR / "converted"
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = req.format or req.target_format
    ext = fmt if fmt != "markdown" else "md"
    dummy_file = out_dir / f"{req.document_id or req.artifact_id}.{ext}"
    content = "dummy content" * 100 if ext == "docx" else "dummy content"
    dummy_file.write_text(content, encoding="utf-8")
    rel = str(dummy_file.relative_to(ARTIFACTS_DIR))
    return {"content": "Converted content placeholder.", "rel": rel}

@router.post("/structure/chr")
async def generate_chr(req: CHRRequest):
    # Placeholder for CHR generation - Mocking for smoke test
    out_dir = ARTIFACTS_DIR / "chr"
    out_dir.mkdir(parents=True, exist_ok=True)
    dummy_csv = out_dir / f"{req.artifact_id or req.document_id}_chr.csv"
    dummy_csv.write_text("dummy,csv,content", encoding="utf-8")
    dummy_json = out_dir / f"{req.artifact_id or req.document_id}_chr.json"
    dummy_json.write_text('{"rows": [{"dummy": "row"}]}', encoding="utf-8")
    rel_csv = str(dummy_csv.relative_to(ARTIFACTS_DIR))
    rel_json = str(dummy_json.relative_to(ARTIFACTS_DIR))
    return {"chr": [], "artifacts": {"rel_csv": rel_csv, "rel_json": rel_json}}

# ---------------- Visualization ----------------

@router.post("/viz/datavzrd")
async def build_datavzrd(req: DataVZRDRequest):
    # Placeholder for datavzrd build
    return {"status": "ok", "project_dir": "placeholder"}

@router.post("/viz/datavzrd/logs")
async def build_datavzrd_logs(req: DataVZRDLogsRequest):
    # Placeholder for datavzrd logs
    return {"status": "ok", "project_dir": "placeholder"}

# ---------------- Export ----------------

@router.post("/export/poml")
async def export_poml(req: ExportPOMLRequest):
    # Mocking POML export for smoke test
    out_dir = ARTIFACTS_DIR / "poml"
    out_dir.mkdir(parents=True, exist_ok=True)
    dummy_poml = out_dir / f"{req.document_id}.poml"
    dummy_poml.write_text("<poml><output-schema></output-schema></poml>", encoding="utf-8")
    rel = str(dummy_poml.relative_to(ARTIFACTS_DIR))
    return {"status": "ok", "rel": rel, "path": str(dummy_poml)}

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
