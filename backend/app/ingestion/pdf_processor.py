"""PDF ingestion pipeline with advanced Docling enrichments."""

from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    PictureDescriptionVlmOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption

from app.analysis import BusinessMetricExtractor, DocumentStructureProcessor, NERProcessor

try:  # pragma: no cover - accelerator options are optional
    from docling.datamodel.accelerator_options import AcceleratorOptions
except ImportError:  # pragma: no cover - CPU-only installs may omit this
    AcceleratorOptions = None  # type: ignore

from .advanced_table_processor import AdvancedTableProcessor
from .chart_processor import ChartProcessor
from .formula_processor import FormulaProcessor


NER_PROCESSOR = NERProcessor()
STRUCTURE_PROCESSOR = DocumentStructureProcessor()
METRIC_EXTRACTOR = BusinessMetricExtractor()

from app.analysis.financial_statement_detector import FinancialStatementDetector
from app.ingestion.complex_table_processor import ComplexTableProcessor

def _torch_cuda_available() -> bool:
    try:  # pragma: no cover - cuda probing depends on runtime
        import torch  # type: ignore

        return hasattr(torch, "cuda") and torch.cuda.is_available()
    except Exception:
        return False


def _build_accelerator_options() -> AcceleratorOptions | None:
    if AcceleratorOptions is None:
        return None

    desired = (os.getenv("DOCLING_DEVICE") or "").strip().lower()
    if not desired or desired == "auto":
        desired = "cuda" if _torch_cuda_available() else "cpu"
    elif desired.startswith("cuda") and not _torch_cuda_available():
        desired = "cpu"

    threads_env = os.getenv("DOCLING_NUM_THREADS")
    num_threads: Optional[int] = None
    if threads_env:
        try:
            num_threads = max(1, int(threads_env))
        except ValueError:
            num_threads = None

    try:
        return AcceleratorOptions(device=desired, num_threads=num_threads)
    except Exception:  # pragma: no cover - docling validates arguments
        return None


def process_pdf(
    file_path: Path,
    report_week: str,
    artifacts_dir: Path,
    artifact_id: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    """Convert a PDF with Docling and surface enriched evidence.

    Note: This is intentionally synchronous because Docling's DocumentConverter.convert()
    is synchronous. Calling this from async code should use asyncio.to_thread() or
    loop.run_in_executor(). FastAPI background tasks run in thread pools, so they
    can call this directly without wrapping.
    """

    artifacts_dir.mkdir(parents=True, exist_ok=True)

    vlm_repo = os.getenv("DOCLING_VLM_REPO")
    use_vlm = bool(vlm_repo)
    ocr_enabled = os.getenv("PDF_OCR_ENABLED", "false").lower() == "true"
    picture_enabled = (
        os.getenv("PDF_PICTURE_DESCRIPTION", "false").lower() == "true" and use_vlm
    )
    accelerator_options = _build_accelerator_options()

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.do_ocr = ocr_enabled
    pipeline_options.do_picture_description = picture_enabled
    if picture_enabled:
        pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
            repo_id=vlm_repo  # type: ignore[arg-type]
        )
    if accelerator_options and hasattr(pipeline_options, "accelerator_options"):
        pipeline_options.accelerator_options = accelerator_options

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    result = converter.convert(str(file_path))
    doc = result.document

    table_processor = AdvancedTableProcessor()
    chart_processor = ChartProcessor(enable_ocr=ocr_enabled)
    formula_processor = FormulaProcessor()

    # Persist Docling exports for downstream inspection/search
    markdown_path = artifacts_dir / f"{file_path.stem}.md"
    json_path = artifacts_dir / f"{file_path.stem}.json"
    text_units_path = artifacts_dir / f"{file_path.stem}.text_units.json"

    markdown_content = doc.export_to_markdown()
    markdown_path.write_text(markdown_content, encoding="utf-8")

    doc_dict = doc.export_to_dict()
    json_path.write_text(json.dumps(doc_dict, indent=2), encoding="utf-8")

    try:
        text_units: List[Dict[str, Any]] = []
        for item in getattr(doc, "texts", []) or []:
            text = (getattr(item, "text", "") or "").strip()
            if not text:
                continue
            page = None
            provenance = getattr(item, "prov", None)
            if provenance:
                try:
                    page = getattr(provenance[0], "page", None)
                except Exception:
                    page = None
            text_units.append({"text": text, "page": page})
        if text_units:
            text_units_path.write_text(
                json.dumps(text_units, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except Exception:
        # Text units are optional; failures should not abort ingestion.
        pass

    facts: List[Dict[str, Any]] = []
    evidence: List[Dict[str, Any]] = []
    analysis_results: Dict[str, Any] = {
        "document_reference": artifact_id or file_path.name,
        "entities": [],
        "structure": None,
        "metric_hits": [],
        "tables": [],
        "charts": [],
        "formulas": [],
    }

    # --------------------------- tables ---------------------------
    analysis_results["document_reference"] = artifact_id or file_path.name
    
    table_normalizer = ComplexTableProcessor()
    statement_detector = FinancialStatementDetector()
    enable_financials = os.getenv("PDF_FINANCIAL_ANALYSIS", "true").strip().lower() != "false"

    # Process tables
    for table_idx, table in enumerate(doc.tables):
        evidence_id = str(uuid.uuid4())

        # Convert table to pandas DataFrame for analysis
        normalized_df, header_info = table_normalizer.normalize_table(table)
        df = normalized_df

        table_analysis = {
            "type": "unknown",
            "confidence": 0.0,
            "summary": {},
        }
        if enable_financials and not df.empty:
            table_analysis = statement_detector.analyze_table(df, header_info)

        # Extract metrics from table
        metrics = extract_metrics_from_table(df)
        if table_analysis.get("summary"):
            for key, value in table_analysis["summary"].items():
                if value is not None:
                    metrics.setdefault(key, value)

        should_persist = bool(metrics) or (
            table_analysis.get("type") not in (None, "", "unknown")
        )

        if should_persist:
            # Get table location - handle different Docling API versions
            bbox = None
            if hasattr(table, 'prov') and table.prov:
                prov = table.prov[0]
                # Try different attribute names for page number (API changed between versions)
                page_num = getattr(prov, 'page', None) or getattr(prov, 'page_no', None)
                bbox_tuple = None
                if hasattr(prov, 'bbox'):
                    bbox_tuple = prov.bbox.as_tuple() if hasattr(prov.bbox, 'as_tuple') else None
                bbox = {
                    'page': page_num,
                    'bbox': bbox_tuple
                }
            
            preview_df = df.head(5)
            preview_str = preview_df.to_string(index=False)
            if table_analysis.get("type") and table_analysis["type"] != "unknown":
                preview_str = (
                    f"{table_analysis['type'].replace('_', ' ').title()}"
                    f" (confidence {table_analysis['confidence']:.2f})\n"
                    f"{preview_str}"
                )

            content_type = "financial_table" if table_analysis.get("type") not in (None, "", "unknown") else "table"
            serialized_rows = _dataframe_to_records(df)
            evidence.append({
                "id": evidence_id,
                "locator": f"{file_path.name}#table{table_idx}",
                "preview": preview_str,
                "content_type": content_type,
                "coordinates": bbox,
                "full_data": {
                    "columns": [str(col) for col in df.columns],
                    "rows": serialized_rows,
                    "header_info": header_info,
                    "statement": table_analysis,
                },
            })

    # Process tables (multi-page aware)
    merged_tables = table_processor.detect_spanning_tables(doc)
    for table_idx, table_entry in enumerate(merged_tables):
        df = table_entry.get("dataframe")
        if df is None or df.empty:
            continue

        evidence_id = str(uuid.uuid4())
        metrics = extract_metrics_from_table(df)

        coordinates = table_entry.get("segments") or []
        preview = df.head(5).to_string(index=False)
        full_payload: Dict[str, Any] = {
            "rows": df.to_dict("records"),
            "pages": table_entry.get("pages", []),
            "merged": table_entry.get("merged", False),
            "header_detected": table_entry.get("header_detected", False),
            "columns": [str(col) for col in df.columns],
        }

        evidence.append(
            {
                "id": evidence_id,
                "locator": f"{file_path.name}#table{table_idx}",
                "preview": preview,
                "content_type": "table",
                "coordinates": coordinates,
                "full_data": full_payload,
            }
        )

        analysis_results["tables"].append(
            {
                "evidence_id": evidence_id,
                "locator": f"{file_path.name}#table{table_idx}",
                "pages": list(full_payload["pages"]),
                "header_detected": full_payload["header_detected"],
                "row_count": int(df.shape[0]),
                "column_names": full_payload["columns"],
            }
        )

        # Always create fact for tables (use structure info if no metrics)
        fact_metrics = metrics if metrics else {
            "rows": int(df.shape[0]),
            "columns": int(df.shape[1]),
            "column_names": list(df.columns)[:10],  # First 10 column names
        }
        facts.append(
            {
                "id": str(uuid.uuid4()),
                "report_week": report_week,
                "entity": "table",
                "metrics": fact_metrics,
                "evidence_id": evidence_id,
            }
        )

    # --------------------------- text metrics ---------------------------
    # NOTE: Asymmetric evidence/fact behavior by design:
    # - Evidence is ALWAYS created for non-empty text sections (preserves full text)
    # - Facts are ONLY created when metrics are extracted (avoids empty fact rows)
    # This differs from tables where facts are always created since tables have
    # inherent structure (row/column counts) even without extracted metrics.
    for section_idx, item in enumerate(getattr(doc, "texts", []) or []):
        text = getattr(item, "text", "") or ""
        if not text.strip():
            continue

        metrics = extract_metrics_from_text(text)

        # Always create evidence for text sections
        evidence_id = str(uuid.uuid4())
        coordinates = None
        provenance = getattr(item, "prov", None)
        if provenance:
            try:
                coordinates = {
                    "page": getattr(provenance[0], "page", None),
                    "bbox": getattr(provenance[0], "bbox", None).as_tuple()
                    if hasattr(provenance[0], "bbox")
                    else None,
                }
            except Exception:
                coordinates = None

        evidence.append(
            {
                "id": evidence_id,
                "locator": f"{file_path.name}#section{section_idx}",
                "preview": text[:300],
                "content_type": "text",
                "coordinates": coordinates,
                "full_data": {"text": text, "metrics": metrics},
            }
        )

        # Only add fact if metrics were extracted
        if metrics:
            facts.append(
                {
                    "id": str(uuid.uuid4()),
                    "report_week": report_week,
                    "entity": None,
                    "metrics": metrics,
                    "evidence_id": evidence_id,
                }
            )

    # --------------------------- charts ---------------------------
    chart_results = chart_processor.process_charts(doc, artifacts_dir, file_path.stem)
    vlm_enabled = bool(vlm_repo)
    for chart_idx, chart in enumerate(chart_results):
        evidence_id = str(uuid.uuid4())
        preview = chart.get("caption") or chart.get("extracted_text") or f"Chart {chart_idx}"
        coordinates = None
        if chart.get("page") is not None or chart.get("bbox") is not None:
            coordinates = {"page": chart.get("page"), "bbox": chart.get("bbox")}

        chart_payload = {**chart, "vlm_enabled": vlm_enabled}
        evidence.append(
            {
                "id": evidence_id,
                "locator": f"{file_path.name}#chart{chart_idx}",
                "preview": (preview or "").strip()[:500],
                "content_type": "chart",
                "coordinates": coordinates,
                "full_data": chart_payload,
            }
        )

        analysis_results["charts"].append(
            {"evidence_id": evidence_id, "locator": f"{file_path.name}#chart{chart_idx}", **chart_payload}
        )

        metrics_payload = {
            key: value
            for key, value in {
                "chart_id": chart.get("id"),
                "chart_type": chart.get("type"),
                "chart_caption": chart.get("caption"),
                "chart_text": chart.get("extracted_text"),
            }.items()
            if value
        }
        if metrics_payload:
            facts.append(
                {
                    "id": str(uuid.uuid4()),
                    "report_week": report_week,
                    "entity": "chart",
                    "metrics": metrics_payload,
                    "evidence_id": evidence_id,
                }
            )

    # --------------------------- formulas ---------------------------
    formulas = formula_processor.extract_formulas(doc)
    for formula_idx, formula in enumerate(formulas):
        evidence_id = str(uuid.uuid4())
        preview = formula.get("latex") or formula.get("content") or f"Formula {formula_idx}"
        coordinates = None
        if formula.get("page") is not None or formula.get("bbox") is not None:
            coordinates = {"page": formula.get("page"), "bbox": formula.get("bbox")}

        evidence.append(
            {
                "id": evidence_id,
                "locator": f"{file_path.name}#formula{formula_idx}",
                "preview": (preview or "").strip()[:500],
                "content_type": "formula",
                "coordinates": coordinates,
                "full_data": formula,
            }
        )

        analysis_results["formulas"].append(
            {"evidence_id": evidence_id, "locator": f"{file_path.name}#formula{formula_idx}", **formula}
        )

        metrics_payload = {
            key: value
            for key, value in {
                "formula": formula.get("latex") or formula.get("content"),
                "kind": formula.get("kind"),
            }.items()
            if value
        }
        if metrics_payload:
            facts.append(
                {
                    "id": str(uuid.uuid4()),
                    "report_week": report_week,
                    "entity": "formula",
                    "metrics": metrics_payload,
                    "evidence_id": evidence_id,
                }
            )

    # --------------------------- analysis outputs ---------------------------
    text_elements = [
        item
        for item in getattr(doc, "texts", []) or []
        if (getattr(item, "text", "") or "").strip()
    ]

    try:
        analysis_results["structure"] = STRUCTURE_PROCESSOR.build_hierarchy(doc)
    except Exception:  # pragma: no cover - best-effort enrichment
        analysis_results["structure"] = None

    try:
        analysis_results["entities"] = NER_PROCESSOR.extract_entities(text_elements)
    except Exception:  # pragma: no cover - spaCy optional in CI
        analysis_results["entities"] = []

    metric_hits: List[Dict[str, Any]] = []
    for idx, item in enumerate(text_elements):
        hits = METRIC_EXTRACTOR.extract_metrics(getattr(item, "text", ""))
        if not hits:
            continue
        page = None
        provenance = getattr(item, "prov", None)
        if provenance:
            try:
                page = getattr(provenance[0], "page", None)
            except Exception:
                page = None
        for hit in hits:
            metric_hits.append(
                {
                    **hit,
                    "page": page,
                    "source_index": idx,
                }
            )
    analysis_results["metric_hits"] = metric_hits

    # Add document-level summary fact (captures document structure even if no metrics)
    doc_pages = getattr(doc, "pages", {}) or {}
    doc_texts = getattr(doc, "texts", []) or []
    doc_tables = getattr(doc, "tables", []) or []
    facts.append(
        {
            "id": str(uuid.uuid4()),
            "report_week": report_week,
            "entity": "document_summary",
            "metrics": {
                "pages": len(doc_pages) if isinstance(doc_pages, (dict, list)) else 1,
                "text_sections": len(doc_texts),
                "tables": len(doc_tables),
                "charts": len(analysis_results.get("charts", [])),
                "formulas": len(analysis_results.get("formulas", [])),
                "total_evidence": len(evidence),
                "total_facts": len(facts),  # Count before this summary
            },
            "evidence_id": None,
        }
    )

    return facts, evidence, analysis_results


def extract_metrics_from_table(df: pd.DataFrame) -> Dict[str, float]:
    """Extract totals for common marketing metrics from a table."""

    metrics: Dict[str, float] = {}

    metric_patterns = {
        "spend": ["spend", "cost", "budget"],
        "revenue": ["revenue", "sales", "income"],
        "conversions": ["conversions", "leads", "sales"],
        "clicks": ["clicks"],
        "impressions": ["impressions", "views"],
        "ctr": ["ctr", "click rate"],
        "cpa": ["cpa", "cost per"],
        "roas": ["roas", "return on"],
    }

    for metric_name, patterns in metric_patterns.items():
        for col in df.columns:
            col_lower = str(col).lower()
            if any(p in col_lower for p in patterns):
                try:
                    numeric_values = pd.to_numeric(df[col], errors="coerce")
                    total = numeric_values.sum()
                    if not pd.isna(total):
                        metrics[metric_name] = float(total)
                except Exception:
                    continue

    if (
        "clicks" in metrics
        and "impressions" in metrics
        and metrics["impressions"] > 0
    ):
        metrics["ctr"] = metrics["clicks"] / metrics["impressions"]

    if (
        "spend" in metrics
        and "conversions" in metrics
        and metrics["conversions"] > 0
    ):
        metrics["cpa"] = metrics["spend"] / metrics["conversions"]

    if "revenue" in metrics and "spend" in metrics and metrics["spend"] > 0:
        metrics["roas"] = metrics["revenue"] / metrics["spend"]

    return metrics


def extract_metrics_from_text(text: str) -> Dict[str, float]:
    """Extract numeric metrics from free-form text using regex patterns."""

    metrics: Dict[str, float] = {}
    haystack = text or ""

    patterns = {
        "roas": r"ROAS[:\s]+([0-9.]+)",
        "cpa": r"CPA[:\s]+\$?\s*([0-9,.]+)",
        "ctr": r"CTR[:\s]+([0-9.]+)\s*%?",
        "revenue": r"revenue[:\s]+\$?\s*([0-9,]+(?:\.[0-9]+)?)",
        "spend": r"spend[:\s]+\$?\s*([0-9,]+(?:\.[0-9]+)?)",
        "conversions": r"conversions?[:\s]+([0-9,]+)",
        "clicks": r"clicks?[:\s]+([0-9,]+)",
        "impressions": r"impressions?[:\s]+([0-9,]+)",
    }

    for metric, pattern in patterns.items():
        match = re.search(pattern, haystack, re.IGNORECASE)
        if not match:
            continue
        value_str = match.group(1).replace(",", "")
        try:
            metrics[metric] = float(value_str)
        except ValueError:
            continue

    return metrics


__all__ = ["process_pdf", "extract_metrics_from_table", "extract_metrics_from_text"]

def _dataframe_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    if df.empty:
        return records
    for row in df.to_dict("records"):
        safe_row: Dict[str, Any] = {}
        for key, value in row.items():
            safe_row[str(key)] = _json_safe_value(value)
        records.append(safe_row)
    return records


def _json_safe_value(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value
