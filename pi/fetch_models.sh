#!/bin/bash
# Download the duck's policies from Hugging Face into pi/models/ (or another folder): every .onnx and .json in the model repo.
#   bash pi/fetch_models.sh                      on the PC, from the repo root; then bash pi/deploy.sh copies them to the Pi
#   bash fetch_models.sh                         on the Pi, in ~/duck
#   bash fetch_models.sh stand_emote_calm        only the files whose names start with this
# Needs curl and python, nothing else. Each file lands under a temporary name and is moved into place only once complete, so a dropped
# link can't leave a truncated model (a cut-off copy did that once, 2026-11-25).
set -e
REPO=${HF_MODEL_REPO:-tinkerbuggy/duck-droids-dynamixel}
cd "$(dirname "$0")"
DEST=${DEST:-models}
mkdir -p "$DEST"
PY=
for p in python3 python .venv/bin/python .venv/Scripts/python.exe; do      # Windows' python3 can be a Store shortcut that fails: try each
    if "$p" -c 'import json' >/dev/null 2>&1; then PY=$p; break; fi
done
[ -n "$PY" ] || { echo "no python found (python3, python or the venv)"; exit 1; }
LIST='
import json, sys
for s in json.load(sys.stdin).get("siblings", []):
    f = s["rfilename"]
    if f.endswith((".onnx", ".json")) and "/" not in f:
        sys.stdout.write(f + "\n")'
FILES=$(curl -fsSL "https://huggingface.co/api/models/$REPO" | "$PY" -c "$LIST" | tr -d '\015')
[ -n "$FILES" ] || { echo "nothing listed at huggingface.co/$REPO"; exit 1; }
n=0
for f in $FILES; do
    [ -n "$1" ] && [[ "$f" != "$1"* ]] && continue
    tmp="$DEST/.$f.part"
    curl -fsSL --retry 3 -o "$tmp" "https://huggingface.co/$REPO/resolve/main/$f"
    mv -f "$tmp" "$DEST/$f"
    echo "  $f ($(wc -c < "$DEST/$f") bytes)"
    n=$((n + 1))
done
echo "$n files from huggingface.co/$REPO into $DEST/"
