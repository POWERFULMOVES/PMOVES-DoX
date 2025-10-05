import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest

from app import database_factory
from app.database import ExtendedDatabase


def test_init_database_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DB_BACKEND", raising=False)
    monkeypatch.delenv("SUPABASE_DUAL_WRITE", raising=False)
    db, meta = database_factory.init_database()

    assert isinstance(db, ExtendedDatabase)
    assert meta["active"].startswith("sqlite")


def test_init_database_dual_write_when_supabase_available(monkeypatch):
    class DummySupabase:
        backend = "supabase"

        def add_artifact(self, *_args, **_kwargs):  # pragma: no cover - helper stub
            return "artifact-id"

    def fake_supabase_database():
        return DummySupabase()

    monkeypatch.setenv("SUPABASE_DUAL_WRITE", "true")
    monkeypatch.delenv("DB_BACKEND", raising=False)
    monkeypatch.setitem(database_factory.__dict__, "SupabaseDatabase", fake_supabase_database)

    db, meta = database_factory.init_database()

    assert isinstance(db, database_factory.DualDatabase)
    assert meta["dual_write"] is True


def test_init_database_supabase_unavailable(monkeypatch):
    class FakeError(Exception):
        pass

    def failing_supabase():
        raise database_factory.SupabaseUnavailable("no creds")

    monkeypatch.setenv("DB_BACKEND", "sqlite")
    monkeypatch.setenv("SUPABASE_DUAL_WRITE", "true")
    monkeypatch.setitem(database_factory.__dict__, "SupabaseDatabase", failing_supabase)

    db, meta = database_factory.init_database()

    assert isinstance(db, ExtendedDatabase)
    assert meta["dual_write"] is False
