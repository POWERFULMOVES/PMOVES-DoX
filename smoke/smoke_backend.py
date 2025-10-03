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

    # 10) export POML and download
    try:
      docs = r.get(f"{API}/documents", timeout=10)
      docs.raise_for_status()
      docs_list = docs.json().get("documents", [])
      if not docs_list:
          fail("no documents to export poml")
      did = docs_list[0]["id"]
      e = r.post(f"{API}/export/poml", json={"document_id": did, "variant": "catalog"}, timeout=30)
      e.raise_for_status()
      rel = e.json().get("rel")
      if not rel:
          fail("poml export missing rel")
      d = r.get(f"{API}/download", params={"rel": rel}, timeout=30)
      d.raise_for_status()
      text = d.text
      if "<poml" not in text or "<output-schema" not in text:
          fail("downloaded POML missing core tags")
      ok("/export/poml and download")
    except Exception as e:
      fail(f"export/poml error: {e}")

    # 11) search rebuild + query
    try:
        sr = r.post(f"{API}/search/rebuild", timeout=30)
        sr.raise_for_status()
        sq = r.post(f"{API}/search", json={"q": "loan", "k": 5}, timeout=10)
        sq.raise_for_status()
        ok("/search rebuild + query")
    except Exception as e:
        fail(f"search error: {e}")

    # 12) logs export CSV
    try:
        le = r.get(f"{API}/logs/export?level=ERROR", timeout=10)
        le.raise_for_status()
        if not le.text.startswith("ts,level,code,component,message"):
            fail("logs/export missing header")
        ok("/logs/export")
    except Exception as e:
        fail(f"logs/export error: {e}")

    # 13) API detail modal endpoint
    try:
        apis = r.get(f"{API}/apis", timeout=10)
        apis.raise_for_status()
        items = apis.json().get("apis", [])
        if items:
            aid = items[0]["id"]
            ad = r.get(f"{API}/apis/{aid}", timeout=10)
            ad.raise_for_status()
        ok("/apis/{id} detail")
    except Exception as e:
        fail(f"api detail error: {e}")

    # 14) Tag presets + dry-run
    try:
        presets = r.get(f"{API}/tags/presets", timeout=10)
        presets.raise_for_status()
        docs = r.get(f"{API}/documents", timeout=10)
        docs.raise_for_status()
        docs_list = docs.json().get("documents", [])
        if docs_list:
            did = docs_list[0]["id"]
            dr = r.post(f"{API}/extract/tags", json={"document_id": did, "dry_run": True, "use_hrm": True}, timeout=60)
            dr.raise_for_status()
            # persist once to test stored hrm metadata
            pr = r.post(f"{API}/extract/tags", json={"document_id": did, "use_hrm": True}, timeout=60)
            pr.raise_for_status()
            tg = r.get(f"{API}/tags?document_id={did}", timeout=10)
            tg.raise_for_status()
            tlist = tg.json().get("tags", [])
            _ = tlist  # no strict assertion; presence is enough
        ok("/tags presets + dry-run extract")
    except Exception as e:
        fail(f"tags/presets or extract error: {e}")

    # 15) HRM experiments and metrics
    try:
        e1 = r.post(f"{API}/experiments/hrm/echo", json={"text":"  a   b  c  "}, timeout=10)
        e1.raise_for_status()
        s1 = r.post(f"{API}/experiments/hrm/sort_digits", json={"seq":"93241"}, timeout=10)
        s1.raise_for_status()
        m1 = r.get(f"{API}/metrics/hrm", timeout=10)
        m1.raise_for_status()
        ok("/experiments/hrm/* + /metrics/hrm")
        # Optional /ask with HRM flag (may be a no-op if HRM not enabled)
        a1 = r.post(f"{API}/ask", params={"question": "what is the total revenue?", "use_hrm": "true"}, timeout=10)
        a1.raise_for_status()
    except Exception as e:
        fail(f"hrm endpoints error: {e}")

    ok("Smoke tests passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
