"""models/active.json: which model each controller mode runs on the real duck, with each model file's SHA-256 so it's exact which one.

  python active_models.py              list the active models, each checked against its recorded SHA-256
  python active_models.py --update     record the SHA-256 of each active model file as it is now (after changing a model in active.json)

pi/launcher.py runs what active.json names and warns at start if a file doesn't match its SHA-256 (a copy cut off, or a different file
under the same name: a half-copied sitstand2.onnx sat on the Pi once, 2026-11-25). pi/fetch_models.sh checks every download against
Hugging Face's own SHA-256 for it.
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ACTIVE = os.path.join(HERE, 'models', 'active.json')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def load(path=ACTIVE):
    return json.load(open(path, encoding='utf-8'))


def check(mode, path=ACTIVE):
    """(model file name or None, 'ok' | 'missing' | 'mismatch' | 'unrecorded' | 'none') for one controller mode."""
    try:
        e = load(path)[mode]
    except (OSError, KeyError, ValueError):
        return None, 'none'
    m = e.get('model')
    if not m:
        return None, 'none'
    f = os.path.join(os.path.dirname(path), m)
    if not os.path.isfile(f):
        return m, 'missing'
    want = e.get('sha256')
    if not want:
        return m, 'unrecorded'
    return m, 'ok' if sha256(f) == want else 'mismatch'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--update', action='store_true', help="record each active model file's SHA-256 in active.json")
    ap.add_argument('--file', default=ACTIVE)
    a = ap.parse_args()
    act = load(a.file)
    bad = 0
    for mode, e in act.items():
        if not isinstance(e, dict):
            continue
        m = e.get('model')
        if not m:
            print(f'{mode:6s} {e.get("combo", ""):24s} no model')
            continue
        f = os.path.join(os.path.dirname(a.file), m)
        if a.update and os.path.isfile(f):
            e['sha256'] = sha256(f)
        name, st = check(mode, a.file) if not a.update else (m, 'ok' if os.path.isfile(f) else 'missing')
        bad += st not in ('ok',)
        print(f'{mode:6s} {e.get("combo", ""):24s} {m:26s} {(e.get("sha256") or "")[:12]:12s} {st}')
    if a.update:
        with open(a.file, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(act, fh, indent=1, ensure_ascii=False)
            fh.write('\n')
        print('recorded in', a.file)
    sys.exit(1 if bad and not a.update else 0)


if __name__ == '__main__':
    main()
