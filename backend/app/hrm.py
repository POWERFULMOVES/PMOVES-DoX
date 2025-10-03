from __future__ import annotations

import time
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class HRMConfig:
    Mmax: int = 6
    Mmin: int = 2
    threshold: float = 0.5


class HRMMetrics:
    def __init__(self) -> None:
        self.total_runs = 0
        self.total_steps = 0
        self.total_latency_ms = 0.0
        self.last: Dict = {}
        self.log_path = Path(os.getenv("HRM_METRICS_LOG", "artifacts/metrics/hrm.log"))
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def record(self, steps: int, latency_ms: float, payload: Dict) -> None:
        self.total_runs += 1
        self.total_steps += steps
        self.total_latency_ms += latency_ms
        self.last = {
            "steps": steps,
            "latency_ms": round(latency_ms, 3),
            "payload": payload,
        }
        # append JSON line to metrics log (best-effort)
        try:
            import json as _json
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(_json.dumps({
                    "ts": __import__("datetime").datetime.utcnow().isoformat() + "Z",
                    "steps": steps,
                    "latency_ms": round(latency_ms, 3),
                    "payload": payload,
                }) + "\n")
        except Exception:
            pass

    def snapshot(self) -> Dict:
        avg_steps = (self.total_steps / self.total_runs) if self.total_runs else 0.0
        avg_latency = (self.total_latency_ms / self.total_runs) if self.total_runs else 0.0
        return {
            "total_runs": self.total_runs,
            "avg_steps": round(avg_steps, 3),
            "avg_latency_ms": round(avg_latency, 3),
            "last": self.last,
        }


def bubble_pass(s: str) -> str:
    """One refinement step over a string of digits: single bubble-sort pass."""
    arr = list(s)
    for i in range(len(arr) - 1):
        if arr[i] > arr[i + 1]:
            arr[i], arr[i + 1] = arr[i + 1], arr[i]
    return "".join(arr)


def is_sorted(s: str) -> bool:
    return all(s[i] <= s[i + 1] for i in range(len(s) - 1))


def refine_sort_digits(seq: str, cfg: HRMConfig) -> Tuple[str, int, List[str]]:
    """Iteratively refine a digit string until sorted or Mmax reached.

    Returns (result, steps_taken, trace)
    """
    x = seq
    trace: List[str] = [x]
    steps = 0
    for m in range(1, cfg.Mmax + 1):
        x2 = bubble_pass(x)
        steps = m
        trace.append(x2)
        # allow halting only after Mmin
        if m >= cfg.Mmin and is_sorted(x2):
            x = x2
            break
        x = x2
    return x, steps, trace
