import asyncio
import sys
from pathlib import Path

import pandas as pd
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.ingestion.advanced_table_processor import AdvancedTableProcessor
from app.ingestion.chart_processor import ChartProcessor
from app.ingestion.formula_processor import FormulaProcessor


class DummyBBox:
    def __init__(self, coords):
        self._coords = coords

    def as_tuple(self):
        return self._coords


class DummyProv:
    def __init__(self, page: int, bbox=None):
        self.page = page
        self.bbox = bbox


class DummyTable:
    def __init__(self, data, columns, page, bbox=None):
        self._df = pd.DataFrame(data, columns=columns)
        self.prov = [DummyProv(page, DummyBBox(bbox) if bbox else None)]

    def export_to_dataframe(self):
        return self._df


class DummyElement:
    def __init__(self, label: str, text: str, page: int):
        self.label = label
        self.text = text
        self.prov = [DummyProv(page, DummyBBox((0.1, 0.1, 0.9, 0.2)))]


class DummyText:
    def __init__(self, text: str, page: int):
        self.text = text
        self.prov = [DummyProv(page, DummyBBox((0.2, 0.2, 0.8, 0.3)))]


class DummyPage:
    def __init__(self, tables=None, elements=None):
        self.tables = tables or []
        self.elements = elements or []


class DummyImage:
    def __init__(self, payload: bytes):
        self._payload = payload

    def save(self, path: Path):
        Path(path).write_bytes(self._payload)


class DummyFigure:
    def __init__(self, caption: str, page: int):
        self.caption = caption
        self.image = DummyImage(b"fakepng")
        self.prov = [DummyProv(page, DummyBBox((0.0, 0.0, 1.0, 1.0)))]
        self.label = "figure"


class DummyDoc:
    def __init__(self, pages, tables=None, pictures=None, texts=None):
        self.pages = pages
        self.tables = tables or []
        self.pictures = pictures or []
        self.texts = texts or []


def test_detect_spanning_tables_merges_consecutive_pages():
    table1 = DummyTable([["A", 10], ["B", 20]], ["Name", "Value"], page=0, bbox=(0.1, 0.1, 0.9, 0.4))
    table2 = DummyTable([["C", 30]], ["Name", "Value"], page=1, bbox=(0.1, 0.1, 0.9, 0.3))
    pages = [DummyPage(tables=[table1]), DummyPage(tables=[table2])]
    doc = DummyDoc(pages=pages)

    processor = AdvancedTableProcessor()
    tables = processor.detect_spanning_tables(doc)

    assert len(tables) == 1
    merged = tables[0]
    assert merged["merged"] is True
    assert merged["pages"] == [0, 1]
    df = merged["dataframe"]
    assert isinstance(df, pd.DataFrame)
    assert df.shape[0] == 3


def test_chart_processor_collects_metadata(tmp_path: Path):
    figure = DummyFigure("Revenue by Quarter", page=2)
    doc = DummyDoc(pages=[], pictures=[figure])

    processor = ChartProcessor(enable_ocr=False)
    charts = asyncio.run(processor.process_charts(doc, tmp_path, "sample"))

    assert len(charts) == 1
    chart = charts[0]
    assert chart["caption"] == "Revenue by Quarter"
    assert chart["page"] == 2
    assert chart["image_path"].startswith("charts/")
    saved = tmp_path / chart["image_path"]
    assert saved.exists()


def test_formula_processor_detects_block_and_inline():
    elements = [DummyElement("equation", "E = mc^2", page=0)]
    texts = [DummyText("The famous relation E = mc^2 links energy and mass.", page=0)]
    pages = [DummyPage(elements=elements)]
    doc = DummyDoc(pages=pages, texts=texts)

    processor = FormulaProcessor()
    formulas = processor.extract_formulas(doc)

    assert len(formulas) >= 2
    pages = {item["page"] for item in formulas}
    assert 0 in pages or None in pages
    kinds = {item["kind"] for item in formulas}
    assert {"block", "inline"}.issubset(kinds)
