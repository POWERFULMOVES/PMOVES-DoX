import ast
import asyncio
import sys
from pathlib import Path

from fastapi.responses import StreamingResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class StubDB:
    def __init__(self, rows):
        self._rows = rows
        self.last_call = None

    def list_logs(self, level=None, code=None, q=None, ts_from=None, ts_to=None, document_id=None):  # noqa: ANN001 - match production signature
        self.last_call = {
            "level": level,
            "code": code,
            "q": q,
            "ts_from": ts_from,
            "ts_to": ts_to,
            "document_id": document_id,
        }
        return self._rows


def test_export_logs_threads_document_id():
    rows = [
        {"ts": "2024-04-01T12:00:00", "level": "INFO", "code": "INGEST", "component": "pipeline", "message": "started"},
    ]
    stub_db = StubDB(rows)
    export_logs = _load_export_logs(stub_db)

    response = asyncio.run(export_logs(level="INFO", document_id="doc-123"))

    assert isinstance(response, StreamingResponse)
    assert response.headers["content-type"].startswith("text/csv")
    assert stub_db.last_call == {
        "level": "INFO",
        "code": None,
        "q": None,
        "ts_from": None,
        "ts_to": None,
        "document_id": "doc-123",
    }

    body = asyncio.run(_collect_stream(response))
    assert "ts,level,code,component,message" in body


def _load_export_logs(stub_db: StubDB):
    source = (REPO_ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
    module_ast = ast.parse(source, filename="backend/app/main.py")
    export_fn = None
    for node in module_ast.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "export_logs":
            export_fn = node
            break

    assert export_fn is not None, "export_logs definition not found"
    export_fn.decorator_list = []

    module = ast.Module(body=[export_fn], type_ignores=[])
    compiled = compile(module, filename="backend/app/main.py", mode="exec")
    namespace = {
        "StreamingResponse": StreamingResponse,
        "db": stub_db,
    }
    exec(compiled, namespace)
    return namespace["export_logs"]


async def _collect_stream(response: StreamingResponse) -> str:
    chunks = []
    async for chunk in response.body_iterator:
        if isinstance(chunk, str):
            chunk = chunk.encode()
        chunks.append(chunk)
    return b"".join(chunks).decode()
