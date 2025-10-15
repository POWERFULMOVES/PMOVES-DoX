import sys
from pathlib import Path

from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app import main  # noqa: E402


class StubDB:
    def __init__(self, artifact_id: str, artifact_path: Path):
        self._artifact = {
            "id": artifact_id,
            "filename": artifact_path.name,
            "filepath": str(artifact_path),
            "filetype": artifact_path.suffix,
        }
        self._document = {
            "id": artifact_id,
            "path": str(artifact_path),
            "type": "txt",
        }
        self._tags: list[dict] = []

    def get_artifacts(self):
        return [self._artifact]

    def list_documents(self, type: str | None = None):  # noqa: A002 - match production signature
        return [self._document]

    def list_tags(self, document_id: str | None = None, q: str | None = None):
        if document_id:
            return [t for t in self._tags if t.get("document_id") == document_id]
        return list(self._tags)

    def list_logs(self, level=None, code=None, q=None, ts_from=None, ts_to=None):  # noqa: ANN001 - test stub
        return []

    def list_apis(self, tag=None, method=None, path_like=None):  # noqa: ANN001 - test stub
        return []

    def list_log_messages(self, document_id: str):
        return []

    def has_tag(self, document_id: str, tag: str) -> bool:
        return any(t.get("document_id") == document_id and t.get("tag", "").lower() == tag.lower() for t in self._tags)

    def add_tag(self, tag: dict):
        self._tags.append(tag)


def test_autotag_endpoint_persists_tags(monkeypatch, tmp_path):
    artifact_id = "artifact-1"
    artifact_path = tmp_path / "sample.txt"
    artifact_path.write_text("Loan Origination enables Loan Servicing.", encoding="utf-8")

    stub_db = StubDB(artifact_id, artifact_path)
    monkeypatch.setattr(main, "db", stub_db)
    monkeypatch.setattr(main, "HRM_ENABLED", False)

    def _fake_run_langextract(**kwargs):
        return {"entities": [{"extraction_text": "Loan Servicing"}]}

    monkeypatch.setattr(main, "run_langextract", _fake_run_langextract)

    client = TestClient(main.app)
    resp = client.post(f"/autotag/{artifact_id}", json={"async_run": True})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["tags_saved"] == 1
    assert data["tags_total"] == 1

    stored_tags = stub_db.list_tags(document_id=artifact_id)
    assert any(t.get("tag") == "Loan Servicing" for t in stored_tags)
