from __future__ import annotations
import os, re, json, hashlib
from typing import List, Tuple
import numpy as np
import faiss  # type: ignore
from sentence_transformers import SentenceTransformer

# Base directory under which all ingestion paths must reside.
# Defaults to the current working directory but can be overridden
# via the INGEST_ROOT environment variable.
INGEST_ROOT = os.path.abspath(os.getenv("INGEST_ROOT", "."))


def _resolve_ingest_path(user_path: str) -> str:
    """
    Resolve a user-supplied path to a safe absolute path under INGEST_ROOT.

    Raises a ValueError if the resolved path would escape INGEST_ROOT.
    """
    if not user_path:
        raise ValueError("Path must not be empty.")

    # Treat the user path as relative to INGEST_ROOT to avoid trusting
    # arbitrary absolute paths provided by the client.
    combined = os.path.join(INGEST_ROOT, user_path)
    resolved = os.path.abspath(combined)

    # Ensure the resolved path is within INGEST_ROOT.
    root = os.path.commonpath([INGEST_ROOT])
    target = os.path.commonpath([INGEST_ROOT, resolved])
    if root != target:
        raise ValueError("Requested path is outside of the allowed ingestion root.")

    return resolved


class RAGIndex:
    def __init__(self, dim: int = 384, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.index = faiss.IndexFlatIP(dim)
        self.chunks: List[str] = []
        self.meta: List[dict] = []

    def _embed(self, texts: List[str]) -> np.ndarray:
        emb = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return emb.astype("float32")

    def add(self, chunks: List[str], metas: List[dict]):
        if not chunks:
            return
        emb = self._embed(chunks)
        self.index.add(emb)
        self.chunks.extend(chunks)
        self.meta.extend(metas)

    def search(self, query: str, k: int = 5) -> List[Tuple[str, dict, float]]:
        q = self._embed([query])
        D, I = self.index.search(q, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx == -1: 
                continue
            results.append((self.chunks[idx], self.meta[idx], float(score)))
        return results

def simple_split(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i+chunk_size])
        i += (chunk_size - overlap)
    return chunks

def load_folder(path: str) -> List[tuple[str, dict]]:
    supported = (".txt", ".md", ".csv", ".json")
    rows = []
    for root, _, files in os.walk(path):
        for f in files:
            if f.lower().endswith(supported):
                fp = os.path.join(root, f)
                try:
                    txt = open(fp, "r", encoding="utf-8", errors="ignore").read()
                except Exception:
                    continue
                for ch in simple_split(txt):
                    rows.append((ch, {"file": fp}))
    return rows

GLOBAL_INDEX = None

def ingest_path(path: str):
    global GLOBAL_INDEX
    # Normalize and validate the user-supplied path to ensure it stays
    # within the configured INGEST_ROOT directory.
    safe_path = _resolve_ingest_path(path)
    chunks = load_folder(safe_path)
    if not chunks:
        GLOBAL_INDEX = None
        return 0
    rag = RAGIndex()
    rag.add([c for c, _ in chunks], [m for _, m in chunks])
    GLOBAL_INDEX = rag
    return len(chunks)

def ask(query: str, k: int = 5):
    if GLOBAL_INDEX is None:
        return {"answer": "No index loaded. Please POST /ingest first.", "contexts": []}
    hits = GLOBAL_INDEX.search(query, k=k)
    ctx = [{"text": t, "meta": m, "score": s} for t, m, s in hits]
    # Minimal "answer" without an LLM
    snippet = " ".join([c["text"][:200] for c in ctx])[:800]
    return {"answer": snippet if snippet else "No relevant context found.", "contexts": ctx}
