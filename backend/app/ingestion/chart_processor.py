"""Chart extraction helpers for Docling PDF output."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency – pytesseract may not be installed in minimal envs.
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pytesseract = None  # type: ignore

try:  # Pillow is optional when Docling already returns encoded bytes
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore


class ChartProcessor:
    """Extract and analyse chart figures produced by Docling."""

    def __init__(self, enable_ocr: bool = True) -> None:
        self.enable_ocr = enable_ocr

    def process_charts(self, doc: Any, artifacts_dir: Path, stem: str) -> List[Dict[str, Any]]:
        """Persist chart images and return lightweight metadata.

        Note: This is synchronous for compatibility with sync callers. The underlying
        operations (_save_figure, _ocr_image) are already synchronous.
        """

        pictures = getattr(doc, "pictures", []) or []
        if not pictures:
            return []

        charts_dir = artifacts_dir / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, Any]] = []
        for idx, figure in enumerate(pictures):
            chart_id = f"{stem}_chart_{idx}"
            output_path = charts_dir / f"{chart_id}.png"
            saved_path = self._save_figure(figure, output_path)

            page = self._extract_page(figure)
            bbox = self._extract_bbox(figure)
            caption = self._extract_caption(figure)
            chart_type = self._detect_chart_type(figure)

            text_summary: Optional[str] = None
            if self.enable_ocr and pytesseract and saved_path:
                text_summary = self._ocr_image(saved_path)

            rel_path = None
            if saved_path:
                try:
                    rel_path = str(saved_path.relative_to(artifacts_dir))
                except ValueError:
                    rel_path = str(saved_path)

            results.append(
                {
                    "id": chart_id,
                    "page": page,
                    "bbox": bbox,
                    "image_path": rel_path,
                    "caption": caption,
                    "type": chart_type,
                    "extracted_text": text_summary,
                }
            )

        return results

    def _save_figure(self, figure: Any, path: Path) -> Optional[Path]:
        image = getattr(figure, "image", None)
        if image is None:
            return None
        try:
            if hasattr(image, "save"):
                image.save(path)
                return path
            if isinstance(image, (bytes, bytearray)):
                path.write_bytes(image)
                return path
            if Image is not None:
                # Some Docling builds return numpy arrays; convert via Pillow when available.
                try:
                    img = Image.fromarray(image)  # type: ignore[arg-type]
                    img.save(path)
                    return path
                except Exception:
                    pass
        except Exception:
            return None
        return None

    def _extract_page(self, figure: Any) -> Optional[int]:
        try:
            prov = getattr(figure, "prov", None)
            if prov:
                return getattr(prov[0], "page", None)
        except Exception:
            return None
        return None

    def _extract_bbox(self, figure: Any) -> Optional[tuple[float, float, float, float]]:
        try:
            prov = getattr(figure, "prov", None)
            if prov:
                bbox = getattr(prov[0], "bbox", None)
                if bbox and hasattr(bbox, "as_tuple"):
                    return tuple(bbox.as_tuple())  # type: ignore[arg-type]
        except Exception:
            return None
        return None

    def _extract_caption(self, figure: Any) -> str:
        for attr in ("caption", "description", "text", "summary", "alt_text"):
            try:
                value = getattr(figure, attr, None)
                if value:
                    value = str(value).strip()
                    if value:
                        return value
            except Exception:
                continue
        return ""

    def _detect_chart_type(self, figure: Any) -> str:
        # Placeholder for heuristics; Docling currently does not expose structured chart types.
        label = getattr(figure, "label", None)
        if isinstance(label, str) and label:
            return label.lower()
        return "unknown"

    def _ocr_image(self, image_path: Path) -> Optional[str]:
        if not pytesseract or Image is None:
            return None
        try:
            with Image.open(image_path) as img:  # type: ignore[attr-defined]
                text = pytesseract.image_to_string(img)  # type: ignore[operator]
            text = (text or "").strip()
            return text or None
        except Exception:
            return None
