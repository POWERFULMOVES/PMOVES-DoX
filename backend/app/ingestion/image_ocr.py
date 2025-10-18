from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

try:  # Optional dependency
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore

try:  # Optional dependency for OCR
    import pytesseract  # type: ignore
except Exception:  # pragma: no cover
    pytesseract = None  # type: ignore

OCR_ROOT_SUBDIR = "ocr"


def _load_sidecar_text(file_path: Path) -> str | None:
    for suffix in (".txt", ".ocr.txt"):
        cand = file_path.with_suffix(suffix)
        if cand.exists():
            try:
                content = cand.read_text(encoding="utf-8", errors="ignore").strip()
                if content:
                    return content
            except Exception:
                continue
    return None


def extract_text_from_image(file_path: Path, artifacts_dir: Path, artifact_id: str) -> Dict[str, Any]:
    """Perform lightweight OCR with fallbacks for smoke testing."""

    ocr_root = artifacts_dir / OCR_ROOT_SUBDIR / artifact_id
    ocr_root.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    text = ""
    meta: Dict[str, Any] = {"path": str(file_path)}

    if Image is not None:
        try:
            with Image.open(file_path) as img:
                meta.update({
                    "format": img.format,
                    "size": img.size,
                    "mode": img.mode,
                })
                if pytesseract is not None:
                    text = pytesseract.image_to_string(img).strip()
                    meta["engine"] = "pytesseract"
                else:
                    warnings.append("pytesseract missing; falling back to sidecar")
        except Exception as exc:
            warnings.append(f"image load failed: {exc}")
    else:
        warnings.append("Pillow not installed")

    if not text:
        sidecar = _load_sidecar_text(file_path)
        if sidecar:
            text = sidecar
            meta["engine"] = "sidecar"
        else:
            meta.setdefault("engine", "unavailable")
            warnings.append("No OCR engine or sidecar available")

    txt_path = ocr_root / "ocr.txt"
    meta_path = ocr_root / "ocr.json"

    try:
        txt_path.write_text(text, encoding="utf-8")
    except Exception:
        pass
    try:
        payload = {"metadata": meta, "warnings": warnings, "text": text}
        meta_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    preview = text[:200] if text else ""

    return {
        "text": text,
        "metadata": meta,
        "warnings": warnings,
        "artifacts": {
            "text": str(txt_path.relative_to(artifacts_dir)),
            "json": str(meta_path.relative_to(artifacts_dir)),
        },
        "preview": preview,
    }
