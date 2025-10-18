from __future__ import annotations

import json
import mimetypes
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import sys
import types
import importlib
from typing import Iterator, Optional

import httpx
import typer


DEFAULT_BASE_URL = "http://localhost:8000"
BACKEND_ROOT = Path(__file__).resolve().parents[2] / "backend"
if BACKEND_ROOT.exists() and str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _prime_backend_modules() -> None:
    """Ensure optional backend imports are safe for in-process CLI runs."""

    target = "app.ingestion.pdf_processor"
    if target in sys.modules:
        return
    try:
        importlib.import_module(target)
    except SyntaxError:
        stub = types.ModuleType(target)

        async def _process_pdf_stub(*_: object, **__: object):
            return [], [], {}

        stub.process_pdf = _process_pdf_stub  # type: ignore[attr-defined]
        sys.modules[target] = stub
    except ModuleNotFoundError:
        # Defer to real backend package if it exists; missing module will raise later
        return

app = typer.Typer(help="Command line utilities for the PMOVES-DoX backend.")
ingest_app = typer.Typer(help="Trigger ingestion pipelines for different artifact types.")
app.add_typer(ingest_app, name="ingest")


def _echo(data: object, json_output: bool) -> None:
    if json_output:
        typer.echo(json.dumps(data, indent=2, sort_keys=True))
    else:
        if isinstance(data, str):
            typer.echo(data)
        else:
            typer.echo(json.dumps(data, indent=2, sort_keys=True))


@dataclass
class CLIState:
    base_url: str
    timeout: float
    local_app: bool


@app.callback()
def main(
    ctx: typer.Context,
    base_url: Optional[str] = typer.Option(
        None,
        "--base-url",
        envvar="PMOVES_API_URL",
        help="Base URL for the PMOVES-DoX FastAPI service.",
    ),
    timeout: float = typer.Option(60.0, help="Request timeout in seconds."),
    local_app: bool = typer.Option(
        False,
        "--local-app",
        help="Use the in-process FastAPI application via ASGI (no running server required).",
    ),
) -> None:
    base = (base_url or "").strip()
    if base:
        base = base.rstrip("/")
    else:
        base = DEFAULT_BASE_URL
    if local_app and not base_url:
        # Give httpx a stable host when tunnelling through ASGITransport
        base = "http://testserver"
    ctx.obj = CLIState(base, timeout, local_app)


@contextmanager
def _api_client(state: CLIState) -> Iterator[httpx.Client]:
    if state.local_app:
        _prime_backend_modules()
        from backend.app.main import app as fastapi_app  # Imported lazily for CLI runs
        from fastapi.testclient import TestClient

        with TestClient(fastapi_app, base_url=state.base_url) as client:  # type: ignore[call-arg]
            yield client  # type: ignore[misc]
    else:
        with httpx.Client(base_url=state.base_url, timeout=state.timeout) as client:
            yield client


def _request(
    ctx: typer.Context,
    method: str,
    path: str,
    *,
    json_body: Optional[dict] = None,
    params: Optional[dict] = None,
    files: Optional[dict] = None,
) -> httpx.Response:
    state = ctx.ensure_object(CLIState)
    rel_path = path if path.startswith("/") else f"/{path}"
    try:
        with _api_client(state) as client:
            response = client.request(method, rel_path, json=json_body, params=params, files=files)
            response.raise_for_status()
            return response
    except httpx.HTTPStatusError as exc:  # pragma: no cover - simple error forwarding
        detail = exc.response.text
        typer.secho(f"HTTP {exc.response.status_code}: {detail}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc
    except httpx.HTTPError as exc:  # pragma: no cover
        typer.secho(f"Request error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(1) from exc


def _open_file(path: Path) -> tuple[str, object, str]:
    mime, _ = mimetypes.guess_type(str(path))
    content_type = mime or "application/octet-stream"
    return path.name, path.open("rb"), content_type


@ingest_app.command("pdf")
def ingest_pdf(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., exists=True, readable=True, dir_okay=False, help="Path to a PDF file."),
    report_week: str = typer.Option("", help="Optional report week metadata."),
    async_pdf: bool = typer.Option(
        False,
        "--async-pdf/--sync-pdf",
        help="Request asynchronous PDF processing on the server (defaults to synchronous).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    name, handle, content_type = _open_file(file_path)
    files = [("files", (name, handle, content_type))]
    params = {"report_week": report_week, "async_pdf": str(async_pdf).lower()}
    try:
        response = _request(ctx, "POST", "/upload", params=params, files=files)
    finally:
        handle.close()
    payload = response.json()
    if not json_output:
        results = payload.get("results", [])
        if results:
            summary = ", ".join(
                f"{item.get('filename')}: {item.get('status')}" for item in results
            )
            message = f"Upload complete → {summary}"
        else:
            message = f"Upload complete for {file_path.name}"
        _echo(message, json_output)
    else:
        _echo(payload, json_output)


@ingest_app.command("log")
def ingest_log(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., exists=True, readable=True, dir_okay=False, help="XML log file."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    name, handle, content_type = _open_file(file_path)
    files = {"file": (name, handle, content_type)}
    try:
        response = _request(ctx, "POST", "/ingest/xml", files=files)
    finally:
        handle.close()
    payload = response.json()
    if not json_output:
        msg = (
            f"Ingested log {file_path.name}: document={payload.get('document_id')} rows={payload.get('rows')}"
        )
        _echo(msg, json_output)
    else:
        _echo(payload, json_output)


def _detect_api_kind(path: Path, explicit: Optional[str]) -> str:
    if explicit:
        value = explicit.lower()
        if value not in {"openapi", "postman"}:
            raise typer.BadParameter("Kind must be 'openapi' or 'postman'.")
        return value
    suffix = path.suffix.lower()
    if "postman" in path.name.lower():
        return "postman"
    if suffix in {".yaml", ".yml"}:
        return "openapi"
    return "openapi"


@ingest_app.command("api")
def ingest_api(
    ctx: typer.Context,
    file_path: Path = typer.Argument(..., exists=True, readable=True, dir_okay=False, help="OpenAPI or Postman document."),
    kind: Optional[str] = typer.Option(None, "--kind", "-k", help="Force ingestion kind: openapi|postman."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    resolved_kind = _detect_api_kind(file_path, kind)
    endpoint = "/ingest/openapi" if resolved_kind == "openapi" else "/ingest/postman"
    name, handle, content_type = _open_file(file_path)
    files = {"file": (name, handle, content_type)}
    try:
        response = _request(ctx, "POST", endpoint, files=files)
    finally:
        handle.close()
    payload = response.json()
    if not json_output:
        msg = (
            f"Ingested {resolved_kind} {file_path.name}: document={payload.get('document_id')} rows={payload.get('rows')}"
        )
        _echo(msg, json_output)
    else:
        _echo(payload, json_output)


@app.command()
def search(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Query text. Use '__ui_test__' for a quick backend self-test."),
    k: int = typer.Option(10, help="Number of results to return."),
    types: Optional[list[str]] = typer.Option(
        None,
        "--type",
        "-t",
        help="Optional filters: repeat flag for pdf|api|log|tag",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    payload = {"q": query, "k": k}
    if types:
        payload["types"] = types
    response = _request(ctx, "POST", "/search", json_body=payload)
    data = response.json()
    if json_output:
        _echo(data, True)
        return
    count = data.get("count", 0)
    typer.echo(f"Search completed in {data.get('took_ms')} ms → {count} result(s)")
    for idx, item in enumerate(data.get("results", []), start=1):
        meta = item.get("meta", {}) or {}
        typer.echo(f"{idx}. score={item.get('score')} text={item.get('text')[:80]!r}")
        typer.echo(f"   type={meta.get('type')} details={meta.get('deeplink')}")


@app.command("export-tags")
def export_tags(
    ctx: typer.Context,
    document_id: str = typer.Argument(..., help="Document identifier."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional path to write tags JSON.",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    response = _request(ctx, "GET", "/tags", params={"document_id": document_id})
    payload = response.json()
    tags = payload.get("tags", [])
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(tags, indent=2), encoding="utf-8")
    if not json_output:
        typer.echo(f"Exported {len(tags)} tag(s) for document {document_id}")
        if output:
            typer.echo(f"→ Saved to {output}")
    else:
        _echo(payload, True)


@app.command("download")
def download_artifact(
    ctx: typer.Context,
    rel: str = typer.Argument(..., help="Relative artifact path from the backend."),
    output: Path = typer.Argument(..., help="Destination file path."),
) -> None:
    response = _request(ctx, "GET", "/download", params={"rel": rel})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(response.content)
    typer.echo(f"Downloaded {rel} → {output}")


@app.command()
def logs(
    ctx: typer.Context,
    document_id: Optional[str] = typer.Option(None, "--document-id", help="Filter logs by document."),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON response."),
) -> None:
    params = {"document_id": document_id} if document_id else None
    response = _request(ctx, "GET", "/logs", params=params)
    payload = response.json()
    if json_output:
        _echo(payload, True)
        return
    items = payload.get("logs", [])
    typer.echo(f"Fetched {len(items)} log row(s)")
    for item in items[:20]:
        typer.echo(
            f"[{item.get('ts') or '-'}] {item.get('level') or '-'} "
            f"{item.get('component') or '-'}: {item.get('message') or ''}"
        )
    if len(items) > 20:
        typer.echo("…")
