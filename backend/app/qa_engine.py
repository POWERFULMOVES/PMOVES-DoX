"""Document-aware Q&A engine with citation retrieval.

Uses FAISS vector search to find relevant evidence, then either:
1. Returns evidence directly with formatted answer (no LLM)
2. Synthesizes answer via TensorZero/Ollama LLM with citations (if available)
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class QAEngine:
    """RAG-based Q&A engine: search → retrieve → answer with citations."""

    def __init__(self, database, search_index=None):
        self.db = database
        self._search_index = search_index
        self._llm_base_url = os.getenv(
            "TENSORZERO_BASE_URL",
            os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
        )
        self._llm_model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        self._use_tensorzero = "tensorzero" in self._llm_base_url.lower()

    def set_search_index(self, index) -> None:
        """Late-bind search index (avoids circular import at init time)."""
        self._search_index = index

    async def ask(self, question: str, top_k: int = 8) -> Dict[str, Any]:
        """Answer a question using document evidence with citations.

        Flow:
        1. Search FAISS index for relevant chunks
        2. If LLM available: synthesize answer with citations
        3. Fallback: return top evidence chunks as the answer
        """
        if not self._search_index:
            return {
                "answer": "Search index not available. Please rebuild the index first.",
                "evidence": [],
                "metric": None,
            }

        # Step 1: Retrieve evidence from vector search
        hits = self._search_index.search(question, k=top_k)
        if not hits:
            return {
                "answer": f"No relevant documents found for: \"{question}\". Try uploading documents first.",
                "evidence": [],
                "metric": None,
            }

        # Build context from search results (SearchResult objects or dicts)
        evidence = []
        context_chunks = []
        for hit in hits:
            # Support both SearchResult dataclass and dict formats
            if hasattr(hit, "text"):
                text = hit.text
                meta = hit.meta if hasattr(hit, "meta") else {}
                score = hit.score if hasattr(hit, "score") else 0
            else:
                text = hit.get("text", "")
                meta = hit.get("meta", {})
                score = hit.get("score", 0)

            if isinstance(meta, dict):
                filename = meta.get("filename", "unknown")
                chunk = meta.get("chunk")
                artifact_id = meta.get("artifact_id")
                deeplink = meta.get("deeplink")
            else:
                filename = getattr(meta, "filename", "unknown")
                chunk = getattr(meta, "chunk", None)
                artifact_id = getattr(meta, "artifact_id", None)
                deeplink = getattr(meta, "deeplink", None)

            evidence.append({
                "text": text,
                "score": round(score, 4),
                "filename": filename,
                "chunk": chunk,
                "artifact_id": artifact_id,
                "deeplink": deeplink,
            })
            context_chunks.append(f"[{filename}] {text}")

        # Step 2: Try LLM synthesis
        llm_answer = self._try_llm_answer(question, context_chunks)

        if llm_answer:
            answer = llm_answer
        else:
            # Step 3: Fallback — format evidence as the answer
            answer = f"Found {len(evidence)} relevant passages for \"{question}\":\n\n"
            for i, ev in enumerate(evidence[:5], 1):
                answer += f"**{i}. [{ev['filename']}]** (relevance: {ev['score']:.0%})\n"
                answer += f"> {ev['text'][:300]}\n\n"

        return {
            "answer": answer,
            "evidence": evidence,
            "metric": None,
        }

    def _try_llm_answer(self, question: str, context_chunks: List[str]) -> Optional[str]:
        """Try to synthesize an answer using TensorZero or Ollama."""
        if not context_chunks:
            return None

        context = "\n\n".join(context_chunks[:6])  # Limit context window
        prompt = (
            "Answer the question based ONLY on the context below. "
            "Cite the source document in square brackets. "
            "If the context doesn't contain enough information, say so.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer:"
        )

        try:
            if self._use_tensorzero:
                return self._call_tensorzero(prompt)
            else:
                return self._call_ollama(prompt)
        except Exception as e:
            logger.warning("LLM synthesis failed: %s", e)
            return None

    def _call_tensorzero(self, prompt: str) -> Optional[str]:
        """Call TensorZero OpenAI-compatible endpoint."""
        url = f"{self._llm_base_url.rstrip('/')}/openai/v1/chat/completions"
        payload = {
            "model": self._llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3,
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.ok:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
        return None

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama generate endpoint."""
        url = f"{self._llm_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self._llm_model,
            "prompt": prompt,
            "stream": False,
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.ok:
            return resp.json().get("response", "").strip()
        return None
