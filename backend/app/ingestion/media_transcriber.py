from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

MEDIA_ROOT_SUBDIR = "media"

_WHISPER_CACHE: Dict[str, Any] = {}


def _maybe_transcribe_with_whisper(audio_path: Path, language: str | None = None) -> Dict[str, Any]:
    try:
        import whisper  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        return {"status": "unavailable", "reason": f"whisper import failed: {exc}"}

    model_name = os.getenv("WHISPER_MODEL", "tiny.en")
    device = os.getenv("WHISPER_DEVICE", "cpu")

    model = _WHISPER_CACHE.get(model_name)
    if model is None:
        try:
            model = whisper.load_model(model_name, device=device)
            _WHISPER_CACHE[model_name] = model
        except Exception as exc:  # pragma: no cover
            return {"status": "unavailable", "reason": f"whisper load failed: {exc}"}

    try:
        result = model.transcribe(str(audio_path), language=language, fp16=False)
        text = (result.get("text") or "").strip()
        segments = result.get("segments") or []
        return {
            "status": "ok",
            "text": text,
            "segments": segments,
            "engine": "openai-whisper",
            "language": result.get("language", language),
        }
    except Exception as exc:  # pragma: no cover
        return {"status": "error", "reason": str(exc)}


def _load_sidecar_transcript(file_path: Path) -> Dict[str, Any] | None:
    for suffix in (".transcript.txt", ".txt", ".vtt", ".srt"):
        sidecar = file_path.with_suffix(suffix)
        if sidecar.exists():
            try:
                text = sidecar.read_text(encoding="utf-8", errors="ignore").strip()
                if text:
                    return {"status": "ok", "text": text, "engine": "sidecar", "segments": []}
            except Exception:
                continue
    return None


def _probe_media(file_path: Path) -> Dict[str, Any]:
    meta: Dict[str, Any] = {"path": str(file_path)}
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration,format_name,bit_rate",
        "-of",
        "json",
        str(file_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout or "{}")
        fmt = payload.get("format") or {}
        meta.update(
            {
                "duration_seconds": float(fmt.get("duration")) if fmt.get("duration") else None,
                "format": fmt.get("format_name"),
                "bit_rate": float(fmt.get("bit_rate")) if fmt.get("bit_rate") else None,
                "source": "ffprobe",
            }
        )
    except FileNotFoundError:
        meta["source"] = "none"
        meta["notes"] = "ffprobe not installed"
    except Exception as exc:
        meta["source"] = "none"
        meta["notes"] = f"ffprobe failed: {exc}"
    return meta


def transcribe_media(
    file_path: Path,
    artifacts_dir: Path,
    artifact_id: str,
    language: str | None = None,
) -> Dict[str, Any]:
    """Transcribe audio/video using Whisper with graceful fallbacks."""

    media_root = artifacts_dir / MEDIA_ROOT_SUBDIR / artifact_id
    media_root.mkdir(parents=True, exist_ok=True)

    probe = _probe_media(file_path)

    result = _maybe_transcribe_with_whisper(file_path, language=language)
    origin = result.get("engine") if isinstance(result, dict) else None

    if result.get("status") != "ok":
        sidecar = _load_sidecar_transcript(file_path)
        if sidecar:
            result = sidecar
            origin = sidecar.get("engine")
        else:
            result = {
                "status": "unavailable",
                "text": "",
                "segments": [],
                "engine": "unavailable",
                "reason": result.get("reason"),
            }

    transcript_text = (result.get("text") or "").strip()
    transcript_path = media_root / "transcript.txt"
    summary_path = media_root / "transcript.json"

    try:
        transcript_path.write_text(transcript_text, encoding="utf-8")
    except Exception:
        pass
    try:
        summary_payload = {
            "engine": origin,
            "result": result,
            "metadata": probe,
        }
        summary_path.write_text(json.dumps(summary_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    preview = transcript_text[:240] if transcript_text else ""

    return {
        "text": transcript_text,
        "segments": result.get("segments") or [],
        "engine": origin,
        "metadata": probe,
        "status": result.get("status"),
        "warnings": [result.get("reason")] if result.get("reason") else [],
        "artifacts": {
            "transcript_txt": str(transcript_path.relative_to(artifacts_dir)),
            "transcript_json": str(summary_path.relative_to(artifacts_dir)),
        },
        "preview": preview,
    }
