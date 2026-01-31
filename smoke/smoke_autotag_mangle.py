import os
import requests

BASE = os.environ.get("SMOKE_API", "http://localhost:8000").rstrip("/")

def main():
    # Try to list documents
    r = requests.get(f"{BASE}/documents")
    r.raise_for_status()
    docs = r.json().get("documents", [])
    if not docs:
        print("NO_DOCS")
        return
    doc = docs[0]
    # Dry‑run tag extraction with POML and inline Mangle only (no execution)
    body = {
        "document_id": doc["id"],
        "dry_run": True,
        "include_poml": True,
        "mangle_file": "docs/samples/mangle/normalized_tags.mg",
        "mangle_exec": False,
        "use_hrm": False,
    }
    r = requests.post(f"{BASE}/extract/tags", json=body)
    r.raise_for_status()
    data = r.json()
    tags = data.get("tags", [])
    print(f"TAGS_PREVIEW={len(tags)}")
    # If mg is available and env allows, try exec path
    if os.environ.get("SMOKE_TRY_MG", "false").lower() == "true":
        body["mangle_exec"] = True
        r2 = requests.post(f"{BASE}/extract/tags", json=body)
        if r2.ok:
            print("MANGLE_EXEC_OK")

if __name__ == "__main__":
    main()

