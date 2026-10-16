#!/usr/bin/env bash
# Run a command and keep its output as submission evidence:
#   docs/screenshots/<name>.txt  - raw output, with the command on the first line
#   docs/screenshots/<name>.png  - rendered "terminal window" (via scripts/render-terminal.py)
#
# Usage:
#   scripts/capture-evidence.sh <name> <command ...>
#   scripts/capture-evidence.sh <name> --title "shown in the title bar" <command ...>
#
# The command is joined and run with `bash -c`, so pipes, && and cd work when quoted:
#   scripts/capture-evidence.sh pytest "cd backend && pytest -v"
#   scripts/capture-evidence.sh kubectl-pods kubectl get pods -n expense-tracker -o wide
#   scripts/capture-evidence.sh compose-up --title "docker compose up --build" "docker compose up --build"
#
# Output is still streamed to the terminal, the command's exit code is preserved, and the PNG is
# rendered even when the command fails or is stopped with Ctrl-C (useful for `compose up`, which
# never exits on its own). Colours are disabled where tools honour NO_COLOR/TERM so the text stays clean.
set -uo pipefail

usage() { sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

[ $# -ge 2 ] || usage
NAME="$1"; shift
TITLE=""
if [ "${1:-}" = "--title" ]; then
  [ $# -ge 3 ] || usage
  TITLE="$2"; shift 2
fi
CMD="$*"
[ -n "$TITLE" ] || TITLE="$CMD"

# Resolve paths relative to the repository root, no matter where the script is called from.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="${EVIDENCE_DIR:-$REPO_ROOT/docs/screenshots}"
mkdir -p "$OUT_DIR"
TXT="$OUT_DIR/$NAME.txt"
PNG="$OUT_DIR/$NAME.png"

render() {
  echo "capture-evidence: text -> $TXT"
  python3 "$SCRIPT_DIR/render-terminal.py" "$TXT" --title "$TITLE" -o "$PNG" \
    --footer "Om Malviya (24BCS10448) - $(date '+%Y-%m-%d %H:%M')"
}
# Render on every exit path, including Ctrl-C, so a long-running capture still produces a picture.
trap 'trap - INT TERM EXIT; render; exit "${STATUS:-130}"' INT TERM EXIT

STATUS_FILE="$OUT_DIR/.$NAME.status"
{
  echo "\$ $CMD"
  # The ( ) subshell keeps a `cd` inside the command from affecting this script.
  ( cd "$REPO_ROOT" && NO_COLOR=1 TERM=dumb FORCE_COLOR=0 PY_COLORS=0 bash -o pipefail -c "$CMD" ) 2>&1
  # The left side of the pipe runs in a subshell, so the exit code travels through a temp file.
  echo "$?" > "$STATUS_FILE"
} | tee "$TXT"

STATUS="$(cat "$STATUS_FILE" 2>/dev/null || echo 1)"
rm -f "$STATUS_FILE"
echo "capture-evidence: command exited with $STATUS"
exit "$STATUS"
