"""Document structure analysis helpers."""

from __future__ import annotations

from typing import Any, Dict, List


class DocumentStructureProcessor:
    """Analyze heading hierarchy from Docling text elements."""

    def build_hierarchy(self, doc: Any) -> Dict[str, Any]:
        """Return a nested representation of the document structure."""

        structure: Dict[str, Any] = {"title": self._extract_title(doc), "sections": []}
        stack: List[Dict[str, Any]] = []

        for element in getattr(doc, "texts", []) or []:
            label = getattr(element, "label", "") or ""
            text = (getattr(element, "text", "") or "").strip()
            if not label or not text:
                continue

            if label.startswith("heading"):
                level = self._coerce_level(label)
                section = {
                    "level": level,
                    "title": text,
                    "content": [],
                    "subsections": [],
                }

                while stack and stack[-1]["level"] >= level:
                    stack.pop()

                if not stack:
                    structure["sections"].append(section)
                else:
                    stack[-1].setdefault("subsections", []).append(section)

                stack.append(section)
            elif label == "paragraph" and stack:
                stack[-1].setdefault("content", []).append(text)

        return structure

    def _extract_title(self, doc: Any) -> str:
        for element in getattr(doc, "texts", []) or []:
            label = getattr(element, "label", "")
            if label == "title":
                text = (getattr(element, "text", "") or "").strip()
                if text:
                    return text
        return "Untitled"

    def _coerce_level(self, label: str) -> int:
        try:
            return int(label.split("-", 1)[1])
        except Exception:
            return 1


__all__ = ["DocumentStructureProcessor"]
