import asyncio
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BACKEND_DIR = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(_BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from backend.app import main


class _StubDB:
    def __init__(self, docs):
        self._docs = list(docs)

    def list_documents(self):
        return list(self._docs)


def test_extract_tags_heuristic_dry_run(monkeypatch, tmp_path):
    doc_path = tmp_path / "doc.txt"
    doc_path.write_text(
        "Loan Origination Platform\nUnderwriting Module\n",
        encoding="utf-8",
    )

    stub_db = _StubDB([
        {"id": "doc-1", "type": "txt", "path": str(doc_path)}
    ])
    monkeypatch.setattr(main, "db", stub_db)

    for env_key in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "LANGEXTRACT_API_KEY"):
        monkeypatch.delenv(env_key, raising=False)

    def _fail_run_langextract(*args, **kwargs):
        raise AssertionError("run_langextract should not be called in heuristic dry-run")

    monkeypatch.setattr(main, "run_langextract", _fail_run_langextract)

    req = main.ExtractTagsRequest(document_id="doc-1", dry_run=True)
    result = asyncio.run(main.extract_tags(req))

    assert result["status"] == "ok"
    assert {"Loan Origination Platform", "Underwriting Module"}.issubset(set(result["tags"]))
    assert result["tags_saved"] == 0
