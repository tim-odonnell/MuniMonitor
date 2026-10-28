#!/usr/bin/env bash
# Portable LLM engine launcher — Building & Inspections Assistant
# Drop a GGUF model into models/ and run:  ./serve.sh
# Options: ./serve.sh [model-name-filter] [--port N] [--ctx N] [--parallel N] [--no-config]
set -euo pipefail
cd "$(dirname "$0")"

PORT=18080; CTX=16384; PAR=1; PATTERN=""; UPDATE_CONFIG=1; MODE=text
while [[ $# -gt 0 ]]; do case "$1" in
  --port) PORT=$2; shift 2;;
  --ctx) CTX=$2; shift 2;;
  --parallel) PAR=$2; shift 2;;
  --no-config) UPDATE_CONFIG=0; shift;;
  vision) MODE=vision; PORT=18081; SEARCH_DIR=models/vision; shift;;
  -h|--help) grep '^#' "$0" | head -4; exit 0;;
  *) PATTERN=$1; shift;;
esac; done

# --- engine resolution: env var > custom drop-in > bundled > PATH ---
BIN="${LLAMA_SERVER:-}"
[[ -z "$BIN" && -x engine/llama-server-custom ]] && BIN=engine/llama-server-custom
[[ -z "$BIN" && -x engine/llama-server ]] && BIN=engine/llama-server
[[ -z "$BIN" ]] && BIN="$(command -v llama-server || true)"
[[ -z "$BIN" ]] && { echo "ERROR: no llama-server engine found (engine/ or PATH)."; exit 1; }
if ! "$BIN" --version >/dev/null 2>&1; then
  echo "ERROR: '$BIN' will not run on this system (likely an older glibc, or wrong arch)."
  echo "Fix: install/build llama.cpp for THIS machine and either put the binary on PATH,"
  echo "     copy it to engine/llama-server-custom, or export LLAMA_SERVER=/path/to/it."
  exit 1
fi

# --- model resolution: search models/ for GGUFs (mmproj files excluded) ---
SEARCH_DIR="models"
[[ "$MODE" == vision ]] && SEARCH_DIR=models/vision
# Unified-folder layout: a shared model store one level up serves all projects
# (text mode only — vision models stay project-local with their mmproj pair).
EXTRA_DIRS=""
[[ "$MODE" == "text" && -d ../models-shared ]] && EXTRA_DIRS=../models-shared
mapfile -t GGUFS < <(find "$SEARCH_DIR" $EXTRA_DIRS -name '*.gguf' ! -iname '*mmproj*' 2>/dev/null | sort)
if [[ -n "$PATTERN" ]]; then
  mapfile -t GGUFS < <(printf '%s\n' "${GGUFS[@]}" | grep -i -- "$PATTERN" || true)
fi
if [[ ${#GGUFS[@]} -eq 0 || -z "${GGUFS[0]}" ]]; then
  echo "ERROR: no .gguf model found in $SEARCH_DIR/ ${PATTERN:+matching '$PATTERN'}."
  echo "Drop a GGUF file (or a folder containing one) into $SEARCH_DIR/ and rerun."
  exit 1
fi
MODEL="${GGUFS[0]}"
[[ ${#GGUFS[@]} -gt 1 ]] && printf 'NOTE: %d models found, using the first. Others:\n%s\n' "${#GGUFS[@]}" "$(printf '  %s\n' "${GGUFS[@]:1}")"

EXTRA=""
# Projector must pair with the model: prefer the one in the model's own folder
# (fetch-models.sh puts each pair in its own subfolder; both are named mmproj-F16.gguf).
if [[ "$MODE" == vision ]]; then MMPROJ=$(find "$(dirname "$MODEL")" -maxdepth 1 -iname '*mmproj*.gguf' 2>/dev/null | head -1); [[ -z "$MMPROJ" ]] && MMPROJ=$(find models/vision models -iname '*mmproj*.gguf' 2>/dev/null | head -1); [[ -z "$MMPROJ" ]] && { echo 'ERROR: vision mode needs an mmproj*.gguf next to the model in models/vision/.'; exit 1; }; EXTRA="--mmproj $MMPROJ"; fi

# --- preflight: python + corpus index ---
command -v python3 >/dev/null || { echo "ERROR: python3 required."; exit 1; }
[[ -f corpus/index.json ]] || { echo "corpus index missing — building it:"; python3 src/ingest.py; }

# --- point this project's config at the server we are about to start ---
if [[ $UPDATE_CONFIG -eq 1 ]]; then
  MODE="$MODE" PORT="$PORT" MODEL_NAME="$(basename "$MODEL" .gguf)" python3 - <<'PY'
import json, os
c = json.load(open("config.json"))
blk = c["vision"] if os.environ["MODE"] == "vision" and "vision" in c else c["llm"]
blk["base_url"] = f"http://127.0.0.1:{os.environ['PORT']}/v1"
blk["model"] = os.environ["MODEL_NAME"]
json.dump(c, open("config.json", "w"), indent=2)
print(f"config.json: {os.environ['MODE']} endpoint -> :{os.environ['PORT']} ({os.environ['MODEL_NAME']})")
PY
fi

echo "============================================================"
echo " Building & Inspections Assistant"
echo " engine : $BIN ($($BIN --version 2>&1 | head -1))"
echo " model  : $MODEL"
echo " serving: http://127.0.0.1:$PORT  (ctx $CTX, parallel $PAR)"
echo " next   : python3 src/ask.py ...   (vision: ./serve.sh vision, then src/vision_check.py --calibrate)"
echo "============================================================"
exec "$BIN" -m "$MODEL" --host 127.0.0.1 --port "$PORT" -c "$CTX" --parallel "$PAR" -ngl 999 $EXTRA
