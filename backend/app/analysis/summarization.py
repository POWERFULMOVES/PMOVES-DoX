from __future__ import annotations

import os
import textwrap
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Literal, Optional, Tuple

from app.extraction.langextract_adapter import run_langextract

SummaryStyle = Literal["bullet", "executive", "action_items"]

PROMPT_TEMPLATES: Dict[SummaryStyle, str] = {
    "bullet": (
        "Summarize the following workspace findings into crisp bullet points. "
        "Focus on quantitative metrics, noteworthy trends, and anomalies."
    ),
    "executive": (
        "Write an executive-ready summary that highlights the overall status, key wins, and areas of concern."
    ),
    "action_items": (
        "Review the findings and produce concrete action items. Each action should include the rationale."
    ),
}


@dataclass
class SummaryPayload:
    """Structured representation of a generated summary."""

    id: str
    style: SummaryStyle
    provider: str
    prompt: str
    scope: str
    scope_key: str
    artifact_ids: List[str]
    summary_text: str
    evidence_ids: List[str]
    created_at: str


class SummarizationService:
    """Generate and persist workspace or artifact summaries."""

    def __init__(self, db: Any, *, default_provider: Optional[str] = None) -> None:
        self.db = db
        self.default_provider = (default_provider or os.getenv("SUMMARY_PROVIDER", "heuristic")).lower()

    # --------------------------------------------------------------------- public
    def generate_summary(
        self,
        *,
        style: SummaryStyle,
        scope: Literal["workspace", "artifact"],
        artifact_ids: Optional[Iterable[str]] = None,
        provider: Optional[str] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """Return a cached summary or generate a new one."""

        artifact_list = sorted({str(a) for a in (artifact_ids or []) if str(a).strip()})
        scope_key = self._build_scope_key(scope, artifact_list)

        if scope == "artifact" and not artifact_list:
            raise ValueError("artifact scope requires at least one artifact id")

        if not force_refresh:
            cached = self._load_cached(scope_key, style)
            if cached:
                return cached

        context_lines, evidence_ids = self._collect_context(scope, artifact_list)
        summary_text, provider_used = self._invoke_provider(
            provider or self.default_provider,
            style,
            context_lines,
            artifact_list,
        )

        payload = SummaryPayload(
            id=str(uuid.uuid4()),
            style=style,
            provider=provider_used,
            prompt=PROMPT_TEMPLATES[style],
            scope=scope,
            scope_key=scope_key,
            artifact_ids=artifact_list,
            summary_text=summary_text,
            evidence_ids=evidence_ids,
            created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        )
        self._persist(payload)
        return self._inflate(payload)

    def list_summaries(
        self,
        *,
        scope: Optional[str] = None,
        style: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        records = self.db.list_summaries(scope=scope, style=style)
        summaries: List[Dict[str, Any]] = []
        for record in records:
            summaries.append(self._inflate(self._payload_from_record(record)))
        return summaries

    # ----------------------------------------------------------------- internals
    def _build_scope_key(self, scope: str, artifact_ids: List[str]) -> str:
        if scope == "workspace":
            return "workspace"
        return f"artifact:{','.join(artifact_ids)}"

    def _load_cached(self, scope_key: str, style: SummaryStyle) -> Optional[Dict[str, Any]]:
        record = self.db.get_summary(scope_key=scope_key, style=style)
        if not record:
            return None
        payload = self._payload_from_record(record)
        return self._inflate(payload)

    def _payload_from_record(self, record: Dict[str, Any]) -> SummaryPayload:
        style = str(record.get("style") or "bullet")
        if style not in PROMPT_TEMPLATES:
            style = "bullet"
        prompt_text = record.get("prompt") or PROMPT_TEMPLATES.get(style, PROMPT_TEMPLATES["bullet"])
        return SummaryPayload(
            id=str(record.get("id")),
            style=style,  # type: ignore[arg-type]
            provider=str(record.get("provider") or "heuristic"),
            prompt=str(prompt_text),
            scope=str(record.get("scope", "workspace")),
            scope_key=str(record.get("scope_key", "workspace")),
            artifact_ids=list(record.get("artifact_ids", [])),
            summary_text=str(record.get("summary_text", "")),
            evidence_ids=list(record.get("evidence_ids", [])),
            created_at=str(record.get("created_at", datetime.utcnow().isoformat(timespec="seconds") + "Z")),
        )

    def _collect_context(self, scope: str, artifact_ids: List[str]) -> Tuple[List[str], List[str]]:
        facts = self.db.get_facts()
        artifact_filter = set(artifact_ids)
        lines: List[str] = []
        evidence_ids: List[str] = []

        for fact in facts:
            if scope == "artifact" and artifact_filter and fact.get("artifact_id") not in artifact_filter:
                continue
            metrics = fact.get("metrics") or {}
            metric_parts = [f"{k}: {v}" for k, v in metrics.items() if v not in (None, "")]
            if not metric_parts:
                continue
            entity = fact.get("entity") or "Unknown entity"
            lines.append(f"{entity} -> {', '.join(metric_parts)}")
            eid = fact.get("evidence_id")
            if eid:
                evidence_ids.append(str(eid))

        if not lines:
            # Fallback to artifact filenames or a placeholder message
            artifacts = self.db.get_artifacts()
            if scope == "artifact" and artifact_filter:
                artifacts = [a for a in artifacts if a.get("id") in artifact_filter]
            if artifacts:
                for art in artifacts:
                    lines.append(
                        f"Artifact {art.get('filename', art.get('id'))} ({art.get('filetype', '?')}) queued for summarization."
                    )
            else:
                lines.append("No structured facts are available; provide a high level status update.")

        return lines, evidence_ids

    def _invoke_provider(
        self,
        provider: str,
        style: SummaryStyle,
        context_lines: List[str],
        artifact_ids: List[str],
    ) -> Tuple[str, str]:
        prompt = PROMPT_TEMPLATES[style]
        context = "\n".join(context_lines)
        provider_name = provider.lower()

        if provider_name == "langextract":
            summary = self._try_langextract(prompt, context)
            if summary:
                return summary, "langextract"
        elif provider_name == "ollama":
            summary = self._try_ollama(prompt, context)
            if summary:
                return summary, "ollama"
        elif provider_name == "openai":
            summary = self._try_openai(prompt, context)
            if summary:
                return summary, "openai"

        summary = self._fallback_summary(style, context_lines, artifact_ids)
        return summary, "heuristic"

    def _try_langextract(self, prompt: str, context: str) -> Optional[str]:
        try:
            response = run_langextract(
                text=context,
                prompt_description=prompt,
                examples=[],
                extraction_passes=1,
                max_char_buffer=8000,
            )
            entities = response.get("entities", [])
            texts = [e.get("extraction_text") for e in entities if e.get("extraction_text")]
            if texts:
                return "\n".join(texts)
        except Exception:
            return None
        return None

    def _try_ollama(self, prompt: str, context: str) -> Optional[str]:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_SUMMARY_MODEL", "llama3.1")
        payload = {
            "model": model,
            "prompt": f"{prompt}\n\nContext:\n{context}",
            "stream": False,
        }
        try:
            import requests

            resp = requests.post(f"{base_url.rstrip('/')}/api/generate", json=payload, timeout=20)
            if resp.ok:
                data = resp.json()
                text = data.get("response")
                if text:
                    return text.strip()
        except Exception:
            return None
        return None

    def _try_openai(self, prompt: str, context: str) -> Optional[str]:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_SUMMARY_MODEL", "gpt-3.5-turbo")
        if not api_key:
            return None
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            completion = client.responses.create(
                model=model,
                input=[
                    {
                        "role": "system",
                        "content": prompt,
                    },
                    {
                        "role": "user",
                        "content": context,
                    },
                ],
            )
            for output in completion.output or []:
                if hasattr(output, "content"):
                    fragments = []
                    for item in output.content:
                        text = getattr(item, "text", None)
                        if text:
                            fragments.append(text)
                    if fragments:
                        return "\n".join(fragments).strip()
        except Exception:
            return None
        return None

    def _fallback_summary(
        self,
        style: SummaryStyle,
        context_lines: List[str],
        artifact_ids: List[str],
    ) -> str:
        if not context_lines:
            return "No content available for summarization."

        if style == "bullet":
            bullets = [f"• {line}" for line in context_lines[:8]]
            return "\n".join(bullets)

        if style == "executive":
            intro = "This workspace consolidates key findings across uploaded artifacts."
            body = " ".join(context_lines[:5])
            return textwrap.fill(f"{intro} {body}", width=90)

        if style == "action_items":
            items = []
            for idx, line in enumerate(context_lines[:6], start=1):
                items.append(f"{idx}. Review insight: {line} and confirm next steps with stakeholders.")
            if not items:
                items.append("1. Review uploaded materials and extract actionable tasks.")
            return "\n".join(items)

        return "\n".join(context_lines)

    def _persist(self, payload: SummaryPayload) -> None:
        record = {
            "id": payload.id,
            "style": payload.style,
            "provider": payload.provider,
            "prompt": payload.prompt,
            "scope": payload.scope,
            "scope_key": payload.scope_key,
            "artifact_ids": payload.artifact_ids,
            "summary_text": payload.summary_text,
            "evidence_ids": payload.evidence_ids,
            "created_at": payload.created_at,
        }
        self.db.store_summary(record)

    def _inflate(self, payload: SummaryPayload) -> Dict[str, Any]:
        evidence_records: List[Dict[str, Any]] = []
        seen: set[str] = set()
        for evidence_id in payload.evidence_ids:
            if not evidence_id or evidence_id in seen:
                continue
            seen.add(evidence_id)
            detail = self.db.get_evidence(evidence_id)
            if detail:
                evidence_records.append(detail)

        return {
            "id": payload.id,
            "style": payload.style,
            "provider": payload.provider,
            "prompt": payload.prompt,
            "scope": {
                "type": payload.scope,
                "key": payload.scope_key,
                "artifact_ids": payload.artifact_ids,
            },
            "summary": payload.summary_text,
            "citations": evidence_records,
            "created_at": payload.created_at,
        }


__all__ = ["SummarizationService", "PROMPT_TEMPLATES", "SummaryStyle"]
