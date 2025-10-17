"""Formula and equation extraction helpers for Docling output."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple


class FormulaProcessor:
    """Detect and normalise mathematical formulas from Docling documents."""

    _BLOCK_LABELS = {"equation", "math", "formula", "latex"}

    def __init__(self) -> None:
        # Rough heuristic for inline formulas: matches tokens containing = or maths symbols
        self.inline_pattern = re.compile(
            r"(?P<formula>(?:[A-Za-z0-9\)\]]+\s*)?(?:=|≈|≤|≥|∝|→|←)\s*[A-Za-z0-9\(\)\[\]\+\-\*/^_.,\s]+)"
        )

    def extract_formulas(self, doc: Any) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen: Set[Tuple[int, str]] = set()

        # Page-level structured elements first
        for page_idx, page in enumerate(getattr(doc, "pages", []) or []):
            elements = getattr(page, "elements", None)
            if not elements:
                continue
            for element in elements:
                label = getattr(element, "label", "") or ""
                text = getattr(element, "text", "") or ""
                if label.lower() in self._BLOCK_LABELS and text:
                    formula = self._build_formula_record(
                        page_idx,
                        text,
                        self._convert_to_latex(text),
                        self._extract_bbox(element),
                        "block",
                    )
                    key = (page_idx, formula["content"])
                    if key not in seen:
                        seen.add(key)
                        results.append(formula)

        # Inline detection from text streams (Docling exposes doc.texts with provenance)
        for item in getattr(doc, "texts", []) or []:
            text = getattr(item, "text", "") or ""
            if not text:
                continue
            page = self._extract_page(item)
            for match in self.inline_pattern.finditer(text):
                raw = match.group("formula").strip()
                if not raw:
                    continue
                key = (page or -1, raw)
                if key in seen:
                    continue
                seen.add(key)
                results.append(
                    self._build_formula_record(
                        page,
                        raw,
                        self._convert_to_latex(raw),
                        self._extract_bbox(item),
                        "inline",
                    )
                )

        return results

    def _extract_page(self, item: Any) -> Optional[int]:
        try:
            prov = getattr(item, "prov", None)
            if prov:
                return getattr(prov[0], "page", None)
        except Exception:
            return None
        return None

    def _extract_bbox(self, item: Any) -> Optional[tuple[float, float, float, float]]:
        try:
            prov = getattr(item, "prov", None)
            if prov:
                bbox = getattr(prov[0], "bbox", None)
                if bbox and hasattr(bbox, "as_tuple"):
                    return tuple(bbox.as_tuple())  # type: ignore[arg-type]
        except Exception:
            return None
        return None

    def _build_formula_record(
        self,
        page: Optional[int],
        content: str,
        latex: str,
        bbox: Optional[tuple[float, float, float, float]],
        kind: str,
    ) -> Dict[str, Any]:
        return {
            "page": page,
            "content": content,
            "latex": latex,
            "bbox": bbox,
            "kind": kind,
        }

    def _convert_to_latex(self, text: str) -> str:
        # Placeholder: Docling already emits LaTeX for many equation blocks.
        # We simply return the trimmed text for now.
        return text.strip()
