import re
from typing import Dict, List, Any

class QAEngine:
    """Simple Q&A engine with citations"""
    
    def __init__(self, database):
        self.db = database
    
    async def ask(self, question: str) -> Dict[str, Any]:
        """Answer a question with citations"""
        q_lower = question.lower()
        
        # Identify what metric the user is asking about
        metric_patterns = {
            "spend": r"\b(spend|cost|budget)\b",
            "revenue": r"\b(revenue|sales|income)\b",
            "conversions": r"\b(conversion|lead|sale)\b",
            "clicks": r"\b(click)\b",
            "impressions": r"\b(impression|view)\b",
            "ctr": r"\b(ctr|click.?through.?rate)\b",
            "cpa": r"\b(cpa|cost.?per)\b",
            "roas": r"\b(roas|return.?on)\b"
        }
        
        target_metric = None
        for metric, pattern in metric_patterns.items():
            if re.search(pattern, q_lower):
                target_metric = metric
                break
        
        if not target_metric:
            return {
                "answer": "I can help you with metrics like: spend, revenue, conversions, clicks, impressions, CTR, CPA, and ROAS. Please ask about one of these.",
                "evidence": [],
                "metric": None
            }
        
        # Collect values and evidence
        values = []
        evidence_ids = []
        
        for fact in self.db.get_facts():
            if target_metric in fact.get("metrics", {}):
                values.append(fact["metrics"][target_metric])
                evidence_ids.append(fact.get("evidence_id"))
        
        if not values:
            return {
                "answer": f"No data found for {target_metric}.",
                "evidence": [],
                "metric": target_metric
            }
        
        total = sum(values)
        avg = total / len(values) if values else 0
        
        # Get evidence details
        evidence_details = []
        for eid in evidence_ids:
            if eid:
                ev = self.db.get_evidence(eid)
                if ev:
                    evidence_details.append(ev)
        
        answer = f"**{target_metric.upper()}** across {len(values)} source(s):\n"
        answer += f"- Total: {total:,.2f}\n"
        answer += f"- Average: {avg:,.2f}\n"
        
        return {
            "answer": answer,
            "evidence": evidence_details,
            "metric": target_metric,
            "total": total,
            "average": avg,
            "count": len(values)
        }
