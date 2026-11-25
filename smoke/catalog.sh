#!/usr/bin/env bash
# Usage: catalog.sh <base-url>
# SMOKE_ATTEMPTS and SMOKE_DELAY_SECONDS override the defaults (12 attempts, 10 s apart).
set -uo pipefail

if [[ $# -ne 1 ]]; then
  echo "usage: $0 <base-url>" >&2
  exit 2
fi

base_url="${1%/}"
attempts="${SMOKE_ATTEMPTS:-12}"
delay_seconds="${SMOKE_DELAY_SECONDS:-10}"

for ((attempt = 1; attempt <= attempts; attempt++)); do
  if body="$(curl -fsS --max-time 15 "$base_url/api/products")" &&
    jq -e 'type == "array" and length >= 1' <<<"$body" >/dev/null; then
    echo "catalog ok on attempt $attempt: $(jq length <<<"$body") products"
    exit 0
  fi
  echo "attempt $attempt/$attempts catalog not ready${body:+: $body}" >&2
  body=""
  ((attempt < attempts)) && sleep "$delay_seconds"
done

echo "catalog check failed after $attempts attempts" >&2
exit 1
