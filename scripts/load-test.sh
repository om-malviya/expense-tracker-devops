#!/usr/bin/env bash
# Simple HTTP load generator for the HPA demo (rubric M8): keeps N parallel curl workers hammering
# the two heaviest read endpoints so the backend's CPU climbs above the HPA target and the
# autoscaler adds replicas. Watch it with:  kubectl -n expense-tracker get hpa -w
#
# Usage:
#   scripts/load-test.sh [BASE_URL] [DURATION_SECONDS] [CONCURRENCY]
#     BASE_URL          default http://expense.local  (compose: http://localhost:8000; port-forward: http://localhost:8080)
#     DURATION_SECONDS  default 120
#     CONCURRENCY       default 20 parallel workers
#
# Examples:
#   scripts/load-test.sh                                  # ingress, 2 minutes, 20 workers
#   scripts/load-test.sh http://localhost:8000 60 10      # docker compose backend
#
# Only curl and bash are needed, so it runs unchanged on macOS, Linux and the CI runner.
set -euo pipefail

BASE_URL="${1:-http://expense.local}"
DURATION="${2:-120}"
CONCURRENCY="${3:-20}"
BASE_URL="${BASE_URL%/}" # strip a trailing slash so the paths below join cleanly

# The summary endpoint aggregates the whole table (sum/group-by) and the list endpoint serialises
# every row - both do real DB work per request, unlike /health, which is what makes them useful
# for driving CPU.
ENDPOINTS=(
  "/api/expenses"
  "/api/expenses/summary"
  "/api/expenses?category=food"
  "/api/expenses/summary"
)

command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }

# Fail fast if the target is unreachable instead of printing 20 workers worth of connection errors.
# An /api path is probed (not /health) so the same check works against the backend directly,
# through nginx in compose, and through the ingress, where / belongs to the frontend.
if ! curl -fsS --max-time 5 -o /dev/null "$BASE_URL/api/expenses/summary"; then
  echo "ERROR: $BASE_URL/api/expenses/summary is not reachable - is the stack up / is the ingress host in /etc/hosts?" >&2
  exit 1
fi

echo "Load test -> $BASE_URL  duration=${DURATION}s  concurrency=${CONCURRENCY}"
echo "Endpoints: ${ENDPOINTS[*]}"
echo "Started $(date '+%H:%M:%S'); press Ctrl-C to stop early."

STATS_DIR="$(mktemp -d)"
trap 'rm -rf "$STATS_DIR"' EXIT
END_AT=$(( $(date +%s) + DURATION ))

worker() {
  local id="$1" ok=0 fail=0 i=0 path
  while [ "$(date +%s)" -lt "$END_AT" ]; do
    path="${ENDPOINTS[$(( i % ${#ENDPOINTS[@]} ))]}"
    if curl -fsS --max-time 10 -o /dev/null "$BASE_URL$path"; then
      ok=$((ok + 1))
    else
      fail=$((fail + 1))
    fi
    i=$((i + 1))
  done
  echo "$ok $fail" > "$STATS_DIR/worker-$id"
}

# Each worker is a background subshell; `wait` collects them all when the clock runs out.
for w in $(seq 1 "$CONCURRENCY"); do
  worker "$w" &
done

# Progress line every 10 s so a screenshot of this terminal shows the test is alive
# (1 s ticks so the script ends on time instead of up to 10 s late).
tick=0
while [ "$(date +%s)" -lt "$END_AT" ]; do
  sleep 1
  tick=$((tick + 1))
  remaining=$(( END_AT - $(date +%s) ))
  if [ $((tick % 10)) -eq 0 ] && [ "$remaining" -gt 0 ]; then
    echo "  ... ${remaining}s remaining ($(date '+%H:%M:%S'))"
  fi
done
wait

total_ok=0; total_fail=0
for f in "$STATS_DIR"/worker-*; do
  read -r ok fail < "$f"
  total_ok=$((total_ok + ok)); total_fail=$((total_fail + fail))
done
total=$((total_ok + total_fail))
echo "Finished $(date '+%H:%M:%S'): $total requests in ${DURATION}s" \
     "(~$(( total / (DURATION > 0 ? DURATION : 1) )) req/s), $total_ok OK, $total_fail failed"
[ "$total_fail" -eq 0 ] || exit 2
