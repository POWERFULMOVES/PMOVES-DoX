from typing import List, Dict, Any, Optional
from .config import settings

# Optional OpenAI support
try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

class LLM:
    def __init__(self):
        self.name = settings.model_name
        self._client = None
        if self.name != "mock" and settings.openai_api_key and OpenAI:
            self._client = OpenAI(api_key=settings.openai_api_key)

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
        # Minimal function-calling style prompt
        if self._client:
            res = self._client.chat.completions.create(
                model=self.name,
                messages=messages,
                temperature=0.2,
            )
            return res.choices[0].message.content or ""
        # Fallback mock: deterministic and transparent
        # Looks for keywords to pick a tool hint.
        last = messages[-1]["content"].lower()
        if any(k in last for k in ["search", "find", "doc", "document", "policy", "faq"]):
            return "[TOOL:rags.search] Please use rag.search to retrieve context, then answer."
        if any(k in last for k in ["table", "csv", "xlsx", "summary", "summarize"]):
            return "[TOOL:reports.summarize_table] Try summarizing the table data."
        return "Here's a concise answer based on available context. (Using mock model)"
