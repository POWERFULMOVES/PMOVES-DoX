#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DB_URL:-}" ]]; then
  echo "[schemavzrd] DB_URL not set. Exiting."
  sleep infinity
fi

OUT="${OUTPUT_DIR:-/app/out/schema}"
mkdir -p "$OUT"
echo "[schemavzrd] Documenting schema to $OUT from $DB_URL"
schemavzrd "$DB_URL" --output "$OUT" || true
echo "[schemavzrd] Serving $OUT at :5174"
cd "$OUT"
python3 -m http.server 5174

