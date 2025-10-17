import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.analysis import BusinessMetricExtractor, DocumentStructureProcessor, NERProcessor


class DummyProv:
    def __init__(self, page: int | None = None):
        self.page = page
        self.bbox = None


class DummyText:
    def __init__(self, text: str, label: str, page: int | None = None):
        self.text = text
        self.label = label
        self.prov = [DummyProv(page)] if page is not None else []


def test_structure_processor_builds_nested_sections():
    doc = SimpleNamespace(
        texts=[
            DummyText("Annual Report", "title"),
            DummyText("Executive Summary", "heading-1"),
            DummyText("We achieved record revenue.", "paragraph"),
            DummyText("Revenue Details", "heading-2"),
            DummyText("Revenue reached $1M.", "paragraph"),
        ]
    )
    processor = DocumentStructureProcessor()
    structure = processor.build_hierarchy(doc)

    assert structure["title"] == "Annual Report"
    assert structure["sections"][0]["title"] == "Executive Summary"
    assert structure["sections"][0]["content"] == ["We achieved record revenue."]
    assert structure["sections"][0]["subsections"][0]["title"] == "Revenue Details"


def test_metric_extractor_detects_common_patterns():
    extractor = BusinessMetricExtractor()
    text = "Our revenue reached $2M with 15% growth and 35% margin."
    hits = extractor.extract_metrics(text)
    types = {hit["type"] for hit in hits}
    assert {"revenue", "growth", "margin"}.issubset(types)
    for hit in hits:
        assert "context" in hit and hit["context"]


def test_ner_processor_with_custom_model():
    spacy = pytest.importorskip("spacy")
    nlp = spacy.blank("en")
    ruler = nlp.add_pipe("entity_ruler")
    ruler.add_patterns([
        {"label": "ORG", "pattern": "Acme Labs"},
        {"label": "PERSON", "pattern": "Jane Doe"},
    ])

    processor = NERProcessor(nlp=nlp)
    elements = [
        DummyText("Acme Labs appointed Jane Doe as CTO.", "paragraph", page=2),
    ]
    entities = processor.extract_entities(elements)

    labels = {ent["label"] for ent in entities}
    assert {"ORG", "PERSON"}.issubset(labels)
    assert all(ent.get("context") for ent in entities)
    assert any(ent.get("page") == 2 for ent in entities)
