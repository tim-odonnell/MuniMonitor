#!/usr/bin/env bash
# Download the model files that git doesn't carry, pinned and SHA256-verified.
# Usage: ./fetch-models.sh [text] [small] [qwen] [vision] [vision-large] [all]
#   (no argument) picks by usable RAM: under 14 GiB -> small; 14-22 GiB (16 GB machines) -> text;
#                 22 GiB and up (24/32 GB+) -> large
#   text          gpt-oss-20b UD-Q4_K_XL, 11.9 GB  -> models-shared/        (validated)
#   small         Gemma 4 E2B QAT Q4_0 (Google), 3.35 GB -> models-shared/  (NOT validated; low-RAM / failure tests)
#   large         Gemma 4 26B-A4B UD-Q3_K_XL, 12.9 GB -> models-shared/     (NOT yet validated; best in testing)
#   qwen          Qwen3.6-35B-A3B UD-Q4_K_XL, 22.9 GB -> models-shared/     (validated, needs 32 GB RAM)
#   vision        Qwen3-VL-8B + mmproj, 6.3 GB  -> building-inspections-claude/models/vision/qwen3-vl-8b/
#   vision-large  Qwen3-VL-30B-A3B + mmproj, 18.8 GB -> .../models/vision/qwen3-vl-30b-a3b/
# Vision candidates are NOT validated — see building-inspections-claude/models/vision/README.md.
# Needs only curl + sha256sum. Re-running resumes partial downloads and skips verified files.
set -euo pipefail
cd "$(dirname "$0")"

VISION_DIR=building-inspections-claude/models/vision

# fetch <repo> <commit> <file> <sha256> <dest-dir>
fetch() {
  local repo=$1 rev=$2 file=$3 sha=$4 dir=$5 dest="$5/$3"
  mkdir -p "$dir"
  if [[ -f "$dest" ]]; then
    echo "checking  $dest"
    if echo "$sha  $dest" | sha256sum -c --status; then echo "ok        $dest"; return; fi
    echo "MISMATCH  $dest — re-downloading"; rm -f "$dest"
  fi
  echo "fetching  $repo/$file  (rev ${rev:0:8})"
  curl -fL --progress-bar --retry 5 --retry-delay 10 -C - -o "$dest.part" \
    "https://huggingface.co/$repo/resolve/$rev/$file"
  echo "verifying $dest"
  if ! echo "$sha  $dest.part" | sha256sum -c --status; then
    echo "ERROR: SHA256 mismatch for $dest.part — delete it and rerun."; exit 1
  fi
  mv "$dest.part" "$dest"; echo "ok        $dest"
}

text() {
  fetch unsloth/gpt-oss-20b-GGUF d449b42d93e1c2c7bda5312f5c25c8fb91dfa9b4 \
    gpt-oss-20b-UD-Q4_K_XL.gguf 10fe673de12c20b74b8d670a9fdf0fd36b43b0a86ffc04daeb175c0a2b98c4f9 models-shared
}
small() {
  fetch google/gemma-4-E2B-it-qat-q4_0-gguf 675cff42a74c774d6cb76f76d8eacb49b48c9b93 \
    gemma-4-E2B_q4_0-it.gguf fa401b55b07ee70a54c6dae3903c783a6e65064312529ea57175cb5f8dec6634 models-shared
  echo "NOTE: Gemma 4 E2B is NOT validated for MuniMonitor — expect wrong answers. Use it to test on"
  echo "      low-RAM machines or to study failures. Start it with: ./serve.sh e2b --ctx 32768"
}
large() {
  fetch unsloth/gemma-4-26B-A4B-it-GGUF c099eb48e663fd284577b04978a94ffccb261841 \
    gemma-4-26B-A4B-it-UD-Q3_K_XL.gguf 90a918830420e6a36e01c0d219e563f1d0ca7f223dffd90ad4e02ef4f3253fde models-shared
  echo "NOTE: Gemma 4 26B-A4B is NOT yet validated for MuniMonitor (best results in testing, but some"
  echo "      answers run away). Start it with: ./serve.sh 26b --ctx 32768"
}
qwen() {
  fetch unsloth/Qwen3.6-35B-A3B-MTP-GGUF 5bc3e238d916f48a861bac2f8a1990a0e9b7e98d \
    Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf 55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1 models-shared
}
vision() {
  local r=unsloth/Qwen3-VL-8B-Instruct-GGUF v=b93a7ee713758252c555be4210c00540df954dc2 d=$VISION_DIR/qwen3-vl-8b
  fetch $r $v Qwen3-VL-8B-Instruct-UD-Q4_K_XL.gguf e3d1a6e87c5cb31e054f2c3bc0dd82ffde052f613de5eef3665b7bd33c9b703e $d
  fetch $r $v mmproj-F16.gguf d406d03ebabefdef86a2c86bf0c1b65f9e046f7a81c218f25de4931b46a07fc4 $d
}
vision-large() {
  local r=unsloth/Qwen3-VL-30B-A3B-Instruct-GGUF v=0af19e7479857aa7f3246466a4ad16c7e7299639 d=$VISION_DIR/qwen3-vl-30b-a3b
  fetch $r $v Qwen3-VL-30B-A3B-Instruct-UD-Q4_K_XL.gguf 9874db2e146b4a1322086667172a96f36061ee950f1b45939ac46a2e25e1aeb0 $d
  fetch $r $v mmproj-F16.gguf 9f248089357599a08a23af40cb5ce0030de14a2e119b7ef57f66cb339bd20819 $d
}

# No argument: pick by usable RAM (the bundled engine runs on the CPU, so the whole model sits in RAM).
# A "16 GB" machine reports ~15.5 GiB to Linux and runs gpt-oss-20b (see SYSTEM-REQUIREMENTS); the
# 12.9 GB Gemma 26B needs 24 GB to leave room for the OS and context. Name a tier to override.
if [[ $# -eq 0 ]]; then
  mem_kb=${FETCH_MEM_KB:-$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)}
  gib=$((mem_kb / 1024 / 1024))
  if (( mem_kb < 14 * 1024 * 1024 )); then
    echo "This machine has $gib GiB of RAM — under the 16 GB the validated model needs: downloading 'small'."
    set -- small
  elif (( mem_kb < 22 * 1024 * 1024 )); then
    echo "This machine has $gib GiB of RAM: downloading 'text' (gpt-oss-20b, the validated model)."
    set -- text
  else
    echo "This machine has $gib GiB of RAM: downloading 'large' (Gemma 4 26B-A4B)."
    set -- large
  fi
  echo "(Run './fetch-models.sh text', 'small' or 'large' to choose yourself.)"
fi
for what in "$@"; do case "$what" in
  text|small|large|qwen|vision|vision-large) "$what";;
  all) text; qwen; vision; vision-large;;
  -h|--help) grep '^#' "$0" | head -13; exit 0;;
  *) echo "unknown: $what (try --help)"; exit 1;;
esac; done
