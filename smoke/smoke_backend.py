import os
import sys
import time
import json
from pathlib import Path

import requests as r


API = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"[ OK ] {msg}")


def main():
    # 1) health
    try:
        h = r.get(f"{API}/health", timeout=10)
        h.raise_for_status()
        ok("/health")
    except Exception as e:
        fail(f"/health error: {e}")

    # 2) upload sample.csv
    sample = ROOT / "samples" / "sample.csv"
    if not sample.exists():
        fail(f"Sample file missing: {sample}")
    files = [("files", (sample.name, open(sample, "rb"), "text/csv"))]
    try:
        u = r.post(f"{API}/upload", files=files, timeout=60)
        u.raise_for_status()
        res = u.json()
        items = res.get("results", [])
        if not items:
            fail("upload returned no results")
        ok("/upload sample.csv")
    except Exception as e:
        fail(f"/upload error: {e}")

    # Grab artifact id from last upload by listing artifacts
    try:
        a = r.get(f"{API}/artifacts", timeout=10)
        a.raise_for_status()
        arts = a.json().get("artifacts", [])
        if not arts:
            fail("no artifacts returned")
        artifact_id = arts[-1]["id"]
        ok(f"/artifacts -> {artifact_id}")
    except Exception as e:
        fail(f"/artifacts error: {e}")

    # 3) facts
    try:
        f0 = r.get(f"{API}/facts", timeout=10)
        f0.raise_for_status()
        facts = f0.json().get("facts", [])
        if len(facts) == 0:
            fail("no facts after upload")
        ok(f"/facts -> {len(facts)} fact(s)")
    except Exception as e:
        fail(f"/facts error: {e}")

    # 4) structure/chr
    try:
        payload = {"artifact_id": artifact_id, "K": 6, "units_mode": "sentences"}
        s = r.post(f"{API}/structure/chr", json=payload, timeout=60)
        s.raise_for_status()
        body = s.json()
        rel_csv = body.get("artifacts", {}).get("rel_csv")
        if not rel_csv:
            fail("CHR missing rel_csv")
        ok("/structure/chr")
        # download
        d = r.get(f"{API}/download", params={"rel": rel_csv}, timeout=30)
        d.raise_for_status()
        if len(d.content) == 0:
            fail("downloaded CHR CSV empty")
    ok("/download CHR CSV")
    except Exception as e:
        fail(f"/structure/chr error: {e}")

    # 5) convert -> txt and download
    try:
        c = r.post(f"{API}/convert", json={"artifact_id": artifact_id, "format": "txt"}, timeout=60)
        c.raise_for_status()
        rel = c.json().get("rel")
        if not rel:
            fail("convert missing rel path")
        d = r.get(f"{API}/download", params={"rel": rel}, timeout=30)
        d.raise_for_status()
        ok("/convert to txt and download")
    except Exception as e:
        fail(f"/convert error: {e}")

    # 6) convert -> docx and download
    try:
        c2 = r.post(f"{API}/convert", json={"artifact_id": artifact_id, "format": "docx"}, timeout=120)
        c2.raise_for_status()
        rel2 = c2.json().get("rel")
        if not rel2:
            fail("convert docx missing rel path")
        d2 = r.get(f"{API}/download", params={"rel": rel2}, timeout=30)
        d2.raise_for_status()
        if len(d2.content) < 100:
            fail("downloaded DOCX seems too small")
        ok("/convert to docx and download")
    except Exception as e:
        fail(f"/convert docx error: {e}")

    # 7) datavzrd config
    try:
        v = r.post(f"{API}/viz/datavzrd", json={"artifact_id": artifact_id}, timeout=30)
        v.raise_for_status()
        ok("/viz/datavzrd")
    except Exception as e:
        fail(f"/viz/datavzrd error: {e}")

    # 8) ingest xml/openapi/postman
    try:
      with open(ROOT/"samples"/"sample.xml", "rb") as f:
        ix = r.post(f"{API}/ingest/xml", files={"file": ("sample.xml", f, "text/xml")}, timeout=30)
      ix.raise_for_status()
      with open(ROOT/"samples"/"sample_openapi.json", "rb") as f:
        ioa = r.post(f"{API}/ingest/openapi", files={"file": ("sample_openapi.json", f, "application/json")}, timeout=30)
      ioa.raise_for_status()
      with open(ROOT/"samples"/"sample_postman.json", "rb") as f:
        ipm = r.post(f"{API}/ingest/postman", files={"file": ("sample_postman.json", f, "application/json")}, timeout=30)
      ipm.raise_for_status()
      # query logs/apis
      ql = r.get(f"{API}/logs?level=ERROR", timeout=10); ql.raise_for_status()
      qa = r.get(f"{API}/apis?method=GET", timeout=10); qa.raise_for_status()
      ok("ingest xml/openapi/postman and query logs/apis")
    except Exception as e:
      fail(f"ingest/query error: {e}")

    # 9) datavzrd logs viz
    try:
      v2 = r.post(f"{API}/viz/datavzrd/logs", json={}, timeout=30)
      v2.raise_for_status()
      ok("/viz/datavzrd/logs")
    except Exception as e:
      fail(f"/viz/datavzrd/logs error: {e}")

    ok("Smoke tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
