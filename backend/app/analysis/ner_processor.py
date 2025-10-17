"""Named entity extraction utilities for Docling text elements."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional


class NERProcessor:
    """Extract named entities from textual content using spaCy when available."""

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        *,
        nlp: Any | None = None,
    ) -> None:
        self.model_name = model_name
        self._nlp = nlp
        self._spacy_module: Any | None = None
        self._load_error: Optional[str] = None
        self._load_attempted = nlp is not None
        if nlp is None:
            try:  # Import lazily so environments without spaCy can still run.
                import spacy  # type: ignore

                self._spacy_module = spacy
            except Exception as exc:  # pragma: no cover - optional dependency
                self._load_error = str(exc)
                self._spacy_module = None

    # ------------------------------------------------------------------ helpers
    def _ensure_model(self) -> Any | None:
        if self._nlp is not None:
            return self._nlp
        if self._load_attempted:
            return self._nlp
        self._load_attempted = True
        if self._spacy_module is None:
            return None
        try:
            self._nlp = self._spacy_module.load(self.model_name)
        except Exception as exc:  # pragma: no cover - depends on local models
            self._load_error = str(exc)
            self._nlp = None
        return self._nlp

    # ----------------------------------------------------------------- interface
    @property
    def available(self) -> bool:
        """Return True when a spaCy model is available for inference."""

        return self._ensure_model() is not None

    @property
    def last_error(self) -> Optional[str]:
        return self._load_error

    # ---------------------------------------------------------------- extraction
    def extract_entities(self, text_elements: Iterable[Any]) -> List[dict]:
        """Run NER over iterable Docling text elements."""

        nlp = self._ensure_model()
        if nlp is None:
            return []

        entities: List[dict] = []
        elements = list(text_elements)
        for index, element in enumerate(elements):
            text = getattr(element, "text", "") or ""
            text = text.strip()
            if not text:
                continue

            doc = nlp(text)
            page: Optional[int] = None
            try:
                provenance = getattr(element, "prov", None)
                if provenance:
                    page = getattr(provenance[0], "page", None)
            except Exception:  # pragma: no cover - provenance metadata optional
                page = None

            for ent in doc.ents:
                entities.append(
                    {
                        "text": ent.text,
                        "label": ent.label_,
                        "start_char": int(ent.start_char),
                        "end_char": int(ent.end_char),
                        "page": page,
                        "context": text,
                        "source_index": index,
                    }
                )

        return entities


__all__ = ["NERProcessor"]
