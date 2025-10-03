#!/usr/bin/env bash
set -euo pipefail

OUT="${OUTPUT_DIR:-/app/out/schema}"
mkdir -p "$OUT"
if command -v schemavzrd >/dev/null 2>&1 && [[ -n "${DB_URL:-}" ]]; then
  echo "[schemavzrd] Documenting schema to $OUT from $DB_URL"
  schemavzrd "$DB_URL" --output "$OUT" || true
else
  if [[ -z "${DB_URL:-}" ]]; then
    echo "[schemavzrd] DB_URL not set; serving existing docs from $OUT"
  else
    echo "[schemavzrd] CLI not available; serving existing docs from $OUT"
  fi
fi
echo "[schemavzrd] Serving $OUT at :5174"
cd "$OUT"
python3 -m http.server 5174
