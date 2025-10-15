import asyncio
import sys
from pathlib import Path

import pandas as pd
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import Database
from app.ingestion.csv_processor import process_csv
from app.qa_engine import QAEngine


def test_qa_engine_returns_evidence_with_saved_id(tmp_path):
    data = pd.DataFrame(
        {
            "Spend": [120.0, 80.0],
            "Revenue": [300.0, 150.0],
        }
    )
    artifact_path = Path(tmp_path) / "sample_metrics.csv"
    data.to_csv(artifact_path, index=False)

    facts, evidence = process_csv(artifact_path, report_week="2024-W01")

    db = Database(db_path=str(Path(tmp_path) / "test.sqlite3"))

    for ev in evidence:
        db.add_evidence(ev)

    for fact in facts:
        db.add_fact(fact)

    stored_facts = db.get_facts()
    assert stored_facts, "Expected facts to be stored in the database"
    assert stored_facts[0]["evidence_id"] == facts[0]["evidence_id"]

    qa = QAEngine(db)
    response = asyncio.run(qa.ask("What is the total spend for the week?"))

    assert response["metric"] == "spend"
    assert response["total"] == pytest.approx(facts[0]["metrics"]["spend"])
    assert response["evidence"], "Expected QA response to include evidence entries"
    returned_ids = {ev["id"] for ev in response["evidence"]}
    assert returned_ids == {facts[0]["evidence_id"]}
