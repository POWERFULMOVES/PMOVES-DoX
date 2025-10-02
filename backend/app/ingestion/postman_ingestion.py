from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import uuid
import json


def process_postman(file_path: Path) -> Tuple[Dict, List[Dict]]:
    """Parse Postman collection JSON into (document_row, api_rows[])."""
    data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    if not isinstance(data, dict) or 'item' not in data:
        raise ValueError("Not a Postman collection")

    doc_id = str(uuid.uuid4())
    info = data.get('info', {}) or {}
    doc = {
        "id": doc_id,
        "path": str(file_path),
        "type": "postman",
        "title": info.get('name') or file_path.name,
        "source": "watch|upload",
    }

    rows: List[Dict] = []

    def walk(items):
        for it in items or []:
            if 'item' in it:
                yield from walk(it['item'])
            else:
                req = it.get('request') or {}
                url = req.get('url') or {}
                method = (req.get('method') or 'GET').upper()
                path = ''
                if isinstance(url, dict):
                    path = '/' + '/'.join(url.get('path', [])) if url.get('path') else (url.get('raw') or '')
                else:
                    path = str(url)
                rows.append({
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "name": it.get('name'),
                    "method": method,
                    "path": path,
                    "summary": it.get('name'),
                    "tags_json": json.dumps([]),
                    "params_json": json.dumps(req.get('url', {})),
                    "responses_json": json.dumps(it.get('response', [])),
                })

    walk(data.get('item'))
    return doc, rows

