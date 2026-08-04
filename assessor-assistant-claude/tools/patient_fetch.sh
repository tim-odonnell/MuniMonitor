#!/usr/bin/env bash
# Patient corpus fetch. legislature.mi.gov's rate limit tightened sharply after a
# day of use from this host; each attempt while blocked appears to reset the
# clock. So: wait a long time BEFORE trying, go very slowly when we do, and stop
# immediately on a wall rather than pushing into it.
#
# This is the legitimate way through — patience, not disguise. Usage:
#   nohup tools/patient_fetch.sh 3600 45 &     # wait 1h, then 45s between requests
set -u
WAIT="${1:-2700}"       # seconds to wait before the first attempt
DELAY="${2:-40}"        # seconds between requests once fetching
ROUNDS="${3:-8}"        # how many cycles to attempt before giving up

cd "$(dirname "$0")/.."
for round in $(seq 1 "$ROUNDS"); do
  echo "=== round $round/$ROUNDS: sleeping ${WAIT}s before probing ==="
  sleep "$WAIT"
  probe=$(curl -s --max-time 45 -A "MuniMonitor-corpus-builder/1.0 (municipal assessing corpus)" \
    "https://www.legislature.mi.gov/Laws/MCL?objectName=mcl-Article-IX-31" 2>/dev/null)
  if echo "$probe" | grep -qi "validation request"; then
    echo "  still blocked; backing off further"
    WAIT=$(( WAIT * 3 / 2 ))       # lengthen the wait each failed round
    continue
  fi
  echo "  clear — fetching at ${DELAY}s pacing"
  python3 tools/fetch_all_michigan.py --delay "$DELAY" 2>&1
  rc=$?
  held=$(ls corpus/mcl-*.md 2>/dev/null | wc -l)
  echo "  round $round finished (rc=$rc); corpus now holds $held mcl/const docs"
  [ "$rc" -eq 0 ] && { echo "=== queue exhausted ==="; break; }
  WAIT=$(( WAIT * 3 / 2 ))
done
echo "=== patient fetch done ==="
