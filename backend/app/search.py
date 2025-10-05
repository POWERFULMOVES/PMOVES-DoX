from __future__ import annotations

import os
import json
import uuid
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
from pathlib import Path

import numpy as np

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None  # type: ignore

from sentence_transformers import SentenceTransformer


Chunk = Dict[str, Any]


def _normalize(v: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms


@dataclass
class SearchResult:
    score: float
    text: str
    meta: Dict[str, Any]


LOGGER = logging.getLogger(__name__)


class SearchIndex:
    """Lightweight vector index across PDFs (markdown), APIs, logs, and tags.

    - Embeddings: sentence-transformers (config: SEARCH_MODEL or default all-MiniLM-L6-v2)
    - Vector store: FAISS (IP) if available, else numpy linear scan fallback
    """

    def __init__(self, db):
        self.db = db
        self.model_name = os.getenv("SEARCH_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = self._resolve_device()
        self.model: Optional[SentenceTransformer] = None
        self.faiss_index = None
        self.ids: List[str] = []
        self.payloads: List[Chunk] = []
        self._loaded = False

    def _resolve_device(self) -> str:
        requested = os.getenv("SEARCH_DEVICE")
        if requested:
            return requested
        try:
            import torch  # type: ignore
            if hasattr(torch, "cuda") and torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _load_model(self):
        if self.model is None:
            self.model = SentenceTransformer(self.model_name, device=self.device)

    def _gather_chunks(self) -> List[Chunk]:
        chunks: List[Chunk] = []

        # PDFs → artifacts markdown
        artifacts = self.db.get_artifacts()
        for a in artifacts:
            fp = Path(a.get("filepath", ""))
            if fp.suffix.lower() != ".pdf":
                continue
            # Prefer text units with page map if available
            tu = Path("artifacts") / f"{fp.stem}.text_units.json"
            if tu.exists():
                try:
                    units = json.loads(tu.read_text(encoding="utf-8", errors="ignore"))
                    if isinstance(units, list):
                        for i, u in enumerate(units):
                            txt = (u.get("text") or "").strip()
                            if not txt:
                                continue
                            page = u.get("page")
                            chunks.append({
                                "id": f"md:{a.get('id')}:{i}",
                                "text": txt[:2000],
                                "meta": {
                                    "type": "pdf",
                                    "artifact_id": a.get("id"),
                                    "filename": a.get("filename"),
                                    "chunk": i,
                                    **({"page": int(page)} if isinstance(page, (int, float)) else {}),
                                }
                            })
                        continue
                except Exception:
                    pass
            md = Path("artifacts") / f"{fp.stem}.md"
            if not md.exists():
                continue
            text = md.read_text(encoding="utf-8", errors="ignore")
            # Simple chunking by headers or paragraphs (fallback)
            parts = [p.strip() for p in text.split("\n\n") if p.strip()]
            for i, p in enumerate(parts):
                chunks.append({
                    "id": f"md:{a.get('id')}:{i}",
                    "text": p[:2000],
                    "meta": {
                        "type": "pdf",
                        "artifact_id": a.get("id"),
                        "filename": a.get("filename"),
                        "chunk": i,
                    }
                })

        # APIs
        for api in self.db.list_apis(tag=None, method=None, path_like=None):
            txt = " ".join([
                api.get("method") or "",
                api.get("path") or "",
                api.get("summary") or "",
                ", ".join(api.get("tags") or [])
            ]).strip()
            if not txt:
                continue
            chunks.append({
                "id": f"api:{api.get('id')}",
                "text": txt[:2000],
                "meta": {"type": "api", **api}
            })

        # Logs
        for log in self.db.list_logs(level=None, code=None, q=None, ts_from=None, ts_to=None):
            msg = (log.get("message") or "").strip()
            if not msg:
                continue
            chunks.append({
                "id": f"log:{log.get('id')}",
                "text": msg[:2000],
                "meta": {"type": "log", **{k: log.get(k) for k in ("level","code","component","ts","document_id")}},
            })

        # Tags
        for t in self.db.list_tags(document_id=None, q=None):
            tag = (t.get("tag") or "").strip()
            if not tag:
                continue
            chunks.append({
                "id": f"tag:{t.get('id')}",
                "text": tag,
                "meta": {"type": "tag", **t}
            })

        return chunks

    def rebuild(self) -> Dict[str, Any]:
        self._load_model()
        chunks = self._gather_chunks()
        if not chunks:
            # reset
            self.faiss_index = None
            self.ids = []
            self.payloads = []
            self._loaded = True
            return {"items": 0}

        texts = [c["text"] for c in chunks]
        emb = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        emb = _normalize(emb.astype("float32"))

        self.ids = [c["id"] for c in chunks]
        self.payloads = chunks

        if faiss is not None:
            dim = emb.shape[1]
            index = faiss.IndexFlatIP(dim)
            index.add(emb)
            self.faiss_index = index
        else:
            # fallback uses numpy arrays
            self.faiss_index = emb

        self._sync_remote_embeddings(chunks, emb)

        self._loaded = True
        return {"items": len(chunks), "backend": "faiss" if faiss is not None else "numpy"}

    def _sync_remote_embeddings(self, chunks: List[Chunk], embeddings: np.ndarray) -> None:
        store = getattr(self.db, "store_search_chunks", None)
        if not callable(store):
            return
        reset = getattr(self.db, "reset_search_chunks", None)
        try:
            if callable(reset):
                reset()
            vectors = embeddings.tolist()
            records: List[Dict[str, Any]] = []
            for chunk, vector in zip(chunks, vectors):
                meta = chunk.get("meta") or {}
                records.append(
                    {
                        "id": chunk.get("id"),
                        "document_id": meta.get("artifact_id") or meta.get("document_id"),
                        "source_type": meta.get("type"),
                        "chunk_index": meta.get("chunk"),
                        "text": chunk.get("text"),
                        "meta": meta,
                        "embedding": vector,
                    }
                )
            store(records)
        except Exception as exc:  # pragma: no cover - remote sync should not break local search
            LOGGER.warning("Failed to sync search embeddings to remote store: %s", exc)

    def search(self, query: str, k: int = 10) -> List[SearchResult]:
        if not self._loaded:
            self.rebuild()
        if not query.strip() or not self.payloads:
            return []

        self._load_model()
        q = self.model.encode([query], convert_to_numpy=True)
        q = _normalize(q.astype("float32"))

        if faiss is not None and isinstance(self.faiss_index, faiss.Index):  # type: ignore
            D, I = self.faiss_index.search(q, min(k, len(self.payloads)))
            scores = D[0]
            idxs = I[0]
        else:
            # cosine similarity via dot product with normalized embeddings
            emb = self.faiss_index  # type: ignore
            sims = (emb @ q.T).ravel()
            idxs = np.argsort(-sims)[: min(k, len(sims))]
            scores = sims[idxs]

        out: List[SearchResult] = []
        for score, idx in zip(scores.tolist(), idxs.tolist()):
            if idx < 0 or idx >= len(self.payloads):
                continue
            ch = self.payloads[idx]
            out.append(SearchResult(score=float(score), text=ch["text"], meta=ch["meta"]))
        return out
