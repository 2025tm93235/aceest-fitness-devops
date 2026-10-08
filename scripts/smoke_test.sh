#!/usr/bin/env bash
# Start the runtime image, wait until /health answers inside the container,
# then call a couple of endpoints. Used by both Jenkins and GitHub Actions.
#
# Usage: bash scripts/smoke_test.sh <image> [container-name]
set -euo pipefail

IMAGE="${1:?usage: smoke_test.sh <image> [container-name]}"
NAME="${2:-aceest-smoke-$$}"
RETRIES="${SMOKE_RETRIES:-30}"

# shellcheck disable=SC2329  # invoked via trap
cleanup() { docker rm -f "${NAME}" >/dev/null 2>&1 || true; }
trap cleanup EXIT

probe() {
    docker exec "${NAME}" python -c "import json, sys, urllib.request; \
r = urllib.request.urlopen('http://127.0.0.1:5000$1', timeout=4); \
print(r.status, r.read().decode()[:200]); sys.exit(0 if r.status == 200 else 1)"
}

echo "Starting ${IMAGE} as ${NAME}"
docker run -d --name "${NAME}" "${IMAGE}" >/dev/null

for attempt in $(seq 1 "${RETRIES}"); do
    if probe /health >/dev/null 2>&1; then
        echo "Application healthy after ${attempt} attempt(s)"
        probe /health
        exit 0
    fi
    sleep 2
done

echo "Application did not become healthy; container logs follow:" >&2
docker logs "${NAME}" >&2 || true
exit 1
