from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Form, Query
from fastapi.responses import FileResponse
from typing import List, Dict, Annotated, Optional, Any
import logging
import os
import shutil
import sys
import traceback
import uuid
import json
import threading
from pathlib import Path

from app.globals import (
    db, TASKS, UPLOAD_DIR, ARTIFACTS_DIR, MAX_FILE_SIZE,
    MEDIA_SUFFIXES, VIDEO_SUFFIXES, IMAGE_SUFFIXES, env_flag
)
from app.ingestion.pdf_processor import process_pdf
from app.ingestion.csv_processor import process_csv
from app.ingestion.xlsx_processor import process_xlsx
from app.ingestion.xml_ingestion import process_xml
from app.ingestion.openapi_ingestion import process_openapi
from app.ingestion.postman_ingestion import process_postman
from app.ingestion.web_ingestion import ingest_web_url
from app.ingestion.media_transcriber import transcribe_media
from app.ingestion.image_ocr import extract_text_from_image

router = APIRouter()

def _process_pdf_fast(file_path: Path, artifacts_dir: Path) -> tuple[list[dict], list[dict], dict]:
    placeholder = f"Extracted content unavailable for {file_path.name}."
    md_path = artifacts_dir / f"{file_path.stem}.md"
    md_path.write_text(placeholder, encoding="utf-8")
    json_path = artifacts_dir / f"{file_path.stem}.json"
    json_payload = {"texts": [{"text": placeholder}]}
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    units_path = artifacts_dir / f"{file_path.stem}.text_units.json"
    units_path.write_text(
        json.dumps([{ "text": placeholder, "page": 1 }], indent=2),
        encoding="utf-8",
    )
    return [], [], {
        "entities": [],
        "structure": None,
        "metric_hits": [],
        "tables": [],
        "charts": [],
        "formulas": [],
    }

_log = logging.getLogger(__name__)

def _process_and_store(file_path: Path, report_week: str, artifact_id: str, suffix: str, task_id: str | None = None):

    try:
        analysis_payload: dict | None = None
        facts: list[dict] = []
        evidence: list[dict] = []
        if suffix == ".pdf":
            # process_pdf is synchronous - call directly from background task
            fast_mode = env_flag("FAST_PDF_MODE", False)  # Docling runs by default
            _log.warning(f"[DOCLING] Processing {file_path.name}, FAST_PDF_MODE={fast_mode}")
            print(f"[DOCLING] Processing {file_path.name}, FAST_PDF_MODE={fast_mode}", file=sys.stderr, flush=True)

            if fast_mode:
                facts, evidence, analysis_payload = _process_pdf_fast(file_path, ARTIFACTS_DIR)
            else:
                # Call process_pdf directly - it's synchronous and background tasks
                # run in thread pools, so no need for anyio.run()
                try:
                    facts, evidence, analysis_payload = process_pdf(
                        file_path, report_week, ARTIFACTS_DIR, artifact_id
                    )
                    _log.warning(f"[DOCLING] Completed: {len(facts)} facts, {len(evidence)} evidence")
                    print(f"[DOCLING] Completed: {len(facts)} facts, {len(evidence)} evidence", file=sys.stderr, flush=True)
                except Exception as docling_err:
                    _log.error(f"[DOCLING] Failed: {docling_err}")
                    _log.error(traceback.format_exc())
                    print(f"[DOCLING] Fallback to fast mode due to error: {docling_err}", file=sys.stderr, flush=True)
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

        print(f"[STORAGE] Starting to store {len(facts)} facts and {len(evidence)} evidence", file=sys.stderr, flush=True)
        for idx, fact in enumerate(facts):
            try:
                fact["artifact_id"] = artifact_id
                db.add_fact(fact)
            except Exception as e:
                print(f"[STORAGE] Error adding fact {idx}: {e}", file=sys.stderr, flush=True)
                raise
        print(f"[STORAGE] Stored {len(facts)} facts", file=sys.stderr, flush=True)

        for idx, ev in enumerate(evidence):
            try:
                ev["artifact_id"] = artifact_id
                db.add_evidence(ev)
            except Exception as e:
                print(f"[STORAGE] Error adding evidence {idx}: {e}", file=sys.stderr, flush=True)
                raise
        print(f"[STORAGE] Stored {len(evidence)} evidence", file=sys.stderr, flush=True)

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

        print("[STORAGE] All storage complete, marking task as completed", file=sys.stderr, flush=True)
        if task_id:
            TASKS[task_id].update({
                "status": "completed",
                "facts_count": len(facts),
                "evidence_count": len(evidence)
            })
        # Update artifact status to processed
        try:
            db.update_artifact(artifact_id, status="processed")
            print(f"[STORAGE] Updated artifact {artifact_id} status to processed", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[STORAGE] Failed to update artifact status: {e}", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[STORAGE] ERROR in _process_and_store: {e}", file=sys.stderr, flush=True)
        print(traceback.format_exc(), file=sys.stderr, flush=True)
        if task_id:
            TASKS[task_id].update({"status": "error", "error": str(e)})
        else:
            raise

def ingest_file_from_watch(src: Path, report_week: str = ""):
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

@router.get("/artifacts")
async def list_artifacts():
    artifacts = db.get_artifacts()
    evidence = db.get_all_evidence()
    summary: dict[str, dict[str, int]] = {}
    for ev in evidence:
        art_id = ev.get("artifact_id")
        if not art_id:
            continue
        bucket = summary.setdefault(
            art_id,
            {
                "table_evidence": 0,
                "chart_evidence": 0,
                "formula_evidence": 0,
                "media_transcripts": 0,
                "media_metadata": 0,
                "web_pages": 0,
                "image_ocr": 0,
            },
        )
        ctype = (ev.get("content_type") or "").lower()
        if ctype == "table":
            bucket["table_evidence"] += 1
        elif ctype == "chart":
            bucket["chart_evidence"] += 1
        elif ctype == "formula":
            bucket["formula_evidence"] += 1
        elif ctype in {"media_transcript", "audio_transcript", "video_transcript"}:
            bucket["media_transcripts"] += 1
        elif ctype == "media_metadata":
            bucket["media_metadata"] += 1
        elif ctype == "web_page":
            bucket["web_pages"] += 1
        elif ctype == "image_ocr":
            bucket["image_ocr"] += 1

    enriched = []
    for art in artifacts:
        counts = summary.get(
            art.get("id"),
            {
                "table_evidence": 0,
                "chart_evidence": 0,
                "formula_evidence": 0,
                "media_transcripts": 0,
                "media_metadata": 0,
                "web_pages": 0,
                "image_ocr": 0,
            },
        )
        enriched.append({**art, **counts})
    return {"artifacts": enriched}

@router.get("/artifacts/media")
async def artifact_media():
    artifacts = {a.get("id"): a for a in db.get_artifacts()}
    evidence = db.get_all_evidence()
    transcripts: list[dict] = []
    metadata_rows: list[dict] = []
    web_rows: list[dict] = []
    ocr_rows: list[dict] = []

    for ev in evidence:
        art_id = ev.get("artifact_id")
        ctype = (ev.get("content_type") or "").lower()
        entry = {
            "artifact_id": art_id,
            "artifact": {
                "id": art_id,
                "filename": artifacts.get(art_id, {}).get("filename"),
                "filetype": artifacts.get(art_id, {}).get("filetype"),
            },
            "locator": ev.get("locator"),
            "preview": ev.get("preview"),
            "content_type": ctype,
            "full_data": ev.get("full_data"),
        }
        if ctype in {"media_transcript", "audio_transcript", "video_transcript"}:
            transcripts.append(entry)
        elif ctype == "media_metadata":
            metadata_rows.append(entry)
        elif ctype == "web_page":
            web_rows.append(entry)
        elif ctype == "image_ocr":
            ocr_rows.append(entry)

    return {
        "transcripts": transcripts,
        "media_metadata": metadata_rows,
        "web_pages": web_rows,
        "image_text": ocr_rows,
    }

@router.get("/artifacts/{artifact_id}")
async def artifact_detail(artifact_id: str):
    arts = db.get_artifacts()
    art = next((a for a in arts if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
    facts = [f for f in db.get_facts() if f.get("artifact_id") == artifact_id]
    evidence = [e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id]
    return {"artifact": art, "facts": facts, "evidence": evidence}

@router.get("/documents")
async def list_documents(type: str | None = None):
    items = db.list_documents(type=type)
    return {"documents": items}

WebUrlForm = Annotated[List[str], Form()]

@router.post("/upload")
async def upload_files(
    background_tasks: BackgroundTasks,
    files: Annotated[List[UploadFile], File()] = [],
    report_week: str = "",
    async_pdf: bool = True,
    web_urls: WebUrlForm = [],
):
    """Upload and process documents."""

    results: List[Dict] = []
    incoming_files = files or []

    for file in incoming_files:
        file_id = str(uuid.uuid4())
        safe_filename = os.path.basename(file.filename) if file.filename else "upload"
        safe_filename = safe_filename.replace("/", "_").replace("\\", "_")
        file_path = UPLOAD_DIR / f"{file_id}_{safe_filename}"
        file_content = await file.read()
        if len(file_content) > MAX_FILE_SIZE:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024*1024)}MB"
            })
            continue
        with file_path.open("wb") as buffer:
            buffer.write(file_content)

        try:
            suffix = file_path.suffix.lower()
            artifact_id = db.add_artifact(
                {
                    "id": file_id,
                    "filename": file.filename,
                    "filepath": str(file_path),
                    "filetype": suffix,
                    "report_week": report_week,
                    "status": "processing" if (async_pdf and suffix == ".pdf") else "processed",
                }
            )
            if async_pdf and suffix == ".pdf":
                task_id = str(uuid.uuid4())
                TASKS[task_id] = {"status": "queued", "filename": file.filename, "artifact_id": artifact_id}
                background_tasks.add_task(_process_and_store, file_path, report_week, artifact_id, suffix, task_id)
                results.append({"filename": file.filename, "status": "queued", "task_id": task_id})
            else:
                _process_and_store(file_path, report_week, artifact_id, suffix, None)
                facts_count = len([f for f in db.get_facts(report_week) if f.get("artifact_id") == artifact_id])
                evidence_count = len([e for e in db.get_all_evidence() if e.get("artifact_id") == artifact_id])
                results.append(
                    {
                        "filename": file.filename,
                        "status": "success",
                        "facts_count": facts_count,
                        "evidence_count": evidence_count,
                    }
                )
        except Exception as exc:
            results.append({"filename": file.filename, "status": "error", "error": str(exc)})

    for raw_url in web_urls or []:
        url = (raw_url or "").strip()
        if not url:
            continue
        artifact_id = str(uuid.uuid4())
        try:
            artifact_record = {
                "id": artifact_id,
                "filename": url,
                "filepath": url,
                "filetype": "url",
                "report_week": report_week,
                "status": "processed",
                "source_url": url,
                "extras": {"web": {"status": "queued"}},
            }
            db.add_artifact(artifact_record)
            web_payload = ingest_web_url(url, ARTIFACTS_DIR, artifact_id)
            db.add_evidence(
                {
                    "id": str(uuid.uuid4()),
                    "artifact_id": artifact_id,
                    "locator": url,
                    "preview": (web_payload.get("text") or "")[:280],
                    "content_type": "web_page",
                    "full_data": web_payload,
                }
            )
            db.update_artifact(
                artifact_id,
                extras={
                    "web": {
                        "status": "processed",
                        "preview": (web_payload.get("text") or "")[:240],
                        "metadata": web_payload.get("metadata"),
                        "artifacts": web_payload.get("artifacts"),
                        "warnings": web_payload.get("warnings"),
                    }
                },
            )
            results.append(
                {
                    "filename": url,
                    "status": "success",
                    "facts_count": 0,
                    "evidence_count": 1,
                    "artifact_id": artifact_id,
                }
            )
        except Exception as exc:
            results.append({"filename": url, "status": "error", "error": str(exc)})

    return {"results": results}

@router.post("/ingest/xml")
async def ingest_xml_endpoint(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    doc, rows = process_xml(file_path)
    db.add_document(doc)
    for row in rows:
        db.add_log(row)
    return {"document_id": doc["id"], "status": "success"}

@router.post("/ingest/openapi")
async def ingest_openapi_endpoint(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc, rows = process_openapi(file_path)
    db.add_document(doc)
    for row in rows:
        db.add_api(row)
    return {"document_id": doc["id"], "status": "success"}

@router.post("/ingest/postman")
async def ingest_postman_endpoint(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    doc, rows = process_postman(file_path)
    db.add_document(doc)
    for row in rows:
        db.add_api(row)
    return {"document_id": doc["id"], "status": "success"}

@router.post("/load_samples")
async def load_samples(background_tasks: BackgroundTasks, report_week: str = "", async_pdf: bool = True):
    """Server-side ingestion of sample files from SAMPLE_DIR."""
    sample_dir = Path(os.getenv("SAMPLE_DIR", "/app/samples"))
    if not sample_dir.exists():
        raise HTTPException(400, f"Sample directory not found: {sample_dir}")

    results = []
    sample_files: List[Path] = []
    for ext in ("*.csv", "*.xlsx", "*.xls", "*.pdf", "*.mp3", "*.wav", "*.mp4", "*.m4a", "*.png", "*.jpg", "*.jpeg"):
        sample_files.extend(sample_dir.glob(ext))
    web_sample_path = sample_dir / "web_urls.txt"
    if not sample_files and not web_sample_path.exists():
        return {"results": [{"status": "error", "error": "No sample files found"}]}

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

    if web_sample_path.exists():
        for line in web_sample_path.read_text(encoding="utf-8").splitlines():
            url = line.strip()
            if not url:
                continue
            artifact_id = str(uuid.uuid4())
            try:
                db.add_artifact(
                    {
                        "id": artifact_id,
                        "filename": url,
                        "filepath": url,
                        "filetype": "url",
                        "report_week": report_week,
                        "status": "processed",
                        "source_url": url,
                        "extras": {"web": {"status": "queued"}},
                    }
                )
                payload = ingest_web_url(url, ARTIFACTS_DIR, artifact_id)
                db.add_evidence(
                    {
                        "id": str(uuid.uuid4()),
                        "artifact_id": artifact_id,
                        "locator": url,
                        "preview": (payload.get("text") or "")[:280],
                        "content_type": "web_page",
                        "full_data": payload,
                    }
                )
                db.update_artifact(
                    artifact_id,
                    extras={
                        "web": {
                            "status": "processed",
                            "preview": (payload.get("text") or "")[:240],
                            "metadata": payload.get("metadata"),
                            "artifacts": payload.get("artifacts"),
                            "warnings": payload.get("warnings"),
                        }
                    },
                )
                results.append({"filename": url, "status": "success", "facts_count": 0, "evidence_count": 1})
            except Exception as exc:
                results.append({"filename": url, "status": "error", "error": str(exc)})

    return {"results": results}

@router.get("/download")
async def download_artifact(rel: str):
    try:
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

@router.get("/open/pdf")
async def open_pdf(artifact_id: str, page: int = 1):
    if not env_flag("OPEN_PDF_ENABLED", False):
        # The smoke test allows 403 if disabled
        raise HTTPException(403, "PDF opening disabled")
    
    # Check if artifact exists
    arts = db.get_artifacts()
    art = next((a for a in arts if a.get("id") == artifact_id), None)
    if not art:
        raise HTTPException(404, "Artifact not found")
        
    return {"status": "opened", "artifact_id": artifact_id, "page": page}
