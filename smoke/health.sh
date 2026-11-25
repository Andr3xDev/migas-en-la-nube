#!/usr/bin/env bash
# Usage: health.sh <base-url> <environment>
# SMOKE_ATTEMPTS and SMOKE_DELAY_SECONDS override the defaults (12 attempts, 10 s apart).
set -uo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <base-url> <environment>" >&2
  exit 2
fi

base_url="${1%/}"
expected_environment="$2"
attempts="${SMOKE_ATTEMPTS:-12}"
delay_seconds="${SMOKE_DELAY_SECONDS:-10}"

for ((attempt = 1; attempt <= attempts; attempt++)); do
  if body="$(curl -fsS --max-time 15 "$base_url/api/health")" &&
    jq -e --arg env "$expected_environment" \
      '.status == "ok" and .environment == $env' <<<"$body" >/dev/null; then
    echo "health ok on attempt $attempt: $body"
    exit 0
  fi
  echo "attempt $attempt/$attempts not healthy${body:+: $body}" >&2
  body=""
  ((attempt < attempts)) && sleep "$delay_seconds"
done

echo "health check failed after $attempts attempts" >&2
exit 1
