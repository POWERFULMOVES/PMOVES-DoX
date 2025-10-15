import asyncio
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app import main
from backend.app.search import SearchIndex, SearchResult


class StubSearchIndex:
    def __init__(self, results):
        self._results = list(results)

    def search(self, query: str, k: int = 10):
        return list(self._results)

    def rebuild(self):
        return {"items": len(self._results)}


class DummyDB:
    def __init__(self, artifacts):
        self._artifacts = artifacts

    def get_artifacts(self):
        return self._artifacts

    def list_apis(self, tag=None, method=None, path_like=None):
        return []

    def list_logs(self, level=None, code=None, q=None, ts_from=None, ts_to=None, document_id=None):
        return []

    def list_tags(self, document_id=None, q=None):
        return []


@pytest.fixture
def stub_search(monkeypatch):
    def _factory(results):
        stub = StubSearchIndex(results)
        monkeypatch.setattr(main, "search_index", stub)
        return stub

    return _factory


def test_search_accepts_empty_type_list(stub_search):
    results = [
        SearchResult(score=0.92, text="PDF chunk", meta={
            "type": "pdf", "artifact_id": "art-1", "chunk": 0, "filename": "guide.pdf"
        }),
        SearchResult(score=0.75, text="API summary", meta={
            "type": "api", "id": "api-1", "path": "/status"
        }),
    ]
    stub_search(results)

    req = main.SearchRequest(q="guide", k=10, types=[])
    payload = asyncio.run(main.search(req))

    assert "took_ms" in payload
    assert payload["count"] == len(payload["results"]) == 2
    pdf_entry = next(item for item in payload["results"] if item["meta"]["type"] == "pdf")
    deeplink = pdf_entry["meta"]["deeplink"]
    assert deeplink["panel"] == "workspace"
    assert deeplink["artifact_id"] == "art-1"
    assert "page" not in deeplink


def test_search_ignores_invalid_type_filters(stub_search):
    results = [
        SearchResult(score=0.61, text="Log entry", meta={
            "type": "log", "document_id": "log-1", "code": "E100"
        })
    ]
    stub_search(results)

    req = main.SearchRequest(q="error", k=5, types=["unknown"])
    payload = asyncio.run(main.search(req))

    assert payload["results"] == []
    assert payload["count"] == 0
    assert "took_ms" in payload


def test_search_filters_mixed_case_types_and_preserves_page(stub_search):
    results = [
        SearchResult(score=0.88, text="PDF hit", meta={
            "type": "pdf", "artifact_id": "art-2", "chunk": 1, "page": 7
        }),
        SearchResult(score=0.54, text="Tag hit", meta={
            "type": "tag", "document_id": "doc-3", "tag": "urgent"
        }),
    ]
    stub_search(results)

    req = main.SearchRequest(q="guide", k=5, types=["PDF", "unknown"])
    payload = asyncio.run(main.search(req))

    assert payload["count"] == len(payload["results"]) == 1
    entry = payload["results"][0]
    assert entry["meta"]["type"] == "pdf"
    assert entry["meta"]["deeplink"]["panel"] == "workspace"
    assert entry["meta"]["deeplink"]["page"] == 7


def test_search_index_falls_back_to_markdown_when_text_units_invalid(tmp_path, monkeypatch):
    # Ensure relative paths inside SearchIndex resolve within a temp sandbox
    monkeypatch.chdir(tmp_path)

    uploads_dir = tmp_path / "uploads"
    artifacts_dir = tmp_path / "artifacts"
    uploads_dir.mkdir()
    artifacts_dir.mkdir()

    pdf_path = uploads_dir / "guide.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    # Provide markdown fallback but an invalid text_units file
    (artifacts_dir / "guide.md").write_text("Section one\n\nSection two", encoding="utf-8")
    (artifacts_dir / "guide.text_units.json").write_text("{ not json }", encoding="utf-8")

    db = DummyDB([
        {"id": "art-1", "filename": "guide.pdf", "filepath": str(pdf_path)}
    ])

    index = SearchIndex(db)
    chunks = index._gather_chunks()

    assert len(chunks) == 2
    assert all(chunk["meta"]["type"] == "pdf" for chunk in chunks)
    assert all("page" not in chunk["meta"] for chunk in chunks)


def test_open_pdf_rejects_when_fast_mode_enabled(monkeypatch):
    monkeypatch.setenv("FAST_PDF_MODE", "true")
    monkeypatch.setenv("OPEN_PDF_ENABLED", "true")

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.open_pdf("artifact-id"))

    assert exc.value.status_code == 403
    assert "fast mode" in exc.value.detail.lower()


def test_open_pdf_rejects_when_feature_disabled(monkeypatch):
    monkeypatch.setenv("FAST_PDF_MODE", "false")
    monkeypatch.setenv("OPEN_PDF_ENABLED", "false")

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.open_pdf("artifact-id"))

    assert exc.value.status_code == 403
    assert "disabled" in exc.value.detail.lower()


class _OpenPDFStubDB:
    def __init__(self, docs=None, artifacts=None):
        self._docs = docs or []
        self._artifacts = artifacts or []

    def list_documents(self, type=None):
        if type is None:
            return list(self._docs)
        return [d for d in self._docs if d.get("type") == type]

    def get_artifacts(self):
        return list(self._artifacts)


@pytest.fixture
def patch_db(monkeypatch):
    original = main.db

    def _apply(db):
        monkeypatch.setattr(main, "db", db)

    yield _apply
    monkeypatch.setattr(main, "db", original)


def test_open_pdf_missing_file(monkeypatch, tmp_path, patch_db):
    monkeypatch.setenv("FAST_PDF_MODE", "false")
    monkeypatch.setenv("OPEN_PDF_ENABLED", "true")

    fake_uploads = tmp_path / "uploads"
    fake_uploads.mkdir()
    monkeypatch.setattr(main, "UPLOAD_DIR", fake_uploads)

    missing_path = fake_uploads / "missing.pdf"
    patch_db(_OpenPDFStubDB(docs=[{"id": "doc-1", "type": "pdf", "path": str(missing_path)}]))

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.open_pdf("doc-1"))

    assert exc.value.status_code == 403
    assert "missing" in exc.value.detail.lower()


def test_open_pdf_rejects_non_pdf(monkeypatch, tmp_path, patch_db):
    monkeypatch.setenv("FAST_PDF_MODE", "false")
    monkeypatch.setenv("OPEN_PDF_ENABLED", "true")

    fake_uploads = tmp_path / "uploads"
    fake_uploads.mkdir()
    monkeypatch.setattr(main, "UPLOAD_DIR", fake_uploads)

    txt_path = fake_uploads / "notes.txt"
    txt_path.write_text("not a pdf", encoding="utf-8")

    patch_db(_OpenPDFStubDB(docs=[{"id": "doc-2", "type": "pdf", "path": str(txt_path)}]))

    with pytest.raises(main.HTTPException) as exc:
        asyncio.run(main.open_pdf("doc-2"))

    assert exc.value.status_code == 403
    assert "pdf" in exc.value.detail.lower()
