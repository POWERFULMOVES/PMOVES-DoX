import base64
import io
import json
import os
import sys
import time
import wave
import zlib
from pathlib import Path

import requests as r


API = os.getenv("API_BASE", "http://localhost:8484").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]


# Tiny inline fixtures keep the repository free of binary blobs while still
# exercising the multimodal ingestion paths end-to-end.
SAMPLE_IMAGE_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/xcAAoMBgVbA3qoAAAAASUVORK5CYII="

SAMPLE_VIDEO_MP4_Z_B64 = (
    "eNrt08tLlAscxvF3TC3t4pTmZJkz3tLUzLvjzDsvJBoeFyYHOYcgykIOuDhpVHgQNFOQIxFpGzcSFkEb"
    "F+ZiEBLhnbu38daYpaljlpe0tIuWmp75P86X3+ZZ/HgWD3x+/+38+ahNQfjz3B+5f/19S6MUBEHhuRrJ"
    "E6oEwUtQCiVXb10VPD+C0O0ff3QjbCym/mxfeoWuxFAtvTCE6y0ZtqSi0880ClXbgXVFykb7smm247Vt"
    "WN+XbfMyP5R35RxLocPXqXW1v02cL10L2p7wLTt850RX1GzC89R1bYNYIGmlPPG+NiI1OWE1suV4ldLt"
    "E7J1ezXvw/Rk7cvygRn7ttktt8p681Obpe/GSOWbx+9aV+J/rHk9ObikqgpXxl1LFjPL9TOGf6RUQ6gu"
    "P92dGBgTGiYF2fx8dvO/LS4mzZS+Gh809qRYy0w1cpkpxWrsGR8sfZU0s7iY/81n1+YnBYWGBca4E/PT"
    "Q3Wpnp4ZQ7lezLyWrIyrCl9SPTm45hX/o3Xl8bvKNzdGLH1PbXpzq+yWt80z9vKB2pfTk3kfbq+GbLl9"
    "qpQtx1cjkxMiUu9r80StVCA1iOva56mzCV1Rd06UHZ7wDdouXUucb3+rdfk6Cx05ll35oexlzrbp+2zD"
    "Ha9Ns+3LKRvrirYDCtUzTdFpW5IlI1z/wrN1iaFC15def3YsZiMs/mi3vyBkf3ct+bnjxiuH0nsbrC2m"
    "WjnXNG0Re3SDbWMXp3cXir767zj3FQZKJwtO6RKtad1ZO+J1SSF16dszN5MdcYURI8eaDy3vif7Z9Onu"
    "XM5E2OiFfn97hblDdsid5pv2qf7BUeVkyfu6z+rNee97AZ0h4ZHV8Y0pGq23qJaKJat4KUtMe3CmPvpK"
    "aPER196AX5e/BC/UTa26HjktjkaLxvSvPGCasxp71cMr43Nu00fd+pZg3K8KHlI3x8Ym5Wc4dU2GGqnJ"
    "4NTlZ8QmNccOqVXBxv1bgm7d9HHOvTKuHjb2zlkHPD0aU6PF4njkXHXVTQUvXP4S8Mu1t/jIldD66Adn"
    "xLRLWVaxWFJL3qJG25hSHR8e2RlyL2DeW71Z97nkvXJycHSq/6a90+yQO+QKs7/9Qn/YaM7E3bmmT9E/"
    "l/c0Hxo5VhjhiNtMbs/s0iuk69KO2J1lTdMlFpySThYGOvf57xR93V24ON02phsUe6YtuZ6tW0wN1vTe"
    "yqG4cT+3ayn7Oz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAHPvCBD3zg"
    "Ax/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAH"
    "PvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ98"
    "4AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jA"
    "Bz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEP"
    "fOADH/jABz7wgQ984AMf+MAHPvCBD3zgAx/4wAc+8IEPfOADH/jABz7wgQ98/F99/Adk0THn"
)


def _sample_audio_wav() -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x00" * 800)
    return buf.getvalue()


def _sample_video_mp4() -> bytes:
    return zlib.decompress(base64.b64decode(SAMPLE_VIDEO_MP4_Z_B64))


def _sample_image_png() -> bytes:
    return base64.b64decode(SAMPLE_IMAGE_PNG_B64)


def fail(msg: str):
    print(f"[FAIL] {msg}")
    sys.exit(1)


def ok(msg: str):
    print(f"[ OK ] {msg}")


def main():
    # 1) health
    try:
        h = r.get(f"{API}/healthz", timeout=10)
        h.raise_for_status()
        ok("/healthz")
    except Exception as e:
        fail(f"/healthz error: {e}")

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
        for field in ("table_evidence", "chart_evidence", "formula_evidence"):
            if field not in arts[-1]:
                fail(f"artifact summary missing {field}")
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

    # Summaries (workspace + artifact)
    try:
        for style in ("bullet", "executive", "action_items"):
            payload = {"style": style, "scope": "workspace"}
            resp = r.post(f"{API}/summaries/generate", json=payload, timeout=20)
            resp.raise_for_status()
            body = resp.json()
            if body.get("style") != style or not body.get("summary"):
                fail(f"workspace summary missing fields for style {style}")
        ok("/summaries/generate workspace styles")
    except Exception as e:
        fail(f"workspace summaries error: {e}")

    try:
        payload = {"style": "bullet", "scope": "artifact", "artifact_ids": [artifact_id]}
        resp = r.post(f"{API}/summaries/generate", json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data.get("scope", {}).get("artifact_ids"), list):
            fail("artifact summary missing scope artifact_ids")
        hist = r.get(f"{API}/summaries", params={"scope": "artifact", "style": "bullet"}, timeout=10)
        hist.raise_for_status()
        history = hist.json().get("summaries", [])
        if not isinstance(history, list) or len(history) == 0:
            fail("artifact summary history empty")
        ok("/summaries artifact generate + list")
    except Exception as e:
        fail(f"artifact summaries error: {e}")

    # 3b) upload a tiny PDF (for /open/pdf and PDF paths) and run CHR(sentences)
    #    Create a minimal valid PDF from base64 inline to avoid extra deps
    try:
        import base64
        pdf_b64 = (
            b"JVBERi0xLjQKJcTl8uXrp/Og0MTGCjEgMCBvYmoKPDwvVHlwZS9DYXRhbG9nIC9QYWdlcyAyIDAgUj4+IGVuZG9iago"
            b"yIDAgb2JqCjw8IC9UeXBlIC9QYWdlcyAvS2lkcyBbMyAwIFJdIC9Db3VudCAxID4+IGVuZG9iagozIDAgb2JqCjw8IC9U"
            b"eXBlIC9QYWdlIC9QYXJlbnQgMiAwIFIgL01lZGlhQm94IFswIDAgMjAwIDIwMF0gL0NvbnRlbnRzIDQgMCBSIC9SZXNvdXJj"
            b"ZXMgPDwgL0ZvbnQgPDwgL0YxIDUgMCBSID4+ID4+ID4+IGVuZG9iago0IDAgb2JqCjw8IC9MZW5ndGggNDQgPj4gc3RyZWFtCkJUIC9GMQogMjQgVGYgNzIgMTIwIFRkIChIZWxsbyBQREYpIFRqIEVUCmVuZHN0cmVhbQplbmRvYmoKNSAwIG9iago8PCAvVHlwZSAvRm9udCAvU3VidHlwZSAvVHlwZTEgL05hbWUgL0YxIC9CYXNlRm9udCAvSGVsdmV0aWNhID4+IGVuZG9iagp4cmVmCjAgNgowMDAwMDAwMDAwIDY1NTM1IGYgCjAwMDAwMDAwMTAgMDAwMDAgbiAKMDAwMDAwMDA2MiAwMDAwMCBuIAowMDAwMDAwMTE4IDAwMDAwIG4gCjAwMDAwMDAyNzAgMDAwMDAgbiAKMDAwMDAwMDM3MyAwMDAwMCBuIAp0cmFpbGVyCjw8IC9TaXplIDYgL1Jvb3QgMSAwIFIgPj4Kc3RhcnR4cmVmCjQ3MAolJUVPRgo="
        )
        pdf_bytes = base64.b64decode(pdf_b64)
        files_pdf = [("files", ("smoke.pdf", pdf_bytes, "application/pdf"))]
        u2 = r.post(f"{API}/upload?async_pdf=false", files=files_pdf, timeout=60)
        u2.raise_for_status()
        ok("/upload smoke.pdf (sync)")
    except Exception as e:
        fail(f"/upload pdf error: {e}")

    # Fetch latest artifacts again
    try:
        a2 = r.get(f"{API}/artifacts", timeout=10)
        a2.raise_for_status()
        arts2 = a2.json().get("artifacts", [])
        pdf_artifact_id = None
        for item in reversed(arts2):
            if str(item.get("filetype","")) == ".pdf":
                pdf_artifact_id = item["id"]
                break
        if not pdf_artifact_id:
            fail("no PDF artifact found after upload")
        ok(f"PDF artifact -> {pdf_artifact_id}")
    except Exception as e:
        fail(f"/artifacts after pdf error: {e}")

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

    # 4b) CHR on PDF (sentences) and verify JSON rows present; page mapping is optional
    try:
        payload_pdf = {"artifact_id": pdf_artifact_id, "K": 4, "units_mode": "sentences"}
        s_pdf = r.post(f"{API}/structure/chr", json=payload_pdf, timeout=90)
        s_pdf.raise_for_status()
        body_pdf = s_pdf.json()
        rel_json = body_pdf.get("artifacts", {}).get("rel_json")
        if not rel_json:
            fail("CHR PDF missing rel_json")
        djson = r.get(f"{API}/download", params={"rel": rel_json}, timeout=30)
        djson.raise_for_status()
        data = djson.json()
        rows = data.get("rows", [])
        if not isinstance(rows, list) or len(rows) == 0:
            fail("CHR PDF JSON rows missing")
        ok("/structure/chr (pdf sentences)")
    except Exception as e:
        fail(f"/structure/chr pdf error: {e}")

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

    # 7b) upload audio/video/image + URL
    audio_name = "sample_audio.wav"
    video_name = "sample_video.mp4"
    image_name = "sample_image.png"
    web_urls_file = ROOT / "samples" / "web_urls.txt"
    audio_bytes = _sample_audio_wav()
    video_bytes = _sample_video_mp4()
    image_bytes = _sample_image_png()
    files_media = [
        ("files", (audio_name, audio_bytes, "audio/wav")),
        ("files", (video_name, video_bytes, "video/mp4")),
        ("files", (image_name, image_bytes, "image/png")),
    ]
    data_fields = []
    if web_urls_file.exists():
        for line in web_urls_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                data_fields.append(("web_urls", line))
    try:
        upload_media = r.post(f"{API}/upload", files=files_media, data=data_fields, timeout=90)
        upload_media.raise_for_status()
        payload_media = upload_media.json()
        media_results = payload_media.get("results", [])
        if len(media_results) < 3:
            fail("media upload did not return expected results")
        for item in media_results:
            if item.get("status") != "success":
                fail(f"media upload failure: {item}")
        ok("/upload media bundle")
    except Exception as e:
        fail(f"/upload media bundle error: {e}")

    # Validate media artifacts summary
    try:
        media_summary = r.get(f"{API}/artifacts/media", timeout=15)
        media_summary.raise_for_status()
        media_payload = media_summary.json()
        if not media_payload.get("transcripts"):
            fail("media summary missing transcripts")
        if not media_payload.get("media_metadata"):
            fail("media summary missing metadata")
        ok("/artifacts/media")
    except Exception as e:
        fail(f"/artifacts/media error: {e}")

    # Confirm artifact counts for audio/image/web
    try:
        all_artifacts = r.get(f"{API}/artifacts", timeout=15)
        all_artifacts.raise_for_status()
        arts_payload = all_artifacts.json().get("artifacts", [])
        audio_art = next((a for a in arts_payload if a.get("filename") == audio_name), None)
        if not audio_art or audio_art.get("media_transcripts", 0) == 0:
            fail("audio artifact missing transcript count")
        image_art = next((a for a in arts_payload if a.get("filename") == image_name), None)
        if not image_art or image_art.get("image_ocr", 0) == 0:
            fail("image artifact missing OCR count")
        url_art = None
        if data_fields:
            url_value = data_fields[0][1]
            url_art = next((a for a in arts_payload if a.get("filename") == url_value), None)
            if not url_art or url_art.get("web_pages", 0) == 0:
                fail("web artifact missing page evidence")
        ok("media artifacts summary checks")
    except Exception as e:
        fail(f"media artifacts check error: {e}")

    # 8) ingest xml/openapi/postman
    try:
        with open(ROOT/"samples"/"sample.xml", "rb") as f:
            ix = r.post(f"{API}/ingest/xml", files={"file": ("sample.xml", f, "text/xml")}, timeout=30)
        ix.raise_for_status()
        ix_data = ix.json()
        xml_document_id = ix_data.get("document_id")
        if not xml_document_id:
            fail("ingest xml missing document_id")
        with open(ROOT/"samples"/"sample_openapi.json", "rb") as f:
            ioa = r.post(f"{API}/ingest/openapi", files={"file": ("sample_openapi.json", f, "application/json")}, timeout=30)
        ioa.raise_for_status()
        with open(ROOT/"samples"/"sample_postman.json", "rb") as f:
            ipm = r.post(f"{API}/ingest/postman", files={"file": ("sample_postman.json", f, "application/json")}, timeout=30)
        ipm.raise_for_status()
        # query logs/apis
        ql = r.get(f"{API}/logs?level=ERROR", timeout=10)
        ql.raise_for_status()
        ql_doc = r.get(f"{API}/logs", params={"document_id": xml_document_id}, timeout=10)
        ql_doc.raise_for_status()
        logs_filtered = ql_doc.json().get("logs", [])
        if not logs_filtered:
            fail("document-filtered logs returned no rows")
        if any(log.get("document_id") != xml_document_id for log in logs_filtered):
            fail("document-filtered logs include mismatched document_id")
        if "E1001" not in {log.get("code") for log in logs_filtered}:
            fail("document-filtered logs missing expected code")
        qa = r.get(f"{API}/apis?method=GET", timeout=10)
        qa.raise_for_status()
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

    # 11b) search with type filters (api/log/tag), invalid type, and empty types
    try:
        for types in (["api"], ["log"], ["tag"], ["bogus"], []):
            payload = {"q": "loan", "k": 5}
            if types:
                payload["types"] = types
            resp = r.post(f"{API}/search", json=payload, timeout=10)
            resp.raise_for_status()
        ok("/search with filters + invalid type")
    except Exception as e:
        fail(f"search filters error: {e}")

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

    # 12) /open/pdf (allow 200 if enabled or 403 if disabled)
    try:
        op = r.get(f"{API}/open/pdf", params={"artifact_id": pdf_artifact_id, "page": 1}, timeout=15)
        if op.status_code not in (200, 403):
            fail(f"/open/pdf unexpected status: {op.status_code}")
        ok("/open/pdf")
    except Exception as e:
        fail(f"open/pdf error: {e}")

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
