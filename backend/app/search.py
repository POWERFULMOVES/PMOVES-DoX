"""Vector search index for PMOVES-DoX.

Provides semantic search across documents, APIs, logs, and tags using
Ollama embeddings (primary) or SentenceTransformer fallback.
Supports both FAISS-accelerated and numpy-based vector search.

Classes:
    SearchResult: Search result with score, text, and metadata
    SearchIndex: Vector search engine with rebuild and query methods
"""

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

import httpx


Chunk = Dict[str, Any]


@dataclass
class SearchResult:
    """Result from a vector similarity search.

    Attributes:
        score: Similarity score (higher is more similar)
        text: Matching text content
        meta: Metadata including source type, artifact_id, etc.
    """
    score: float
    text: str
    meta: Dict[str, Any]


def _normalize(v: np.ndarray) -> np.ndarray:
    """L2-normalize a vector or matrix of vectors.

    Args:
        v: Input vectors as numpy array.

    Returns:
        Normalized vectors with unit L2 norm.
    """
    norms = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12
    return v / norms


LOGGER = logging.getLogger(__name__)


class SearchIndex:
    """Lightweight vector index across PDFs (markdown), APIs, logs, and tags.

    - Embeddings: Ollama (qwen3-embedding:8b via GPU) or SentenceTransformer fallback
    - Vector store: FAISS (IP) if available, else numpy linear scan fallback

    Environment Variables:
    - OLLAMA_BASE_URL: Ollama service URL (default: http://ollama:11434)
    - OLLAMA_EMBEDDING_MODEL: Model name (default: qwen3-embedding:8b)
    - SEARCH_MODEL: sentence-transformers fallback model (default: all-MiniLM-L6-v2)
    - SEARCH_DEVICE: "cuda", "cpu", or "auto" (for sentence_transformers fallback only)

    Attributes:
        db: Database instance for chunk retrieval
        ollama_base_url: Ollama service URL
        ollama_model: Ollama embedding model name
        faiss_index: FAISS index or numpy array fallback
        ids: List of chunk IDs indexed
        payloads: List of chunk payloads indexed
    """

    def __init__(self, db):
        """Initialize the search index.

        Args:
            db: Database instance for chunk retrieval.
        """
        self.db = db

        # Ollama configuration (primary - GPU-accelerated via Ollama)
        self.ollama_base_url = os.getenv(
            "OLLAMA_BASE_URL",
            "http://ollama:11434"
        )
        self.ollama_model = os.getenv(
            "OLLAMA_EMBEDDING_MODEL",
            "qwen3-embedding:8b"
        )

        # SentenceTransformer configuration (fallback)
        self.st_model_name = os.getenv("SEARCH_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = self._resolve_device()
        self.model: Optional[Any] = None  # SentenceTransformer fallback

        self.faiss_index = None
        self.ids: List[str] = []
        self.payloads: List[Chunk] = []
        self._loaded = False
        self._http_client: Optional[httpx.Client] = None
        self._use_ollama = True  # Flag to track if Ollama is available

    def _resolve_device(self) -> str:
        """Resolve the device for SentenceTransformer embeddings.

        Returns:
            "cuda" if available and requested, "cpu" otherwise.
        """
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
        """Load SentenceTransformer fallback model."""
        if self.model is None and not self._use_ollama:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.st_model_name, device=self.device)

    def _get_http_client(self) -> httpx.Client:
        """Get or create HTTP client for Ollama API calls."""
        if self._http_client is None:
            timeout = httpx.Timeout(300.0, connect=10.0)  # 5 min timeout for embedding generation
            self._http_client = httpx.Client(timeout=timeout)
        return self._http_client

    def _encode_ollama(self, texts: List[str]) -> np.ndarray:
        """Encode texts using Ollama embeddings API.

        Ollama provides an OpenAI-compatible /v1/embeddings endpoint.
        Uses qwen3-embedding:8b model with GPU acceleration.
        """
        client = self._get_http_client()
        embeddings = []

        # Process in batches to avoid payload limits
        batch_size = 32
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            try:
                response = client.post(
                    f"{self.ollama_base_url}/v1/embeddings",
                    json={
                        "model": self.ollama_model,
                        "input": batch
                    },
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                result = response.json()

                # Handle OpenAI-compatible response format
                if "data" in result:
                    data = result["data"]
                    if isinstance(data, list):
                        # Sort by index to ensure correct order
                        data_sorted = sorted(data, key=lambda x: x.get("index", 0))
                        batch_embeddings = [item["embedding"] for item in data_sorted]
                        embeddings.extend(batch_embeddings)
                    else:
                        # Single embedding response
                        embeddings.append(data["embedding"])
                else:
                    LOGGER.warning("Unexpected Ollama response format: %s", result)
                    raise ValueError("Unexpected response format from Ollama")

            except httpx.HTTPStatusError as e:
                LOGGER.error("Ollama HTTP error %s: %s", e.response.status_code, e.response.text)
                # Fall back to SentenceTransformer on HTTP errors
                self._use_ollama = False
                self._load_model()
                return self._encode_sentence_transformers(texts)
            except Exception as e:
                LOGGER.warning("Ollama embedding failed: %s. Falling back to SentenceTransformer.", e)
                self._use_ollama = False
                self._load_model()
                return self._encode_sentence_transformers(texts)

        if not embeddings:
            raise RuntimeError("Failed to get embeddings from Ollama")

        return np.array(embeddings, dtype=np.float32)

    def _encode_sentence_transformers(self, texts: List[str]) -> np.ndarray:
        """Encode texts using SentenceTransformer (fallback when Ollama unavailable)."""
        if self.model is None:
            self._load_model()
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def _encode(self, texts: List[str]) -> np.ndarray:
        """Encode texts using Ollama (primary) or SentenceTransformer (fallback)."""
        if self._use_ollama:
            return self._encode_ollama(texts)
        else:
            return self._encode_sentence_transformers(texts)

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
        """Rebuild the search index from all available content.

        Gathers chunks from PDFs, APIs, logs, and tags, generates embeddings,
        and builds a new FAISS or numpy index.

        Returns:
            Dictionary with items count, backend type, and embedding provider.
        """
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
        emb = self._encode(texts)
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
        return {
            "items": len(chunks),
            "backend": "faiss" if faiss is not None else "numpy",
            "embedding_provider": "ollama" if self._use_ollama else "sentence_transformers"
        }

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
        """Search for similar chunks using vector similarity.

        Args:
            query: Search query text.
            k: Maximum number of results to return.

        Returns:
            List of SearchResult objects sorted by similarity score.
        """
        if not self._loaded:
            self.rebuild()
        if not query.strip() or not self.payloads:
            return []

        self._load_model()
        q = self._encode([query])
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

    def get_embeddings_for_document(self, document_id: str) -> List[List[float]]:
        """Retrieve all embedding vectors for chunks belonging to a document."""
        if not self._loaded:
            self.rebuild()

        vectors: List[List[float]] = []
        for i, ch in enumerate(self.payloads):
            meta = ch.get("meta") or {}
            # Match strict ID or artifact ID
            if meta.get("artifact_id") == document_id or meta.get("document_id") == document_id:
                vec: Optional[np.ndarray] = None
                if faiss is not None and hasattr(self.faiss_index, "reconstruct"):
                    # FAISS reconstruct returns numpy array
                    vec = self.faiss_index.reconstruct(i)
                elif isinstance(self.faiss_index, np.ndarray):
                    vec = self.faiss_index[i]

                if vec is not None:
                    vectors.append(vec.tolist())
        return vectors
