from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import uuid
import xml.etree.ElementTree as ET
import os
import json
import yaml


def _load_xpath_map() -> Optional[Dict]:
    """Load an optional XPath mapping from env.

    Env options:
    - XML_XPATH_MAP: inline JSON/YAML mapping
    - XML_XPATH_MAP_FILE: path to a JSON/YAML file with the mapping

    Mapping format:
    {
      "entry": "//log | //entry",
      "fields": {
        "ts": "./ts | ./timestamp | ./time",
        "level": "./level | ./severity",
        "code": "./code | ./error | ./status",
        "component": "./component | ./service | ./module",
        "message": "./message | ./msg | ./text"
      }
    }
    """
    raw = os.getenv("XML_XPATH_MAP")
    path = os.getenv("XML_XPATH_MAP_FILE")
    data = None
    try:
        if path and Path(path).exists():
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
            try:
                data = json.loads(text)
            except Exception:
                data = yaml.safe_load(text)
        elif raw:
            try:
                data = json.loads(raw)
            except Exception:
                data = yaml.safe_load(raw)
    except Exception:
        data = None
    if isinstance(data, dict) and data.get("entry") and data.get("fields"):
        return data  # type: ignore
    return None


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

    # If a mapping is provided, use it
    mapping = _load_xpath_map()
    if mapping:
        entry_sel = mapping.get("entry", ".//entry | .//log")
        fields = mapping.get("fields", {}) or {}
        # xml.etree.ElementTree does not support full XPath unions; split on '|'
        selectors = [s.strip() for s in entry_sel.split("|") if s.strip()]
        found: List[ET.Element] = []
        for s in selectors:
            found.extend(root.findall(s))
        for el in found:
            def pick(xpath_expr: str) -> Optional[str]:
                vals: List[str] = []
                for sel in [p.strip() for p in xpath_expr.split("|") if p.strip()]:
                    node = el.find(sel)
                    if node is not None and node.text:
                        vals.append(node.text.strip())
                return vals[0] if vals else None

            row = {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "ts": pick(fields.get("ts", "./ts | ./timestamp | ./time")),
                "level": pick(fields.get("level", "./level | ./severity")),
                "code": pick(fields.get("code", "./code | ./error | ./status")),
                "component": pick(fields.get("component", "./component | ./service | ./module")),
                "message": pick(fields.get("message", "./message | ./msg | ./text")),
                "attrs_json": None,
            }
            rows.append(row)

    # Fallback: try common tags
    if not rows:
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
