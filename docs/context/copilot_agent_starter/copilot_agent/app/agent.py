from typing import Dict, Any, List
from .model_adapter import LLM
from .tools import rag, reports

class Agent:
    def __init__(self):
        self.llm = LLM()

    def chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        # Ask LLM (or mock) for a suggestion
        hint = self.llm.chat(messages, tools=[
            {"name": "rag.search"}, {"name": "reports.summarize_table"}
        ])

        steps = []
        last = messages[-1]["content"]

        # Tool routing (very simple / transparent)
        if "[TOOL:rags.search]" in hint or "[TOOL:rag.search]" in hint or "rag.search" in hint.lower() or "search" in last.lower():
            res = rag.ask(last)
            steps.append({"tool": "rag.search", "result": res})
            return {"answer": res["answer"], "steps": steps}

        if "reports.summarize_table" in hint.lower():
            # Expect user pasted CSV in the last message
            res = reports.summarize_table(last)
            steps.append({"tool": "reports.summarize_table", "result": res[:500]})
            return {"answer": res, "steps": steps}

        # Default: return model text
        return {"answer": hint, "steps": steps}
