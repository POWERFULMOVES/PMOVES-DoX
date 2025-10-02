from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import uuid
import json
import yaml


def process_openapi(file_path: Path) -> Tuple[Dict, List[Dict]]:
    """Parse OpenAPI (YAML/JSON) into (document_row, api_rows[])."""
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        data = json.loads(text)
    except Exception:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("Invalid OpenAPI file")
    if not ("openapi" in data or ("swagger" in data)):
        raise ValueError("Not an OpenAPI document")

    doc_id = str(uuid.uuid4())
    doc = {
        "id": doc_id,
        "path": str(file_path),
        "type": "openapi",
        "title": data.get('info', {}).get('title') or file_path.name,
        "source": "watch|upload",
    }

    rows: List[Dict] = []
    paths = data.get('paths', {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        for method, op in methods.items():
            if method.upper() not in {"GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"}:
                continue
            op = op or {}
            tags = op.get('tags') or []
            params = op.get('parameters') or []
            responses = op.get('responses') or {}
            rows.append({
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "name": op.get('operationId'),
                "method": method.upper(),
                "path": path,
                "summary": op.get('summary') or op.get('description'),
                "tags_json": json.dumps(tags),
                "params_json": json.dumps(params),
                "responses_json": json.dumps(responses),
            })
    return doc, rows

