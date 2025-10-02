from pathlib import Path
import os
from typing import List, Dict, Any, Tuple
import uuid
import json
import re
import pandas as pd
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    VlmPipelineOptions,
    PictureDescriptionVlmOptions,
)

async def process_pdf(
    file_path: Path, 
    report_week: str, 
    artifacts_dir: Path
) -> Tuple[List[Dict], List[Dict]]:
    """
    Process PDF using Docling with IBM Granite model
    Returns (facts, evidence)
    """
    
    # Configure Docling pipeline
    vlm_repo = os.getenv("DOCLING_VLM_REPO")
    use_vlm = bool(vlm_repo)
    if use_vlm:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = True
        pipeline_options.do_ocr = True
        pipeline_options.do_picture_description = True
        pipeline_options.picture_description_options = PictureDescriptionVlmOptions(
            repo_id=vlm_repo
        )
    else:
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_table_structure = True
        pipeline_options.do_ocr = True
    
    # Initialize converter with Granite backend
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    
    # Convert PDF
    result = converter.convert(str(file_path))
    doc = result.document
    
    # Export to structured formats
    markdown_path = artifacts_dir / f"{file_path.stem}.md"
    json_path = artifacts_dir / f"{file_path.stem}.json"
    
    # Save markdown
    markdown_content = doc.export_to_markdown()
    markdown_path.write_text(markdown_content, encoding="utf-8")
    
    # Save JSON for structured analysis
    doc_dict = doc.export_to_dict()
    json_path.write_text(json.dumps(doc_dict, indent=2), encoding="utf-8")
    
    # Extract facts from tables and text
    facts = []
    evidence = []
    
    # Process tables
    for table_idx, table in enumerate(doc.tables):
        evidence_id = str(uuid.uuid4())
        
        # Convert table to pandas DataFrame for analysis
        df = table.export_to_dataframe()
        
        # Extract metrics from table
        metrics = extract_metrics_from_table(df)
        
        if metrics:
            # Get table location
            bbox = None
            if hasattr(table, 'prov') and table.prov:
                bbox = {
                    'page': table.prov[0].page if table.prov else None,
                    'bbox': table.prov[0].bbox.as_tuple() if hasattr(table.prov[0], 'bbox') else None
                }
            
            evidence.append({
                "id": evidence_id,
                "locator": f"{file_path.name}#table{table_idx}",
                "preview": df.head(5).to_string(),
                "content_type": "table",
                "coordinates": bbox,
                "full_data": df.to_dict('records')
            })
            
            facts.append({
                "id": str(uuid.uuid4()),
                "report_week": report_week,
                "entity": None,
                "metrics": metrics,
                "evidence_id": evidence_id
            })
    
    # Process text sections for key metrics
    for section_idx, item in enumerate(doc.texts):
        text = item.text
        metrics = extract_metrics_from_text(text)
        
        if metrics:
            evidence_id = str(uuid.uuid4())
            
            # Get text location
            bbox = None
            if hasattr(item, 'prov') and item.prov:
                bbox = {
                    'page': item.prov[0].page if item.prov else None,
                    'bbox': item.prov[0].bbox.as_tuple() if hasattr(item.prov[0], 'bbox') else None
                }
            
            evidence.append({
                "id": evidence_id,
                "locator": f"{file_path.name}#section{section_idx}",
                "preview": text[:300],
                "content_type": "text",
                "coordinates": bbox
            })
            
            facts.append({
                "id": str(uuid.uuid4()),
                "report_week": report_week,
                "entity": None,
                "metrics": metrics,
                "evidence_id": evidence_id
            })
    
    # Process charts/figures if available (surface VLM descriptions when present)
    if hasattr(doc, 'pictures'):
        vlm_repo = os.getenv("DOCLING_VLM_REPO")
        for fig_idx, figure in enumerate(doc.pictures):
            evidence_id = str(uuid.uuid4())

            bbox = None
            if hasattr(figure, 'prov') and figure.prov:
                bbox = {
                    'page': getattr(figure.prov[0], 'page', None) if figure.prov else None,
                    'bbox': figure.prov[0].bbox.as_tuple() if hasattr(figure.prov[0], 'bbox') else None
                }

            # Try to extract any available description text from the figure
            desc = None
            for attr in ("description", "alt_text", "caption", "text", "summary"):
                if hasattr(figure, attr):
                    val = getattr(figure, attr)
                    try:
                        desc = (val or "").strip()
                    except Exception:
                        desc = None
                    if desc:
                        break
            if not desc:
                desc = f"Figure {fig_idx}"

            evidence.append({
                "id": evidence_id,
                "locator": f"{file_path.name}#figure{fig_idx}",
                "preview": desc[:500],
                "content_type": "figure",
                "coordinates": bbox,
                "vlm": bool(vlm_repo),
            })
    
    return facts, evidence


def extract_metrics_from_table(df: pd.DataFrame) -> Dict[str, float]:
    """Extract metrics from a pandas DataFrame"""
    metrics = {}
    
    # Look for common metric columns
    metric_patterns = {
        "spend": ["spend", "cost", "budget"],
        "revenue": ["revenue", "sales", "income"],
        "conversions": ["conversions", "leads", "sales"],
        "clicks": ["clicks"],
        "impressions": ["impressions", "views"],
        "ctr": ["ctr", "click rate"],
        "cpa": ["cpa", "cost per"],
        "roas": ["roas", "return on"]
    }
    
    for metric_name, patterns in metric_patterns.items():
        for col in df.columns:
            col_lower = str(col).lower()
            if any(p in col_lower for p in patterns):
                try:
                    # Sum numeric values
                    numeric_values = pd.to_numeric(df[col], errors='coerce')
                    total = numeric_values.sum()
                    if not pd.isna(total):
                        metrics[metric_name] = float(total)
                except:
                    pass
    
    # Calculate derived metrics
    if 'clicks' in metrics and 'impressions' in metrics and metrics['impressions'] > 0:
        metrics['ctr'] = metrics['clicks'] / metrics['impressions']
    
    if 'spend' in metrics and 'conversions' in metrics and metrics['conversions'] > 0:
        metrics['cpa'] = metrics['spend'] / metrics['conversions']
    
    if 'revenue' in metrics and 'spend' in metrics and metrics['spend'] > 0:
        metrics['roas'] = metrics['revenue'] / metrics['spend']
    
    return metrics


def extract_metrics_from_text(text: str) -> Dict[str, float]:
    """Extract metrics from text using regex patterns"""
    metrics = {}
    
    patterns = {
        "roas": r"ROAS[:\s]+([0-9.]+)",
        "cpa": r"CPA[:\s]+\$?\s*([0-9,.]+)",
        "ctr": r"CTR[:\s]+([0-9.]+)\s*%?",
        "revenue": r"revenue[:\s]+\$?\s*([0-9,]+(?:\.[0-9]+)?)",
        "spend": r"spend[:\s]+\$?\s*([0-9,]+(?:\.[0-9]+)?)",
        "conversions": r"conversions?[:\s]+([0-9,]+)",
        "clicks": r"clicks?[:\s]+([0-9,]+)",
        "impressions": r"impressions?[:\s]+([0-9,]+)"
    }
    
    for metric, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                metrics[metric] = float(value_str)
            except ValueError:
                pass
    
    return metrics
