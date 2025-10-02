import json
from typing import List, Dict, Optional
from pathlib import Path

class Database:
    """Simple in-memory database (replace with SQLite/PostgreSQL in production)"""
    
    def __init__(self):
        self.artifacts = []
        self.facts = []
        self.evidence = []
    
    def add_artifact(self, artifact: Dict) -> str:
        self.artifacts.append(artifact)
        return artifact["id"]
    
    def add_fact(self, fact: Dict):
        self.facts.append(fact)
    
    def add_evidence(self, evidence: Dict):
        self.evidence.append(evidence)
    
    def get_facts(self, report_week: Optional[str] = None) -> List[Dict]:
        if report_week:
            return [f for f in self.facts if f.get("report_week") == report_week]
        return self.facts
    
    def get_evidence(self, evidence_id: str) -> Optional[Dict]:
        return next((e for e in self.evidence if e["id"] == evidence_id), None)
    
    def get_all_evidence(self) -> List[Dict]:
        return self.evidence
    
    def get_artifacts(self) -> List[Dict]:
        return self.artifacts
    
    def reset(self):
        self.artifacts.clear()
        self.facts.clear()
        self.evidence.clear()
