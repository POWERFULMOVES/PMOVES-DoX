from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple
import uuid
import xml.etree.ElementTree as ET


def process_xml(file_path: Path) -> Tuple[Dict, List[Dict]]:
    """
    Parse a generic XML log into (document_row, log_rows[]).
    Expected log entries are <entry> or <log> elements with children like ts, level, code, component, message.
    This is intentionally flexible; unknown shapes are flattened heuristically.
    """
    text = file_path.read_text(encoding="utf-8", errors="ignore")
    root = ET.fromstring(text)

    doc_id = str(uuid.uuid4())
    doc = {
        "id": doc_id,
        "path": str(file_path),
        "type": "xml",
        "title": file_path.name,
        "source": "watch|upload",
    }

    rows: List[Dict] = []

    def get_text(el, name):
        child = el.find(name)
        return (child.text or "").strip() if child is not None and child.text else None

    # try common tags
    for el in root.findall('.//entry') + root.findall('.//log'):
        row = {
            "id": str(uuid.uuid4()),
            "document_id": doc_id,
            "ts": get_text(el, 'ts') or get_text(el, 'timestamp') or get_text(el, 'time'),
            "level": (get_text(el, 'level') or get_text(el, 'severity')),
            "code": get_text(el, 'code') or get_text(el, 'error') or get_text(el, 'status'),
            "component": get_text(el, 'component') or get_text(el, 'service') or get_text(el, 'module'),
            "message": get_text(el, 'message') or get_text(el, 'msg') or get_text(el, 'text'),
            "attrs_json": None,
        }
        rows.append(row)

    # Fallback: treat any child with text as message
    if not rows:
        for el in root.iter():
            if list(el):
                continue
            if el.text and el.text.strip():
                rows.append({
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "ts": None,
                    "level": None,
                    "code": None,
                    "component": el.tag,
                    "message": el.text.strip(),
                    "attrs_json": None,
                })

    return doc, rows

