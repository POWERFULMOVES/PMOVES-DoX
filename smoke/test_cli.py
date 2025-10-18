"""End-to-end smoke test for the pmoves-cli Typer application."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
import unittest

from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.pmoves_cli.cli import app


class CLISmokeTest(unittest.TestCase):
    runner: CliRunner

    @classmethod
    def setUpClass(cls) -> None:  # pragma: no cover - test harness setup
        cls.runner = CliRunner()
        cls.repo_root = REPO_ROOT
        cls.sample_xml = cls.repo_root / "samples" / "sample.xml"
        if not cls.sample_xml.exists():
            raise FileNotFoundError(f"Sample XML missing: {cls.sample_xml}")

    def _env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("FAST_PDF_MODE", "true")
        # Persist all artefacts into the isolated filesystem used by CliRunner
        env.setdefault("DB_PATH", str(Path("cli-smoke.sqlite3").resolve()))
        return env

    def test_ingest_log_and_fetch_logs(self) -> None:
        with self.runner.isolated_filesystem():
            ingest_result = self.runner.invoke(
                app,
                [
                    "--local-app",
                    "--base-url",
                    "http://testserver",
                    "ingest",
                    "log",
                    str(self.sample_xml),
                    "--json",
                ],
                env=self._env(),
            )
            self.assertEqual(ingest_result.exit_code, 0, msg=ingest_result.output)
            ingest_payload = json.loads(ingest_result.stdout)
            self.assertEqual(ingest_payload.get("status"), "ok")
            document_id = ingest_payload.get("document_id")
            self.assertTrue(document_id)

            logs_result = self.runner.invoke(
                app,
                [
                    "--local-app",
                    "--base-url",
                    "http://testserver",
                    "logs",
                    "--document-id",
                    document_id,
                    "--json",
                ],
                env=self._env(),
            )
            self.assertEqual(logs_result.exit_code, 0, msg=logs_result.output)
            payload = json.loads(logs_result.stdout)
            entries = payload.get("logs", [])
            self.assertGreaterEqual(len(entries), 1)
            messages = [entry.get("message") for entry in entries if entry.get("message")]
            self.assertTrue(
                any("Missing income document" in msg for msg in messages),
                msg=f"Unexpected log messages: {messages}",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
