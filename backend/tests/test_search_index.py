import sys
import types
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.search import SearchIndex


class DummyDB:
    def __init__(self):
        self.reset_called = False
        self.stored = None

    def get_artifacts(self):
        return []

    def list_apis(self, tag=None, method=None, path_like=None):
        return [{
            "id": "api-1",
            "method": "GET",
            "path": "/status",
            "summary": "Status endpoint",
            "tags": ["health"],
        }]

    def list_logs(self, level=None, code=None, q=None, ts_from=None, ts_to=None):
        return []

    def list_tags(self, document_id=None, q=None):
        return []

    def reset_search_chunks(self):
        self.reset_called = True

    def store_search_chunks(self, records):
        self.stored = records


def test_rebuild_pushes_embeddings_to_remote(monkeypatch):
    db = DummyDB()
    index = SearchIndex(db)

    def fake_load_model():
        index.model = types.SimpleNamespace(
            encode=lambda texts, **_: np.ones((len(texts), 3), dtype="float32")
        )

    monkeypatch.setattr(index, "_load_model", fake_load_model)

    result = index.rebuild()

    assert result["items"] == 1
    assert db.reset_called is True
    assert isinstance(db.stored, list)
    assert len(db.stored) == 1
    record = db.stored[0]
    assert record["source_type"] == "api"
    assert record["chunk_index"] is None or isinstance(record["chunk_index"], int)
    assert isinstance(record["embedding"], list)
    assert len(record["embedding"]) == 3
