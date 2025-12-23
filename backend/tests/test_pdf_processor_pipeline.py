import asyncio
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion import pdf_processor


class DummyBBox:
    def __init__(self, coords):
        self._coords = coords

    def as_tuple(self):
        return tuple(self._coords)


class DummyProv:
    def __init__(self, page: int, bbox=None):
        self.page = page
        self.bbox = bbox


class DummyTable:
    def __init__(self, data, columns, page, bbox):
        self._df = pd.DataFrame(data, columns=columns)
        self.prov = [DummyProv(page, DummyBBox(bbox))]

    def export_to_dataframe(self):
        return self._df


class DummyElement:
    def __init__(self, label: str, text: str, page: int):
        self.label = label
        self.text = text
        self.prov = [DummyProv(page, DummyBBox((0.1, 0.1, 0.9, 0.2)))]


class DummyText:
    def __init__(self, label: str, text: str, page: int):
        self.label = label
        self.text = text
        self.prov = [DummyProv(page, DummyBBox((0.2, 0.2, 0.8, 0.3)))]


class DummyImage:
    def save(self, path: Path):
        path.write_bytes(b"fakepng")


class DummyFigure:
    def __init__(self, caption: str, page: int):
        self.caption = caption
        self.image = DummyImage()
        self.prov = [DummyProv(page, DummyBBox((0.0, 0.0, 1.0, 1.0)))]
        self.label = "figure"


class DummyPage:
    def __init__(self, tables=None, elements=None):
        self.tables = tables or []
        self.elements = elements or []


class DummyDoc:
    def __init__(self, pages, pictures, texts):
        self.pages = pages
        self.pictures = pictures
        self.texts = texts
        self.tables = [t for p in pages for t in p.tables]

    def export_to_markdown(self):
        return "# Sample Document"

    def export_to_dict(self):
        return {"texts": [{"text": t.text} for t in self.texts]}


class DummyConverter:
    def __init__(self, *_, **__):
        pass

    def convert(self, *_):
        return SimpleNamespace(document=build_dummy_doc())


def build_dummy_doc() -> DummyDoc:
    table_cols = ["Name", "Value"]
    table1 = DummyTable([["A", 10], ["B", 20]], table_cols, page=0, bbox=(0.1, 0.1, 0.9, 0.4))
    table2 = DummyTable([["C", 30]], table_cols, page=1, bbox=(0.1, 0.1, 0.9, 0.3))

    pages = [
        DummyPage(tables=[table1], elements=[DummyElement("equation", "E = mc^2", page=0)]),
        DummyPage(tables=[table2]),
    ]

    texts = [
        DummyText("title", "Sample Report", page=0),
        DummyText("heading-1", "Executive Summary", page=0),
        DummyText("paragraph", "Revenue reached $1M with ROAS: 3.5.", page=0),
        DummyText("paragraph", "CPA: $12.50 after conversions: 100", page=1),
        DummyText("heading-2", "Financials", page=1),
    ]

    figures = [DummyFigure("Revenue by Quarter", page=1)]

    return DummyDoc(pages=pages, pictures=figures, texts=texts)


def test_process_pdf_collects_advanced_artifacts(tmp_path, monkeypatch):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    artifacts_dir = tmp_path / "artifacts"

    monkeypatch.setattr(pdf_processor, "DocumentConverter", DummyConverter)

    facts, evidence, analysis = asyncio.run(
        pdf_processor.process_pdf(
            pdf_path,
            "2025-W40",
            artifacts_dir,
            "artifact-123",
        )
    )

    table_evidence = [ev for ev in evidence if ev.get("content_type") == "table"]
    chart_evidence = [ev for ev in evidence if ev.get("content_type") == "chart"]
    formula_evidence = [ev for ev in evidence if ev.get("content_type") == "formula"]

    assert len(table_evidence) == 1
    assert table_evidence[0]["full_data"]["merged"] is True
    assert analysis["tables"][0]["row_count"] == 3

    assert chart_evidence, "chart evidence not captured"
    chart_path = chart_evidence[0]["full_data"].get("image_path")
    if chart_path:
        saved = artifacts_dir / chart_path
        assert saved.exists()

    assert formula_evidence, "formula evidence missing"

    assert any(fact.get("entity") == "chart" for fact in facts)
    assert any(fact.get("entity") == "formula" for fact in facts)

    assert analysis["structure"] and analysis["structure"].get("sections")
    assert analysis["metric_hits"], "metric hits should be populated"

    md_path = artifacts_dir / "sample.md"
    json_path = artifacts_dir / "sample.json"
    units_path = artifacts_dir / "sample.text_units.json"
    assert md_path.exists()
    assert json_path.exists()
    assert units_path.exists()
