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
    comp = data.get('components', {}) or {}
    sec_schemes = comp.get('securitySchemes', {}) or {}
    global_sec = data.get('security', None)  # list of requirement objects or None
    paths = data.get('paths', {}) or {}
    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue
        path_params = methods.get('parameters') or []
        for method, op in methods.items():
            if method.upper() not in {"GET","POST","PUT","PATCH","DELETE","HEAD","OPTIONS"}:
                continue
            op = op or {}
            tags = op.get('tags') or []
            # merge path-level parameters into op-level
            params = (path_params or []) + (op.get('parameters') or [])
            # compute effective security for this op: op.security or global security
            op_sec = op.get('security', global_sec)
            # normalize into a simple list of scheme names used (union)
            used_schemes: List[str] = []
            if isinstance(op_sec, list):
                for req in op_sec:
                    if isinstance(req, dict):
                        for k in req.keys():
                            if k not in used_schemes:
                                used_schemes.append(k)
            responses = op.get('responses') or {}
            # attach normalized security info under an extension key
            if used_schemes:
                responses = {**responses, "x_security": {"schemes": used_schemes}}
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
