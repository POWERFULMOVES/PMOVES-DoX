"""Pattern-based extraction of business metrics with context."""

from __future__ import annotations

import re
from typing import Dict, List


class BusinessMetricExtractor:
    """Extract simple financial and growth metrics from raw text."""

    def __init__(self) -> None:
        self.patterns: Dict[str, List[str]] = {
            "revenue": [
                r"revenue[:\s]+\$?\s*([0-9,.]+[KMB]?)",
                r"sales[:\s]+\$?\s*([0-9,.]+[KMB]?)",
                r"\$([0-9,.]+[KMB]?)\s+in\s+revenue",
                r"revenue\s+(?:reached|totaled)\s+\$?\s*([0-9,.]+[KMB]?)",
            ],
            "growth": [
                r"growth[:\s]+([0-9.]+)%",
                r"increase[d]?\s+by\s+([0-9.]+)%",
                r"([0-9.]+)%\s+growth",
            ],
            "margin": [
                r"margin[:\s]+([0-9.]+)%",
                r"([0-9.]+)%\s+margin",
            ],
            "profit": [
                r"profit[:\s]+\$?\s*([0-9,.]+[KMB]?)",
                r"net\s+income[:\s]+\$?\s*([0-9,.]+[KMB]?)",
            ],
        }

    def extract_metrics(self, text: str, context_window: int = 50) -> List[Dict]:
        """Extract matching metric spans with a slice of surrounding context."""

        metrics: List[Dict] = []
        haystack = text or ""
        for metric_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, haystack, re.IGNORECASE):
                    start = max(0, match.start() - context_window)
                    end = min(len(haystack), match.end() + context_window)
                    metrics.append(
                        {
                            "type": metric_type,
                            "value": match.group(1),
                            "context": haystack[start:end],
                            "position": match.start(),
                        }
                    )
        return metrics


__all__ = ["BusinessMetricExtractor"]
