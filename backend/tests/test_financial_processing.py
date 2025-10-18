from __future__ import annotations

import uuid
from types import SimpleNamespace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.analysis.financial_statement_detector import FinancialStatementDetector
from app.ingestion.complex_table_processor import ComplexTableProcessor
from app.main import app, db


class FakeCell:
    def __init__(self, row_index: int, column_index: int, text: str, row_span: int = 1, col_span: int = 1):
        self.row_index = row_index
        self.column_index = column_index
        self.text = text
        self.row_span = row_span
        self.col_span = col_span


@pytest.fixture()
def sample_income_statement_cells() -> list[FakeCell]:
    """Synthetic table derived from the curated income statement PDF sample."""
    pdf_path = Path("samples/financials/financial_statements.pdf")
    assert pdf_path.exists(), "Curated financial statement sample PDF is missing"
    return [
        FakeCell(0, 0, "Metric", row_span=2),
        FakeCell(0, 1, "FY 2023", col_span=2),
        FakeCell(1, 1, "Actual"),
        FakeCell(1, 2, "Budget"),
        FakeCell(2, 0, "Revenue"),
        FakeCell(2, 1, "1,200"),
        FakeCell(2, 2, "1,150"),
        FakeCell(3, 0, "Expenses"),
        FakeCell(3, 1, "600"),
        FakeCell(3, 2, "580"),
        FakeCell(4, 0, "Net Income"),
        FakeCell(4, 1, "600"),
        FakeCell(4, 2, "570"),
    ]


def test_complex_table_processor_handles_merged_cells(sample_income_statement_cells: list[FakeCell]) -> None:
    processor = ComplexTableProcessor()
    table = SimpleNamespace(cells=sample_income_statement_cells)

    merged_df = processor.process_merged_cells(table)
    assert merged_df.iloc[0, 1] == "FY 2023"
    assert merged_df.iloc[1, 0] == "Metric"

    normalized_df, header_info = processor.normalize_table(table)
    assert header_info["levels"] == 2
    assert normalized_df.columns[0] == "Metric"
    assert normalized_df.iloc[0]["Metric"] == "Revenue"
    assert normalized_df.iloc[-1]["Metric"] == "Net Income"


def test_financial_statement_detector_identifies_income_statement(sample_income_statement_cells: list[FakeCell]) -> None:
    processor = ComplexTableProcessor()
    detector = FinancialStatementDetector()

    table = SimpleNamespace(cells=sample_income_statement_cells)
    df, header_info = processor.normalize_table(table)

    stmt_type, confidence = detector.detect_statement_type(df, header_info)
    assert stmt_type == "income_statement"
    assert confidence > 0.5

    summary = detector.parse_financial_statement(df, stmt_type)
    assert summary["revenue"] == pytest.approx(1200.0)
    assert summary["net_income"] == pytest.approx(600.0)


def test_financial_analysis_endpoint_returns_statements() -> None:
    client = TestClient(app)
    db.reset()

    evidence_id = str(uuid.uuid4())
    db.add_evidence(
        {
            "id": evidence_id,
            "artifact_id": "artifact-1",
            "locator": "sample.pdf#table0",
            "preview": "Income Statement",
            "content_type": "financial_table",
            "coordinates": None,
            "full_data": {
                "columns": ["Metric", "FY 2023 / Actual"],
                "rows": [
                    {"Metric": "Revenue", "FY 2023 / Actual": 1200.0},
                    {"Metric": "Net Income", "FY 2023 / Actual": 600.0},
                ],
                "header_info": {"levels": 2, "headers": [["Metric", "FY 2023"], ["Metric", "Actual"]]},
                "statement": {
                    "type": "income_statement",
                    "confidence": 0.66,
                    "summary": {"revenue": 1200.0, "net_income": 600.0},
                },
            },
        }
    )

    response = client.get("/analysis/financials")
    assert response.status_code == 200
    payload = response.json()
    statements = payload.get("statements")
    assert statements and statements[0]["statement_type"] == "income_statement"
    assert statements[0]["summary"]["net_income"] == 600.0

    db.reset()
