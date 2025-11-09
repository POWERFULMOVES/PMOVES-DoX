import socket
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.app.ingestion.web_ingestion import _is_safe_url  # noqa: E402


def test_is_safe_url_rejects_hostname_resolving_to_private(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):  # noqa: ANN001 - test stub
        return [
            (socket.AF_INET, None, None, None, ("127.0.0.1", 0)),
            (socket.AF_INET6, None, None, None, ("::1", 0, 0, 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    safe, message = _is_safe_url("http://example.test")
    assert not safe
    assert "disallowed" in message


def test_is_safe_url_allows_public_resolution(monkeypatch):
    def fake_getaddrinfo(host, port, *args, **kwargs):  # noqa: ANN001 - test stub
        return [
            (socket.AF_INET, None, None, None, ("93.184.216.34", 0)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    safe, message = _is_safe_url("https://www.example.com")
    assert safe
    assert message == ""
