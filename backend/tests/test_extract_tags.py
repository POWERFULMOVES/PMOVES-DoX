import asyncio
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app import main  # noqa: E402


class StubDB:
    def __init__(self, documents):
        self._documents = list(documents)
        self.saved_tags = []

    def list_documents(self, type=None):  # noqa: A002 - match production signature
        return list(self._documents)

    def has_tag(self, document_id, tag):
        return False

    def add_tag(self, tag):
        self.saved_tags.append(tag)


def test_extract_tags_uses_heuristic_when_dry_run(monkeypatch, tmp_path):
    for env_name in ("GOOGLE_API_KEY", "OPENAI_API_KEY", "LANGEXTRACT_API_KEY"):
        monkeypatch.delenv(env_name, raising=False)

    doc_path = tmp_path / "sample.txt"
    doc_path.write_text(
        "Loan Origination Platform enables Underwriting and Servicing features.",
        encoding="utf-8",
    )

    stub_db = StubDB([
        {"id": "doc-1", "type": "openapi", "path": str(doc_path)},
    ])
    monkeypatch.setattr(main, "db", stub_db)

    request = main.ExtractTagsRequest(document_id="doc-1", dry_run=True)
    result = asyncio.run(main.extract_tags(request))

    assert result["status"] == "ok"
    assert result["tags_saved"] == 0
    assert "Loan Origination Platform" in result["tags"]
    assert "Underwriting" in result["tags"]
    assert stub_db.saved_tags == []
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
