#!/bin/bash
# Download the duck's policies from Hugging Face into pi/models/ (or another folder): every .onnx and .json in the model repo, active.json
# (which model each controller mode runs, with SHA-256s) among them.
#   bash pi/fetch_models.sh                      on the PC, from the repo root; then bash pi/deploy.sh copies them to the Pi
#   bash fetch_models.sh                         on the Pi, in ~/duck
#   bash fetch_models.sh stand_emote_calm        only the files whose names start with this
# Needs curl and python, nothing else. Each file lands under a temporary name, is checked against Hugging Face's own hash for it (SHA-256
# for the large files, the git blob hash for the small ones), and only then moved into place: a dropped link or a corrupt download can't
# leave a broken model (a cut-off copy did that once, 2026-11-25).
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
        lfs = s.get("lfs") or {}
        kind, h = ("sha256", lfs["sha256"]) if lfs.get("sha256") else ("blob", s.get("blobId", ""))
        sys.stdout.write(f + " " + kind + " " + h + "\n")'
CHECK='
import hashlib, sys
path, kind, want = sys.argv[1:4]
data = open(path, "rb").read()
got = hashlib.sha256(data).hexdigest() if kind == "sha256" else hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
sys.exit(0 if got == want else 1)'
ENTRIES=$(curl -fsSL "https://huggingface.co/api/models/$REPO?blobs=true" | "$PY" -c "$LIST" | tr -d '\015')
[ -n "$ENTRIES" ] || { echo "nothing listed at huggingface.co/$REPO"; exit 1; }
n=0
while read -r f kind h; do
    [ -n "$1" ] && [[ "$f" != "$1"* ]] && continue
    tmp="$DEST/.$f.part"
    curl -fsSL --retry 3 -o "$tmp" "https://huggingface.co/$REPO/resolve/main/$f"
    if [ -n "$h" ] && ! "$PY" -c "$CHECK" "$tmp" "$kind" "$h"; then
        rm -f "$tmp"
        echo "  $f: its $kind doesn't match Hugging Face's: not kept (run again)"
        exit 1
    fi
    mv -f "$tmp" "$DEST/$f"
    echo "  $f ($(wc -c < "$DEST/$f") bytes, $kind ${h:0:12} checked)"
    n=$((n + 1))
done <<< "$ENTRIES"
echo "$n files from huggingface.co/$REPO into $DEST/, each checked"
