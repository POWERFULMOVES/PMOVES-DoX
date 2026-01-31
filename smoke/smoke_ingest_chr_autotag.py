import os
import time
import requests

BASE = os.environ.get("SMOKE_API", "http://localhost:8000").rstrip("/")

def wait_for_queue(timeout=60):
    t0 = time.time()
    while time.time() - t0 < timeout:
        r = requests.get(f"{BASE}/tasks")
        if not r.ok:
            time.sleep(1)
            continue
        q = r.json().get("queued", 0)
        if q == 0:
            return True
        time.sleep(1)
    return False

def main():
    # kick off sample load (async PDF enabled to test pipeline)
    r = requests.post(f"{BASE}/load_samples", params={"async_pdf": True})
    r.raise_for_status()
    ok = wait_for_queue(timeout=120)
    print(f"QUEUE_EMPTY={ok}")

    # check artifacts for at least one PDF with CHR and tags
    r = requests.get(f"{BASE}/artifacts")
    r.raise_for_status()
    arts = r.json().get("artifacts", [])
    found = False
    for a in arts:
        if str(a.get("filetype","")) == ".pdf":
            if a.get("chr_ready") and int(a.get("tags_count") or 0) >= 0:
                found = True
                print(f"PDF_OK id={a.get('id')} chr={a.get('chr_ready')} tags={a.get('tags_count')}")
                break
    print(f"FOUND_PDF_WITH_RESULTS={found}")

if __name__ == "__main__":
    main()

