#!/usr/bin/env bash
set -euo pipefail

ART_DIR="/app/artifacts/datavzrd"
OUT_DIR="/app/out"
mkdir -p "$OUT_DIR"

pick_viz() {
  if [[ -n "${VIZ_FILE:-}" && -f "$VIZ_FILE" ]]; then
    echo "$VIZ_FILE"
    return 0
  fi
  # pick latest viz.yaml by mtime
  mapfile -t files < <(find "$ART_DIR" -type f -name viz.yaml -printf '%T@ %p\n' | sort -nr | awk '{print $2}')
  if (( ${#files[@]} > 0 )); then
    echo "${files[0]}"
    return 0
  fi
  return 1
}

last_mtime=0
while true; do
  if viz=$(pick_viz); then
    mt=$(stat -c %Y "$viz" 2>/dev/null || echo 0)
    if [[ "$mt" != "$last_mtime" ]]; then
      echo "[datavzrd] Building dashboard from $viz"
      mkdir -p "$OUT_DIR"
      datavzrd "$viz" --output "$OUT_DIR" --overwrite-output || true
      last_mtime="$mt"
    fi
  else
    echo "[datavzrd] No viz.yaml found in $ART_DIR. Waiting..."
  fi
  if ! pgrep -f "python3 -m http.server 5173" >/dev/null; then
    echo "[datavzrd] Serving /app/out at :5173"
    (cd "$OUT_DIR" && python3 -m http.server 5173) &
  fi
  sleep 3
done
